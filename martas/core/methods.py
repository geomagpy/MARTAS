#!/usr/bin/env python
# coding=utf-8

import unittest
from magpy.core import database
from magpy.core import methods
from magpy.opt import cred as cred
import os
import sys
import glob
from datetime import datetime, timezone, timedelta
from dateutil.parser import parse
#import dateutil.parser as dparser
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
import pexpect


"""
Methods:

| class           |  method  |  version |  tested  |              comment             | manual | *used by |
| --------------- |  ------  |  ------- |  ------- |  ------------------------------- | ------ | ---------- |
|  **martaslog**  |          |          |          |                                  |        | monitor,threshold |
|  martaslog      |  __init__  |  2.0.0 |      yes |                                  | -      |          |
|  martaslog      |  msg     |  2.0.0   |      yes |  tested: mail,telegram, not:mqtt | -      |          |
|  martaslog      |  notify  |  2.0.0   |      yes |                                  | -      |          |
|  martaslog      |  receiveroption  |  2.0.0 |  yes |                                | -      |          |
|  martaslog      |  updatelog |  2.0.0 |      yes |                                  | -      |          |
|                 |  add_sensor  |  2.0.0 |      - |                               | -       | mysql,ow,arduino libs |
|                 |  check_conf  |  2.0.0 |      - |                                  | -      | basevalue, flags  |
|                 |  connect_db  |  2.0.0 |    yes |                                  | -      | archive  |
|                 |  datetime_to_array  |  2.0.0 |  yes |                             | -      | libs     |
|                 |  data_to_file  |  2.0.0 |  yes |                                  | -      | libs     |
|                 |  get_bool  |  2.0.0 |      yes |                                  | -      | archive,filter |
|                 |  get_conf  |  2.0.0 |      yes |                                  | -      | marcosscripts |
|                 |  get_json  |  2.0.0 |      yes |                                  | -      | file_upload |
|                 |  get_sensors  |  2.0.0 |   yes |                                  | -      | marcosscripts |
|                 |  put_json  |  2.0.0 |      yes |                                  | -      | file_upload |
|                 |  scptransfer  |  2.0.0 |    -  |                                  | -      | up/download |
|                 |  sendmail  |  2.0.0 |      yes |  identical method in imbot       | -      | imbot    |
|                 |  sendtelegram |  2.0.0  |  yes |  identical method in imbot       | -      | marcosscripts, imbot |
|                 |  time_to_array  |  2.0.0 | yes |                                  | -      | libs     |

"""

SENSORELEMENTS =  ['sensorid','port','baudrate','bytesize','stopbits', 'parity','mode','init','rate','stack','protocol','name','serialnumber','revision','path','pierid','ptime','sensorgroup','sensordesc']



def add_sensors(path, dictionary, block=None):
    """
    DESCRIPTION:
        append sensor information to sensors.cfg
    PATH:
        sensors.conf
    """

    owheadline = "# OW block (automatically determined)"
    arduinoheadline = "# Arduino block (automatically determined)"
    mysqlheadline = "# SQL block (automatically determined)"
    owidentifier = '!'
    arduinoidentifier = '?'
    mysqlidentifier = '$'
    delimiter = '\n'
    num = []
    headline = ""
    identifier = ""

    def makeline(dictionary,delimiter):
        lst = []
        for el in SENSORELEMENTS:
            lst.append(str(dictionary.get(el,'-')))
        return ','.join(lst)+delimiter

    newline = makeline(dictionary,delimiter)

    # 1. if not block in ['OW','Arduino'] abort
    if not block in ['OW','ow','Ow','Arduino','arduino','ARDUINO','SQL','MySQL','mysql','MYSQL','sql']:
        print ("provided block needs to be 'OW', 'Arduino' or 'SQL'")
        return False

    # 2. check whether sensors.cfg existis
    # abort if not
    # read all lines
    try:
        sensors = open(path,'r')
    except:
        print ("could not read sensors.cfg")
        return False
    sensordata = sensors.readlines()
    if not len(sensordata) > 0:
        print ("no data found in sensors.cfg")
        return False

    if block in ['OW','ow','Ow']:
        num = [line for line in sensordata if line.startswith(owheadline)]
        identifier = owidentifier
        headline = owheadline
    elif block in ['Arduino','arduino','ARDUINO']:
        num = [line for line in sensordata if line.startswith(arduinoheadline)]
        identifier = arduinoidentifier
        headline = arduinoheadline
    elif block in ['SQL','MySQL','mysql','MYSQL','sql']:
        num = [line for line in sensordata if line.startswith(mysqlheadline)]
        identifier = mysqlidentifier
        headline = mysqlheadline

    # 3. Append/Insert line
    if len(num) > 0:
            cnt = [idx for idx,line in enumerate(sensordata) if line.startswith(identifier) or  line.startswith('#'+identifier)]
            lastline = max(cnt)
            if not (identifier+newline) in sensordata:
                if not ('#'+identifier+newline) in sensordata:
                    sensordata.insert(lastline+1,identifier+newline)
    else:
            sensordata.append(delimiter)
            sensordata.append(headline+delimiter)
            sensordata.append(identifier+newline)

    # 6. write all lines to sensors.cfg
    with open(path, 'w') as f:
        f.write(''.join(sensordata))

    return True


