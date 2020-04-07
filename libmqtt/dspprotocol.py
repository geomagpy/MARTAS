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
from core import acquisitionsupport as acs
from magpy.stream import KEYLIST
import serial


def send_command_ascii(ser,command,eol):
    #use printable here
    response = ''
    command = eol+command+eol
    if(ser.isOpen() == False):
        ser.open()
    sendtime = datetime.utcnow()
    ser.write(command)
    # skipping all empty lines 
    while response == '': 
        response = ser.readline()
    responsetime = datetime.utcnow()
    # return only ascii
    line = ''.join(filter(lambda x: x in string.printable, response))
    line = line.strip()
    return line, responsetime


def datetime2array(t):
    return [t.year,t.month,t.day,t.hour,t.minute,t.second,t.microsecond]

## Arduino active request protocol
## --------------------

class DSPProtocol(object):
    """
    Protocol to read Arduino data (usually from ttyACM0)
    Tested so far only for Arduino Uno on a Linux machine
    The protocol works only if the serial output follows the MagPy convention:
    Up to 99 Sensors are supported identified by unique sensor names and ID's.

    ARDUINO OUTPUT:
        - serial output on ttyACM0 needs to follow the MagPy definition:
            Three data sequences are supported:
            1.) The meta information
                The meta information line contains all information for a specific sensor.
                If more than one sensor is connected, then several meta information
                lines should be sent (e.g. M1:..., M2:..., M99:...)
                Meta lines should be resent once in a while (e.g. every 10-100 data points)
                Example:
                     M1: SensorName: MySensor, SensorID: 12345, SensorRevision: 0001
            2.) The header line
                The header line contains information on the provided data for each sensor.
                The typical format includes the MagPy key, the actual Variable and the unit.
                Key and Variable are separeted by an underscore, unit is provided in brackets.
                Like the Meta information the header should be sent out once in a while
                Example:
                     H1: f_F [nT], t1_Temp [degC], var1_Quality [None], var2_Pressure [mbar]
            3.) The data line:
                The data line containes all data from a specific sensor
                Example:
                     D1: 46543.7898, 6.9, 10, 978.000

         - recording starts after meta and header information have been received

    """

    ## need a reference to our WS-MCU gateway factory to dispatch PubSub events
    ##
    def __init__(self, client, sensordict, confdict):
        # Specific commands for ultrasonic wind sensor
        # self.addressanemo = '01'
        self.commands = [{'data':'11TR00005'},{'meta':''},{'head':''}] # ,self.addressanemo+'TR00002']

        self.commands = [{'data':'01TR00002','c1':'01SH','c2':'01SL'}]
        self.hexcoding = False
        self.eol = '\r'


        self.client = client #self.wsMcuFactory = wsMcuFactory
        self.sensordict = sensordict
        self.confdict = confdict
        self.count = 0  ## counter for sending header information

        self.sensorname = sensordict.get('name')
        self.baudrate=int(sensordict.get('baudrate'))
        self.port = confdict['serialport']+sensordict.get('port')
        self.parity=sensordict.get('parity')
        self.bytesize=sensordict.get('bytesize')
        self.stopbits=sensordict.get('stopbits')
        self.timeout=2 # should be rate depended

        self.hostname = socket.gethostname()
        self.printable = set(string.printable)
        self.datalst = []
        self.datacnt = 0
        rate = sensordict.get('rate','0')
        try:
            rate = int(rate)
        except:
            rate = 1
        if rate < 5:
            self.metacnt = 10 # send header at reduced rate
        else:
            self.metacnt = 1
        self.counter = {}

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

        # ULTRASONIC specific
        self.sensorid = ''
        self.serialnum = ''
        self.serial1 = ''
        self.serial2 = ''


    def processData(self, sensorid, line, ntptime):
        """processing and storing data - requires sensorid and meta info
           data looks like (TR00002):
           01.6 290 +14.8 0E*4F
           windspeed, winddirection, virtualtemperature, status*pruefsumme
        """
        # currenttime = datetime.utcnow()
        outdate = datetime.strftime(ntptime, "%Y-%m-%d")
        filename = outdate
        header = ''
        datearray = datetime2array(ntptime)
        packcode = '6hLlll'
        multiplier = [10,10,1]
        #print ("Processing line for {}: {}".format(sensorid, line))
        vals = line.split()
        if len(vals) > 3:
            try:
                datearray.append(int(float(vals[2])*10))
                datearray.append(int(float(vals[0])*10))
                datearray.append(int(float(vals[1])*1))
            except:
                log.msg('{} protocol: Error while appending data to file'.format(self.sensordict.get('protocol')))

            try:
                data_bin = struct.pack('<'+packcode,*datearray) #little endian
            except:
                log.msg('{} protocol: Error while packing binary data'.format(self.sensordict.get('protocol')))

            #asseble header from available global information - write only if information is complete
            key = '[t2,var1,var2]'
            ele = '[Tv,V,Dir]'
            unit = '[degC,m_s,deg]'
            multplier = str(multiplier).replace(" ","")
            # Correct some common old problem
            unit = unit.replace('deg C', 'degC')
            #print ("ID process", sensorid)

            header = "# MagPyBin {} {} {} {} {} {} {}".format(sensorid, key, ele, unit, multplier, packcode, struct.calcsize('<'+packcode))
            data = ','.join(list(map(str,datearray)))

            if not self.confdict.get('bufferdirectory','') == '':
                acs.dataToFile(self.confdict.get('bufferdirectory'), sensorid, filename, data_bin, header)

        else:
            data = ''

        return data, header


    def sendRequest(self):

        success = True
        # connect to serial
        ser = serial.Serial(self.port, baudrate=int(self.baudrate), parity=self.parity, bytesize=int(self.bytesize), stopbits=int(self.stopbits), timeout=int(self.timeout))
        for commdict in self.commands:
            for item in sorted(commdict):
                comm = commdict.get(item)
                if self.debug:
                    print ("sending item {} with command {}".format(item, comm))
                # eventually more frequently ask for 'data'
                answer, actime = send_command_ascii(ser,comm,self.eol)
                # disconnect from serial
                ser.close()
                if self.debug:
                    print ("got answer: {}".format(answer))
                self.serialnum = self.serial1+self.serial2
                if item == 'data' and len(self.serialnum) > 7:
                    sensorid = "{}_{}_0001".format(str(self.sensorname),str(self.serialnum))
                    data, head = self.processData(sensorid, answer, actime)
                    # send data via mqtt
                    if not data == '':
                        self.sendmqtt(sensorid,data,head)
                if item == 'c2':
                    self.serial2 = answer.replace('!'+comm,'').strip()
                if item == 'c1':
                    self.serial1 = answer.replace('!'+comm,'').strip()

                # ##########################################################
                # answer is a string block with eventually multiple lines
                # apply the old linereceived method to each line of the answer
                # thats it ...

                #answer = ''.join(filter(lambda x: x in string.printable, answer))
                """
                if not success and self.errorcnt < 5:
                    self.errorcnt = self.errorcnt + 1
                    log.msg('SerialCall: Could not interpret response of system when sending %s' % item) 
                elif not success and self.errorcnt == 5:
                    try:
                        check_call(['/etc/init.d/martas', 'restart'])
                    except subprocess.CalledProcessError:
                        log.msg('SerialCall: check_call didnt work')
                        pass # handle errors in the called executable
                    except:
                        log.msg('SerialCall: check call problem')
                        pass # executable not found
                    #os.system("/etc/init.d/martas restart")
                    log.msg('SerialCall: Restarted martas process')
                """
        # disconnect from serial
        ser.close()

        # get answer
        #print("All commands send")

    def sendmqtt(self,sensorid,data,head):
        """
            call this method after processing data
        """

        ok = True
        if ok:

            topic = self.confdict.get('station') + '/' + sensorid

            senddata = False
            try:
                coll = int(self.sensordict.get('stack'))
            except:
                coll = 0

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
                if self.debug:
                    print ("publishing...")
                self.client.publish(topic+"/data", data, qos=self.qos)
                # If multiple sensors are connected, self.count needs to be a dict (with topic)
                # Initialize counter for each topic
                if self.counter.get(sensorid,'') == '':
                    self.counter[sensorid] = 0
                cnt = self.counter.get(sensorid)

                if cnt == 0:
                    ## 'Add' is a string containing dict info like: 
                    ## SensorID:ENV05_2_0001,StationID:wic, PierID:xxx,SensorGroup:environment,... 
                    add = "SensorID:{},StationID:{},DataPier:{},SensorModule:{},SensorGroup:{},SensorDescription:{},DataTimeProtocol:{}".format( sensorid,self.confdict.get('station','').strip(),self.sensordict.get('pierid','').strip(),self.sensordict.get('protocol','').strip(),self.sensordict.get('sensorgroup','').strip(),self.sensordict.get('sensordesc','').strip(),self.sensordict.get('ptime','').strip() )
                    self.client.publish(topic+"/dict", add, qos=self.qos)
                    self.client.publish(topic+"/meta", head, qos=self.qos)

                cnt += 1
                if cnt >= self.metacnt:
                    cnt = 0
                # update counter in dict 
                self.counter[sensorid] = cnt

