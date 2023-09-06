"""
fluke289protocol written 2023 by richard.mandl@geosphere.at
for MARTAS MQTT protocol by Roman Leonhardt and Rachel Bailey to be used in the Conrad Observatory.
Makes sense only when using a Fluke 289 mulimeter or compatible
"""
from __future__ import print_function
from __future__ import absolute_import

# ###################################################################
# Import packages
# ###################################################################

import struct # for binary representation
import socket # for hostname identification
from datetime import datetime, timedelta
from twisted.python import log
from core import acquisitionsupport as acs
import serial
import time, sys

# ###################################################################

# some helpful function
def datetime2array(t):
    return [t.year,t.month,t.day,t.hour,t.minute,t.second,t.microsecond]

# constants for Fluke 289 readings
STATE = ['INVALID','NORMAL','BLANK','DISCHARGE','OL','OL_MINUS','OPEN_TC']
ATTRIBUTE = ['NONE','OPEN_CIRCUIT','SHORT_CIRCUIT','GLITCH_CIRCUIT','GOOD_DIODE','LO_OHMS','NEGATIVE_EDGE','POSITIVE_EDGE','HIGH_CURRENT']

PREFIX = ['n','u','m','','k','M']

class fluke289Protocol:        
    """
    Protocol to read from a Fluke 289 Multimeter
    """

    def __init__(self, client, sensordict, confdict):
        self.client = client
        self.sensordict = sensordict 
        self.confdict = confdict
        # variables for broadcasting via mqtt:
        self.count=0
        self.datalst = []
        self.datacnt = 0
        self.metacnt = 10
        ###
        self.port = confdict['serialport']+sensordict.get('port')
        self.baudrate = int(sensordict.get('baudrate'))
        if not self.baudrate == 115200:
            log.msg('baudrate for Fluke 289 must be 115200. exiting...')
        self.port = confdict['serialport']+sensordict.get('port')
        self.parity=sensordict.get('parity')
        self.bytesize=sensordict.get('bytesize')
        self.stopbits=sensordict.get('stopbits')
        self.timeout=0 # should be rate depended
    
        # QOS
        self.qos=int(confdict.get('mqttqos',0))
        if not self.qos in [0,1,2]:
            self.qos = 0
        log.msg("  -> setting QOS:", self.qos)

        # switch on debug mode
        debugtest = confdict.get('debug')
        self.debug = False
        if debugtest == 'True':
            log.msg('DEBUG - {}: Debug mode activated.'.format(self.sensordict.get('protocol')))
            self.debug = True    # prints many test messages
        else:
            log.msg('  -> Debug mode = {}'.format(debugtest))
        # query serial number at startup
        self.get_serialnumber = False
        # serial number of config file will be checked at startup
        self.sn = '' # self.sensordict['serialnumber']
        self.oldsensorid = ''
        self.ser = None



    def open_connection(self):
        log.msg("connecting to serial port")
        try:
            ser = serial.Serial(self.port, baudrate=int(self.baudrate), parity=self.parity, bytesize=int(self.bytesize), stopbits=int(self.stopbits), timeout=self.timeout)
        except:
            return False
        self.ser = ser
        return ser

    def write_read(self,ser,command,end="MARTASEND",maxcnt=20,debug=False):
        data = b""
        if ser:
            # don't produce log entries, when there isn't even a connection
            try:
                ser.flush()
                if sys.version_info >= (3, 0):
                    ser.write(command.encode("utf-8"))
                else:
                    ser.write(command)
                time.sleep(0.05)
                data=ser.readline()
                if sys.version_info >= (3, 0):
                    data = str(data.decode("utf-8"))
                else:
                    data = str(data)
                if not data:
                    if debug:
                        log.msg("DEBUG - got empty line")
                datalist = data.split('\r')
                return datalist
            except serial.SerialException as e:
                if self.debug:
                    log.msg("SerialException found ({})".format(e))
                time.sleep(1)
                #self.restart()
            except:
                log.msg("Other exception found")
                raise

    def sendRequest(self):
        # connect to serial
        ser = self.ser
        if not ser or not ser.isOpen():
            ser = self.open_connection()
            if ser:
                self.get_serialnumber = True
                return
        if self.get_serialnumber:
            answer = self.write_read(self.ser,'ID\r\n',debug=self.debug)
            if not len(answer) == 3:
                if self.debug:
                    log.msg('error: got invalid serial number: '+str(answer))
                return
            error = answer[0]
            datastring = answer[1]
            data = datastring.split(',')
            model = data[0]
            sw_version = data[1]
            sn = data[2]
            log.msg(str(error)+'\t'+model+'\t'+sw_version+'\t'+sn)
            if not sn == self.sensordict['serialnumber']:
                log.msg('S/N '+sn+' and the one given in the config file '+self.sensordict['serialnumber']+' differ')
            self.sn=sn
            self.get_serialnumber = False
            return

        if not ser:
            # exit, when there is no serial connection
            return
        answer = self.write_read(ser,'QM\r\n',debug=self.debug)
        if not len(answer) == 3:
            if self.debug:
                log.msg('error: got invalid data: '+str(answer))
            return
        error = answer[0]
        datastring = answer[1]
        data = datastring.split(',')
        value = data[0]
        unit = data[1]
        state = data[2]
        state_nr = STATE.index(state)
        attribute = data[3]
        attribute_nr = ATTRIBUTE.index(attribute)
        if self.debug:
            log.msg(str(error)+'\t'+value+'\t'+unit+'\t'+state+'\t'+str(state_nr)+'\t'+attribute+'\t'+str(attribute_nr))

        t = datetime.utcnow()
        darray = datetime2array(t)
        packcode = "<6hLl"
        # header
        packcodeH = "6hLl"
        valuelist = value.split('E')
        if valuelist[1] == '+37':
            # invalid data
            if self.debug:
                log.msg('invalid data (+9.9999999E+37)')
            return
        prefix = PREFIX[int(valuelist[1])//3+3]
        valueint = int(float(valuelist[0]) * 10000)
        if self.debug:
            log.msg(str(valueint)+'\t'+unit)
        darray.append(valueint)
        instrument = 'FLUKE289'+prefix+unit
        unit = '['+prefix+unit+']'
        # redefine sensorid e.g. FLUKE289VAC_123456_0001
        sensorid = self.sensordict['sensorid']
        sensorid = instrument+'_'+self.sn+'_'+sensorid.split('_')[2]
        if not sensorid == self.oldsensorid:
            self.oldsensorid = sensorid
            log.msg('switched to '+sensorid)
        instrument = '['+instrument+']'
        header = "# MagPyBin %s %s %s %s %s %s %d" % (sensorid,'[var1]',instrument,unit,'[10000]',packcodeH,struct.calcsize(packcode))
        data_bin = struct.pack(packcode,*darray)
        # date of dataloggers timestamp
        filedate = datetime.strftime(datetime(darray[0],darray[1],darray[2]), "%Y-%m-%d")
        if not self.confdict.get('bufferdirectory','') == '':
            acs.dataToFile(self.confdict.get('bufferdirectory'), sensorid, filedate, data_bin, header)
            if self.debug:
                log.msg('Daten gesichert...')

        # sending via MQTT
        data = ','.join(list(map(str,darray)))
        senddata = False
        head = header
        topic = self.confdict.get('station') + '/' + self.sensordict.get('sensorid')
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