def check_conf(config, startdate=None, enddate='now', varios=None, scalars=None, piers=None, debug=False):
    """
    DESCRIPTION
        this method will extend/modify the configuration data with basevalue analysis specific parameters
    """

    if varios == None:
        varios = []
    if scalars == None:
        scalars = []
    if piers == None:
        piers = []
    if enddate == 'now' or config.get('enddate') == 'now':
        endtime = datetime.now(timezone.utc).replace(tzinfo=None)
        config['enddate'] = endtime.strftime("%Y-%m-%d")
        if not startdate:
            starttime = endtime - timedelta(days=380)
            config['startdate'] = starttime.strftime("%Y-%m-%d")
    elif enddate == 'file':
        # determine startdate and enddate from the available files in the directory
        pass
    elif enddate:
        endtime = parse(enddate)
        config['enddate'] = endtime.strftime("%Y-%m-%d")
        if not startdate:
            starttime = endtime - timedelta(days=380)
            config['startdate'] = starttime.strftime("%Y-%m-%d")
    else:
        enddate = config.get('enddate', None)
        if enddate in ['None', 'False', None, 0]:
            config['enddate'] = None
    if startdate:
        starttime = parse(startdate)
        config['startdate'] = starttime.strftime("%Y-%m-%d")
    else:
        startdate = config.get('startdate', None)
        if startdate in ['None', 'False', None, 0]:
            config['startdate'] = None

    if varios and len(varios) > 0:
        print(" Setting variometers to {}".format(varios))
        config['vainstlist'] = varios
    if scalars and len(scalars) > 0:
        print(" Setting scalars to {}".format(scalars))
        config['scinstlist'] = scalars
    if piers and len(piers) > 0:
        print(" Setting piers to {}".format(piers))
        config['pierlist'] = piers
    pl = config.get('pierlist')
    if not isinstance(pl, (list, tuple)):
        config['pierlist'] = [pl]
    if not config.get('primarypier'):
        if len(config.get('pierlist')) > 0:
            config['primarypier'] = config.get('pierlist')[0]

    if config.get('year') in ['None', 'False', None, 0]:
        config['year'] = None
    elif config.get('year') in ['current', 'now']:
        config['year'] = datetime.now(timezone.utc).replace(tzinfo=None).year

    if config.get('blvdatapath', '') in ['None', 'False', '', None]:
        config['blvdatapath'] = os.path.join(config.get('base', ''), 'archive', config.get('obscode', ''), 'DI', 'data')

    if not isinstance(config.get('dbcredentials'), list):
        config['dbcredentials'] = [config.get('dbcredentials')]
    if not isinstance(config.get('vainstlist'), list):
        config['vainstlist'] = [config.get('vainstlist')]
    if not isinstance(config.get('scinstlist'), list):
        config['scinstlist'] = [config.get('scinstlist')]
    if not isinstance(config.get('pierlist'), list):
        config['pierlist'] = [config.get('pierlist')]

    credentials = config.get('dbcredentials')
    credential = None
    connectdict = {}
    if len(credentials) > 0:
        credential = credentials[0]
        # connecting all databases and store it
        for credel in credentials:
            connectdict[credel] = connect_db(credential)
    config['conncetedDB'] = connectdict

    if debug:
        print("- Connecting to primary database {}".format(credential))
    try:
        db = connect_db(credential)
        if debug:
            print (" ... success")
        config['primaryDB'] = db
    except:
        config['primaryDB'] = None

    sourcepath = os.path.join(config.get('base', ''), 'archive', config.get('obscode', ''))

    if config.get('didatapath') == 'raw':
        config['didatapath'] = os.path.join(sourcepath, 'DI', 'raw')
    elif config.get('didatapath') == 'analyze':
        config['didatapath'] = os.path.join(sourcepath, 'DI', 'analyze')
        if config.get('movetoarchive') in ['True', 'true', True]:
            config['movetoarchive'] = os.path.join(sourcepath, 'DI', 'raw')
    elif config.get('didatapath') == '':
        config['didatapath'] = os.path.join(sourcepath, 'DI', 'raw')

    for key in config:
        if config.get(key) in ['False', 'false']:
            config[key] = False
        if config.get(key) in ['True', 'true']:
            config[key] = True

    return config


