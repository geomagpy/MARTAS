#!/usr/bin/env python
# ###################################################################
# Import packages
# ###################################################################

import struct # for binary representation
import socket # for hostname identification
import string # for ascii selection
from datetime import datetime, timezone
from twisted.python import log
from martas.core import methods as mm

from random import randint

"""
TestProtocol:
a typical sensors input would look like:
TEST_1234_0001,USB0,57600,8,1,N,active,,-,1,Test,Test,1234,0001,-,MyPier,NTP,Test environment
"""

class TestProtocol(object):
    """
    Protocol to simulate a record. Test is an active protocol.
    It will create a random number between 40 and 60 and send it at regular intervals.
    To be used for testing procedures.
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
        self.qos=int(confdict.get('mqttqos',0))
        if not self.qos in [0,1,2]:
            self.qos = 0
        log.msg("  -> setting QOS:", self.qos)

    def processData(self, data):
        """Processing test data """

        currenttime = datetime.now(timezone.utc).replace(tzinfo=None)
        outdate = datetime.strftime(currenttime, "%Y-%m-%d")
        filename = outdate
        timestamp = datetime.strftime(currenttime, "%Y-%m-%d %H:%M:%S.%f")
        packcode = '6hLl'
        sensorid = self.sensor
        header = "# MagPyBin %s %s %s %s %s %s %d" % (sensorid, '[x]', '[RN]', '[random]', '[1000]', packcode, struct.calcsize('<'+packcode))
        datearray = mm.time_to_array(timestamp)
        data_bin = None

        try:
            datearray.append(int(data*1000))
            data_bin = struct.pack('<'+packcode,*datearray)  #use little endian byte order
        except:
            log.msg('Error while packing binary data')
            pass

        if not self.confdict.get('bufferdirectory','') == '' and data_bin:
            mm.data_to_file(self.confdict.get('bufferdirectory'), sensorid, filename, data_bin, header)
        return ','.join(list(map(str,datearray))), header

    def sendRequest(self):
        topic = self.confdict.get('station') + '/' + self.sensordict.get('sensorid')
        value = 50. + (randint(-9, 9)) + 1./float(randint(1, 9))
        try:
            data, head = self.processData(value)

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

            print (topic, data, senddata)
            if senddata:
                self.client.publish(topic+"/data", data, qos=self.qos)
                if self.count == 0:
                    ## 'Add' is a string containing dict info like: 
                    ## SensorID:ENV05_2_0001,StationID:wic, PierID:xxx,SensorGroup:environment,... 
                    add = "SensorID:{},StationID:{},DataPier:{},SensorModule:{},SensorGroup:{},SensorDecription:{},DataTimeProtocol:{}".format( self.sensordict.get('sensorid',''),self.confdict.get('station',''),self.sensordict.get('pierid',''),self.sensordict.get('protocol',''),self.sensordict.get('sensorgroup',''),self.sensordict.get('sensordesc',''),self.sensordict.get('ptime','') )
                    self.client.publish(topic+"/dict", add, qos=self.qos)
                    self.client.publish(topic+"/meta", head, qos=self.qos)
                self.count += 1
                if self.count >= self.metacnt:
                    self.count = 0
        except:
            log.err('{}: Unable to parse data {}'.format(self.sensordict.get('protocol'), value))
