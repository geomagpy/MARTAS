from __future__ import print_function
from __future__ import absolute_import

# ###################################################################
# Import packages
# ###################################################################

import re     # for interpretation of lines
import struct # for binary representation
import socket # for hostname identification
import string # for ascii selection
import sys
import numpy as np
from datetime import datetime, timedelta
from twisted.protocols.basic import LineReceiver
from twisted.python import log
from core import acquisitionsupport as acs


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

    Treatment of GPS and NTP time:
    The protocol determines two times: 1) GPS time provided by the data logger
    2) NTP time of the PC when data is received by serial comm.
    Primary time is selected in sensor.cfg (either NTP or GPS)
    Timediff between GPS and NTP is recorded, and a 1000 line median average is send
    within the DataDictionary (DataNTPTimeDelay).
    Besides, a waring message is generated if NTP and GPS times differ by more than 3 seconds.
    For this comparison (and only here) a typical correction (delay) value is applied to NTP.
    e.g. 6.2 sec for POS1.
    """

    def __init__(self, client, sensordict, confdict):
        """
        'client' could be used to switch between different publishing protocols
                 (e.g. MQTT or WS-MCU gateway factory) to publish events
        'sensordict' contains a dictionary with all sensor relevant data (sensors.cfg)
        'confdict' contains a dictionary with general configuration parameters (martas.cfg)
        """
        print ("  -> Initializing GSM19...")
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
        self.timesource = self.sensordict.get('ptime','')
        self.delaylist = []  # delaylist contains up to 1000 diffs between gps and ntp
                             # the median of this values is used for ntp timedelay
        self.timedelay = 0.0
        self.timethreshold = 3 # secs - waring if timedifference is larger the 3 seconds

        # QOS
        self.qos=int(confdict.get('mqttqos',0))
        if not self.qos in [0,1,2]:
            self.qos = 0
        log.msg("  -> setting QOS:", self.qos)
        # PYTHON version
        self.pvers = sys.version_info[0]

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
        intensity = 88888.8
        typ = "none"
        dontsavedata = False

        packcode = '6hLLl6hL'
        header = "# MagPyBin %s %s %s %s %s %s %d" % (self.sensor, '[f,var1,sectime]', '[f,err,sectime]', '[nT,none,none]', '[1000,1000,1]', packcode, struct.calcsize('<'+packcode))

        try:
            # Extract data
            data_array = data
            if len(data_array) == 2:
                typ = "oldbase"
            elif len(data_array) == 3:
                typ = "valid"
            # add other types here
        except:
            log.err('GSM19 - Protocol: Output format not supported - use either base, ... or mobile')

        # Extracting the data from the station
        # Extrat time info and use as primary if GPS is on (in this case PC time is secondary)
        #                          PC is primary when a GPS is not connected

        if typ == "valid" or typ == "oldbase": # Comprises Mobile and Base Station mode with single sensor and no GPS
            intensity = float(data_array[1])
            try:
                systemtime = datetime.strptime(date+"-"+data_array[0], "%Y-%m-%d-%H%M%S.%f")
            except:
                # This exception happens for old GSM19 because time is
                # provided e.g. as 410356 instead of 170356 for 17:03:56 (Thursday)
                # e.g 570301.0 instead of 09:03:01 (Friday)
                try:
                    hournum = int(data_array[0][:-6])
                    rest = data_array[0][-6:]
                    factor = np.floor(hournum/24.) # factor = days since starting
                    hour = int(hournum - factor*24.)
                    systemtime = datetime.strptime(date+"-"+str(hour)+rest, "%Y-%m-%d-%H%M%S.%f")
                    #print ("Got oldbase systemtime")
                except:
                    systemtime = currenttime
                    self.timesource = 'NTP'
            if len(data_array) == 2:
                typ = "base"
                errorcode = 99
            elif len(data_array[2]) == 3:
                typ = "base"
                errorcode = int(data_array[2])
            else:
                typ = "gradient"
                gradient = float(data_array[2])
        elif typ == "none":
            dontsavedata = True
            pass

        gpstime = datetime.strftime(systemtime, "%Y-%m-%d %H:%M:%S.%f")

        try:
            # Analyze time difference between GSM internal time and utc from PC
            timelist = sorted([systemtime,currenttime])
            timediff = timelist[1]-timelist[0]
            #secdiff = timediff.seconds + timediff.microseconds/1E6
            delta = timediff.total_seconds()
            if not delta in [0.0, np.nan, None]:
                self.delaylist.append(timediff.total_seconds())
                self.delaylist = self.delaylist[-1000:]
            if len(self.delaylist) > 100:
                try:
                    self.timedelay = np.median(np.asarray(self.delaylist))
                except:
                    self.timedelay = 0.0
            if delta > self.timethreshold:
                self.errorcnt['time'] +=1
                if self.errorcnt.get('time') < 2:
                    log.msg("{} protocol: large time difference observed for {}: {} sec".format(self.sensordict.get('protocol'), sensorid, secdiff))
            else:
                self.errorcnt['time'] = 0
        except:
            pass

        if self.sensordict.get('ptime','') in ['NTP','ntp']:
            secondtime = gpstime
            maintime = timestamp
        else:
            maintime = gpstime
            secondtime = timestamp

        try:
            if not typ == "none":
                # extract time data
                datearray = acs.timeToArray(maintime)
                try:
                    datearray.append(int(intensity*1000.))
                    if typ == 'base':
                        datearray.append(int(errorcode*1000.))
                    else:
                        datearray.append(int(gradient*1000.))
                    internalarray = acs.timeToArray(secondtime)
                    datearray.extend(internalarray)
                    data_bin = struct.pack('<'+packcode,*datearray)
                except:
                    log.msg('GSM19 - Protocol: Error while packing binary data')
                    pass
        except:
            log.msg('GSM19 - Protocol: Error with binary save routine')
            pass

        if not self.confdict.get('bufferdirectory','') == '':
            acs.dataToFile(self.confdict.get('bufferdirectory'), self.sensor, filename, data_bin, header)

        return ','.join(list(map(str,datearray))), header


    def lineReceived(self, line):
        topic = self.confdict.get('station') + '/' + self.sensordict.get('sensorid')
        if self.pvers > 2:
            line=line.decode('ascii')
        # extract only ascii characters
        line = ''.join(filter(lambda x: x in string.printable, str(line)))

        ok = True
        try:
            data = line.split()
            if len(data) >= 2:
                data, head = self.processData(data)
            else:
                log.msg('{}: Data seems not to be appropriate G19 data. Received data looks like: {}'.format(self.sensordict.get('protocol'),line))
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