def connect_db(mcred, exitonfailure=True, report=True):

    db = None
    if report:
        print ("  Accessing data bank... ")
    try:
        db = database.DataBank(host=cred.lc(mcred, 'host'), user=cred.lc(mcred, 'user'),
                               password=cred.lc(mcred, 'passwd'),
                               database=cred.lc(mcred, 'db'))
        if report:
            print ("   -> success. Connected to {}".format(cred.lc(mcred,'db')))
    except:
        if report:
            print ("   -> failure - check your credentials / databank")
        if exitonfailure:
            sys.exit()
    return db


def datetime_to_array(t):
    return [t.year,t.month,t.day,t.hour,t.minute,t.second,t.microsecond]


def data_to_file(outputdir="", sensorid="", filedate="", bindata=None, header=None):
    # File Operations
    path = ""
    try:
        #hostname = socket.gethostname()
        path = os.path.join(outputdir,sensorid)
        # outputdir defined in main options class
        if not os.path.exists(path):
            os.makedirs(path)
    except:
        print ("buffer {}: bufferdirectory could not be created - check permissions".format(sensorid))
    try:
        fname = "{}_{}.bin".format(sensorid, filedate)
        savefile = os.path.join(path, fname)
        if sys.version_info>(3,0,0):
            if not os.path.isfile(savefile):
                with open(savefile, "wb") as myfile:
                    head = "{}{}".format(header,"\n")
                    myfile.write(head.encode('utf-8'))
                    myfile.write(bindata)
                    myfile.write("\n".encode('utf-8'))
            else:
                with open(savefile, "ab") as myfile:
                    myfile.write(bindata)
                    myfile.write("\n".encode('utf-8'))
        else:
            if not os.path.isfile(savefile):
                with open(savefile, "wb") as myfile:
                    myfile.write(header + "\n")
                    myfile.write("{}{}".format(bindata,"\n"))
            else:
                with open(savefile, "a") as myfile:
                    myfile.write("{}{}".format(bindata,"\n"))
    except:
        print("buffer {}: Error while saving file".format(sensorid))


def get_bool(string):
    if string in ['True','true','TRUE','Yes','yes','ja','Ja']:
        return True
    else:
        return False


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

def get_json(path):
    """
    DESCRIPTION
        replaces getcurrentdata
    usage: get_json(currentvaluepath)
    example: update kvalue
    fulldict = getcurrentdata(currentvaluepath)
    valdict = fulldict.get('magnetism',{})
    valdict['k'] = [kval,'']
    valdict['k-time'] = [kvaltime,'']
    fulldict[u'magnetism'] = valdict
    writecurrentdata(path, fulldict)
    """
    fulldict = {}
    if os.path.isfile(path):
        with open(path, 'r') as file:
            fulldict = json.load(file)
    else:
        print ("path not found")
    return fulldict


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

    if not path:
        return sensorlist

    if path.endswith('json'):
        # Load new json version of sensors configuration
        # 'sensorid':'ENV05_2_0001', 'port':'USB0', 'baudrate':9600, 'bytesize':8, 'stopbits':1, 'parity':'EVEN', 'mode':'a', 'init':None, 'rate':10, 'protocol':'Env', 'name':'ENV05', 'serialnumber':'2', 'revision':'0001', 'path':'-', 'pierid':'A2', 'ptime':'NTP', 'sensordesc':'Environment sensor measuring temperature and humidity'
        pass
    else:
        with open(path, 'r') as sensors:
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


def put_json(path,dic):
    """
    DESCRIPTION
        replaces writecurrentdata
    usage: writecurrentdata(currentvaluepath,fulldict)
    example: update kvalue
    see getcurrentdata
    """
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(dic, f, ensure_ascii=False, indent=4)
    return True


def scptransfer(src,dest,passwd,**kwargs):
    """
    DEFINITION:
        copy file by scp

    PARAMETERS:
    Variables:
        - src:        (string) e.g. /path/to/local/file or user@remotehost:/path/to/remote/file
        - dest:       (string) e.g. /path/to/local/file or user@remotehost:/path/to/remote/file
        - passwd:     (string) users password
    Kwargs:
        - timeout:    (int)  define timeout - default is 30

    REQUIRES:
        Requires package pexpect

    USED BY:
       cleanup
    """
    timeout = kwargs.get('timeout')

    COMMAND="scp -oPubKeyAuthentication=no %s %s" % (src, dest)

    child = pexpect.spawn(COMMAND)
    if timeout:
        child.timeout=timeout
    child.expect('assword:')   # please not "assword" is correct as it supports both "password" and "Password"
    child.sendline(passwd)
    child.expect(pexpect.EOF)
    print(child.before)


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

    if debug:
        print ("Message", msg)
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


