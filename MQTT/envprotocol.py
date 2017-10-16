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

class EnvProtocol(LineReceiver):
    """
    Protocol to read MessPC EnvironmentalSensor 5 data from usb unit
    Each sensor has its own class (that can be improved...)
    The protocol defines the sensor name in its init section, which
    is used to dipatch url links and define local storage folders

    """

    ## need a reference to our client (e.g. MQTT ot WS-MCU gateway factory) to publish events
    ##
    def __init__(self, client, sensordict, confdict):
        self.client = client
        self.sensordict = sensordict    
        self.confdict = confdict
        self.count = 0  ## counter for sending header information
        self.sensor = sensordict.get('sensorid')
        #self.outputdir = outputdir confdict.get('outputdir')
        self.hostname = socket.gethostname()
        self.printable = set(string.printable)
        print(self.sensor)

    def connectionMade(self):
        log.msg('%s connected.' % self.sensor)

    def connectionLost(self, reason):
        log.msg('%s lost.' % self.sensor)

    def processEnvData(self, data):
        """Process Environment data """

        currenttime = datetime.utcnow()
        outdate = datetime.strftime(currenttime, "%Y-%m-%d")
        filename = outdate
        actualtime = datetime.strftime(currenttime, "%Y-%m-%dT%H:%M:%S.%f")
        outtime = datetime.strftime(currenttime, "%H:%M:%S")
        timestamp = datetime.strftime(currenttime, "%Y-%m-%d %H:%M:%S.%f")
        packcode = '6hLllL'
        sensorid = self.sensor
        header = "# MagPyBin %s %s %s %s %s %s %d" % (sensorid, '[t1,t2,var1]', '[T,DewPoint,RH]', '[degC,degC,per]', '[1000,1000,1000]', packcode, struct.calcsize(packcode))

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
            data_bin = struct.pack(packcode,*datearray)
        except:
            log.msg('Error while packing binary data')
            pass

        if not self.confdict.get('bufferdirectory','') == '':
            acs.dataToFile(self.confdict.get('bufferdirectory'), sensorid, filename, data_bin, header)

        return ','.join(list(map(str,datearray))), header

    def lineReceived(self, line):

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
            
        #except ValueError:
        #    log.err('{}: Unable to parse data {}'.format(self.sensordict.get('protocol'), line))


