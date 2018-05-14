#!/usr/bin/env python3
#telegrem-disk-browser via telegram bot

'''
This script is interface for access to your file system on your own machine. 
Uses telegram-bot-api via python-telegram-bot library.

Requirements:
	Python 3.6+
	python-telegram-bot (pip install python-telegram-bot --upgrade)
	emoji (pip install emoji --upgrade)

Limits:
	Max size of file for upload 50MB.

Configure:
	For normal work need a config file named as "config.json" in a same folder 
	whith this script. For create a template just run once this script. 
	Config file contain your "token", "home_path" and "user_id".

	"token" is a token of your telegram bot 
		(https://core.telegram.org/bots#6-botfather)

	"home_path" is path of directory, what will be displayed as root (any way 
	you can explore on the parent folders) 

	"user_id" - is a user id of you telegram account. For get it just run this 
	script another time (Will be displeyed in console). 

'''

import os
import sys
import json
import zipfile
import logging

import telegram
from emoji import emojize
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, KeyboardButton, \
	InlineKeyboardMarkup, ReplyKeyboardMarkup

logging.basicConfig(
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
	level=logging.INFO
	)
logger = logging.getLogger(__name__)


class Config(object):
	'''Class-container for configuration data.

	'''

	@property
	def token(self):
		return self.__token

	@property
	def home_path(self):
		return self.__home_path

	@property
	def user_id(self):
		return self.__user_id

	def __init__(self, config_file):

		self.__keys = ['token', 'home_path', 'user_id']
		self.config_file = config_file
		self.chat_id = None

		# Check for exist configuration file.
		if os.path.exists(config_file) and os.path.isfile(config_file):
			# Read config file.
			with open(config_file) as file: 
				try:
					config = json.load(file)
				except:
					print('Error while read "config.json"')

			# Setup config data as attributes.
			try:
				self.__token = config['token']
			except KeyError as detail:
				# Stop program if token doesn't setup.
				sys.exit(self._key_error_message(detail))
			try:
				self.__home_path = config['home_path']
			except KeyError as detail:
				sys.exit(self._key_error_message(detail))					
			else:
				if not os.path.exists(config['home_path']):
					sys.exit("OSError: home path {} doesn't exist"
						.format(config['home_path']))
			try:
				self.__user_id = config['user_id']
			except KeyError as detail:
				print(self._key_error_message(detail))
				print("Try to send /start command to chat of bot.")

		else:
			# Creating template of config file.
			config_template = ""

			for key in self.__keys:
				config_template.join('\t"{0}": "Your {} with quotes"'
					.format(key) + (',\n' if key!=self.__keys[-1] else '')) 

			config_template = "{\n" + config_template + "\n}"

			with open(self.config_file, 'w') as file:
				file.write(config_template)

			sys.exit("{} doesn't exist. Created a template."
				.format(self.config_file))

	
	def _key_error_message(self, detail):
		return "{}: {} doesn't exist in {}.".format(type(detail).__name__, 
			detail.args[0], self.config_file)	