def time_to_array(timestring):
    """
    DESCRIPTION
        Converts a ISO time string to an dt like array.
        Speedtests indicate that this is by far the fastest method.
        A combination of dparser and datetime_to_array would need 20 times longer.
        Accepted strings look like:
        013-12-12T23:12:23.122324
        013-12-12 23:12:23.122324
    APPLICATION
        in libraries
    """

    try:
        splittedfull = timestring.split(' ')
        if not len(splittedfull) > 1:
            splittedfull = timestring.split('T') # ISO format
        splittedday = splittedfull[0].split('-')
        splittedsec = splittedfull[1].split('.')
        splittedtime = splittedsec[0].split(':')
        datearray = splittedday + splittedtime
        datearray.append(splittedsec[1])
        datearray = list(map(int,datearray))
        return datearray
    except:
        print('Error while extracting time array')
        return []

class martaslog(object):
    """
    Class for dealing with and sending out change notifications
    of acquisition and analysis states
    """

    def __init__(self, logfile='/var/log/magpy/martasstatus.log', receiver='mqtt'):
        self.mqtt = {'broker': 'localhost', 'delay': 60, 'port': 1883, 'stationid': 'wic', 'client': 'P1', 'user': None,
                     'password': None}
        self.telegram = {'config': "/home/leon/telegramtest.conf"}
        self.email = {'config': "/home/leon/mail.cfg"}

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
        return changes

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
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client)
            if not mqttuser == None:
                client.username_pw_set(username=mqttuser, password=mqttpassword)
            print(broker, mqttport, mqttdelay)
            client.connect(broker, mqttport, mqttdelay)
            client.publish(topic, json.dumps(dictionary))
            print('Update sent to MQTT')
        elif self.receiver == 'telegram':
            tgmsg = ''
            teleconfig = self.telegram.get('config')
            for elem in dictionary:
                tgmsg += "{}: {}\n".format(elem, dictionary[elem])
            sendtelegram(tgmsg, configpath=teleconfig, debug=False)
            print('Update sent to telegram')
        elif self.receiver == 'email':
            msg = ''
            for elem in dictionary:
                msg += "{}: {}\n".format(elem, dictionary[elem])
            mailpath = self.email.get('config', "")
            maildict = get_conf(mailpath)
            maildict['text'] = msg
            sendmail(maildict, maildict.get("mailcred"), debug=False)
            print('Message send by mail')
        else:
            print("Given receiver is not yet supported - just keeping it in the log")

    def receiveroptions(self, receiver, options):
        dictionary = eval('self.{}'.format(receiver))
        for elem in options:
            dictionary[elem] = options[elem]
        print("Dictionary {} updated".format(receiver))



class TestMethods(unittest.TestCase):
    """
    Test environment for all methods
    """

    def test_connect_db(self):
        db = connect_db('cobsdb',False,True)
        self.assertTrue(db)

    def test_datetime_to_array(self):
        dt = datetime(2021,11,22)
        ar = datetime_to_array(dt)
        self.assertEqual(ar[1],11)

    def test_get_bool(self):
        val = get_bool("TRUE")
        self.assertTrue(val)

    def test_get_conf(self):
        cfg = get_conf("../conf/martas.cfg")
        self.assertEqual(cfg.get("station"),"myhome")

    def test_get_put_json(self):
        cfg = get_conf("../conf/martas.cfg")
        put_json("/tmp/test_martas_methods.json", cfg)
        cfgnew = get_json("/tmp/test_martas_methods.json")
        self.assertEqual(cfg.get("station"),cfgnew.get("station"))

    def test_get_sensors(self):
        recent = True
        sens = get_sensors("../conf/sensors.cfg")
        self.assertEqual(sens,[])

    def test_time_to_array(self):
        s = "2021-11-22 23:12:23.122324"
        ar = time_to_array(s)
        self.assertEqual(ar[1],11)

    def test_martaslog(self):
        receiver = "email" # ["email","telegram"]
        receiver = "telegram" # ["email","telegram"]
        logfile = "/tmp/testlog.log"
        logcont = {"tester":"off"}
        with open(logfile, 'w') as file:
            file.write(json.dumps(logcont))  # use `json.loads` to do the reverse
        ml = martaslog(logfile=logfile,receiver=receiver)
        if receiver == 'telegram':
            ml.telegram['config'] = "../conf/telegram.cfg"
        elif receiver == 'email':
            ml.email['config'] = "../conf/mail.cfg"
        elif receiver == 'mqtt':
            ml.mqtt['broker'] = "localhost"
            ml.mqtt['stationid'] = "tst"
        statusdict = {"tester":"on"}
        changes = ml.msg(statusdict)
        self.assertTrue(changes)


if __name__ == "__main__":
    unittest.main(verbosity=2)