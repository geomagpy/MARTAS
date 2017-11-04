from __future__ import print_function
from __future__ import absolute_import

# ###################################################################
# Import packages
# ###################################################################

import re     # for interpretation of lines
import struct # for binary representation
import socket # for hostname identification
import string # for ascii selection
from datetime import datetime, timedelta
#from twisted.protocols.basic import LineReceiver
from twisted.python import log
from magpy.acquisition import acquisitionsupport as acs

SENSORELEMENTS =  ['sensorid','port','baudrate','bytesize','stopbits', 'parity','mode','init','rate','stack','protocol','name','serialnumber','revision','path','pierid','offsets','sensorgroup','sensordesc']


def AddSensor(path, dictionary, block=None):
    """
    DESCRIPTION:
        append sensor information to sensors.cfg
    PATH:
        sensors.conf
    """

    owheadline = "# OW block (automatically determined)"
    arduinoheadline = "# Arduino block (automatically determined)"
    owidentifier = '!'
    arduinoidentifier = '?'
    delimiter = '\n'

    def makeline(dictionary,delimiter):
        lst = []
        for el in SENSORELEMENTS:
            lst.append(str(dictionary.get(el,'-')))
        return ','.join(lst)+delimiter

    newline = makeline(dictionary,delimiter)

    # 1. if not block in ['OW','Arduino'] abort
    if not block in ['OW','Arduino']:
        print ("provided block needs to be 'OW' or 'Arduino'")
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

    # 3. if block == OW
    #    owheadline = "# OW block (automatically determined)"
    #    locate owheadline - get position of last identifier 
    #    else add owheadline at the end of the file
    # 4. if block == Arduino
    #    owheadline = "# OW block (automatically determined)"
    #    locate owheadline - get position of last identifier 
    #    else add owheadline at the end of the file
    if block in ['OW','ow','Ow']:
        num = [line for line in sensordata if line.startswith(owheadline)]
        identifier = owidentifier
        headline = owheadline
    elif block in ['Arduino','arduino','ARDUINO']:
        num = [line for line in sensordata if line.startswith(arduinoheadline)]
        identifier = arduinoidentifier
        headline = arduinoheadline

    # 5. Append/Insert line 
    if len(num) > 0:
            cnt = [idx for idx,line in enumerate(sensordata) if line.startswith(identifier)]
            lastline = max(cnt)
            sensordata.insert(lastline+1,identifier+newline)
    else:
            sensordata.append(delimiter)
            sensordata.append(headline+delimiter)
            sensordata.append(identifier+newline)

    # 6. write all lines to sensors.cfg
    with open(path, 'w') as f:
        f.write(''.join(sensordata))

    return True

 
def GetSensors(path, identifier=None, secondidentifier=None):
    """
    DESCRIPTION:
        read sensor information from a file
        Now: just define them by hand
    PATH:
        sensors.conf
    CONTENT:
        # sensors.conf contains specific information for each attached sensor
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
        a dictionary containing:
        'sensorid':'ENV05_2_0001', 'port':'USB0', 'baudrate':9600, 'bytesize':8, 'stopbits':1, 'parity':'EVEN', 'mode':'a', 'init':None, 'rate':10, 'protocol':'Env', 'name':'ENV05', 'serialnumber':'2', 'revision':'0001', 'path':'-', 'pierid':'A2', 'offsets':'0', 'sensordesc':'Environment sensor measuring temperature and humidity'
    
    """
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


def GetConf(path):
    """
    DESCRIPTION:
        read default configuration paths etc from a file
        Now: just define them by hand
    PATH:
        defaults are stored in magpymqtt.conf

        File looks like:
        # Configuration data for data transmission using MQTT (MagPy/MARTAS)
        # use # to uncomment
        # ##################################################################
        #
        # Working directory
        # -----------------
        # Please specify the path to the configuration files 
        configpath : /home/leon/CronScripts/MagPyAnalysis/MQTT

        # Definition of the bufferdirectory
        # ---------------------------------
        # Within this path, MagPy's write routine will store binary data files
        bufferdirectory : /srv/ws

        # Serial ports path
        # -----------------
        serialport : /dev/tty
        timeout : 60.0

        # MQTT definitions 
        # ----------------
        broker : localhost
        mqttport : 1883
        mqttdelay : 60

        # One wire configuration
        # ----------------------
        # ports: u for usb ---- NEW: owserver needs to be running - then just get port and address
        owport : usb
        owaddress : localhost

        # Logging
        # ----------------------
        # specify location to which logging information is send
        # e.g. sys.stdout , /home/cobs/logs/logmqtt.log
        logging : sys.stdout

    """
    # Init values:
    confdict = {}
    confdict['sensorsconf'] = '/home/leon/CronScripts/MagPyAnalysis/MQTT/sensors.cfg'
    #confdict['bufferdirectory'] = '/srv/ws'
    confdict['station'] = 'wic'
    confdict['bufferdirectory'] = '/srv/mqtt'
    confdict['serialport'] = '/dev/tty'
    confdict['timeout'] = 60.0
    confdict['broker'] = 'localhost'
    confdict['mqttport'] = 1883
    confdict['mqttdelay'] = 60
    confdict['logging'] = 'sys.stdout'
    confdict['owport'] = 4304
    confdict['owhost'] = 'localhost'

    try:
        config = open(path,'r')
        confs = config.readlines()

        for conf in confs:
            conflst = conf.split(':')
            if conf.startswith('#'): 
                continue
            elif conf.isspace():
                continue
            elif len(conflst) == 2:
                conflst = conf.split(':')
                key = conflst[0].strip()
                value = conflst[1].strip()
                confdict[key] = value
    except:
        print ("Problems when loading conf data from file. Using defaults")

    return confdict


