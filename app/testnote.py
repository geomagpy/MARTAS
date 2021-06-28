#!/usr/bin/env python
# coding=utf-8

"""
Testing notifications
"""

from magpy.stream import *

scriptpath = os.path.dirname(os.path.realpath(__file__))
coredir = os.path.abspath(os.path.join(scriptpath, '..', 'core'))
sys.path.insert(0, coredir)
from martas import martaslog as ml
from martas import sendmail as sm

import telegram_send
import os
import getopt


# Basic MARTAS Telegram logging configuration for IMBOT manager


def main(argv):
    notificationtype = 'telegram'
    configpath = '/etc/martas/telegram.cfg'
    message = ''
    name = "TestMessage"
    logpath = '/var/log/magpy/testmessage.log'
    note = {}
    debug = False

    try:
        opts, args = getopt.getopt(argv,"hn:m:c:l:p:D",["notificationtype=","message=","logname=","logpath=","debug=",])
    except getopt.GetoptError:
        print ('testnote.py -n <notificationtype> -m <message> -c <configpath> -l <logname> -p <logpath>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print ('-------------------------------------')
            print ('Description:')
            print ('-- testnote.py will send a note to the specificied notification channel --')
            print ('-----------------------------------------------------------------')
            print ('testnote is a python3 program to send')
            print ('a note.')
            print ('')
            print ('-------------------------------------')
            print ('Usage:')
            print ('python3 testnote.py -n <notificationtype> -m <message>')
            print ('-------------------------------------')
            print ('Options:')
            print ('-m            : path for telegram configuration file')
            print ('-n            : email, telegram or log')
            print ('-c            : configuration path')
            print ('-l            : logname')
            print ('-p            : logpath')
            print ('-------------------------------------')
            print ('Example of memory:')
            print ('-------------------------------------')
            print ('Application:')
            print ('python3 testnote.py -n email -m "Hello World" -c /etc/martas/mail.cfg -l TestMessage -p /home/user/test.log')
            print ('python3 testnote.py -n telegram -m "Hello World, I am here" -c /etc/martas/telegram.cfg -l TestMessage -p /home/leon/test.log')
            print ('python3 testnote.py -n log -m "Hello World again" -l TestMessage -p /home/leon/test.log')
            sys.exit()
        elif opt in ("-n", "--notifictaiontype"):
            notificationtype = arg
        elif opt in ("-m", "--message"):
            message = arg
        elif opt in ("-c", "--configpath"):
            configpath = os.path.abspath(arg)
        elif opt in ("-l", "--logname"):
            name = arg
        elif opt in ("-p", "--logpath"):
            logpath = os.path.abspath(arg)
        elif opt in ("-D", "--debug"):
            debug = True

    if debug:
        print ("Basic code test OK")
        sys.exit(0)
        
    if not notificationtype in ['email','telegram','log']:
        print ("Notification type not supported. Needs to be one of email, telegram, log")
        sys.exit()

    note[name] = message 

    martaslog = ml(logfile=logpath,receiver=notificationtype)
    martaslog.telegram['config'] = configpath
    martaslog.email['config'] = configpath
    martaslog.msg(note)


if __name__ == "__main__":
   main(sys.argv[1:])

