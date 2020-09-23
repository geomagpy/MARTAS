from __future__ import print_function
from __future__ import absolute_import

# ###################################################################
# Import packages
# ###################################################################

import re     # for interpretation of lines
import sys    # for version identification
import struct # for binary representation
import socket # for hostname identification
import string # for ascii selection
from datetime import datetime, timedelta
#from twisted.protocols.basic import LineReceiver
from twisted.python import log
from core import acquisitionsupport as acs

try:
    import pyownet
    onewire = True
    owsensorlist = []
except:
    print("Onewire (pyownet) package not available")
    onewire = False


typedef = {'DS18B20':['temperature'], 'DS2438':['temperature','VAD','VDD','humidity','vis'], 'DS1420':['well'], 'DS18S20':['temperature']}


if onewire:
    class OwProtocol():
        """
        Protocol to read one wire data from usb DS unit.
        For this protocol "owserver" needs to be running.
        All connected sensors are listed and data is distributed in dependency of sensor id
        Dipatch url links are defined by channel 'ow' and id+'value'
        Known issues:
        When renaming th PC, owserver can not properly be reached. -> Restart 
        """
        # TODO check humidity and pressure
        def __init__(self, client, sensordict, confdict):
            log.msg("  -> one wire: Initializing ...")
            self.client = client
            self.sensordict = sensordict    
            self.confdict = confdict
            self.owhost = confdict.get('owhost')
            self.owport = int(confdict.get('owport'))
            self.sensor = sensordict.get('sensorid') # should be Ow
            self.hostname = socket.gethostname()
            self.printable = set(string.printable)
            self.reconnectcount = 0
            self.removelist = [] # list of sensorspaths from sensors.cfg which are not found
            # Extract eventually existing one wire sensors from sensors.cfg
            log.msg("  -> one wire: Checking existing sensors ...")
            self.existinglist = acs.GetSensors(confdict.get('sensorsconf'),identifier='!')
            log.msg("  -> one wire: Checking for new sensors ...")
            self.sensorarray = self.GetOneWireSensorList(self.existinglist)
            self.count = [0]*len(self.sensorarray)  ## counter for sending header information
            self.metacnt = 2  # Send header information often for OW
            self.datalst = [[]]*len(self.sensorarray)
            self.datacnt = [0]*len(self.sensorarray)
            log.msg("  -> one wire: Initialized")
            #print (self.existinglist)
            #print (self.count)

            # QOS
            self.qos=int(confdict.get('mqttqos',0))
            if not self.qos in [0,1,2]:
                self.qos = 0
            log.msg("  -> setting QOS:", self.qos)


        def GetOneWireSensorList(self, existinglist=[]):
            try:
                self.owproxy = pyownet.protocol.proxy(host=self.owhost, port=self.owport)
                sensorlst = self.owproxy.dir()
            except:
                #log.msg("  -> one wire: could not contact to owhost")
                return []
            #log.msg("  -> one wire: {}".format(sensorlst))
            # Python3 checks
            #if sys.version_info >= (3, 0):
            # compare currently read sensorlst with original sensorlst (eventually from file)
            existingpathlist = [line.get('path') for line in existinglist]
            # Identify attached sensors and their types
            idlist = []
            fakelst = []
            # check for sensors which should be there but are not
            notfound = [el for el in existingpathlist if not el in sensorlst]
            for el in notfound:
                if not el in self.removelist:
                    log.msg("OW: sensor with path {} (as listed in sensors.cfg) is not found".format(el))
                    self.removelist.append(el)

            for el in sensorlst:
                values = {}
                # get posistions of sensorid, protocol(OW), name(DS18B20), serialnumber, revision and path
                # ADD SENSORDICT ELEMENTS to acquisition support
                #'sensorid','port','baudrate','bytesize','stopbits', 'parity','mode','init','rate',       				'protocol','name','serialnumber','revision','path','pierid','sensordesc'
                if not el in fakelst:
                    # make an array of IDs
                    line = []
                    idel = el.replace('/','').replace('.','').strip()
                    line.append(idel)
                    line.append(el)
                    #line.append(sensorname)
                    # make a dict for each ID
                    path = el+'type'
                    typ = self.owproxy.read(path)
                    #log.msg(typ)
                    # Python3 checks
                    if sys.version_info >= (3, 0):
                       try:
                           typ = typ.decode('ascii')
                       except:
                           pass 
                    if not typ == 'DS1420': # do not add dongle
                        if el in self.removelist:
                            # el found again
                            # Dropping it from removelist
                            log.msg("OW: sensor with path {} is active again".format(el)) 
                            self.removelist.remove(el)
                        if el in existingpathlist:
                            #print ("Sensor {} existing".format(path))
                            values = [line for line in existinglist if line.get('path') == el][0]
                        else:
                            values['path'] = el
                            values['serialnumber'] = idel
                            values['name'] = typ
                            values['protocol'] = 'Ow'
                            revision = '0001'
                            values['revision'] = revision
                            values['stack'] = 0
                            values['sensorid'] = '{}_{}_{}'.format(typ,idel,revision)
                            log.msg("OW: Writing new sensor input to sensors.cfg ...")
                            success = acs.AddSensor(self.confdict.get('sensorsconf'), values, block='OW')
                            #success = acs.AddSensor(self.confdict.get('sensorsconf'), values, block='OW')
                            if success:
                                log.msg("    {} written".format(values.get('sensorid')))
                                # extend existingpathlist
                                self.existinglist.append(values)
                        idlist.append(values)
            return idlist

        #def connectionMade(self):
        #    log.msg('%s connected.' % self.sensor)

        #def connectionLost(self, reason):
        #    log.msg('%s lost.' % self.sensor)


        def sendRequest(self):
            #log.msg("Sending periodic request ...")
            sensorarray = self.GetOneWireSensorList(self.existinglist)
            if not len(self.count) == len(sensorarray):
                # if length of sensorarray is changing - reset counters 
                self.count = [0]*len(sensorarray)
                self.datalst = [[]]*len(self.sensorarray)
                self.datacnt = [0]*len(self.sensorarray)
            for idx, line in enumerate(sensorarray):
                #print ("Getting sensor ID:", line.get('sensorid'))
                sensorid = line.get('sensorid')
                valuedict = {}
                for para in typedef.get(line.get('name')):
                    path = line.get('path')+para
                    if para == 'humidity': ## Check whether separete treatment is necessary
                        pass
                        #line.get('path')+para
                        #print ("ALL", self.owproxy.dir())
                        #print ("sens",self.owproxy.dir(line.get('path')))
                        #if para == 'pressure':
                        #    #if sensortypus == "pressure":
                        #    #    #print "Pressure [hPa]: ", self.mpxa4100(vad,temp)
                        #    #    humidity = self.mpxa4100(vad,temp)
                        #    pass
                    valuedict[para] = self.owproxy.read(path)

                topic = self.confdict.get('station') + '/' + sensorid
                data, head  = self.processOwData(sensorid, valuedict)

                # To find out, which parameters are available use:
                #print (self.owproxy.dir(line.get('path')))

                senddata = False
                try:
                    coll = int(line.get('stack'))
                except:
                    coll = 0
                #coll = int(self.sensordict.get('stack'))
                if coll > 1:
                    self.metacnt = 1 # send meta data with every block for stacked transfer
                    if self.datacnt[idx] < coll:
                        self.datalst[idx].append(data)
                        self.datacnt[idx] += 1
                    else:
                        senddata = True
                        data = ';'.join(self.datalst[idx])
                        self.datalst[idx] = []
                        self.datacnt[idx] = 0
                else:
                    senddata = True

                if senddata:
                    self.client.publish(topic+"/data", data, qos=self.qos)
                    if self.count[idx] == 0:
                        ## 'Add' is a string containing dict info like: 
                        ## SensorID:ENV05_2_0001,StationID:wic, PierID:xxx,SensorGroup:environment,... 
                        add = "SensorID:{},StationID:{},DataPier:{},SensorModule:{},SensorGroup:{},SensorDecription:{},DataTimeProtocol:{}".format( line.get('sensorid',''),self.confdict.get('station',''),line.get('pierid',''),line.get('protocol',''),line.get('sensorgroup',''),line.get('sensordesc',''),line.get('ptime','') )
                        #print ("...", add)
                        self.client.publish(topic+"/dict", add, qos=self.qos)
                        self.client.publish(topic+"/meta", head, qos=self.qos)
                    self.count[idx] += 1
                    if self.count[idx] >= self.metacnt:
                        self.count[idx] = 0


        def processOwData(self, sensorid, datadict):
            """Process OW data """
            currenttime = datetime.utcnow()
            outdate = datetime.strftime(currenttime, "%Y-%m-%d")
            filename = outdate
            actualtime = datetime.strftime(currenttime, "%Y-%m-%dT%H:%M:%S.%f")
            outtime = datetime.strftime(currenttime, "%H:%M:%S")
            timestamp = datetime.strftime(currenttime, "%Y-%m-%d %H:%M:%S.%f")
            packcode = '6hL'+'l'*len(datadict)
            multplier = str([1000]*len(datadict)).replace(' ','')
            if sensorid.startswith('DS18'):
                key = '[t1]'
                ele = '[T]'
                unit = '[degC]'
            elif sensorid.startswith('DS2438'):
                #'temperature','VAD','VDD','humidity','vis'
                key = '[t1,var1,var2,var3,var4]'
                ele = '[T,RH,VDD,VAD,VIS]'
                unit = '[degC,per,V,V,V,V]'

            header = "# MagPyBin %s %s %s %s %s %s %d" % (sensorid, key, ele, unit, multplier, packcode, struct.calcsize('<'+packcode))

            data_bin = None
            datearray = ''
            try:
                datearray = acs.timeToArray(timestamp)
                paralst = typedef.get(sensorid.split('_')[0])
                for para in paralst:
                    if para in datadict:
                        datearray.append(int(float(datadict[para])*1000))
                data_bin = struct.pack('<'+packcode,*datearray)  # little endian
            except:
                log.msg('Error while packing binary data')

            if not self.confdict.get('bufferdirectory','') == '' and data_bin:
                acs.dataToFile(self.confdict.get('bufferdirectory'), sensorid, filename, data_bin, header)
            #print ("Sending", ','.join(list(map(str,datearray))), header)
            return ','.join(list(map(str,datearray))), header

