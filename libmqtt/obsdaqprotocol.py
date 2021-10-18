from __future__ import print_function
from __future__ import absolute_import

"""
Protocol for PalmAcq and ObsDAQ by MINGEO, Hungary

works for ObsDaqs since 55Fxxx serial numbers when connected to a
PalmAcq by a combined port cable
The MARTAS host is connected to PalmAcq by USB cable

Settings are made in a config file defined in martas.cfg like
obsdaqconfpath  :  /etc/martas/obsdaq.cfg

"""


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
import math
import serial # for initializing command
import os,sys

# Relative import of core methods as long as martas is not configured as package
scriptpath = os.path.dirname(os.path.realpath(__file__))
coredir = os.path.abspath(os.path.join(scriptpath, '..', 'core'))
sys.path.insert(0, coredir)
from acquisitionsupport import GetConf2 as GetConf2


def datetime2array(t):
    return [t.year,t.month,t.day,t.hour,t.minute,t.second,t.microsecond]

def getRoundingFactor(lsb):
    # rounding factor is used for rounding reasonably
    return 10**(-1*round(math.log(lsb)/math.log(10)-1))


## Mingeo ObsDAQ protocol
##
class obsdaqProtocol(LineReceiver):
    """
    The Obsdaq protocol gets data assuming:
        connected to a PalmAcq
        PalmAcq is in Transparent mode (see manual)

    SETUP:
        1.) use palmacq.py to make settings of PalmAcq 
        2.) use obsdaq.py to make settings of ObsDAQ
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
        self.datalstSup = []
        self.datacnt = 0
        self.metacnt = 10
        self.errorcnt = {'time':0}

        self.delaylist = []  # delaylist contains up to 1000 diffs between gps and ntp
                             # the median of this values is used for ntp timedelay
        self.timedelay = 0.0
        self.timethreshold = 3 # secs - waring if timedifference is larger the 3 seconds

        # Serial configuration
        self.baudrate=int(sensordict.get('baudrate'))
        self.port = confdict['serialport']+sensordict.get('port')
        self.parity=sensordict.get('parity')
        self.bytesize=int(sensordict.get('bytesize'))
        self.stopbits=int(sensordict.get('stopbits'))
        self.delimiter='\r'
        self.timeout=2 # should be rate dependend
        sensorSuplst = self.sensor.split('_')
        if len(sensorSuplst) == 3:
            self.sensoridSup = '_'.join([sensorSuplst[0]+'sup',sensorSuplst[1],sensorSuplst[2]])


        # QOS
        self.qos=int(confdict.get('mqttqos',0))
        if not self.qos in [0,1,2]:
            self.qos = 0
        log.msg("  -> setting QOS:", self.qos)

        # Debug mode
        debugtest = confdict.get('debug')
        self.debug = False
        if debugtest == 'True':
            log.msg('DEBUG - {}: Debug mode activated.'.format(self.sensordict.get('protocol')))
            self.debug = True    # prints many test messages
        else:
            log.msg('  -> Debug mode = {}'.format(debugtest))

        # get obsdaq specific constants
        self.obsdaqconf = GetConf2(self.confdict.get('obsdaqconfpath'))
        
        self.headernames = '[{},{},{},{}]'.format(self.obsdaqconf.get('NAME_X'),self.obsdaqconf.get('NAME_Y'),self.obsdaqconf.get('NAME_Z'),'ntptime')
        self.headerunits = '[{},{},{},{}]'.format(self.obsdaqconf.get('UNIT_X'),self.obsdaqconf.get('UNIT_Y'),self.obsdaqconf.get('UNIT_Z'),'none')
        CCdic = {'02':10.,'03':5.,'04':2.5}
        self.gainmax = CCdic[str(self.obsdaqconf.get('CC')).zfill(2)]
        self.scale_x = float(self.obsdaqconf.get('SCALE_X'))
        self.scale_y = float(self.obsdaqconf.get('SCALE_Y'))
        self.scale_z = float(self.obsdaqconf.get('SCALE_Z'))
        # least significant bit, smallest discrete value in given unit
        self.lsb_x = 2**-23 * self.gainmax * self.scale_x
        self.lsb_y = 2**-23 * self.gainmax * self.scale_y
        self.lsb_z = 2**-23 * self.gainmax * self.scale_z
        # rounding factor is used for rounding reasonably
        self.rfactor_x = getRoundingFactor(self.lsb_x)
        self.rfactor_y = getRoundingFactor(self.lsb_y)
        self.rfactor_z = getRoundingFactor(self.lsb_z)
        # header factor is used for sending decimal numbers as integer (or long)
        self.factor_x = 1
        if self.rfactor_x > 1.:
            self.factor_x = int(self.rfactor_x)
        self.factor_y = 1
        if self.rfactor_y > 1.:
            self.factor_y = int(self.rfactor_y)
        self.factor_z = 1
        if self.rfactor_z > 1.:
            self.factor_z = int(self.rfactor_z)
        self.headerfactors = '[{},{},{},{}]'.format(self.factor_x,self.factor_y,self.factor_z,1)

        # get constants for Obsdaq's supplementary channels
        self.headernamesSup = '[{},{},{},{},{}]'.format(self.obsdaqconf.get('NAME_V'),self.obsdaqconf.get('NAME_T'),self.obsdaqconf.get('NAME_P'),self.obsdaqconf.get('NAME_Q'),self.obsdaqconf.get('NAME_R'))
        self.headerunitsSup = '[{},{},{},{},{}]'.format(self.obsdaqconf.get('UNIT_V'),self.obsdaqconf.get('UNIT_T'),self.obsdaqconf.get('UNIT_P'),self.obsdaqconf.get('UNIT_Q'),self.obsdaqconf.get('UNIT_R'))
        self.scale_p = float(self.obsdaqconf.get('SCALE_P'))
        self.scale_q = float(self.obsdaqconf.get('SCALE_Q'))
        self.scale_r = float(self.obsdaqconf.get('SCALE_R'))
        # least significant bit, smallest discrete value in given unit = 1V / 8000 * scale , see manual
        self.lsb_p = 1./8000 * self.scale_p
        self.lsb_q = 1./8000 * self.scale_q
        self.lsb_r = 1./8000 * self.scale_r
        # rounding factor is used for rounding reasonably
        self.rfactor_p = getRoundingFactor(self.lsb_p)
        self.rfactor_q = getRoundingFactor(self.lsb_q)
        self.rfactor_r = getRoundingFactor(self.lsb_r)
        # header factor is used for sending decimal numbers as integer (or long)
        self.factor_p = 1
        if self.rfactor_p > 1.:
            self.factor_p = int(self.rfactor_p)
        self.factor_q = 1
        if self.rfactor_q > 1.:
            self.factor_q = int(self.rfactor_q)
        self.factor_r = 1
        if self.rfactor_r > 1.:
            self.factor_r = int(self.rfactor_r)
        # Obsdaq's voltage and temperature are measured and calculated fixed, see manual
        self.headerfactorsSup = '[{},{},{},{},{}]'.format('10000','1000',self.factor_p,self.factor_q,self.factor_r)

        # get constants for Obsdaq's supplementary channels
        self.headernamesSup = '[{},{},{},{},{}]'.format(self.obsdaqconf.get('NAME_V'),self.obsdaqconf.get('NAME_T'),self.obsdaqconf.get('NAME_P'),self.obsdaqconf.get('NAME_Q'),self.obsdaqconf.get('NAME_R'))
        self.headerunitsSup = '[{},{},{},{},{}]'.format(self.obsdaqconf.get('UNIT_V'),self.obsdaqconf.get('UNIT_T'),self.obsdaqconf.get('UNIT_P'),self.obsdaqconf.get('UNIT_Q'),self.obsdaqconf.get('UNIT_R'))


    def connectionMade(self):
        log.msg('  -> {} connected.'.format(self.sensor))

    def connectionLost(self, reason):
        log.msg('  -> {} lost.'.format(self.sensor))
        log.msg(reason)

    def processData(self, data):
        currenttime = datetime.utcnow()
        outdate = datetime.strftime(currenttime, "%Y-%m-%d")
        filename = outdate
        sensorid = self.sensor
        datearray = []
        dontsavedata = False

        packcode = '6hLlll6hL'
        header = "# MagPyBin %s %s %s %s %s %s %d" % (self.sensor, '[x,y,z,sectime]', self.headernames, self.headerunits, self.headerfactors, packcode, struct.calcsize(packcode))
        supplement = False
        packcodeSup = '6hLlllll'
        
        headerSup = "# MagPyBin %s %s %s %s %s %s %d" % (self.sensoridSup, '[var1,var2,var3,var4,var5]', self.headernamesSup, self.headerunitsSup, self.headerfactorsSup, packcode, struct.calcsize(packcode))

        if data.startswith(':R'):
            # :R,00,YYMMDD.hhmmss.sss,*xxxxxxyyyyyyzzzzzzt
            # :R,00,YYMMDD.hhmmss.sss,*xxxxxxyyyyyyzzzzzzt:vvvvttttppppqqqqrrrr
            # :R,00,200131.143739.617,*0259FEFFF1BFFFFCEDL:04AC11CC000B000B000B
            d = data.split(',')
            Y = int('20'+d[2][0:2])
            M = int(d[2][2:4])
            D = int(d[2][4:6])
            h = int(d[2][7:9])
            m = int(d[2][9:11])
            s = int(d[2][11:13])
            us = int(d[2][14:17]) * 1000
            timestamp = datetime(Y,M,D,h,m,s,us)
            if d[3][0] == '*':
                x = (int('0x'+d[3][1:7],16) ^ 0x800000) - 0x800000
                # old line:
                #x = float(x) * 2**-23 * self.gainmax * self.scale_x
                x = round( float(x) * self.lsb_x * self.rfactor_x) / self.rfactor_x
                y = (int('0x'+d[3][7:13],16) ^ 0x800000) - 0x800000
                y = round( float(y) * self.lsb_y * self.rfactor_y) / self.rfactor_y
                z = (int('0x'+d[3][13:19],16) ^ 0x800000) - 0x800000
                z = round( float(z) * self.lsb_z * self.rfactor_z) / self.rfactor_z
                # (triggerflag not used here)
                triggerflag = d[3][19]
            else:
                typ = "none"
            sup = d[3].split(':')
            if len(sup) == 2:
                supplement = True
                voltage = int(sup[1][0:4],16) ^ 0x8000 - 0x8000
                voltage = float(voltage) * 2.6622e-3 + 9.15
                voltage = round(voltage*10000)/10000.
                temp = int(sup[1][4:8],16) ^ 0x8000 - 0x8000
                temp = float(temp) / 128.
                temp = round(temp*1000)/1000.
                p = (int('0x'+sup[1][8:12],16) ^ 0x8000) - 0x8000
                p = float(p) / 8000.0 * self.scale_p + float(self.obsdaqconf.get('DIFF_P'))
                p = round(p*self.rfactor_p)/self.rfactor_p
                q = (int('0x'+sup[1][12:16],16) ^ 0x8000) - 0x8000
                q = float(q) / 8000.0 * self.scale_q + float(self.obsdaqconf.get('DIFF_Q'))
                q = round(q*self.rfactor_q)/self.rfactor_q
                r = (int('0x'+sup[1][16:20],16) ^ 0x8000) - 0x8000
                r = float(r) / 8000.0 * self.scale_r + float(self.obsdaqconf.get('DIFF_R'))
                r = round(r*self.rfactor_r)/self.rfactor_r
            if self.debug:
                log.msg(str(timestamp)+'\t',end='')
                log.msg(str(x)+'\t',end='')
                log.msg(str(y)+'\t',end='')
                log.msg(str(z)+'\t',end='')
                log.msg(str(triggerflag))
                if len(sup) == 2:
                    log.msg('supplementary:\t',end='')
                    log.msg(str(voltage)+' V\t',end='')
                    log.msg(str(temp)+' degC\t',end='')
                    log.msg(str(p)+'\t',end='')
                    log.msg(str(q)+'\t',end='')
                    log.msg(str(r)+'\t')
            typ = "valid"
        else:
            typ = "none"
            if self.debug:
                log.msg(':R not found')
 
        if not typ == "valid": 
            dontsavedata = True

        if not typ == "none":
            datearray = datetime2array(timestamp)
            try:
                datearray.append(int(x * self.factor_x))
                datearray.append(int(y * self.factor_y))
                datearray.append(int(z * self.factor_z))
                # add secondary time (NTP-time)
                datearray.extend(datetime2array(currenttime))
                data_bin = struct.pack('<'+packcode,*datearray)
            except:
                log.msg('{} protocol: Error while packing binary data'.format(self.sensordict.get('protocol')))
            if not self.confdict.get('bufferdirectory','') == '':
                acs.dataToFile(self.confdict.get('bufferdirectory'), sensorid, filename, data_bin, header)
            returndata = ','.join(list(map(str,datearray)))

            if supplement:
                try:
                    datearraySup = datetime2array(timestamp)
                    datearraySup.append(int(voltage *10000))
                    datearraySup.append(int(temp *1000))
                    datearraySup.append(int(p *self.factor_p))
                    datearraySup.append(int(q *self.factor_q))
                    datearraySup.append(int(r *self.factor_r))
                    data_bin_Sup = struct.pack('<'+packcodeSup,*datearraySup)
                except:
                    log.msg('{} protocol: Error while packing binary supplement data'.format(self.sensordict.get('protocol')))
                if not self.confdict.get('bufferdirectory','') == '':
                    acs.dataToFile(self.confdict.get('bufferdirectory'), self.sensoridSup, filename, data_bin_Sup, headerSup)
                returndataSup = ','.join(list(map(str,datearraySup)))
            else:
                returndataSup = ''
                headerSup = ''

        else:
            returndata = ''
            returndataSup = ''
            headerSup = ''

        return returndata, header, returndataSup, headerSup

         
    def lineReceived(self, line):
        topic = self.confdict.get('station') + '/' + self.sensordict.get('sensorid')
        topicSup = self.confdict.get('station') + '/' + self.sensoridSup
        # extract only ascii characters 
        line = ''.join(filter(lambda x: x in string.printable, line))
        ok = True
        try:
            data, head, dataSup, headSup = self.processData(line)
        except:
            print('{}: Data seems not to be PalmAcq data: Looks like {}'.format(self.sensordict.get('protocol'),line))
            ok = False

        if ok:
            senddata = False
            coll = int(self.sensordict.get('stack'))
            if coll > 1:
                self.metacnt = 1 # send meta data with every block
                if self.datacnt < coll:
                    self.datalst.append(data)
                    self.datalstSup.append(dataSup)
                    self.datacnt += 1
                else:
                    senddata = True
                    data = ';'.join(self.datalst)
                    dataSup = ';'.join(self.datalstSup)
                    self.datalst = []
                    self.datalstSup = []
                    self.datacnt = 0
            else:
                senddata = True

            if senddata:
                self.client.publish(topic+"/data", data, qos=self.qos)
                self.client.publish(topicSup+"/data", dataSup, qos=self.qos)
                if self.count == 0:
                    add = "SensorID:{},StationID:{},DataPier:{},SensorModule:{},SensorGroup:{},SensorDecription:{},DataTimeProtocol:{}".format( self.sensordict.get('sensorid',''),self.confdict.get('station',''),self.sensordict.get('pierid',''),self.sensordict.get('protocol',''),self.sensordict.get('sensorgroup',''),self.sensordict.get('sensordesc',''),self.sensordict.get('ptime','') )
                    self.client.publish(topic+"/dict", add, qos=self.qos)
                    self.client.publish(topic+"/meta", head, qos=self.qos)
                    self.client.publish(topicSup+"/meta", headSup, qos=self.qos)
                self.count += 1
                if self.count >= self.metacnt:
                    self.count = 0

