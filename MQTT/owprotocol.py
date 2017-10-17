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
#from twisted.protocols.basic import LineReceiver
from twisted.python import log
from magpy.acquisition import acquisitionsupport as acs

from methodstobemovedtoacs import *

owport = 4304
owhost = 'localhost'

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
        Protocol to read one wire data from usb DS unit
        All connected sensors are listed and data is distributed in dependency of sensor id
        Dipatch url links are defined by channel 'ow' and id+'value'
        Save path ? folders ?

        """
        def __init__(self, client, sensordict, confdict):
            self.client = client
            self.sensordict = sensordict    
            self.confdict = confdict
            self.count = 0  ## counter for sending header information
            self.sensor = sensordict.get('sensorid') # should be Ow
            self.hostname = socket.gethostname()
            self.printable = set(string.printable)
            self.reconnectcount = 0
            # Extract eventually existing one wire sensors from sensors.cfg
            self.existinglist = GetSensors(confdict.get('sensorsconf'),identifier='!')
            #self.existinglist = acs.GetSensors(confdict.get('sensorsconf'),identifier='!')
            self.sensorarray = self.GetOneWireSensorList(self.existinglist)
            print (self.sensorarray)

        def GetOneWireSensorList(self, existinglist=[]):
            self.owproxy = pyownet.protocol.proxy(host=owhost, port=owport)
            sensorlst = self.owproxy.dir()
            # compare currently read sensorlst with original sensorlst (eventually from file)
            existingpathlist = [line.get('path') for line in existinglist]
            # if new sensors are found, extend file

            # Identify attached sensors and their types
            idlist = []
            fakelst = []
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
                    line.append(sensorname)
                    # make a dict for each ID
                    path = el+'type'
                    typ = self.owproxy.read(path)
                    if not typ == 'DS1420': # do not add dongle
                        if el in existingpathlist:
                            values = [line for line in existinglist if line.get('path') == el][0]
                        else:
                            values['path'] = el
                            values['serialnumber'] = idel
                            values['name'] = typ
                            values['protocol'] = 'Ow'
                            revision = '0001'
                            values['revision'] = revision
                            values['sensorid'] = typ+'_'+idel+'_'+revision
                            success = AddSensor(path, values, block='OW')
                            #success = acs.AddSensor(path, values, block='OW')

                    idlist.append(values)
            return idlist

        #def connectionMade(self):
        #    log.msg('%s connected.' % self.sensor)

        #def connectionLost(self, reason):
        #    log.msg('%s lost.' % self.sensor)


        def sendRequest(self):
            print ("Sending periodic request ...")
            sensorarray = self.GetOneWireSensorList()
            for line in sensorarray:
                print ("Getting sensor:", line.get('path'))
                print ("Asigning sensor ID:", line.get('sensorid'))
                sensorid = line.get('sensorid')
                valuedict = {}
                for para in typedef.get(line.get('name')):
                    path = line.get('path')+para
                    valuedict[para] = self.owproxy.read(path)

                topic = self.confdict.get('station') + '/' + sensorid
                data, head  = self.processOwData(sensorid, valuedict)

                # To find out, which parameters are available use:
                #print (self.owproxy.dir(line[1]))

                self.client.publish(topic+"/data", data)
                if self.count == 0:
                    self.client.publish(topic+"/meta", head)
                self.count += 1
                if self.count == 10:
                    self.count = 0



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
'temperature','VAD','VDD','humidity','vis'
                key = '[t1,va3,var4,var1,var5]'
                ele = '[T,VAD,VDD,RH,VIS]'
                unit = '[degC,V,V,per,V]'

            print ("len(valuedict)", datadict, len(datadict))

            header = "# MagPyBin %s %s %s %s %s %s %d" % (sensorid, key, ele, unit, multplier, packcode, struct.calcsize(packcode))


            return data, header
