# telegram-disk-browser
<b>Telegram Bot for explore remote disk via python-telegram-bot api. </b> <br />

This script is interface for access to your file system on your own machine. <br />
Uses telegram-bot-api via python-telegram-bot library.<br />

Functionality:<br />
- Navigate of paths.<br />
- Selection some path(s).<br />
- Download selected.<br />
- So that's it.<br />

Requirements: <br />
- Python 3.6+ (actually didn't test it on older versions)<br />
- python-telegram-bot (pip install python-telegram-bot --upgrade)<br />
- emoji (pip install emoji --upgrade)<br />

Limits:<br />
- Max size of file for upload 50MB.<br />
- You can not do anything except what is said in the functional =\ <br />

Configure:<br />
	For normal work need a config file named as "config.json" in a same folder with this script. For create a template just run once this script. <br />
	Config file contain your "token", "home_path" and "user_id".<br />
	"token" is a token of your telegram bot (https://core.telegram.org/bots#6-botfather)<br />
	"home_path" is path of directory, what will be displayed as root (anyway you can explore on the parent folders) <br />
	"user_id" - is a user id of you telegram account. For get it just run this script another time (Will be displayed in console as when you send /start command).<br /><br />
  
  Actually this bot doesnt best solution for get access to your own remote files. It is written just for get some experience.
