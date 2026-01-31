
#!/usr/bin/env python
# coding=utf-8

"""
MagPy - telegram bot interaction
################################

Package requirements:
pip install geomagpy (>= 0.3.99)
pip install telepot (>= )

Optional python packages:
pip install psutil    # status memory, cpu
pip install platform  # system definitions

Optional linux packages
sudo apt-get install fswebcam   # getting cam pictures

Optional for remote ssh link opening:
install tmate version >= 2.4

add cronstop to regularly restart the bot (root)
sudo crontab -e
PATH=/bin/sh
0  6  *  *  *  /etc/init.d/telegrambot restart > /dev/NULL 2&>1
0  14  *  *  *  /etc/init.d/telegrambot restart > /dev/NULL 2&>1
0  22  *  *  *  /etc/init.d/telegrambot restart > /dev/NULL 2&>1


# ADD Option to locate configuration file

Tool for interaction with remote systems:
Commands: external stations: - status, getlog (amount of lines), martas (restart martas), healthstate (disk status, processor), type

Commands: cobs:              - checkDB, get nagios infi

"""

from martas.core.message import ActionHandler

# Define packages to be used (local refers to test environment)
# ------------------------------------------------------------
import telepot
from telepot.loop import MessageLoop
import logging
import os
import urllib3
import time


def setuplogger(name='telegrambot',loglevel='DEBUG',path='stdout'):

    logpath = None
    try:
        level = eval("logging.{}".format(loglevel))
    except:
        level = logging.DEBUG
    if not path in ['sys.stdout','stdout']:
        logpath = path
    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s : %(message)s',
                              "%Y-%m-%d %H:%M:%S")

    logger = logging.getLogger(name)
    logger.setLevel(level)
    if logpath:
        print ("telegrambot: Creating log file")
        # create file handler which logs even debug messages
        fh = logging.FileHandler(logpath)
        fh.setLevel(level)
        # create console handler with a higher log level
        ch = logging.StreamHandler()
        ch.setLevel(logging.ERROR)
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        logger.addHandler(fh)
        logger.addHandler(ch)
    else:
        print ("telegrambot: logging to stdout")
        ch = logging.StreamHandler()
        ch.setLevel(level)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    return logger


mainpath = os.path.dirname(os.path.realpath(__file__))
telegramcfgpath = os.path.join(mainpath,"..","conf","telegrambot.cfg")
ah = ActionHandler(configpath=telegramcfgpath, commands=None)

tglogger = setuplogger(name='telegrambot',loglevel=ah.configuration.get('loglevel'),path=ah.configuration.get('bot_logging').strip())

proxy = ah.configuration.get('proxy','').strip()
proxyport = ah.configuration.get('proxyport','').strip()

if proxy:
    print (" found proxy")
    proxy_url="http://{}:{}".format(proxy,proxyport)
    telepot.api._pools = {'default': urllib3.ProxyManager(proxy_url=proxy_url, num_pools=3, maxsize=10, retries=False, timeout=30),}
    telepot.api._onetime_pool_spec = (urllib3.ProxyManager, dict(proxy_url=proxy_url, num_pools=1, maxsize=1, retries=False, timeout=30))
    print (" ... established to {}".format(proxy_url))

    # Extract command lists


def handle(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    tglogger.info("Bot -> ContentType: {}; ChatType: {}".format(content_type, chat_type))
    firstname = msg['from']['first_name']
    userid = msg['from']['id']
    ah.messageconfig['firstname'] = firstname

    chat_id = msg['chat']['id']
    command = msg['text'].replace('/','')

    if not str(chat_id) in ah.configuration.get('allowed_users'):
        bot.sendMessage(chat_id, "My mother told me not to speak to strangers, sorry...")
        tglogger.warning('--------------------- Unauthorized access -------------------------')
        tglogger.warning('!!! unauthorized access attempt ({}) from ChatID {} (User: {}) !!!'.format(command,chat_id,firstname))
        tglogger.warning('-------------------------------------------------------------------')
    else:
        if content_type == 'text':
            tglogger.info('Received command "{}" from ChatID {} (User: {})'.format(command,chat_id,firstname))
            al = ah.interpret(command)
            message = ah.execute_action(al, input=command, debug=True)
            for com in message:
                cc = message.get(com)
                comcontent = cc.get('message')
                text = comcontent.get("text","")
                calls = comcontent.get("call",[])
                pics = comcontent.get("pictures",[])
                for call in calls:
                    print ("executing call", call)
                    text += ah.execute_call(call)
                    if 'fswebcam' in call:
                        pics.append('/tmp/webimage.jpg')
                if text:
                    bot.sendMessage(chat_id, text, parse_mode='Markdown')
                for pic in pics:
                    if os.path.isfile(pic):
                        bot.sendPhoto(chat_id, open(pic,'rb'))

bot = telepot.Bot(ah.configuration.get('bot_id'))
MessageLoop(bot, handle).run_as_thread()
tglogger.info('Listening ...')

# Keep the program running.
while 1:
    try:
        time.sleep(10)
    except KeyboardInterrupt:
        tglogger.info('\n Program interrupted')
        exit()
    except:
        tglogger.error('Other error or exception occurred!')