class Disk(object):
	'''Tracking current folder, dirlist inside current folder and home path

	'''

	# Setting up properties.
	# Main property: "path".
	# Slave properties: "relpathlist", "pathlist" and "selected".
	# They are changed whenever main property is changed.

	@property
	def path(self): # path - current path.
		return self.__path

	@path.setter
	def path(self, new_path):
		if os.path.exists(new_path):

			try:
				if self.__path != new_path or new_path == config.home_path:
					update = True
				else:
					update = False
			
			except AttributeError:  # Means what "__path" attribute not created.
				update = True
			
			if update:
				self.__path = new_path
				self.__relpathlist = self._sort_path_list(os.listdir(self.__path))
				self.__pathlist = [os.path.join(self.__path, relpath) 
						for relpath in self.__relpathlist]
				# Clear up list of selected path whenever "__path" property is 
				# changed.
				self.__selected = [] 
				self.__sizeofselected = 0
				self.__cursor = 0

		else:
			raise OSError("While change 'path' given wrong value.\n"\
				"Path: {} doesn't exists".format(new_path))


	@property
	def relpathlist(self): # List of paths relative of current path.
		return self.__relpathlist
	
	@property 
	def pathlist(self): # List of absolute paths in current path.
		return self.__pathlist

	@property
	def cursor(self): # Current start index of pathlist.
		return self.__cursor

	@cursor.setter
	def cursor(self, new_indx):
		self.__cursor = new_indx

	@property
	def selected(self): # List of selected paths by user.
		return self.__selected

	@property
	def sizeofselected(self): # Total size of selected pathlist (in bytes).
		return self.__sizeofselected	


	def __init__(self, config):
		self.path = config.home_path


	def worker(self, key):
		'''Function for interact with callback data from CallbackQueryHandler

		'''
		value = key.split('//')[-1]

		if 'select//' in key: 
			# Key 'select//' used as trigger for select path.

			# Select path name from key ("key//path_name").
			path_name = self.relpathlist[int(value)]

			# If path_name not exist in selected list it will add to them,
			# else will be removed
			if os.path.join(self.path, path_name) not in self.selected:
				self.selected.append(os.path.join(self.path, path_name))
			else:
				self.selected.remove(os.path.join(self.path, path_name))
			self.__sizeofselected = sum([self._get_size(path)
					for path in self.selected])

		elif 'up//' in key:
			# Key 'up//' used for decrease cursor in pathlist.
			# Means moving up on pathlist. 
			self.cursor -= int(key.split('//')[-1]) 
			if self.cursor <= 0:
				self.cursor = 0

		elif 'down//' in key:
			# Key 'down//' used for decrease cursor in pathlist.
			# Means moving diwn on pathlist. 
			self.cursor += int(key.split('//')[-1]) 

		elif 'cd//' in key:
			# Means action to change directory. 

			if value == '..': # Means change dir to parent dir.
				self.path = self.path[:-self.path[::-1].find('/')-1]

			else: # Just move down to the path_name
				path_name = self.relpathlist[int(value)]
				if not os.path.isfile(os.path.join(self.path, path_name)):
					self.path = os.path.join(self.path, path_name)
				else:
					# If value is a file name (not dir) return False
					# Means message wasn't changed.
					return False

		return True

	def set_home(self):
		'''Set current path to home path'''
		self.path = config.home_path

	def _update_path(self, value):
		self.__path = value
		self.__pathlist = self._sort_path_list([os.path.join(self.__path, path)  
				for path in os.listdir(self.__path)])

		self.__relpathlist = [path.split('/')[-1] for path in self.__pathlist]
		# Clear up list of selected path whenever "__path" property changed.
		self.__selected = [] 
		self.__sizeofselected = 0
		self.__cursor = 0

	def _sort_path_list(self, pathlist):
		'''Sort path list of  template: sorted dirs + sorted files'''
		d, f = [], [] #dirs, files list
		for path in pathlist:
			if os.path.isfile(path):
				f.append(path) 
			else:
				d.append(path)
		return sorted(d) + sorted(f)

	def _get_size(self, start_path):
		total_size = 0
		if os.path.isfile(start_path):
			total_size += os.path.getsize(start_path)
		else:
			for dirpath, dirnames, filenames in os.walk(start_path):
				for f in filenames:
					fp = os.path.join(dirpath, f)
					total_size += os.path.getsize(fp)
		return total_size

def menu():
	'''Generate button menu of path list

	'''
	# Max paths count in buttons menu.
	menu_size = 10

	# The dict of emoji icons.
	icons = {
		'file' : emojize(':page_facing_up:', use_aliases=True),
		'folder' : emojize(':file_folder:', use_aliases=True),
		'radio_button' : emojize(':radio_button:',use_aliases=True),
		'download' : emojize(':arrow_down:', use_aliases=True)
	}

	# The list of buttons starts from:
	# 'move back' button
	# 'download' button
	button_list = [[
		InlineKeyboardButton('...', callback_data='cd//..'), 
		InlineKeyboardButton(icons['download'] + 'Download', 
							callback_data='upload//')
		]]

	# Start and end indexes of path list for current menu.
	from_, to_ = disk.cursor, disk.cursor + menu_size + 1

	for path, relpath, it in list(zip(
			disk.pathlist[from_:to_], 
			disk.relpathlist[from_:to_],
			range(disk.cursor, len(disk.pathlist))
			)):
		if it < disk.cursor + menu_size:
			icon = icons['file'] if os.path.isfile(path) else icons['folder']
			relpath_index = str(disk.relpathlist.index(relpath))
			button_list += [[
				InlineKeyboardButton(
					(icons['file'] if os.path.isfile(path) 
						else icons['folder']) +	relpath, 
					callback_data='cd//' + relpath_index),		
				InlineKeyboardButton(
					(icons['radio_button'] if path in disk.selected else '') + 
						'Select' + ('ed' if path in disk.selected else ''), 
					callback_data='select//' + relpath_index)
				]]
		else:
			# If list of path more then 10 item put on the end a new 
			# "move down" button.

			button_list += [[
			InlineKeyboardButton('...', 
				callback_data='down//{0}'.format(menu_size)), 
			]]
			break

	# If cursor of list was changed insert a new "move up" button.
	if disk.cursor > 0:
		button_list.insert(1, [
			InlineKeyboardButton('...', 
				callback_data='up//{0}'.format(menu_size))
			])

	reply_markup = InlineKeyboardMarkup(button_list)
	return reply_markup

