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
	For normal work need a config file named as "config.json" in a same folder whith this script. For create a template just run once this script. 
	Config file contain yor "token", "home_path" and "user_id".
	"token" is a token of your telegram bot (https://core.telegram.org/bots#6-botfather)
	"home_path" is path of directory, what will be displayed as root (any way you can explore on the parent folders) 
	"user_id" - is a user id of you telegram account. For get it just run this script another time (Will be displeyed in console). 
'''

import json
import telegram
import re
import zipfile
import os
import sys
import logging
from emoji import emojize
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, KeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

class Config(object):
	'''Class-container for configuration data'''

	def __init__(self, config_file):
		self.__keys = ['token', 'home_path', 'user_id']
		self.config_file = config_file
		self.chat_id = None
		#Check for exist configuration file:
		if os.path.exists(config_file) and os.path.isfile(config_file):
			with open(config_file) as file: 
				try:
					config = json.load(file) #decode json config file
				except:
					print('Error while read json file. Try to setup your config file with name "config.json"')


			#Setup config data as attributes
			detail_list = []
			try:
				self.token = config['token']
			except KeyError as detail:
				detail_list.append(detail)
				self.token = None
			try:
				self.home_path = config['home_path']
			except KeyError as detail:
				detail_list.append(detail)
				self.home_path = None
			try:
				self.user_id = config['user_id']
			except KeyError as detail:
				detail_list.append(detail)
				self.user_id = None
			if len(detail_list):
				print('Does not set up configuration parameter(s):', detail_list)
		else:
			config_template = '{\n'
			for key in self.__keys:
				#config_template += f'\t"{key}": "Your {key} here with quotes"' + (',\n' if key!=self.__keys[-1] else '')
				config_template += '\t"{0}": "Your {0} here with quotes"'.format(key) + (',\n' if key!=self.__keys[-1] else '')
			config_template += '\n}'
			with open(self.config_file, 'w') as file:
				file.write(config_template)
			sys.exit()

class Disk(object):
	'''Tracking current folder, dirlist inside current folder and home path'''

	#setting up properties
	#main property: "path"
	#slave properties: "relpathlist", "pathlist" and "selected"
	#They are changed whenever main property is changed

	@property #main property
	def path(self): #path - current path
		return self.__path

	@path.setter
	def path(self, new_path): 
		if self.__path != new_path and os.path.exists(new_path):
			self.updatepath(new_path)

	@property
	def relpathlist(self): #list of paths relative of current path
		return self.__relpathlist
	
	@property 
	def pathlist(self): #list of absolute paths in current path
		return self.__pathlist

	@property
	def curindx(self): #current start index of pathlist what displayed right now 
		return self.__curindx

	@curindx.setter
	def curindx(self, new_indx):
		self.__curindx = new_indx

	@property
	def selected(self): #list of selected paths by user (cleared when changing path)
		return self.__selected

	@property
	def sizeofselected(self): #sum size of selected path list in bytes
		return self.__sizeofselected	

	@property #keys is another property what transmit private "__keys" attribute.
	def keys(self): #list of keys using for callback data 
		return self.__keys

	#INIT:
	def __init__(self, config):
		self.__keys = {'select//', 'download//'}
		self.updatepath(config.home_path)

	def updatepath(self, value):
		self.__path = value
		self.__pathlist = self.sortpathlist([os.path.join(self.__path, path) for path in os.listdir(self.__path)])
		self.__relpathlist = [path.split('/')[-1] for path in self.__pathlist]
		self.__selected = [] #clear up list of selected path whenever "__path" property changed
		self.__sizeofselected = 0
		self.__curindx = 0

	def worker(self, key):
		if '//' in key:
			#split key and data
			data = key.split('//')[-1]

			if 'select//' in key: 
				#Key 'select//' used as trigger:	
				#If data not exist in selected list - it will add to them,
				#else will be removed
				if os.path.join(self.path, data) not in self.selected:
					self.selected.append(os.path.join(self.path, data))
				else:
					self.selected.remove(os.path.join(self.path, data))
				self.__sizeofselected = sum([self.getsize(path) for path in self.selected ])

			if 'up//' in key:
				self.curindx -= int(key.split('//')[-1]) 
				if self.curindx <= 0:
					self.curindx = 0

			if 'down//' in key:
				self.curindx += int(key.split('//')[-1]) 

		else: #use like 'change directory' function
			if key == '..': #means change dir to parent
				self.path = self.path[:-self.path[::-1].find('/')-1]
			else:
				if not os.path.isfile(os.path.join(self.path, key)):
					self.path = os.path.join(self.path, key)

	def sethome(self):
		'''Restore current path to home path'''
		self.path = config.home_path

	############################## Tools: ##############################

	def sortpathlist(self, pathlist):
		'''Sort path list of  template: sorted dirs + sorted files'''
		d, f = [], [] #dirs, files list
		for path in pathlist:
			if os.path.isfile(path):
				f.append(path) 
			else:
				d.append(path)
		return sorted(d) + sorted(f)

	def replacekeys(text):
		'''Remove all keys from string'''
		for key in self.keys:
			text = text.replace(key, '')
		return text

	def getsize(self, start_path):
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
	'''Generator button menu of path list'''
	menu_size = 10

	button_list = [[
		InlineKeyboardButton('...', callback_data='..'), 
		InlineKeyboardButton(emojize(':arrow_down:', use_aliases=True)+'Download', callback_data='download//')
		]]
	for path, relpath, it in list(zip(
			disk.pathlist[disk.curindx:disk.curindx+menu_size+1], 
			disk.relpathlist[disk.curindx:disk.curindx+menu_size+1],
			range(disk.curindx, len(disk.pathlist))
			)):
		if it < disk.curindx+menu_size:
			icon = emojize((":page_facing_up:" if os.path.isfile(path) else ":file_folder:"), use_aliases=True)
			button_list += [[
				InlineKeyboardButton(icon+relpath, callback_data=relpath),
				InlineKeyboardButton((emojize(':radio_button:',use_aliases=True) if path in disk.selected else '  ')+'Select'+('ed' if path in disk.selected else ''), callback_data='select//'+relpath)
				]]
		else:
			#if list of path more then 10 item just add a new button for walk on a folder
			button_list += [[
			InlineKeyboardButton('...', callback_data='down//{0}'.format(menu_size)), 
			]]
			break
	if disk.curindx > 0:
		button_list.insert(1, [
			InlineKeyboardButton('...', callback_data='up//{0}'.format(menu_size))
			])
	reply_markup = InlineKeyboardMarkup(button_list)
	return reply_markup

def start(bot, update):
	user_id = update.message.from_user.id

	#Check user as owner:
	if str(user_id) != config.user_id:
		print('Some user trying get access to the bot. Permission denied')
		print(update.message.from_user)
	else:
		'''Function calls when /start command was type by user'''
		print('Accessing user', update.message.from_user)
		#set home folder:
		disk.sethome()
		#save chat id to config data:
		config.chat_id=update.message.chat_id
		#Send 'about' message:
		bot.send_message(chat_id=config.chat_id, text="Browse remote file system.")
		
		#generate menu of buttons
		reply_markup = menu()
		#send it as message
		bot.send_message(chat_id=config.chat_id,
						text='path:'+disk.path.replace(config.home_path, '')+'/',
						reply_markup=reply_markup)

def echoPathList(bot, update):
	query = update.callback_query

	disk.worker(query.data)
	reply_markup = menu()

	#generate str with size of selected files and dirs
	size_str = disk.sizeofselected
	size_res = ['B', 'KB', 'MB', 'GB', 'TB']
	for it, res in enumerate(size_res):
		if size_str/1024 < 1:
			size_str = '~'+str(round(size_str, 0)) + res
			break
		else:
			if it == len(size_res):
				size_str = '~'+str(round(size_str, 0)) + res
			else:
				size_str /= 1024

	text_message = 'path:'+disk.path.replace(config.home_path, '')+'/'+('\nSelected:' + size_str if len(disk.selected) >  0 else '') #add generated str to text of message
	print(query.message.text, text_message)
	try:
		bot.edit_message_text(text=text_message,
                          chat_id=config.chat_id,
                          message_id=query.message.message_id,
                          reply_markup=reply_markup)
	except:
		print('Message is not modified')

def download(bot, update):
	if len(disk.selected)>0:
		if len(disk.selected) == 1:
			zip_name = disk.selected[0].split('/')[-1]
		else:
			zip_name = disk.path.split('/')[-1]
		zip_name = '{}.zip'.format(zip_name)

		if sum(map(os.path.getsize, disk.selected))/1024**2 > 49:
			print(sum(map(os.path.getsize, disk.selected))/1024**2)
			print('Cant uploading files. Overlimit 50MB')
		else:
			#creatting archive
			print('Creating archive...')
			z = zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED)

			for path in disk.selected:
				if os.path.isfile(path):
					z.write(path, os.path.relpath(path, disk.path))
				else:
					for root, dirs, files in os.walk(path):
						for file in files:
							z.write(os.path.join(root, file), os.path.join(root, file).replace(disk.path, ''))
						if os.listdir(root) == []:
							z.write(root, os.path.relpath(root, disk.path))

			print('Uploading file(s)...')
			z.close()
			z.printdir()
			try:
				bot.send_document(chat_id=config.chat_id, document=open(zip_name, 'rb'))
			except:
				print('Cant upload file. Maybe, zip file larger of 50 MB?')
			os.remove(zip_name)
	
if __name__ == '__main__':
	config = Config(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json'))
	disk = Disk(config)

	updater = Updater(token=config.token)
	dispatcher = updater.dispatcher

	dispatcher.add_handler(CommandHandler('start', start))
	#pattern='^((?!download//).)*$' - patern excluding "download//"
	dispatcher.add_handler(CallbackQueryHandler(echoPathList, pattern='^((?!download//).)*$'))
	dispatcher.add_handler(CallbackQueryHandler(download, pattern=r'^download//.*?'))

	# Start the Bot
	updater.start_polling()
	# Run the bot until the user presses Ctrl-C or the process receives SIGINT,
	# SIGTERM or SIGABRT
	updater.idle()