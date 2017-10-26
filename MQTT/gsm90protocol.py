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

#import sys, time, os
#import binascii, csv


## GEM -GSM90 protocol
##
class GSM90Protocol(LineReceiver):
    """
    Protocol to read GSM90 data
    This protocol defines the individual sensor related read process. 
    It is used to dipatch url links containing specific data.
    Sensor specific coding is contained in method "processData".
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

    def connectionMade(self):
        log.msg('  -> {} connected.'.format(self.sensor))

    def connectionLost(self, reason):
        log.msg('  -> {} lost.'.format(self.sensor))

    def processData(self, data):
        """ GSM90 data """
        currenttime = datetime.utcnow()
        outdate = datetime.strftime(currenttime, "%Y-%m-%d")
        actualtime = datetime.strftime(currenttime, "%Y-%m-%dT%H:%M:%S.%f")
        outtime = datetime.strftime(currenttime, "%H:%M:%S")
        timestamp = datetime.strftime(currenttime, "%Y-%m-%d %H:%M:%S.%f")
        filename = outdate
        sensorid = self.sensor
        packcode = '6hLLL6hL'
        header = "# MagPyBin %s %s %s %s %s %s %d" % (self.sensor, '[f,var1,sectime]', '[f,errorcode,internaltime]', '[nT,none,none]', '[1000,1,1]', packcode, struct.calcsize(packcode))

        try:
            # Extract data
            # old data looks like 04-22-2015 142244  48464.53 99
            data_array = data.strip().split()
            if len(data_array) == 4:
                intensity = float(data_array[2])
                err_code = int(data_array[3])
                try:
                    try:
                        internal_t = datetime.strptime(data_array[0]+'T'+data_array[1], "%m-%d-%YT%H%M%S.%f")
                    except:
                        internal_t = datetime.strptime(data_array[0]+'T'+data_array[1], "%m-%d-%YT%H%M%S")
                    internal_time = datetime.strftime(internal_t, "%Y-%m-%d %H:%M:%S.%f")
                except:
                    internal_time = timestamp #datetime.strftime(datetime.utcnow(), "%Y-%m-%d %H:%M:%S.%f")
                #print internal_time
            else:
                err_code = 0
                intensity = float(data_array[0])
                internal_time = timestamp #datetime.strftime(datetime.utcnow(), "%Y-%m-%d %H:%M:%S")
        except:
            log.err('{} protocol: Data formatting error. Data looks like: {}'.format(self.sensordict.get('protocol'),data))

        try:
            # Analyze time difference between GSM internal time and utc from PC
            timediff = interal_t-currenttime
            log.msg("timediff: {}".format(timediff))
            #if timediff > threshold:
            #    self.errorcnt.get('time') +=1
            #    if self.errorcnt.get('time') < 3:
            #        log.msg("timediff: {}".format(timediff))
            #else:
            #    self.errorcnt.get('time') = 0
        except:
            pass

        try:
            ## GSM90 does not provide any info on whether the GPS reading is OK or not
            gps = True
            if gps:
                baktimestamp = timestamp
                timestamp = internal_time
                internal_time = baktimestamp

            # extract time data
            datearray = acs.timeToArray(timestamp)
            try:
                datearray.append(int(intensity*1000.))
                datearray.append(err_code)
                #print timestamp, internal_time
                internalarray = acs.timeToArray(internal_time)
                datearray.extend(internalarray)
                data_bin = struct.pack(packcode,*datearray)
            except:
                log.msg('{} protocol: Error while packing binary data'.format(self.sensordict.get('protocol')))

            if not self.confdict.get('bufferdirectory','') == '':
                acs.dataToFile(self.confdict.get('bufferdirectory'), sensorid, filename, data_bin, header)

        except:
            log.msg('{} protocol: Error with binary save routine'.format(self.sensordict.get('protocol')))


        return ','.join(list(map(str,datearray))), header


    def lineReceived(self, line):

        topic = self.confdict.get('station') + '/' + self.sensordict.get('sensorid')
        # extract only ascii characters 
        line = ''.join(filter(lambda x: x in string.printable, line))

        #try:
        ok = True
        if ok:
            try:
                data = line.split()
                data, head = self.processData(data)
            except:
                print('{}: Data seems not be GSM90Data: Looks like {}'.format(self.sensordict.get('protocol'),line))

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
                self.count += 1
                if self.count >= self.metacnt:
                    self.count = 0

