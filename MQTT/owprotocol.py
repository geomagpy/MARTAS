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
from twisted.internet import task
from twisted.python import log
from magpy.acquisition import acquisitionsupport as acs

owport = 4304
owhost = 'localhost'

try:
    import pyownet
    onewire = True
    owsensorlist = []
except:
    print("Onewire (pyownet) package not available")
    onewire = False


typedef = {'DS18B20':['temperature','temperature12'], 'DS2438':['temperature','VAD','VDD','humidity','vis'], 'DS1420':['well'], 'DS18S20':['temperature','xyz']}


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
            self.sensorarray = self.GetOneWireSensorList()
            print (self.sensorarray)

        def GetStoredOneWireInfo(self, owid):
            line = [line for line in self.storedlist if line[0] == owid] # read during init
            if not len(line) > 0:
                line = [owid.replace('/','').replace('.','').strip(),owid,self.owproxy.read(owid+'type'),'OW','0001','wic','A2']

        def GetOneWireSensorList(self):
            self.owproxy = pyownet.protocol.proxy(host=owhost, port=owport)
            sensorlst = self.owproxy.dir()
            # compare currently read sensorlst with original sensorlst (eventually from file)
            # if new sensors are found, extend file 

            # Identify attached sensors and their types
            idlist = []
            fakelst = []
            for el in sensorlst:
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
                    line.append(typ)
                    print (typedef.get(typ))
                    if not typ == 'DS1420': # do not add dongle
                        idlist.append(line)
            return idlist

        #def connectionMade(self):
        #    log.msg('%s connected.' % self.sensor)

        #def connectionLost(self, reason):
        #    log.msg('%s lost.' % self.sensor)

        def saveowlist(self,filename, owlist):
            with open(filename, 'wb') as f:
                wr = csv.writer(f, quoting=csv.QUOTE_ALL)
                for row in owlist:
                    wr.writerow(row)

        def loadowlist(self,filename):
            with open(filename, 'rb') as f:
                reader = csv.reader(f)
                owlist = [row for row in reader]
            return owlist

        def sendRequest(self):
            print ("Sending Request")
            sensorarray = self.GetOneWireSensorList()
            for line in sensorarray:
                print (line)
                print ("path:", line[1])
                for para in typedef.get(line[2]):
                    print ("Parameter", para)
                    path = line[1]+para
                    print (self.owproxy.read(path))
                print (self.owproxy.dir(line[1]))
            """
            try:
                self.root = ow.Sensor('/').sensorList()

                if not (self.root == owsensorlist):
                    log.msg('Rereading sensor list')
                    ow.init(self.source)
                    self.root = ow.Sensor('/').sensorList()
                    owsensorlist = self.root
                    self.connectionMade(self.root)
                self.reconnectcount = 0
            except:
                self.reconnectcount = self.reconnectcount + 1
                log.msg('Reconnection event triggered - Number: %d' % self.reconnectcount)
                time.sleep(2)
                if self.reconnectcount < 10:
                    self.owConnected()
                else:
                    print("owConnect: reconnection not possible")

            self.oneWireInstruments(self.root)
            """
            topic = self.confdict.get('station') + '/' + self.sensordict.get('sensorid')
            # extract only ascii characters 
            line = ''.join(filter(lambda x: x in string.printable, line))

            #try:
            ok = True
            if ok:
                data = line.split()
                if len(data) == 3:
                    data, head = self.processEnvData(data)
                else:
                    print('{}: Data seems not be EnvData: Looks like {}'.format(self.sensordict.get('protocol'),line))

                self.client.publish(topic+"/data", data)
                if self.count == 0:
                    self.client.publish(topic+"/meta", head)
                self.count += 1
                if self.count == 10:
                    self.count = 0



        def processOwData(self, data):
            """Process OW data """
            currenttime = datetime.utcnow()
            outdate = datetime.strftime(currenttime, "%Y-%m-%d")
            filename = outdate
            actualtime = datetime.strftime(currenttime, "%Y-%m-%dT%H:%M:%S.%f")
            outtime = datetime.strftime(currenttime, "%H:%M:%S")
            timestamp = datetime.strftime(currenttime, "%Y-%m-%d %H:%M:%S.%f")

            packcode = '6hLllL'
            sensorid = self.sensor
            header = "# MagPyBin %s %s %s %s %s %s %d" % (sensorid, '[t1,t2,var1]', '[T,DewPoint,RH]', '[degC,degC,per]', '[1000,1000,1000]', packcode, struct.calcsize(packcode))

