#!/usr/bin/env python
# coding=utf-8

"""
# MARTAS main loggin class

## 1. INTRODUCTION

Martas.py is a basic logging class for scheduled python jobs (e.g. cron) and sending such logs to different receivers.
It contains the martaslog class and sendlog methods, which can be used to create 
logs within scheduled python scripts and deliver any occuring changes to users. Among the possible receivers, to which
logs can be delivered, are email, telegram and standard log files.

## 2. LOGGING PRINCIPLE

The logging class accepts dictionaries with key and values. The dictionary will be saved
in within a logging file at a defined path. Whenever called again, these dictionary will be loaded
and checked for changing contents in keys AND values. Any changes will be delivered to the receiver.

## 3. APPLICATION

>from martas import martaslog as ml
>martaslog = ml(logfile=logfile,receiver='email')  # other receivers: email, telegram, log, mqtt
>martaslog.email['config'] = cfg
>statusdict = {"Measurement1" : "Everything OK"}
>martaslog.msg(statusdict)

In order to use email and telegram, configuration files are requiered. These files need to
contain information like

## 4. TELEGRAM messages

Telegram messages are based on the python package telegram_send. Firstly, you need to create a telegram channel
using BotFather. From BotFather you will get the channels token. The chat_id is your account id within the Telegram network,
a nine digit code for the user sending the command. HOW TO GET THE CHAT_ID?

This information needs to be added into a configuration file. e.g. telegram.cfg:

>[telegram]
>token = xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
>chat_id = xxxx

Contents of a telegram configuration file are produced as follows: The token is established 


#### mail.cfg:

see MARTAS/conf/mail.cfg

"""

from __future__ import print_function
from __future__ import unicode_literals

# Define packges to be used (local refers to test environment) 
# ------------------------------------------------------------
import os
import glob
from datetime import datetime
import paho.mqtt.client as mqtt
import json
import socket

#import subprocess
#from subprocess import check_call
#import telepot
#from telepot.loop import MessageLoop

try:
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.base import MIMEBase
    from email.mime.text import MIMEText
    from email.utils import COMMASPACE, formatdate
    from email import encoders
    from smtplib import SMTP, SMTP_SSL
except:
    pass


def sendmail(dic):
    """
    Function for sending mails with attachments
    """

    #if not smtpserver:
    #    smtpserver = 'smtp.web.de'
    if 'Attach' in dic:
        files = map(lambda s:s.strip(), dic['Attach'].split(','))
    else:
        files = []
    if not dic['Text']:
        text = 'Cheers, Your Analysis-Robot'
    if not 'Subject' in dic:
        dic['Subject'] = 'Automatic message'
    if 'mailcred' in dic:
        ## import credential routine
        import magpy.opt.cred as cred
        #read credentials
        print ("Reading credentials")
        dic['smtpserver'] = cred.lc(dic.get('mailcred'),'smtp')
        dic['user'] = cred.lc(dic.get('mailcred'),'user')
        dic['pwd'] = cred.lc(dic.get('mailcred'),'passwd')
        #dic['port'] = cred.lc(dic.get('mailcred'),'port') ## port is currently not stored by addcred
    if 'port' in dic:
        port = int(dic['port'])
    else:
        port = None
    if 'user' in dic:
        user = dic['user']
    else:
        user = ''

    msg = MIMEMultipart()
    msg['From'] = dic['From']
    send_from = dic['From']
    #msg['To'] = COMMASPACE.join(send_to)
    msg['To'] = dic['To']
    if len(dic['To'].split(',')) > 1:
        send_to = list(map(lambda s:s.strip(), dic['To'].split(',')))
    else:
        send_to = dic.get('To').strip()
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = dic['Subject']
    msg.attach( MIMEText(dic['Text']) )

    # TODO log if file does not exist
    for f in files:
        part = MIMEBase('application', "octet-stream")
        part.set_payload( open(f,"rb").read() )
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(f))
        msg.attach(part)

    # seems as if server name needs to be specified in py3.7 and 3.8, should work in older versions as well
    if port in [465]:
        smtp = SMTP_SSL(dic.get('smtpserver'))
    else:
        smtp = SMTP(dic.get('smtpserver'))
    smtp.set_debuglevel(False)
    if port:
        smtp.connect(dic.get('smtpserver'), port)
    else:
        smtp.connect(dic.get('smtpserver'))
    smtp.ehlo()
    if port in [587]:
        print ("Using tls")
        smtp.starttls()
    smtp.ehlo()
    if user:
        smtp.login(user, dic.get('pwd'))
    smtp.sendmail(send_from, send_to, msg.as_string())
    smtp.close()


