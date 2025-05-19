#!/usr/bin/env python
# coding=utf-8

from magpy.core import database
from magpy.core import methods
from magpy.opt import cred as cred
import os
import sys
import glob
from datetime import datetime
import paho.mqtt.client as mqtt
import json
import socket
import configparser
import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import formatdate
from email import encoders


"""
Methods:

| class           |  method  |  version |  tested  |              comment             | manual | *used by |
| --------------- |  ------  |  ------- |  ------- |  ------------------------------- | ------ | ---------- |
|  **martaslog**  |          |          |          |                                  |        |            |
|  martaslog      |          |  2.0.0   |          |                                  | -      |            |
|  martaslog      |          |  2.0.0   |          |                                  | 5.2     | |
|  **basic**      |            |  2.0.0 |     yes  |                                  | 5.1     | |
|                 |  get_conf  |  2.0.0 |     -  |                                  | -       | marcosscripts |
|                 |  sendmail  |  2.0.0 |     -  |  identical method in imbot       | -       | imbot |
|                 |  sendtelegram |  2.0.0  | -  |  identical method in imbot       | 5.1     | marcosscripts, imbot |

"""

SENSORELEMENTS =  ['sensorid','port','baudrate','bytesize','stopbits', 'parity','mode','init','rate','stack','protocol','name','serialnumber','revision','path','pierid','ptime','sensorgroup','sensordesc']

def get_conf(path, confdict=None):
    """
    Version 2020-10-28
    DESCRIPTION:
       can read a text configuration file and extract lists and dictionaries
    VARIBALES:
       path             Obvious
       confdict         provide default values
    SUPPORTED:
       key   :    stringvalue                                 # extracted as { key: str(value) }
       key   :    intvalue                                    # extracted as { key: int(value) }
       key   :    item1,item2,item3                           # extracted as { key: [item1,item2,item3] }
       key   :    subkey1:value1;subkey2:value2               # extracted as { key: {subkey1:value1,subkey2:value2} }
       key   :    subkey1:value1;subkey2:item1,item2,item3    # extracted as { key: {subkey1:value1,subkey2:[item1...]} }
    """
    exceptionlist = ['bot_id']
    if not confdict:
        confdict = {}

    try:
        #config = open(path,'r')
        with open(path, 'r') as config:
            confs = config.readlines()
            for conf in confs:
                conflst = conf.split(':')
                if conflst[0].strip() in exceptionlist or methods.is_number(conflst[0].strip()):
                    # define a list where : occurs in the value and is not a dictionary indicator
                    conflst = conf.split(':',1)
                if conf.startswith('#'):
                    continue
                elif conf.isspace():
                    continue
                elif len(conflst) == 2:
                    conflst = conf.split(':',1)
                    key = conflst[0].strip()
                    value = conflst[1].strip()
                    # Lists
                    if value.find(',') > -1:
                        value = value.split(',')
                        value = [el.strip() for el  in value]
                    try:
                        confdict[key] = int(value)
                    except:
                        confdict[key] = value
                elif len(conflst) > 2:
                    # Dictionaries
                    if conf.find(';') > -1 or len(conflst) == 3:
                        ele = conf.split(';')
                        main = ele[0].split(':')[0].strip()
                        cont = {}
                        for el in ele:
                            pair = el.split(':')
                            # Lists
                            subvalue = pair[-1].strip()
                            if subvalue.find(',') > -1:
                                subvalue = subvalue.split(',')
                                subvalue = [el.strip() for el  in subvalue]
                            try:
                                cont[pair[-2].strip()] = int(subvalue)
                            except:
                                cont[pair[-2].strip()] = subvalue
                        confdict[main] = cont
                    else:
                        print ("Subdictionary expected - but no ; as element divider found")
    except:
        print ("Problems when loading conf data from file. Using defaults")

    return confdict


