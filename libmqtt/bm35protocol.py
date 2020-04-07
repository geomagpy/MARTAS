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
from twisted.protocols.basic import LineReceiver
from twisted.python import log
from core import acquisitionsupport as acs
import serial # for initializing command
import os

def datetime2array(t):
    return [t.year,t.month,t.day,t.hour,t.minute,t.second,t.microsecond]


## meteolabor BM35 protocol
##
class BM35Protocol(LineReceiver):
    """
    The BM35 protocol for extracting atmospheric pressure data from BM35
    SETUP of BM35 (RS485 version):
        1.) connect a RS485 to RS232 converter
    Supported modes:
        instantaneous values every half second
    """
    def __init__(self, client, sensordict, confdict):
        """
        'client' could be used to switch between different publishing protocols
                 (e.g. MQTT or WS-MCU gateway factory) to publish events
        'sensordict' contains a dictionary with all sensor relevant data (sensors.cfg)
        'confdict' contains a dictionary with general configuration parameters (martas.cfg)
        """
        self.client = client
        self.sensordict = sensordict    
        self.confdict = confdict
        self.count = 0  ## counter for sending header information
        self.sensor = sensordict.get('sensorid')
        self.hostname = socket.gethostname()
        self.printable = set(string.printable)
        #log.msg("  -> Sensor: {}".format(self.sensor))
        self.datalst = []
        self.datacnt = 0
        self.metacnt = 10
        self.errorcnt = {'time':0}

        self.delaylist = []  # delaylist contains up to 1000 diffs between gps and ntp
                             # the median of this values is used for ntp timedelay
        self.timedelay = 0.0
        self.timethreshold = 3 # secs - waring if timedifference is larger the 3 seconds

        # Serial configuration
        self.baudrate=int(sensordict.get('baudrate'))
        self.port = confdict['serialport']+sensordict.get('port')
        self.parity=sensordict.get('parity')
        self.bytesize=int(sensordict.get('bytesize'))
        self.stopbits=int(sensordict.get('stopbits'))
        self.timeout=2 # should be rate dependend


        # QOS
        self.qos=int(confdict.get('mqttqos',0))
        if not self.qos in [0,1,2]:
            self.qos = 0
        log.msg("  -> setting QOS:", self.qos)

        # Debug mode
        debugtest = confdict.get('debug')
        self.debug = False
        if debugtest == 'True':
            log.msg('DEBUG - {}: Debug mode activated.'.format(self.sensordict.get('protocol')))
            self.debug = True    # prints many test messages
        else:
            log.msg('  -> Debug mode = {}'.format(debugtest))

    def connectionMade(self):
        log.msg('  -> {} connected.'.format(self.sensor))

    def connectionLost(self, reason):
        log.msg('  -> {} lost.'.format(self.sensor))

    def processData(self, data):

        currenttime = datetime.utcnow()
        outdate = datetime.strftime(currenttime, "%Y-%m-%d")
        filename = outdate
        sensorid = self.sensor
        datearray = []
        pressure_raw = 88888.8
        pressure = 88888.8
        typ = "none"
        dontsavedata = False

        packcode = '6hLL'
        header = "# MagPyBin %s %s %s %s %s %s %d" % (self.sensor, '[var3]', '[p1]', '[mBar]', '[1000]', packcode, struct.calcsize(packcode))

        try:
            if len(data) == 2:
                typ = "valid"
            # add other types here
        except:
            # TODO??? base x mobile?
            log.err('BM35 - Protocol: Output format not supported - use either base, ... or mobile')
 
        if typ == "valid": 
            pressure_raw = float(data[0].strip())
            pressure = float(data[1].strip())
        elif typ == "none":
            dontsavedata = True
            pass

        if not typ == "none":
            # extract time data
            datearray = datetime2array(currenttime)
            try:
                datearray.append(int(pressure*1000.))
                data_bin = struct.pack('<'+packcode,*datearray)
            except:
                log.msg('{} protocol: Error while packing binary data'.format(self.sensordict.get('protocol')))

            if not self.confdict.get('bufferdirectory','') == '':
                acs.dataToFile(self.confdict.get('bufferdirectory'), sensorid, filename, data_bin, header)
            returndata = ','.join(list(map(str,datearray)))
        else:
            returndata = ''

        return returndata, header


    def lineReceived(self, line):
        topic = self.confdict.get('station') + '/' + self.sensordict.get('sensorid')
        # extract only ascii characters
        line = ''.join(filter(lambda x: x in string.printable, str(line)))

        ok = True
        try:
            data = line.split(',')
            data, head = self.processData(data)
        except:
            print('{}: Data seems not be BM35Data: Looks like {}'.format(self.sensordict.get('protocol'),line))
            ok = False

        if ok:
            senddata = False
            coll = int(self.sensordict.get('stack'))
            if coll > 1:
                self.metacnt = 1 # send meta data with every block
                if self.datacnt < coll:
                    self.datalst.append(data)
                    self.datacnt += 1
                else:
                    senddata = True
                    data = ';'.join(self.datalst)
                    self.datalst = []
                    self.datacnt = 0
            else:
                senddata = True

            if senddata:
                self.client.publish(topic+"/data", data, qos=self.qos)
                if self.count == 0:
                    add = "SensorID:{},StationID:{},DataPier:{},SensorModule:{},SensorGroup:{},SensorDecription:{},DataTimeProtocol:{}".format( self.sensordict.get('sensorid',''),self.confdict.get('station',''),self.sensordict.get('pierid',''),self.sensordict.get('protocol',''),self.sensordict.get('sensorgroup',''),self.sensordict.get('sensordesc',''),self.sensordict.get('ptime','') )
                    self.client.publish(topic+"/dict", add, qos=self.qos)
                    self.client.publish(topic+"/meta", head, qos=self.qos)
                self.count += 1
                if self.count >= self.metacnt:
                    self.count = 0

