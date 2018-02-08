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

        self.delaylist = []  # delaylist contains up to 1000 diffs between gps and ntp
                             # the median of this values is used for ntp timedelay
        self.timedelay = 0.0
        self.timethreshold = 3 # secs - waring if timedifference is larger the 3 seconds

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
        """ GSM90 data """
        currenttime = datetime.utcnow()
        outdate = datetime.strftime(currenttime, "%Y-%m-%d")
        actualtime = datetime.strftime(currenttime, "%Y-%m-%dT%H:%M:%S.%f")
        outtime = datetime.strftime(currenttime, "%H:%M:%S")
        timestamp = datetime.strftime(currenttime, "%Y-%m-%d %H:%M:%S.%f")
        filename = outdate
        sensorid = self.sensor
        packcode = '6hLLL6hL'
        header = "# MagPyBin %s %s %s %s %s %s %d" % (self.sensor, '[f,var1,sectime]', '[f,errorcode,internaltime]', '[nT,none,none]', '[1000,1,1]', packcode, struct.calcsize('<'+packcode))

        try:
            # Extract data
            # old data looks like 04-22-2015 142244  48464.53 99
            data_array = data
            if len(data) == 4:
                intensity = float(data[2])
                err_code = int(data[3])
                try:
                    try:
                        internal_t = datetime.strptime(data[0]+'T'+data[1], "%m-%d-%YT%H%M%S.%f")
                    except:
                        internal_t = datetime.strptime(data[0]+'T'+data[1], "%m-%d-%YT%H%M%S")
                    internal_time = datetime.strftime(internal_t, "%Y-%m-%d %H:%M:%S.%f")
                except:
                    internal_time = timestamp #datetime.strftime(datetime.utcnow(), "%Y-%m-%d %H:%M:%S.%f")
                #print internal_time
            elif len(data) == 3: # GSM v7.0
                intensity = float(data[1])                
                err_code = int(data[2])
                try:
                    internal_t = datetime.strptime(outdate+'T'+data[0], "%Y-%m-%dT%H%M%S.%f")
                    internal_time = datetime.strftime(internal_t, "%Y-%m-%d %H:%M:%S.%f")
                except:
                    internal_time = timestamp #datetime.strftime(datetime.utcnow(), "%Y-%m-%d %H:%M:%S.%f")
            else:
                err_code = 0
                intensity = float(data[0])
                internal_time = timestamp #datetime.strftime(datetime.utcnow(), "%Y-%m-%d %H:%M:%S")
        except:
            log.err('{} protocol: Data formatting error. Data looks like: {}'.format(self.sensordict.get('protocol'),data))

        try:
            # Analyze time difference between GSM internal time and utc from PC
            timelist = sorted([internal_t,currenttime])
            timediff = timelist[1]-timelist[0]
            #secdiff = timediff.seconds + timediff.microseconds/1E6
            #timethreshold = 3
            delta = timediff.total_seconds()
            if not delta in [0.0, np.nan, None]:
                self.delaylist.append(timediff.total_seconds())
                self.delaylist = self.delaylist[-1000:]
            if len(self.delaylist) > 100:
                try:
                    self.timedelay = np.median(np.asarray(self.delaylist))
                except:
                    self.timedelay = 0.0
            #if secdiff > timethreshold:
            if delta > self.timethreshold:
                self.errorcnt['time'] +=1
                if self.errorcnt.get('time') < 2:
                    log.msg("{} protocol: large time difference observed for {}: {} sec".format(self.sensordict.get('protocol'), sensorid, secdiff))
            else:
                self.errorcnt['time'] = 0 
        except:
            pass

        if self.sensordict.get('ptime','') in ['NTP','ntp']:
            secondtime = internal_time
            maintime = timestamp
        else:
            maintime = internal_time
            secondtime = timestamp

        try:
            ## GSM90 does not provide any info on whether the GPS reading is OK or not

            # extract time data
            datearray = acs.timeToArray(maintime)
            try:
                datearray.append(int(intensity*1000.))
                datearray.append(err_code)
                #print timestamp, internal_time
                internalarray = acs.timeToArray(secondtime)
                datearray.extend(internalarray)
                data_bin = struct.pack('<'+packcode,*datearray)
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

        ok = True
        try:
            data = line.split()
            data, head = self.processData(data)
        except:
            print('{}: Data seems not be GSM90Data: Looks like {}'.format(self.sensordict.get('protocol'),line))
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

