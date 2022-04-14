from __future__ import print_function
from __future__ import absolute_import

# ###################################################################
# Import packages
# ###################################################################

import re     # for interpretation of lines
import struct # for binary representation
import socket # for hostname identification
from datetime import datetime, timedelta
from core import acquisitionsupport as acs
from magpy.opt import cred as mpcred
from twisted.python import log

import os
import dateutil.parser as dparser
import urllib.request
import json 


class GICProtocol():
    """
    Protocol to read GIC URL data , data looks like
    [{"client":"gic01","date":"2022-04-13","timeUTC":"16:43:05","temperatureDegC":"34.8","NpcMilliAmps":"120.0434"},{"client":"gic02",... }]

    The protocol defines the sensor name in its init section, which
    is used to dipatch url links and define local storage folders
    
    Add the following line to sensors.cfg:
    gicaut,URL,-,-,-,-,active,None,60,1,GIC,GIC,-,0001,-,different,NTP,spaceweather,geomagnetically induced currents
    #CR1000JC_1_0002,USB0,38400,8,1,N,active,None,2,1,cr1000jc,CR1000JC,02367,0002,-,TEST,NTP,meteorological,snow height



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
        self.revision = sensordict.get('revision')
        self.hostname = socket.gethostname()
        #print ("  -> Sensor: {}".format(self.sensor))
        self.datalst = []
        self.datacnt = 0
        self.metacnt = 10
        self.url = mpcred.lc(self.sensor,'address')
        self.qos=int(confdict.get('mqttqos',0))
        if not self.qos in [0,1,2]:
            self.qos = 0
        log.msg("  -> setting QOS:", self.qos)

    def sendRequest(self):
        #try
        with urllib.request.urlopen(self.url) as url:
            data = json.loads(url.read().decode())
        self.dataReceived(data)
        #expect:
        #log.msg('  -> {} unavailable.'.format(self.sensor))
        

    def processData(self, data):
        """Process GIC URL data """

        if not data:
            log.msg('  -> {} - received empty data structure'.format(self.sensor))
            return {}
        currenttime = datetime.utcnow()
        datadict = {}
        for el in data:
            dataname = el.get("client")
            gic = el.get("NpcMilliAmps")
            sdate = el.get("date")
            stime = el.get("timeUTC")
            temperature = el.get("temperatureDegC")
            # ignore empty and experimental data sets
            if gic and not gic in [555000] and not dataname in ['gic20'] and not sdate in [555000]:
                datatime = dparser.parse("{} {}".format(sdate,stime))
                ###
                filename = datetime.strftime(currenttime, "%Y-%m-%d") # use PC time for buffername
                timestamp = datetime.strftime(datatime, "%Y-%m-%d %H:%M:%S.%f")
                ###
                packcode = '6hLlL'
                sensorid = "{}_{}_{}".format(self.sensor.upper(),dataname.upper(),self.revision)
                header = "# MagPyBin %s %s %s %s %s %s %d" % (sensorid, '[x,t2]', '[GIC,T]', '[mA,degC]', '[10000,10000]', packcode, struct.calcsize('<'+packcode))

                try:
                    gic = float(gic)
                except:
                    gic = 999999
                try:
                    temperature = float(temperature)
                except:
                    temperature = 999999
                try:
                    if not gic==999999:
                        datearray = acs.timeToArray(timestamp)
                        datearray.append(int(gic*1000))
                        datearray.append(int(temperature*1000))
                        data_bin = struct.pack('<'+packcode,*datearray)  #use little endian byte order
                except:
                    log.msg('Error while packing binary data')
                    pass

                if not self.confdict.get('bufferdirectory','') == '':
                    acs.dataToFile(self.confdict.get('bufferdirectory'), sensorid, filename, data_bin, header)
                datadict[sensorid] = {'line': ','.join(list(map(str,datearray))), 'head':header}
                
        return datadict

    def dataReceived(self, data):
        # extract data array and buffer it
        datadict = self.processData(data)
        for dataid in datadict:
            topic = self.confdict.get('station') + '/' + dataid
            datavals = datadict.get(dataid)
            dataline = datavals.get('line')
            datahead = datavals.get('head')

            #ok=True
            #if ok:
            try:
                senddata = False
                coll = int(self.sensordict.get('stack'))
                if coll > 1:
                    self.metacnt = 1 # send meta data with every block
                    if self.datacnt < coll:
                        self.datalst.append(dataline)
                        self.datacnt += 1
                    else:
                        senddata = True
                        dataline = ';'.join(self.datalst)
                        self.datalst = []
                        self.datacnt = 0
                else:
                    senddata = True

                if senddata:
                    self.client.publish(topic+"/data", dataline, qos=self.qos)
                    if self.count == 0:
                        ## 'Add' is a string containing dict info like: 
                        ## SensorID:ENV05_2_0001,StationID:wic, PierID:xxx,SensorGroup:environment,... 
                        add = "SensorID:{},StationID:{},DataPier:{},SensorModule:{},SensorGroup:{},SensorDecription:{},DataTimeProtocol:{}".format( self.sensordict.get('sensorid',''),self.confdict.get('station',''),self.sensordict.get('pierid',''),self.sensordict.get('protocol',''),self.sensordict.get('sensorgroup',''),self.sensordict.get('sensordesc',''),self.sensordict.get('ptime','') )
                        self.client.publish(topic+"/dict", add, qos=self.qos)
                        self.client.publish(topic+"/meta", datahead, qos=self.qos)
                    self.count += 1
                    if self.count >= self.metacnt:
                        self.count = 0
            except:
                log.err('{}: Unable to parse data {}'.format(self.sensordict.get('protocol'), line))


