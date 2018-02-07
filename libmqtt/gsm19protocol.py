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


## GEM -GSM19 protocol
##
class GSM19Protocol(LineReceiver):
    """
    The GSM 19 protocol for extracting RTT data from GSM19
    SETUP of GSM19:
        1.) in the main menu go to C-Info
        2.) in info select B-RS232
        3.) choose BAUD rate of 115200 - press F
        4.) real time RS232 transmission: select yes and press F
        5.) F again, thats it go back to main menu
    Supported modes:
        base
    """

    def __init__(self, client, sensordict, confdict):
        """
        'client' could be used to switch between different publishing protocols
                 (e.g. MQTT or WS-MCU gateway factory) to publish events
        'sensordict' contains a dictionary with all sensor relevant data (sensors.cfg)
        'confdict' contains a dictionary with general configuration parameters (martas.cfg)
        """
        print ("Initialize the connection and set automatic mode (use ser.commands?)")
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
        timestamp = datetime.strftime(currenttime, "%Y-%m-%d %H:%M:%S.%f")
        intensity = 88888.8
        typ = "none"
        dontsavedata = False

        packcode = '6hLLl'
        header = "# MagPyBin %s %s %s %s %s %s %d" % (self.sensor, '[f,var1]', '[f,err]', '[nT,none]', '[1000,1000]', packcode, struct.calcsize(packcode))

        try:
            # Extract data
            #data_array = data.strip().split()
            data_array = data
            if len(data_array) == 3:
                typ = "valid"
            # add other types here
        except:
            log.err('GSM19 - Protocol: Output format not supported - use either base, ... or mobile')

        # Extracting the data from the station
        # Extrat time info and use as primary if GPS is on (in this case PC time is secondary)
        #                          PC is primary when a GPS is not connected

        if typ == "valid": # Comprises Mobile and Base Station mode with single sensor and no GPS
            intensity = float(data_array[1])
            #print "Intensity", intensity
            # Extracting time from instrument - put that to the primary time column?
            systemtime = datetime.strptime(date+"-"+data_array[0], "%Y-%m-%d-%H%M%S.%f")
            #print "Times:", systemtime, timestamp
            # Test whether data_array[2] == int
            if len(data_array[2]) < 3:
                typ = "base"
                errorcode = int(data_array[2])
            else:
                typ = "gradient"
                gradient = float(data_array[2])
        elif typ == "none":
            dontsavedata = True
            pass

        try:
            if not typ == "none":
                # extract time data
                datearray = timeToArray(timestamp)
                try:
                    datearray.append(int(intensity*1000.))
                    if typ == 'base':
                        datearray.append(int(errorcode*1000.))
                    else:
                        datearray.append(int(gradient*1000.))
                    data_bin = struct.pack(packcode,*datearray)
                except:
                    log.msg('GSM19 - Protocol: Error while packing binary data')
                    pass
        except:
            log.msg('GSM19 - Protocol: Error with binary save routine')
            pass

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
                self.client.publish(topic+"/data", data, qos=self.qos)
                if self.count == 0:
                    self.client.publish(topic+"/meta", head, qos=self.qos)
                    ## 'Add' is a string containing dict info like: 
                    ## SensorID:ENV05_2_0001,StationID:wic, PierID:xxx,SensorGroup:environment,... 
                    add = "SensoriD:{},StationID:{},DataPier:{},SensorModule:{},SensorGroup:{},SensorDecription:{},DataTimeProtocol:{}".format( self.sensordict.get('sensorid',''),self.confdict.get('station',''),self.sensordict.get('pierid',''),self.sensordict.get('protocol',''),self.sensordict.get('sensorgroup',''),self.sensordict.get('sensordesc',''),self.sensordict.get('ptime','') )
                    self.client.publish(topic+"/dict", add, qos=self.qos)
                self.count += 1
                if self.count >= self.metacnt:
                    self.count = 0            
        except:
            log.err('{}: Unable to parse data {}'.format(self.sensordict.get('protocol'), line))