class martaslog(object):
    """
    Class for dealing with and sending out change notifications
    of acquisition and analysis states
    """
    def __init__(self, logfile='/var/log/magpy/martasstatus.log', receiver='mqtt',loglevel='1'):
        self.mqtt = {'broker':'localhost','delay':60,'port':1883,'stationid':'wic', 'client':'P1','user':None,'password':None}
        self.telegram = {'config':"/home/leon/telegramtest.conf"}
        self.email = {'config':"/etc/martas/mail.cfg"}
        self.logfile = logfile
        self.receiver = receiver
        self.hostname = socket.gethostname()
        self.loglevel = loglevel  # 1: only mark changes, don't remove non-existing inputs
                                  # 0: record all changes, remove info, which is not existing any more
        # requires json, socket etc

    def updatelog(self,logfile,logdict):
        changes={}
        if os.path.isfile(logfile):
            # read log if exists and exentually update changed information
            # return changes
            with open(logfile, 'r') as file:
                exlogdict = json.load(file)
            print ("Logfile {} loaded".format(logfile))
            for el in logdict:
                if not el in exlogdict:
                    # Adding new sensor and state
                    print ("Not Existing:", el)
                    changes[el] = logdict[el]
                else:
                    print ("Existing:", el)
                    # Checking state
                    if not logdict[el] == exlogdict[el]:
                        # state changed
                        changes[el] = logdict[el]
            ## check for element in exlogdict which are not in logdict
            for el in exlogdict:
                print ("Checking for elements in existing log too be removed")
                print ("loglevel: {}".format(self.loglevel))
                if not el in logdict:
                    if self.loglevel == '0':
                        # Sensor has been removed
                        print ("Previously existing input removed:", el)
                        changes[el] = "removed"

            if not len(changes) == 0:
                # overwrite prexsiting logfile
                print ("-------------")
                print ("Changes found")
                print ("-------------")
                with open(logfile, 'w') as file:
                    file.write(json.dumps(logdict)) # use `json.loads` to do the reverse
        else:
            # write logdict to file
            with open(logfile, 'w') as file:
                file.write(json.dumps(logdict)) # use `json.loads` to do the reverse
            print ("Logfile {} written successfully".format(logfile))

        return changes

    def msg(self, dictionary):
        changes = self.updatelog(self.logfile,dictionary)
        if len(changes) > 0:
            self.notify(changes)
        return changes


    def notify(self, dictionary):
        #if receiver == "stdout":
        print ("Changed content:", dictionary)

        if self.receiver == 'mqtt':
            stationid = self.mqtt.get('stationid')
            broker = self.mqtt.get('broker')
            mqttport = self.mqtt.get('port')
            mqttdelay = self.mqtt.get('delay')
            client = self.mqtt.get('client')
            mqttuser = self.mqtt.get('user')
            mqttpassword = self.mqtt.get('password')
            topic = "{}/{}/{}".format(stationid,"statuslog",self.hostname)
            print ("Done. Topic={},".format(topic))
            print ("Done. User={},".format(mqttuser))
            client = mqtt.Client(client)
            if not mqttuser == None:
                client.username_pw_set(username=mqttuser, password=mqttpassword)
            print (broker, mqttport, mqttdelay)
            client.connect(broker, mqttport, mqttdelay)
            client.publish(topic,json.dumps(dictionary))
            print ('Update sent to MQTT')
        elif self.receiver == 'telegram':
            #try: # import Ok
            import telegram_send
            # except: # import error
            #try: # conf file exists
            # except: # send howto
            # requires a existing configuration file for telegram_send
            # to create one use:
            # python
            # import telegram_send
            # telegram_send.configure("/path/to/my/telegram.cfg",channel=True)
            tgmsg = ''
            for elem in dictionary:
                tgmsg += "{}: {}\n".format(elem, dictionary[elem])
            telegram_send.send(messages=[tgmsg],conf=self.telegram.get('config'),parse_mode="markdown")
            print ('Update sent to telegram')
        elif self.receiver == 'email':
            mailmsg = ''
            for elem in dictionary:
                mailmsg += "{}: {}\n".format(elem, dictionary[elem])
            import acquisitionsupport as acs
            self.email = acs.GetConf(self.email.get('config'))
            #print(self.email)
            self.email['Text'] = mailmsg
            sendmail(self.email)
            print ('Update sent to email')
        elif self.receiver == 'log':
            print ('Updating logfile only')
        else:
            print ("Given receiver is not yet supported")

    def receiveroptions(self,receiver,options):
        dictionary = eval('self.{}'.format(receiver))
        for elem in options:
            dictionary[elem] = options[elem]
        print ("Dictionary {} updated".format(receiver))
     

# class martaslog():
#     def init -> logfile
#              -> change notification
#     def updatelog -> see below
#     def msg(dict) -> call updatelog
#                   -> send changes to specified output
#     def receiver(protocol,configdict) -> smtp,telegram,mqtt
#     def logfile(path) -> smtp,telegram,mqtt
#
# Application:
# from martas import martaslog as ml
# martaslog = ml(logfile=logfile,receiver='email')  # other receivers: email, telegram, log, mqtt
# martaslog.email['config'] = cfg
# statusdict = {"Measurement1" : "Everything OK"}
# martaslog.msg(statusdict)


