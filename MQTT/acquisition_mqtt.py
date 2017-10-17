#!/usr/bin/env python
"""
Secondary acquisition routine of MARTAS: 
MQTT protocol by Roman Leonhardt and Rachel Bailey to be used in the Conrad Observatory.

How should it work:
PURPOSE:
acquisition_mqtt.py reads e.g. serial data and publishes that using the mqtt protocol.
An "collector" e.g. MARCOS can subscribe to the "publisher" and access the data stream.

REQUIREMENTS:
1.) install a MQTT broker (e.g. ubuntu (< 16.04): 
sudo apt-add-repository ppa:mosquitto-dev/mosquitto-ppa
sudo apt-get update
sudo apt-get install mosquitto mosquitto-clients)
2.) Secure comm and authencation: https://www.digitalocean.com/community/tutorials/how-to-install-and-secure-the-mosquitto-mqtt-messaging-broker-on-ubuntu-16-04

METHODS:
acquisition_mqtt.py contains the following methods:

GetSensors: read a local definition file (sensors.txt) which contains information
            on SensorID, Port, Bausrate (better Serial communication details), active/passive, 
            init requirements, optional SensorDesc

GetDefaults: read initialization file with local paths, publishing server, ports, etc.

SendInit: send eventually necessary initialization data as defined in sensors.txt

GetActive: Continuously obtain serial data from instrument and convert it to an binary 
           information line to be published (using libraries)

GetPassive: Send scheduled request to serial port to obtain serial data from instrument 
            and convert it to an binary information line to be published (using libraries)

1. how to convert incoming serial datalines to magpy.stream contents
2. an eventual initialization protocol too be send to the serial port before
3.  
call method: defined here

Usage:
sudo python acquisition.py

"""

from __future__ import print_function
from __future__ import absolute_import

# ###################################################################
# Import packages
# ###################################################################

## Import MagPy
## -----------------------------------------------------------
from magpy.stream import *

## Import support packages
## -----------------------------------------------------------
import socket
from serial import PARITY_EVEN
from serial import SEVENBITS

## Import MQTT
## -----------------------------------------------------------
import paho.mqtt.client as mqtt

## Import twisted for serial port communication and web server
## -----------------------------------------------------------
if sys.platform == 'win32':
    ## on windows, we need to use the following reactor for serial support
    ## http://twistedmatrix.com/trac/ticket/3802
    ##
    from twisted.internet import win32eventreactor
    win32eventreactor.install()
# IMPORT TWISTED
from twisted.internet import reactor
print("Using Twisted reactor", reactor.__class__)
print()
from twisted.python import usage, log
from twisted.protocols.basic import LineReceiver
from twisted.internet.serialport import SerialPort

import threading

from methodstobemovedtoacs import *

"""
import sys
import time
import os
from datetime import datetime, timedelta
import re
import struct, binascii

from twisted.python import usage, log
from twisted.protocols.basic import LineReceiver
from twisted.internet.serialport import SerialPort
from twisted.internet import task
from twisted.web.server import Site
from twisted.web.static import File
"""

## Import libraries
## -----------------------------------------------------------
#from magpy.acquisition.gsm19protocol import GSM19Protocol
# import all libraries here

# ###################################################################
# Default specifications and initialization parameters
# ###################################################################

now = datetime.utcnow()
hostname = socket.gethostname()

SUPPORTED_PROTOCOLS = ['Env','Ow','Lemi'] # should be provided by MagPy

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
        # ports: u for usb 
        owport : usb
        # Defining a measurement frequency in secs (should be >= amount of sensors connected)
        timeoutow : 30.0

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


def SendInit(confdict,sensordict):
    """
    DESCRIPTION:
    send eventually necessary initialization data as defined in sensors.conf
    """
    pass

def do_every (interval, worker_func, iterations = 0):
    if iterations != 1:
        threading.Timer(interval,do_every, [interval, worker_func, 0 if iterations == 0 else iterations-1]).start ()
    worker_func()

def ActiveThread(confdict,sensordict, mqttclient, activeconnections):
    """
    1. identify protocol from sensorid
    2. Apply protocol (read serial and return data)
    3. add data to Publish
    -> do all that in while True
    """

    sensorid = sensordict.get('sensorid')
    print ("Starting ActiveThread for {}".format(sensorid))

    print ("0. Identify protocol")
    protocolname = sensordict.get('protocol')
    print ("   Found protocol {}".format(protocolname))

    protlst = [activeconnections[key] for key in activeconnections]
    amount = protlst.count(protocolname) + 1 # Load existing connections (new amount is len(exist)+1)
    #amount = 1                           # Load existing connections (new amount is len(exist)+1)
    print ("1. Importing ...")
    if protocolname in SUPPORTED_PROTOCOLS:
        importstr = "from {}protocol import {}Protocol as {}Prot{}".format(protocolname.lower(),protocolname,protocolname,amount)
        evalstr = "{}Prot{}(mqttclient,sensordict, confdict)".format(protocolname,amount)
        exec importstr
        protocol = eval(evalstr)

    print ("2. Starting looping call task using appropriate protocol")
    proto = "{}Prot{}".format(protocolname,amount)

    try:
        rate = int(sensordict.get('rate'))
    except:
        print ("did not found appropriate sampling rate - using 30 sec")
        rate = 30

    do_every(rate, protocol.sendRequest)

    activeconnection = {sensorid: protocolname}
    print ("active connection established ... success") 

    return activeconnection