def start(bot, update):
	'''Function calls when /start command was type by user

	'''
	user_data = update.message.from_user

	#Check user as owner:
	if str(user_data.id) != str(config.user_id):
		print("Unknown user {} trying intercept with a bot. Permission denied"
			.format(user_data.username))
		print("User data:", user_data)
	else:
		print("Connected owner")
		# Set home folder as current path.
		disk.set_home()
		# Save chat id into config data.
		config.chat_id=update.message.chat_id
		# Send 'about' message.
		bot.send_message(chat_id=config.chat_id, 
						text="Browse remote file system.")
		
		# Generate menu of buttons.
		reply_markup = menu()
		# Send buttons menu as message.
		bot.send_message(
			chat_id=config.chat_id,
			text='path:' + disk.path.replace(config.home_path, '') + '/',
			reply_markup=reply_markup)

def echoPathList(bot, update):
	query = update.callback_query

	# Run worker with last callback data. 
	# worker function return boolean value:
	# True if message need to update. Else False.
	if disk.worker(query.data):
	# Generate menu.
		reply_markup = menu()

		# Generate string with size of selected files and dirs.
		size_str = disk.sizeofselected
		size_res = ['B', 'KB', 'MB', 'GB']
		for it, res in enumerate(size_res):
			if size_str / 1024 < 1:
				size_str = '~' + str(round(size_str, 0)) + res
				break
			else:
				if it == len(size_res):
					size_str = '~' + str(round(size_str, 0)) + res
				else:
					size_str /= 1024

		text_message = 'path:' + disk.path.replace(config.home_path, '') + '/'\
			+ ('\nSelected:' + size_str if len(disk.selected) >  0 else '')
		bot.edit_message_text(text=text_message,
	                          chat_id=config.chat_id,
	                          message_id=query.message.message_id,
	                          reply_markup=reply_markup)
	else:
		print('Message is not modified')

def upload(bot, update):
	if len(disk.selected) > 0:
		if len(disk.selected) == 1:
			zip_name = disk.selected[0].split('/')[-1]
		else:
			zip_name = disk.path.split('/')[-1]
		zip_name = '{}.zip'.format(zip_name)

		if sum(map(os.path.getsize, disk.selected))/1024**2 > 49:
			print(sum(map(os.path.getsize, disk.selected))/1024**2)
			print("Cant uploading files. Overlimit 50MB")

		# Creatting archive.
		print("Creating archive...")
		z = zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED)

		for path in disk.selected:
			if os.path.isfile(path):
				z.write(path, os.path.relpath(path, disk.path))
			else:
				for root, dirs, files in os.walk(path):
					for file in files:
						z.write(os.path.join(root, file), 
							os.path.join(root, file).replace(disk.path, ''))
					if os.listdir(root) == []:
						z.write(root, os.path.relpath(root, disk.path))
		z.close()

		zip_size = os.path.getsize(zip_name) /1000**2
		# Try to send file if he does not larger of 50 MB.
		try:

			if zip_size <= 50:
				print('Zip size {}'.format(zip_size))
				print('Uploading file(s)...')
				bot.send_document(chat_id=config.chat_id, 
								document=open(zip_name, 'rb'))
			else:
				print("Can't upload file. Zipfile larger of 50 MB: {}"
					.format(zip_size))
		except:
			print('Cant upload file. Maybe, zip file larger of 50 MB?')
		finally:
			os.remove(zip_name)
	
if __name__ == '__main__':
	# Send absolute path of config file.
	config = Config(os.path.join(os.path.dirname(os.path.abspath(__file__)), 
					'config.json'))
	disk = Disk(config)

	updater = Updater(token=config.token)
	dispatcher = updater.dispatcher

	dispatcher.add_handler(CommandHandler('start', start))
	# '^((?!upload//).)*$' - patern excluding "upload//"
	dispatcher.add_handler(CallbackQueryHandler(echoPathList,
							pattern='^((?!upload//).)*$'))
	dispatcher.add_handler(CallbackQueryHandler(upload,
							pattern=r'^upload//.*?'))

	# Start the Bot
	updater.start_polling()
	# Run the bot until the user presses Ctrl-C or the process receives SIGINT,
	# SIGTERM or SIGABRT
	updater.idle()