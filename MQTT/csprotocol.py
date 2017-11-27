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
from magpy.acquisition import acquisitionsupport as acs

import os


## Caesium protocol
##
class CsProtocol(LineReceiver):
    """
    Protocol to read Geometrics CS Sensor data from serial unit
    Each sensor has its own class (that can be improved...)
    The protocol defines the sensor name in its init section, which
    is used to dipatch url links and define local storage folders

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

    def connectionMade(self):
        log.msg('  -> {} connected.'.format(self.sensor))

    def connectionLost(self, reason):
        log.msg('  -> {} lost.'.format(self.sensor))


    def processData(self, data):
        """Convert raw ADC counts into SI units as per datasheets"""

        currenttime = datetime.utcnow()
        # Correction for ms time to work with databank:
        currenttime_ms = currenttime.microsecond/1000000.
        ms_rounded = round(float(currenttime_ms),3)
        if not ms_rounded >= 1.0:
            currenttime = currenttime.replace(microsecond=int(ms_rounded*1000000.))
        else:
            currenttime = currenttime.replace(microsecond=0) + timedelta(seconds=1.0)
        filename = datetime.strftime(currenttime, "%Y-%m-%d")
        actualtime = datetime.strftime(currenttime, "%Y-%m-%dT%H:%M:%S.%f")
        lastActualtime = currenttime
        outtime = datetime.strftime(currenttime, "%H:%M:%S")
        timestamp = datetime.strftime(currenttime, "%Y-%m-%d %H:%M:%S.%f")

        packcode = '6hLL'
        header = "# MagPyBin %s %s %s %s %s %s %d" % (self.sensor, '[f]', '[f]', '[nT]', '[1000]', packcode, struct.calcsize(packcode))

        try:
            value = float(data[0].strip('$'))
            if 10000 < value < 100000:
                intensity = value
            else:
                intensity = 88888.0
        except ValueError:
            log.err("CS - Protocol: Not a number. Instead found:", data[0])
            intensity = 88888.0

        try:
            datearray = asc.timeToArray(timestamp)
            datearray.append(int(intensity*1000))
            data_bin = struct.pack(packcode,*datearray)
        except:
            log.msg('Error while packing binary data')
            pass

        #return value every second
        #if lastActualtime+timedelta(microseconds=999000) <= currenttime:   # Using ms instead of s accounts for only small errors, not all.

        if not self.confdict.get('bufferdirectory','') == '':
            acs.dataToFile(self.confdict.get('bufferdirectory'), sensorid, filename, data_bin, header)

        return ','.join(list(map(str,datearray))), header


    def lineReceived(self, line):

        topic = self.confdict.get('station') + '/' + self.sensordict.get('sensorid')
        # extract only ascii characters 
        line = ''.join(filter(lambda x: x in string.printable, line))

        try:
            data = line.split()
            if len(data) == 3:
                data, head = self.processData(data)
            else:
                log.msg('{}: Data seems not be appropriate data. Received data looks like: {}'.format(self.sensordict.get('protocol'),line))

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
                self.client.publish(topic+"/data", data)
                if self.count == 0:
                    self.client.publish(topic+"/meta", head)
                    ## 'Add' is a string containing dict info like: 
                    ## SensorID:ENV05_2_0001,StationID:wic, PierID:xxx,SensorGroup:environment,... 
                    add = "SensoriD:{},StationID:{},DataPier:{},SensorModule:{},SensorGroup:{},SensorDecription:{},DataTimeProtocol:{}".format( self.sensordict.get('sensorid',''),self.confdict.get('station',''),self.sensordict.get('pierid',''),self.sensordict.get('protocol',''),self.sensordict.get('sensorgroup',''),self.sensordict.get('sensordesc',''),self.sensordict.get('ptime','') )
                    self.client.publish(topic+"/dict", add)
                self.count += 1
                if self.count >= self.metacnt:
                    self.count = 0            
        except:
            log.err('{}: Unable to parse data {}'.format(self.sensordict.get('protocol'), line))