def PassiveThread(confdict,sensordict, mqttclient, establishedconnections):
    """
    1. identify protocol from sensorid
    2. Apply protocol (read serial and return data)
    3. add data to Publish
    -> do all that in while True
    """
    sensorid = sensordict.get('sensorid')
    print ("Starting PassiveThread for {}".format(sensorid))

    print ("0. Identify protocol")
    protocolname = sensordict.get('protocol')
    print ("   Found protocol {}".format(protocolname))
    protlst = [establishedconnections[key] for key in establishedconnections]
    amount = protlst.count(protocolname) + 1 # Load existing connections (new amount is len(exist)+1)
    #amount = 1                           # Load existing connections (new amount is len(exist)+1)
    print ("1. Importing ...")
    if protocolname in SUPPORTED_PROTOCOLS:
        importstr = "from {}protocol import {}Protocol as {}Prot{}".format(protocolname.lower(),protocolname,protocolname,amount)
        evalstr = "{}Prot{}(mqttclient,sensordict, confdict)".format(protocolname,amount)
        exec(importstr)
        protocol = eval(evalstr)

    print ("2. Establishing connection using appropriate protocol")
    port = confdict['serialport']+sensordict.get('port')
    print ("   Connecting to port {} ".format(port)) 
    serialPort = SerialPort(protocol, port, reactor, baudrate=int(sensordict.get('baudrate')))

    passiveconnection = {sensorid: protocolname}
    print ("passive connection established ... success") 

    return passiveconnection


# -------------------------------------------------------------------
# MQTT connect:
# -------------------------------------------------------------------

def onConnect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))

def onMessage(client, userdata, message):
   # Decode the payload to get rid of the 'b' prefix and single quotes:
   print('It is ' + str(message.payload.decode("utf-8")))

def onDisconnect(client, userdata, message):
   print("Disconnected from the broker.")

#####################################################################
# MAIN PROGRAM
#####################################################################

if __name__ == '__main__':

    ##
    ## Run like: python acquisition.py --conf='/home/cobs/MARTAS/defaults.conf'

    passive_count = 0
    active_count = 0

    ##  Load defaults dict
    ##  ----------------------------
    conf = GetConf('martas.cfg')

    broker = conf.get('broker')
    mqttport = int(conf.get('mqttport'))
    mqttdelay = int(conf.get('mqttdelay'))

    ##  Start Twisted logging system
    ##  ----------------------------
    if conf['logging'] == 'sys.stdout':
        log.startLogging(sys.stdout)
    else:
        try:
            log.startLogging(open(conf['logging'],'a'))
        except:
            log.startLogging(sys.stdout)
            print ("Could not open {}. Switching log to stdout.".format(conf['logging']))

    ##  Get Sensor data
    ##  ----------------------------
    #sensorlist = GetSensors(conf.get('sensors'))
    sensorlist = GetSensors(conf.get('sensorsconf'))
    print ("Configuration", conf)
    print ("-----------------------------------------")
    print ("Sensorlist", sensorlist)
    print ("-----------------------------------------")

    ## create and connect to MQTT client
    ##  ----------------------------
    client = mqtt.Client(clean_session=True)
    client.on_connect = onConnect
    client.connect(broker, mqttport, mqttdelay)
    client.loop_start()

    establishedconnections = {}
    ## Connect to serial port (sensor dependency) -> returns publish 
    # Start subprocesses for each publishing protocol
    for sensor in sensorlist:
        print ("Sensor and Mode:", sensor.get('sensorid'), sensor.get('mode'))
        print ("----------------")
        print ("Initialization:", sensor.get('init'))
        # if init:
        #     SendInit(confdict,sensordict) and run commands
        if sensor.get('mode') in ['p','passive','Passive','P']:
            connected = PassiveThread(conf,sensor,client,establishedconnections)
            print ("acquisition_mqtt: PassiveThread initiated for {}. Ready to receive data ...".format(sensor.get('sensorid')))
            establishedconnections.update(connected)
            passive_count +=1
        elif sensor.get('mode') in ['a','active','Active','A']:
            print ("acquisition_mqtt: ActiveThread initiated for {}. Periodically requesting data ...".format(sensor.get('sensorid')))
            connected_act = ActiveThread(conf,sensor,client,establishedconnections)

            #thread.start(sensorprotocol)
            pass
        else:
            print ("acquisition_mqtt: Mode not recognized")

        sensorid = sensor.get('sensorid')
        #port = sensor[1]
        #serialcomm = sensor[2]
        #sensorid = sensor[0]
        #sensorid = sensor[0]
        #sensorid = sensor[0]

        #thread.start(sensorprotocol)

    # Start all passive clients
    if passive_count > 0:
        print ("acquisition_mqtt: Starting reactor for passive sensors. Sending data now ...")
        reactor.run()


