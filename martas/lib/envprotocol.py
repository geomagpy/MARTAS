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
from datetime import datetime
from twisted.protocols.basic import LineReceiver
from twisted.python import log
from martas.core import acquisitionsupport as acs


class EnvProtocol(LineReceiver):
    """
    Protocol to read MessPC EnvironmentalSensor 5 data from usb unit
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
        """Process Environment data """

        currenttime = datetime.utcnow()
        outdate = datetime.strftime(currenttime, "%Y-%m-%d")
        filename = outdate
        actualtime = datetime.strftime(currenttime, "%Y-%m-%dT%H:%M:%S.%f")
        outtime = datetime.strftime(currenttime, "%H:%M:%S")
        timestamp = datetime.strftime(currenttime, "%Y-%m-%d %H:%M:%S.%f")
        packcode = '6hLllL'
        sensorid = self.sensor
        header = "# MagPyBin %s %s %s %s %s %s %d" % (sensorid, '[t1,t2,var1]', '[T,DewPoint,RH]', '[degC,degC,per]', '[1000,1000,1000]', packcode, struct.calcsize('<'+packcode))

        valrh = re.findall(r'\d+',data[0])
        if len(valrh) > 1:
            temp = float(valrh[0] + '.' + valrh[1])
        else:
            temp = float(valrh[0])
        valrh = re.findall(r'\d+',data[1])
        if len(valrh) > 1:
            rh = float(valrh[0] + '.' + valrh[1])
        else:
            rh = float(valrh[0])
        valrh = re.findall(r'\d+',data[2])
        if len(valrh) > 1:
            dew = float(valrh[0] + '.' + valrh[1])
        else:
            dew = float(valrh[0])

        try:
            datearray = acs.timeToArray(timestamp)
            datearray.append(int(temp*1000))
            datearray.append(int(dew*1000))
            datearray.append(int(rh*1000))
            data_bin = struct.pack('<'+packcode,*datearray)  #use little endian byte order
        except:
            log.msg('Error while packing binary data')
            pass

        if not self.confdict.get('bufferdirectory','') == '':
            acs.dataToFile(self.confdict.get('bufferdirectory'), sensorid, filename, data_bin, header)
        return ','.join(list(map(str,datearray))), header

    def lineReceived(self, line):
        topic = self.confdict.get('station') + '/' + self.sensordict.get('sensorid')
        if self.pvers > 2:
            line=line.decode('latin')
        line = ''.join(filter(lambda x: x in string.printable, str(line)))

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
                    ## 'Add' is a string containing dict info like:
                    ## SensorID:ENV05_2_0001,StationID:wic, PierID:xxx,SensorGroup:environment,...
                    add = "SensorID:{},StationID:{},DataPier:{},SensorModule:{},SensorGroup:{},SensorDecription:{},DataTimeProtocol:{}".format( self.sensordict.get('sensorid',''),self.confdict.get('station',''),self.sensordict.get('pierid',''),self.sensordict.get('protocol',''),self.sensordict.get('sensorgroup',''),self.sensordict.get('sensordesc',''),self.sensordict.get('ptime','') )
                    self.client.publish(topic+"/dict", add, qos=self.qos)
                    self.client.publish(topic+"/meta", head, qos=self.qos)
                self.count += 1
                if self.count >= self.metacnt:
                    self.count = 0
        except:
            log.err('{}: Unable to parse data {}'.format(self.sensordict.get('protocol'), line))
