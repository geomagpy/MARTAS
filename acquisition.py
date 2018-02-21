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
local = True
if local:
    import sys
    sys.path.insert(1,'/home/leon/Software/magpy-git/')


import threading
import sys, getopt, os
from datetime import datetime

## Import MagPy packages
## -----------------------------------------------------------
from magpy.opt import cred as mpcred
from magpy.acquisition import acquisitionsupport as acs

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
from twisted.python import log
from twisted.protocols.basic import LineReceiver
from twisted.internet.serialport import SerialPort


# ###################################################################
# Default specifications and initialization parameters
# ###################################################################

now = datetime.utcnow()
hostname = socket.gethostname()
msgcount = 0


SUPPORTED_PROTOCOLS = ['Env','Ow','Lemi','Arduino','GSM90','GSM19','Cs','POS1','MySQL','Lm','Lnm','BM35'] # should be provided by MagPy
"""
Protocol types:
ok		Env 	: passive		: environment
ok		Ow	: active (group)	: environment
ok		Arduino	: active (group)	: environment
none		BM35	: active 		: environment
current work	Lemi	: passive		: mag
ok      	GSM90	: passive (init)	: mag
(test requ.)	POS1	: passive (init)	: mag
written (time test missing)	GSM19	: passive 		: mag
written 	Cs	: passive 		: mag
-	   	PalmDac : passive		: mag
current work	MySQL	: active (group)	: general db call
-	        Active	: active		: general active call
current work	CR1000	: active		: all
"""



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
    log.msg("Starting ActiveThread for {}".format(sensorid))
    protocolname = sensordict.get('protocol')
    log.msg("  -> Importing protocol {}".format(protocolname))

    protlst = [activeconnections[key] for key in activeconnections]
    amount = protlst.count(protocolname) + 1 # Load existing connections (new amount is len(exist)+1)
    #amount = 1                           # Load existing connections (new amount is len(exist)+1)
    if protocolname in SUPPORTED_PROTOCOLS:
        importstr = "from libmqtt.{}protocol import {}Protocol as {}Prot{}".format(protocolname.lower(),protocolname,protocolname,amount)
        if confdict.get('debug') == 'True':
            log.msg("DEBUG -> Importstring looks like: {}".format(importstr))

        evalstr = "{}Prot{}(mqttclient,sensordict, confdict)".format(protocolname,amount)
        exec importstr
        protocol = eval(evalstr)
        log.msg(evalstr)
    else:
        log.msg("  -> did not find protocol in SUPPORTED_PROTOCOL list")

    log.msg("  -> Starting active thread ...")
    proto = "{}Prot{}".format(protocolname,amount)

    try:
        rate = int(sensordict.get('rate'))
    except:
        log.msg("  -> did not find appropriate sampling rate - using 30 sec")
        rate = 30

    do_every(rate, protocol.sendRequest)

    activeconnection = {sensorid: protocolname}
    log.msg("  -> active connection established ... sampling every {} sec".format(rate)) 

    return activeconnection

def PassiveThread(confdict,sensordict, mqttclient, establishedconnections):
    """
    1. identify protocol from sensorid
    2. Apply protocol (read serial and return data)
    3. add data to Publish
    -> do all that in while True
    """
    sensorid = sensordict.get('sensorid')
    log.msg("Starting PassiveThread for {}".format(sensorid))
    protocolname = sensordict.get('protocol')
    log.msg("  -> Found protocol {}".format(protocolname))
    protlst = [establishedconnections[key] for key in establishedconnections]
    amount = protlst.count(protocolname) + 1 # Load existing connections (new amount is len(exist)+1)
    #amount = 1                           # Load existing connections (new amount is len(exist)+1)
    if protocolname in SUPPORTED_PROTOCOLS:
        importstr = "from libmqtt.{}protocol import {}Protocol as {}Prot{}".format(protocolname.lower(),protocolname,protocolname,amount)
        if confdict.get('debug') == 'True':
            log.msg("DEBUG  -> Importstring looks like: {}".format(importstr))
        evalstr = "{}Prot{}(mqttclient,sensordict, confdict)".format(protocolname,amount)
        exec(importstr)
        protocol = eval(evalstr)

    port = confdict['serialport']+sensordict.get('port')
    log.msg("  -> Connecting to port {} ...".format(port)) 
    serialPort = SerialPort(protocol, port, reactor, baudrate=int(sensordict.get('baudrate')))

    passiveconnection = {sensorid: protocolname}
    log.msg("  -> passive connection established") 

    return passiveconnection


# -------------------------------------------------------------------
# MQTT connect:
# -------------------------------------------------------------------

def onConnect(client, userdata, flags, rc):
    log.msg("Connected with result code " + str(rc))
    global msgcount
    if rc == 0 and msgcount < 4:
        log.msg("Moving on...")
    elif rc == 5 and msgcount < 4:
        log.msg("Authetication required")
    msgcount += 1 
    # add a counter here with max logs

def onMessage(client, userdata, message):
   # Decode the payload to get rid of the 'b' prefix and single quotes:
   log.msg('It is ' + str(message.payload.decode("utf-8")))

def onDisconnect(client, userdata, message):
   log.msg("Disconnected from the broker.")

#####################################################################
# MAIN PROGRAM
#####################################################################

