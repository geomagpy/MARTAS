from __future__ import print_function
from __future__ import absolute_import

# ###################################################################
# Import packages
# ###################################################################

import re     # for interpretation of lines
import struct # for binary representation
import socket # for hostname identification
import string # for ascii selection
import numpy as np
from datetime import datetime, timedelta
from twisted.protocols.basic import LineReceiver
from twisted.python import log
from core import acquisitionsupport as acs

## vehicle detector protocol
##
class vehicledetectorProtocol(LineReceiver):
    """
    The vehicle detector protocol for extracting RTT data from 
    vehicle detector by Department of Measurement, Fakulta elektrotechnicka, cvut.cz, Praha
      contains a pair of HMC1021 single-axis AMR sensors in 75mm distance.
    SETUP:
        1.) a transceiver like ST3485 is useful for the RS485 interface
        2.) data stream comes permanently, 62.5 Samples/s
        3.) BAUD rate 230400, parity even 
    Data format: ASCII "Sxxxxxxx Syyyyyyy\r\n" where S are signs, x are sensor S1
      measurement and y sensor S2 measurement, both in nT
    NTP time of the PC when data is received by serial comm.
    """

    def __init__(self, client, sensordict, confdict):
        """
        'client' could be used to switch between different publishing protocols
                 (e.g. MQTT or WS-MCU gateway factory) to publish events
        'sensordict' contains a dictionary with all sensor relevant data (sensors.cfg)
        'confdict' contains a dictionary with general configuration parameters (martas.cfg)
        """
        print ("  -> Initializing Vehicle Detector...")
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
        self.metacnt = 100
        self.errorcnt = {'time':0}
        self.timesource = self.sensordict.get('ptime','')
        self.delaylist = []  # delaylist contains up to 1000 diffs between gps and ntp
                             # the median of this values is used for ntp timedelay
        self.timedelay = 0.0
        #self.timethreshold = 3 # secs - waring if timedifference is larger the 3 seconds

        # QOS
        self.qos=int(confdict.get('mqttqos',0))
        if not self.qos in [0,1,2]:
            self.qos = 0
        log.msg("  -> setting QOS:", self.qos)

    def connectionMade(self):
        log.msg('  -> {} connected.'.format(self.sensor))

    def connectionLost(self, reason):
        log.msg('  -> {} lost.'.format(self.sensor))

    def processData(self, data):

        currenttime = datetime.utcnow()
        date = datetime.strftime(currenttime, "%Y-%m-%d")
        actualtime = datetime.strftime(currenttime, "%Y-%m-%dT%H:%M:%S.%f")
        outtime = datetime.strftime(currenttime, "%H:%M:%S")
        filename = date
        timestamp = datetime.strftime(currenttime, "%Y-%m-%d %H:%M:%S.%f")
        amr1 = 88888.8
        amr2 = 88888.8
        grad = 88888.8
        typ = "none"
        dontsavedata = False

        packcode = '6hLlll'
        header = "# MagPyBin %s %s %s %s %s %s %d" % (self.sensor, '[var1,var2,var3]', '[amr1,amr2,grad]', '[nT,nT,nT]', '[1,1,1]', packcode, struct.calcsize('<'+packcode))

        try:
            # Extract data
            data_array = data
            if len(data_array) == 2:
                typ = "valid"
            else:
                typ = "none"
            # add other types here
        except:
            log.err('Vehicle Detector - Protocol: Error while receiving data')

        # Extracting the data from the sensor

        if typ == "valid": 
            amr1 = int(data_array[0])
            amr2 = int(data_array[1])
            grad = amr2 - amr1
            systemtime = currenttime
            self.timesource = 'NTP'
        elif typ == "none":
            dontsavedata = True
            pass

        try:
            if not typ == "none":
                # extract time data
                datearray = acs.datetime2array(systemtime)
                try:
                    datearray.append(int(amr1*1))
                    datearray.append(int(amr2*1))
                    datearray.append(int(grad*1))
                    data_bin = struct.pack('<'+packcode,*datearray)
                except:
            else:
                    log.msg('Vehicle Detector - Protocol: Error while packing binary data')
                    pass
        except:
            log.msg('Vehicle Protocol - Protocol: Error with binary save routine')
            pass

        if not self.confdict.get('bufferdirectory','') == '':
            acs.dataToFile(self.confdict.get('bufferdirectory'), self.sensor, filename, data_bin, header)

        return ','.join(list(map(str,datearray))), header


    def lineReceived(self, line):
        topic = self.confdict.get('station') + '/' + self.sensordict.get('sensorid')
        # extract only ascii characters
        line = ''.join(filter(lambda x: x in string.printable, str(line)))

        ok = True
        try:
            data = line.split()
            if len(data) >= 2:
                data, head = self.processData(data)
            else:
                log.msg('{}: Data seems not to be appropriate vehicle detector data. Received data looks like: {}'.format(self.sensordict.get('protocol'),line))
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
                        add = "SensorID:{},StationID:{},DataPier:{},SensorModule:{},SensorGroup:{},SensorDecription:{},DataTimeProtocol:{},DataNTPTimeDelay:{}".format( self.sensordict.get('sensorid',''),self.confdict.get('station',''),self.sensordict.get('pierid',''),self.sensordict.get('protocol',''),self.sensordict.get('sensorgroup',''),self.sensordict.get('sensordesc',''),self.timesource, self.timedelay )
                        self.client.publish(topic+"/dict", add, qos=self.qos)
                        self.client.publish(topic+"/meta", head, qos=self.qos)
                    self.count += 1
                    if self.count >= self.metacnt:
                        self.count = 0            
        except:
            log.err('{}: Unable to parse data {}'.format(self.sensordict.get('protocol'), line))