def get_sensors(path, identifier=None, secondidentifier=None):
    """
    DESCRIPTION:
        read sensor information from a file
        Now: just define them by hand
    PATH:
        sensors.cfg or sensors.json
    CONTENT:
        # sensors.cfg contains specific information for each attached sensor
        # ###################################################################
        # Information which need to be provided comprise:
        # sensorid: an unique identifier for the specfic sensor consiting of SensorName,
        #           its serial number and a revision number (e.g. GSM90_12345_0001)
        # connection: e.g. the port to which the instument is connected (USB0, S1, ACM0, DB-mydb)
        # serial specifications: baudrate, bytesize, etc
        # sensor mode: passive (sensor is broadcasting data by itself)
        #              active (sensor is sending data upon request)
        # initialization info:
        #              None (passive sensor broadcasting data without initialization)
        #              [parameter] (passive sensor with initial init e.g. GSM90,POS1)
        #              [parameter] (active sensor, specific call parameters and wait time)
        # protocol:
        #
        # optional sensor description:
        #
        # each line contains the following information
        # sensorid port baudrate bytesize stopbits parity mode init protocol sensor_description
        #e.g. ENV05_2_0001;USB0;9600;8;1;EVEN;passive;None;Env;wic;A2;'Environment sensor measuring temperature and humidity'

        ENV05_2_0001;USB0;9600;8;1;EVEN;passive;None;Env;'Environment sensor measuring temperature and humidity'
    RETURNS:
        a list of dictionariues containing:
        'sensorid':'ENV05_2_0001', 'port':'USB0', 'baudrate':9600, 'bytesize':8, 'stopbits':1, 'parity':'EVEN', 'mode':'a', 'init':None, 'rate':10, 'protocol':'Env', 'name':'ENV05', 'serialnumber':'2', 'revision':'0001', 'path':'-', 'pierid':'A2', 'ptime':'NTP', 'sensordesc':'Environment sensor measuring temperature and humidity'

    """
    sensorlist = []
    if path.endswith('json'):
        # Load new json version of sensors configuration
        # 'sensorid':'ENV05_2_0001', 'port':'USB0', 'baudrate':9600, 'bytesize':8, 'stopbits':1, 'parity':'EVEN', 'mode':'a', 'init':None, 'rate':10, 'protocol':'Env', 'name':'ENV05', 'serialnumber':'2', 'revision':'0001', 'path':'-', 'pierid':'A2', 'ptime':'NTP', 'sensordesc':'Environment sensor measuring temperature and humidity'
        pass
    else:
        sensors = open(path,'r')
        sensordata = sensors.readlines()
        sensorlist = []
        sensordict = {}
        elements = SENSORELEMENTS

        # add identifier here
        #

        for item in sensordata:
            sensordict = {}
            try:
                parts = item.split(',')
                if item.startswith('#'):
                    continue
                elif item.isspace():
                    continue
                elif item.startswith('!') and not identifier:
                    continue
                elif item.startswith('?') and not identifier:
                    continue
                elif item.startswith('$') and not identifier:
                    continue
                elif not identifier and len(item) > 8:
                    for idx,part in enumerate(parts):
                        sensordict[elements[idx]] = part
                elif item.startswith(str(identifier)) and len(item) > 8:
                    if not secondidentifier:
                        for idx,part in enumerate(parts):
                            if idx == 0:
                                part = part.strip(str(identifier))
                            sensordict[elements[idx]] = part
                    elif secondidentifier in parts:
                        for idx,part in enumerate(parts):
                            if idx == 0:
                                part = part.strip(str(identifier))
                            sensordict[elements[idx]] = part
                    else:
                        pass
            except:
                # Possible issue - empty line
                pass
            if not sensordict == {}:
                sensorlist.append(sensordict)

    return sensorlist


def sendmail(dic, credentials="webmail", debug=False):
    """
    DESCRIPTION
        Mailing function for sending contents of a mailing dictionary with attachments
    DEPENDENCIES
        requires the magpy credential module to obsfucate credential information on mail server.
        You can insert new credentials either with "addcred" after installation of MagPy or use:
        from magpy.opt import cred as cred
        cred.cc('mail','webmail', user='user@web.xx', passwd="secret", smtp='smtp.provider.xx', port='587')
    VARIABLES
        dic : dict with 'subject', 'from', 'to', 'text', 'attachment'
    """

    if debug:
        print ("sendmail - input dictionary: ", dic)

    if 'attachment' in dic and isinstance(dic.get('attachment',[]), (list,tuple)):
        files = dic.get('attachment',[])
    else:
        files = []
    text = dic.get('text','Cheers, Your Analysis-Robot')
    subject = dic.get('subject','Automatic message')

    smtpserver = cred.lc(credentials,'smtp')
    user = cred.lc(credentials,'user')
    pwd = cred.lc(credentials,'passwd')
    port = cred.lc(credentials,'port')
    if port:
        port = int(port)
    if not smtpserver:
        print ("sendmail: will not work. Please check your credentials and mailserver defintion")
        return

    msg = MIMEMultipart()
    msg['From'] = user #dic.get('from')
    send_to = ', '.join(dic.get('to'))
    msg['To'] = send_to
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject
    msg.attach( MIMEText(text) )

    # TODO log if file does not exist
    for f in files:
        if not os.path.isfile(f):
            print ("File {} not existing".format(f))
        else:
            part = MIMEBase('application', "octet-stream")
            part.set_payload( open(f,"rb").read() )
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(f))
            msg.attach(part)

    # seems as if server name needs to be specified in py3.7 and 3.8, should work in older versions as well
    if port in [465]:
        smtp = smtplib.SMTP_SSL(smtpserver)
    else:
        smtp = smtplib.SMTP(smtpserver)
    smtp.set_debuglevel(False)
    if port:
        smtp.connect(smtpserver, port)
    else:
        smtp.connect(smtpserver)
    smtp.ehlo()
    if port in [587]:
        if debug:
            print ("Using tls")
        smtp.starttls()
    smtp.ehlo()
    if user and not user in ['None','False']:
        smtp.login(user, pwd)
    smtp.send_message(msg)
    smtp.close()