def main(argv):
    ##
    ## Run like: python acquisition.py -m '/home/cobs/MARTAS/defaults.conf'

    global now
    global hostname
    global msgcount
    global SUPPORTED_PROTOCOLS

    passive_count = 0
    active_count = 0
    martasfile = 'martas.cfg'
    cred = ''
    creduser = ''
    credhost = ''
    pwd = 'None'

    ##  Get eventually provided options
    ##  ----------------------------
    usagestring = 'acquisition.py -m <martas> -c <credentials> -P <password>'
    try:
        opts, args = getopt.getopt(argv,"hm:c:P:U",["martas=","credentials=","password=","debug=",])
    except getopt.GetoptError:
        print('Check your options:')
        print(usagestring)
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print('------------------------------------------------------')
            print('Usage:')
            print(usagestring)
            print('------------------------------------------------------')
            print('Options:')
            print('-h                             help')
            print('-m                             path to martas configuration')
            print('-c                             credentials, if authentication is used')
            print('-P                             alternatively provide password')
            print('------------------------------------------------------')
            print('Examples:')
            print('1. Basic (using defauilt martas.cfg')
            print('   python acquisition.py')
            print('2. Using other configuration')
            print('   python acquisition.py -m "/home/myuser/mymartas.cfg"')
            sys.exit()
        elif opt in ("-m", "--martas"):
            martasfile = arg
        elif opt in ("-c", "--credentials"):
            try:
                cred = arg
                print ("Accessing credential information for {}".format(cred))
                credhost = mpcred.lc(cred,'address')
                creduser = mpcred.lc(cred,'user')
                pwd = mpcred.lc(cred,'passwd')
            except:
                pass
        elif opt in ("-P", "--password"):
            pwd = arg


    ##  Load defaults dict
    ##  ----------------------------
    conf = acs.GetConf(martasfile)
    # Add a ceck routine here whether conf information was obtained

    broker = conf.get('broker')
    mqttport = int(conf.get('mqttport'))
    mqttdelay = int(conf.get('mqttdelay'))

    ##  Get Sensor data
    ##  ----------------------------
    sensorlist = acs.GetSensors(conf.get('sensorsconf'))

    ## create MQTT client
    ##  ----------------------------
    client = mqtt.Client(clean_session=True)
    user = conf.get('mqttuser','')
    if not user in ['','-',None,'None']:
        # Should have two possibilities:
        # 1. check whether credentials are provided
        if not cred == '':
            if not creduser == user:
                print ('User names provided in credentials and martas.cfg differ. Please check!')
                pwd = 'None'
        if pwd == 'None':
            # 2. request pwd input
            print ('MQTT Authentication required for User {}:'.format(user))
            import getpass
            pwd = getpass.getpass()

        client.username_pw_set(username=user,password=pwd)

    ##  Start Twisted logging system
    ##  ----------------------------
    if conf.get('logging').strip() == 'sys.stdout':
        log.startLogging(sys.stdout)
    else:
        try:
            print (" -- Logging to {}".format(conf.get('logging')))
            log.startLogging(open(conf.get('logging'),'a'))
            log.msg("----------------")
            log.msg("  -> Logging to {}".format(conf.get('logging')))
        except:
            log.startLogging(sys.stdout)
            print ("Could not open {}. Switching log to stdout.".format(conf['logging']))

    ## connect to MQTT client
    ##  ----------------------------
    client.on_connect = onConnect
    client.connect(broker, mqttport, mqttdelay)
    client.loop_start()

    establishedconnections = {}
    ## Connect to serial port (sensor dependency) -> returns publish 
    # Start subprocesses for each publishing protocol
    for sensor in sensorlist:
        log.msg("----------------")
        log.msg("Sensor and Mode:", sensor.get('sensorid'), sensor.get('mode'))
        log.msg("----------------")
        init = sensor.get('init')
        if not init in ['','None',None,0,'-']:
            log.msg("  - Initialization using {}".format(init))
            initdir = conf.get('initdir')
            initapp = os.path.join(initdir,init)
            # Check if provided initscript is existing
            import subprocess
            try:
                log.msg("  - running initialization .{}".format(initapp))
                log.msg(subprocess.check_output(['sh',initapp]))
            except subprocess.CalledProcessError as e:
                log.msg("  - init command '{}' returned with error (code {}): {}".format(e.cmd, e.returncode, e.output))
        if sensor.get('mode') in ['p','passive','Passive','P']:
            try:
                connected = PassiveThread(conf,sensor,client,establishedconnections)
                log.msg(" - PassiveThread initiated for {}. Ready to receive data ...".format(sensor.get('sensorid')))
                establishedconnections.update(connected)
                passive_count +=1
            except:
                log.msg(" - !!! PassiveThread failed for {} !!!".format(sensor.get('sensorid')))
                pass
        elif sensor.get('mode') in ['a','active','Active','A']:
            try:
                log.msg(" - ActiveThread initiated for {}. Periodically requesting data ...".format(sensor.get('sensorid')))
                connected_act = ActiveThread(conf,sensor,client,establishedconnections)
            except:
                log.msg(" - !!! ActiveThread failed for {} !!!".format(sensor.get('sensorid')))
                pass
        else:
            log.msg("acquisition_mqtt: Mode not recognized")

        sensorid = sensor.get('sensorid')

    # Start all passive clients
    if passive_count > 0:
        log.msg("acquisition_mqtt: Starting reactor for passive sensors. Sending data now ...")
        reactor.run()


if __name__ == "__main__":
   main(sys.argv[1:])

