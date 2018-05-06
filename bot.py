import json
import logging
import telegram
import re
import zipfile
import os
from emoji import emojize
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram import InlineKeyboardButton, KeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from os import listdir, walk
from os.path import isfile, join, exists

#Запускаем логи (хз зачем)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

#Читаем конфиг
with open('config.json') as f:
	config = json.load(f)
#Список используемых ключей для callback_data
keys = {'select//', 'download//'}

def replaceKeys(text):
	'''Remove all keys from string'''
	for key in keys:
		text = text.replace(key, '')
	return text

def isKeyIn(text, _keys=keys):
	'''Проверяет есть ли любой из списка ключей в строке'''
	for k in _keys:
		if k in text:
			return True
	return False

class Path:
	'''Tracking current dir, pathlist inside, homepath'''
	def __init__(self):
		self.__path = config['home_path']
		self.__homepath = config['home_path']
		self.__pathlist = self.sortPathlist(listdir(self.__homepath))
		self.selected = []

	def get(self):
		return self.__path

	def cd(self, key):
		if isKeyIn(key) == False:
			#Очищаем список выбранных объектов
			self.selected = []
			if key == '..':
				#вырезаем родительскую папку:
				__path = self.__path[:-self.__path[::-1].find('/')-1]
			else:
				key = replaceKeys(key)
				#если ключ пустой, то слеш не добавляем:
				__path = self.__path + ('/' + key if key != '' else '') 
			if not isfile(__path) and exists(__path):
				self.__path = __path
				self.__pathlist = self.sortPathlist(listdir(self.__path))
		else:
			text = replaceKeys(key) #вырезаем из текста ключ
			key = key.replace(text, '') #вырезаем ключ из текста
			if key == 'select//':
				if text not in self.selected:
					self.selected.append(text)
				else:
					self.selected.remove(text)

	def sethome(self):
		self.__path = self.__homepath
		self.__pathlist = listdir(self.__homepath)

	def getPathList(self):
		return self.sortPathlist(self.__pathlist)

	def sortPathlist(self, pathlist):
		f, d = [], []		
		for path in pathlist:
			if isfile(self.__path + '/' + path):
				f.append(path)
			else:
				d.append(path)
		return d + f

path = Path()

def menu():
	'''Генератор кнопочного меню-списка файловой'''
	button_list = [[
		InlineKeyboardButton('...', callback_data='..'), 
		InlineKeyboardButton(emojize(':arrow_down:', use_aliases=True)+'Download', callback_data='download//')
		],]
	for p in path.getPathList():
		icon = emojize((":page_facing_up:" if isfile(path.get() +'/'+p) else ":file_folder:"), use_aliases=True)
		button_list += [[
			InlineKeyboardButton(icon+p, callback_data=p),
			InlineKeyboardButton((emojize(':radio_button:',use_aliases=True) if p in path.selected else '  ')+'Select'+('ed' if p in path.selected else ''), callback_data='select//'+p)
			],]
	reply_markup = InlineKeyboardMarkup(button_list)
	return reply_markup

def start(bot, update):
	path.sethome()
	path.selected = []
	config['chat_id']=update.message.chat_id
	bot.send_message(chat_id=config['chat_id'], text="Browse remote file system.")
	reply_markup = menu()
	bot.send_message(chat_id=update.message.chat_id,
					text=path.get().replace(config['home_path'], '')+'/',
					reply_markup=reply_markup)

def echoPathList(bot, update):
	query = update.callback_query
	path.cd(str(query.data))
	reply_markup = menu()
	new_text = path.get().replace(config['home_path'], '')+'/'
	try:
		bot.edit_message_text(text=new_text,
                          chat_id=query.message.chat_id,
                          message_id=query.message.message_id,
                          reply_markup=reply_markup)
	except:
		print('Message is not modified')

def download(bot, update):
	if len(path.selected)>0:
		print('Uploading archive!')
		z = zipfile.ZipFile("download.zip", "w")

		for p in path.selected:
			if isfile(path.get() + '/' + p):
				z.write(path.get() + '/' + p, p)
			else:
				for root, dirs, files in os.walk(path.get() + '/' + p):
					for file in files:
						z.write(os.path.join(root, file), os.path.join(root, file).replace(path.get(), ''))
					if listdir(root) == []:
						z.write(root, root.replace(path.get(), ''))
		
		z.close()
		z.printdir()
		try:
			bot.send_document(chat_id=config['chat_id'], document=open('download.zip', 'rb'))
		except:
			print('Cant upload file. Maybe, zip file larger of 50 MB?')
		os.remove('download.zip')

def main():
	updater = Updater(token=config['token'])
	dispatcher = updater.dispatcher

	dispatcher.add_handler(CommandHandler('start', start))
	#pattern='^((?!download//).)*$' - строка, которае не содержит "download//"
	dispatcher.add_handler(CallbackQueryHandler(echoPathList, pattern='^((?!download//).)*$'))
	dispatcher.add_handler(CallbackQueryHandler(download, pattern=r'^download//.*?'))

	# Start the Bot
	updater.start_polling()
	# Run the bot until the user presses Ctrl-C or the process receives SIGINT,
	# SIGTERM or SIGABRT
	updater.idle()

if __name__ == '__main__':
	main()