def sendtelegram(message, configpath="", debug=True):
    """
    DESCRIPTION
        Sending a telegram message provided that token and chat_id are provided
        Requires configuartion data read by configparser of the following form:

    VARIABLES
        message : string
        configpath  :
    """

    print("Running telegram send:", configpath, message)
    if not message or not configpath or not os.path.isfile(configpath):
        return False
    # telegram notifications - replace and cut
    rep = message.replace('&', 'and').replace('/', '')[:4000]
    print("Sending by telegram:", rep)
    # Send report to the specific user i.e. by telegram
    config = configparser.ConfigParser()
    config.read(configpath)
    token = config.get('telegram', 'token')
    chat_id = config.get('telegram', 'chat_id')
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={rep}"
    print(requests.get(url).json())  # this sends the message
    return True


class martaslog(object):
    """
    Class for dealing with and sending out change notifications
    of acquisition and analysis states
    """

    def __init__(self, logfile='/var/log/magpy/martasstatus.log', receiver='mqtt'):
        self.mqtt = {'broker': 'localhost', 'delay': 60, 'port': 1883, 'stationid': 'wic', 'client': 'P1', 'user': None,
                     'password': None}
        self.telegram = {'config': "/home/leon/telegramtest.conf"}
        self.logfile = logfile
        self.receiver = receiver
        self.hostname = socket.gethostname()
        # requires json, socket etc

    def updatelog(self, logfile, logdict):
        changes = {}
        if os.path.isfile(logfile):
            # read log if exists and exentually update changed information
            # return changes
            with open(logfile, 'r') as file:
                exlogdict = json.load(file)
            print("Logfile {} loaded".format(logfile))
            for el in logdict:
                if not el in exlogdict:
                    # Adding new sensor and state
                    print("Not Existing:", el)
                    changes[el] = logdict[el]
                else:
                    print("Existing:", el)
                    # Checking state
                    if not logdict[el] == exlogdict[el]:
                        # state changed
                        changes[el] = logdict[el]
            ## check for element in exlogdict which are not in logdict
            for el in exlogdict:
                if not el in logdict:
                    # Sensor has been removed
                    print("Removed:", el)
                    changes[el] = "removed"

            if not len(changes) == 0:
                # overwrite prexsiting logfile
                print("-------------")
                print("Changes found")
                print("-------------")
                with open(logfile, 'w') as file:
                    file.write(json.dumps(logdict))  # use `json.loads` to do the reverse
        else:
            # write logdict to file
            with open(logfile, 'w') as file:
                file.write(json.dumps(logdict))  # use `json.loads` to do the reverse
            print("Logfile {} written successfully".format(logfile))

        return changes

    def msg(self, dictionary):
        changes = self.updatelog(self.logfile, dictionary)
        if len(changes) > 0:
            self.notify(changes)

    def notify(self, dictionary):
        # if receiver == "stdout":
        print("Changed content:", dictionary)

        if self.receiver == 'mqtt':
            stationid = self.mqtt.get('stationid')
            broker = self.mqtt.get('broker')
            mqttport = self.mqtt.get('port')
            mqttdelay = self.mqtt.get('delay')
            client = self.mqtt.get('client')
            mqttuser = self.mqtt.get('user')
            mqttpassword = self.mqtt.get('password')
            topic = "{}/{}/{}".format(stationid, "statuslog", self.hostname)
            print("Done. Topic={},".format(topic))
            print("Done. User={},".format(mqttuser))
            client = mqtt.Client(client)
            if not mqttuser == None:
                client.username_pw_set(username=mqttuser, password=mqttpassword)
            print(broker, mqttport, mqttdelay)
            client.connect(broker, mqttport, mqttdelay)
            client.publish(topic, json.dumps(dictionary))
            print('Update sent to MQTT')
        elif self.receiver == 'telegram':
            # try: # import Ok
            # import telegram_send
            # except: # import error
            # try: # conf file exists
            # except: # send howto
            # requires a existing configuration file for telegram_send
            # to create one use:
            # python
            # import telegram_send
            # telegram_send.configure("/path/to/my/telegram.cfg",channel=True)
            tgmsg = ''
            for elem in dictionary:
                tgmsg += "{}: {}\n".format(elem, dictionary[elem])
            sendtelegram(tgmsg, configpath=self.telegram.get('config'), debug=False)
            # telegram_send.send(messages=[tgmsg],conf=self.telegram.get('config'),parse_mode="markdown")
            print('Update sent to telegram')
        else:
            print("Given receiver is not yet supported")

    def receiveroptions(self, receiver, options):
        dictionary = eval('self.{}'.format(receiver))
        for elem in options:
            dictionary[elem] = options[elem]
        print("Dictionary {} updated".format(receiver))

