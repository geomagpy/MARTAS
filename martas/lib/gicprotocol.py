
# ###################################################################
# Import packages
# ###################################################################

import struct # for binary representation
import socket # for hostname identification
from datetime import datetime, timezone, timedelta
from martas.core import methods as mm
from magpy.opt import cred as mpcred
from twisted.python import log

import dateutil.parser as dparser
import urllib.request
import json 


class GICProtocol():
    """
    Protocol to read GIC URL data , data looks like
    [{"client":"gic01","date":"2022-04-13","timeUTC":"16:43:05","temperatureDegC":"34.8","NpcMilliAmps":"120.0434"},{"client":"gic02",... }]

    The protocol defines the sensor name in its init section, which
    is used to dispatch url links and define local storage folders

    URLs are then taken from magpy credentials by extracting the address for the given sensor name. So you first need
    to add access credentials as follows:
    addcred -t transfer -c gicaut -u USERNAME -p PASSWORD -a https://URL.TO.GIC.DATA:PORT

    Add the following line to sensors.cfg to request new data every 60 seconds:
    gicaut,URL,-,-,-,-,active,None,60,1,GIC,GIC,-,0001,-,different,NTP,spaceweather,geomagnetically induced currents


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
        self.debug = False

    def sendRequest(self):

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
        currenttime = datetime.now(timezone.utc).replace(tzinfo=None)
        datadict = {}
        for el in data:
            #if self.debug:
            #print ("ANALYSIS", el)
            dataname = el.get("client")
            gicval = str(el.get("NpcMilliAmps")) # can be a single value, string with ; and an integer
            #print (gicval)
            giclist = gicval.split(";")
            sdate = el.get("date")
            stime = el.get("timeUTC")
            temperature = el.get("temperatureDegC")
            cnt = len(giclist)
            lines = []
            packcode = '6hLll'
            sensorid = "{}_{}_{}".format(self.sensor.upper(), dataname.upper(), self.revision)
            header = "# MagPyBin %s %s %s %s %s %s %d" % (sensorid, '[x,t2]', '[GIC,T]', '[mA,degC]', '[10000,10000]',
                                                          packcode, struct.calcsize('<' + packcode))
            for i,gic in enumerate(giclist):
                # ignore empty and experimental data sets
                gic = float(gic)
                if gic and not gic in [555000] and not dataname in ['gic20'] and not sdate in [555000]:
                    datearray = []
                    data_bin = None
                    if self.debug:
                        print (" i, len and datecorr", i, len(giclist), len(giclist)-(i+1))
                    datatime = dparser.parse("{} {}".format(sdate,stime))-timedelta(seconds=(len(giclist)-(i+1)))
                    ###
                    filename = datetime.strftime(currenttime, "%Y-%m-%d") # use PC time for buffername
                    timestamp = datetime.strftime(datatime, "%Y-%m-%d %H:%M:%S.%f")
                    ###

                    try:
                        gic = float(gic)
                    except:
                        gic = 999999
                    try:
                        temperature = float(temperature)
                    except:
                        temperature = 999999
                    try:
                        if self.debug:
                            print ("Writing:", sensorid, timestamp, gic, temperature)
                        if not gic==999999:
                            datearray = mm.time_to_array(timestamp)
                            datearray.append(int(gic*1000))
                            datearray.append(int(temperature*1000))
                            data_bin = struct.pack('<'+packcode,*datearray)  #use little endian byte order
                    except:
                        log.msg('Error while packing binary data')
                        pass

                    if not self.confdict.get('bufferdirectory','') == '' and data_bin:
                        mm.data_to_file(self.confdict.get('bufferdirectory'), sensorid, filename, data_bin, header)
                    if datearray:
                        lines.append(','.join(list(map(str,datearray))))
                #print (lines, header)
                datadict[sensorid] = {'lines': lines, 'head':header}

        return datadict

    def dataReceived(self, data):
        # extract data array and buffer it
        datadict = self.processData(data)
        for dataid in datadict:
            topic = self.confdict.get('station') + '/' + dataid
            datavals = datadict.get(dataid)
            datalines = datavals.get('lines')
            datahead = datavals.get('head')

            #ok=True
            #if ok:
            try:
                senddata = True

                if senddata:
                    if self.count >= self.metacnt:
                        self.count = 0
                    for dataline in datalines:
                        self.client.publish(topic+"/data", dataline, qos=self.qos)
                    if self.count == 0:
                        ## 'Add' is a string containing dict info like:
                        ## SensorID:ENV05_2_0001,StationID:wic, PierID:xxx,SensorGroup:environment,... 
                        add = "SensorID:{},StationID:{},DataPier:{},SensorModule:{},SensorGroup:{},SensorDescription:{},DataTimeProtocol:{}".format( self.sensordict.get('sensorid',''),self.confdict.get('station',''),self.sensordict.get('pierid',''),self.sensordict.get('protocol',''),self.sensordict.get('sensorgroup',''),self.sensordict.get('sensordesc',''),self.sensordict.get('ptime','') )
                        self.client.publish(topic+"/dict", add, qos=self.qos)
                        self.client.publish(topic+"/meta", datahead, qos=self.qos)
            except:
                log.err('{}: Unable to parse data {}'.format(self.sensordict.get('protocol'), data))

        self.count += 1

