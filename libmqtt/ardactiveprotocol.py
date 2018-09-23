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
from magpy.stream import KEYLIST


def send_command(ser,command,eol,hex=False):
    #use printable here
    printable = set(string.printable)
    response = ''
    fullresponse = ''
    maxcnt = 50
    cnt = 0
    command = command+eol
    if(ser.isOpen() == False):
        ser.open()
    sendtime = datetime.utcnow()
    ser.write(command)
    # skipping all empty lines 
    while response == '': 
        response = ser.readline()
    # read until end-of-messageblock signal is obtained (use some break value)
    while not response.startswith('<MARTASEND>') and not cnt == maxcnt:
        cnt += 1
        fullresponse += response
        response = ser.readline()
    responsetime = datetime.utcnow()
    if cnt == maxcnt:
        fullresponse = 'Maximum count {} was reached'.format(maxcnt)
    return fullresponse


def datetime2array(t):
    return [t.year,t.month,t.day,t.hour,t.minute,t.second,t.microsecond]

## Arduino active request protocol
## --------------------

class ArdactiveProtocol(object):
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
        # SENSORS
        #    'sensorid','port','baudrate','bytesize','stopbits','parity',
        #e.g.   xx
        #     'mode',  'init',  'rate', 'stack',  'protocol',  'name',   'serialnumber', 
        #e.g. active              5        -        
        #    'revision',   'path',   'pierid',   'ptime',   'sensorgroup',   'sensordesc'
        #e.g.
        #     additionally required:
        #     'commands',      'coding',    'eol'
        #e.g. P:1:4;Status       HEX         /r

        # commands is a list of dictionaries, one for each sensor describing some information levels
        #self.addressanemo = '01'
        self.commands = [{'data':'11TR00005'},{'meta':''},{'head':''}] # ,self.addressanemo+'TR00002']

        self.commands = ['','']
        self.hexcoding = False
        self.eol = '/r'


        self.client = client #self.wsMcuFactory = wsMcuFactory
        self.sensordict = sensordict
        self.confdict = confdict
        self.count = 0  ## counter for sending header information

        self.sensor = sensordict.get('sensorid')
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
        self.metacnt = 10
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

        # Arduino specific
        self.board = self.sensor
        if self.debug:
            log.msg("DEBUG - Running on board {}".format(self.board))
        # get existing sensors for the relevant board
        self.existinglist = acs.GetSensors(confdict.get('sensorsconf'),identifier='?',secondidentifier=self.board)
        self.sensor = ''

        # none is verified when initializing
        self.verifiedids = []
        self.infolist = []
        self.headlist = []

    def processBlock(self, sensorid, meta, data):
        """Convert raw ADC counts into SI units as per datasheets"""
        currenttime = datetime.utcnow()
        outdate = datetime.strftime(currenttime, "%Y-%m-%d")
        actualtime = datetime.strftime(currenttime, "%Y-%m-%dT%H:%M:%S.%f")
        outtime = datetime.strftime(currenttime, "%H:%M:%S")
        filename = outdate

        datearray = datetime2array(currenttime)
        packcode = '6hL'
        #sensorid = self.sensordict.get(idnum)
        #events = self.eventdict.get(idnum).replace('evt','').split(',')[3:-1]

        values = []
        multiplier = []
        for dat in data:
            try:
                values.append(float(dat))
                datearray.append(int(float(dat)*10000))
                packcode = packcode + 'l'
                multiplier.append(10000)
            except:
                log.msg('{} protocol: Error while appending data to file (non-float?): {}'.format(self.sensordict.get('protocol'),dat) )

        try:
            data_bin = struct.pack('<'+packcode,*datearray) #little endian
        except:
            log.msg('{} protocol: Error while packing binary data'.format(self.sensordict.get('protocol')))
            pass

        #asseble header from available global information - write only if information is complete
        key = '['+str(meta.get('SensorKeys')).replace("'","").strip()+']'
        ele = '['+str(meta.get('SensorElements')).replace("'","").strip()+']'
        unit = '['+str(meta.get('SensorUnits')).replace("'","").strip()+']'
        multplier = str(multiplier).replace(" ","")
        # Correct some common old problem
        unit = unit.replace('deg C', 'degC')

        header = "# MagPyBin %s %s %s %s %s %s %d" % (sensorid, key, ele, unit, multplier, packcode, struct.calcsize('<'+packcode))

        if not self.confdict.get('bufferdirectory','') == '' and headercomplete:
            acs.dataToFile(self.confdict.get('bufferdirectory'), sensorid, filename, data_bin, header)

        return ','.join(list(map(str,datearray))), header


    def processHead(self, data):
        """
            eventually fill meta directory with special info - frequent
        """
        pass


    def processMeta(self, data):
        """
            eventually fill meta directory with special info - even less frequent
        """
        pass


    def sendRequest(self):

        # connect to serial
        ser = serial.Serial(self.port, baudrate=self.baudrate, parity=self.parity, bytesize=self.bytesize, stopbits=self.stopbits, timeout=timeout)

        # send request string()
        print("Sending commands: {} ...".format(self.commands))
        #answer = send_command(ser,command,eol)
        for sensordict in self.commands:
            for item in sensordict:
                #print ("sending command", item)
                # eventually more frequnetly ask for 'data'
                answer, actime = send_command(ser,sensordict.get(item),self.eol,hex=self.hexcoding)
                # disconnect from serial
                ser.close()
                if item == 'block':
                    success = self.processBlock(answer, actime)
                #if item == 'data':
                #    success = self.processData(sensorid, meta, answer, actime)
                #if item == 'head':
                #    success = self.processHead(answer, actime)
                #if item == 'meta':
                #    success = self.processMeta(answer, actime)

                # ##########################################################
                # answer is a string block with eventually multiple lines
                # apply the old linereceived method to each line of the answer
                # thats it ...

                #answer = ''.join(filter(lambda x: x in string.printable, answer))

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

        # get answer
        print("Answer: {}".format(answer))


        # analyse answer
        #self.processData(answer)
        #self.senddata

        
    def sendmqtt(self,topicdef,payload):
        """
            call this method in process data
        """
        self.client.publish(topic+"/"+topicdef, payload, qos=self.qos)


"""
    def lineReceived(self, line):

        #if self.debug:
        #    log.msg("Received line: {}".format(line))

        # extract only ascii characters 
        line = ''.join(filter(lambda x: x in string.printable, line))

        # Create a list of sensors like for OW
        # dipatch with the appropriate sensor
        evdict, meta, data = self.GetArduinoSensorList(line)

        if len(evdict) > 0:
            sensorid = evdict.get('name')+'_'+evdict.get('serialnumber')+'_'+evdict.get('revision')
            topic = self.confdict.get('station') + '/' + sensorid
            pdata, head = self.processArduinoData(sensorid, meta, data)

            senddata = False
            try:
                coll = int(evdict.get('stack'))
            except:
                coll = 0

            if coll > 1:
                self.metacnt = 1 # send meta data with every block
                if self.datacnt < coll:
                    self.datalst.append(pdata)
                    self.datacnt += 1
                else:
                    senddata = True
                    pdata = ';'.join(self.datalst)
                    self.datalst = []
                    self.datacnt = 0
            else:
                senddata = True

            if senddata:
                self.client.publish(topic+"/data", pdata, qos=self.qos)
                # If multiple sensors are connected, self.count needs to be a dict (with topic)
                # Initialize counter for each topic
                if self.counter.get(sensorid,'') == '':
                    self.counter[sensorid] = 0
                cnt = self.counter.get(sensorid)

                if cnt == 0:
                    ## 'Add' is a string containing dict info like: 
                    ## SensorID:ENV05_2_0001,StationID:wic, PierID:xxx,SensorGroup:environment,... 
                    add = "SensorID:{},StationID:{},DataPier:{},SensorModule:{},SensorGroup:{},SensorDescription:{},DataTimeProtocol:{}".format( evdict.get('sensorid',''),self.confdict.get('station','').strip(),evdict.get('pierid','').strip(),evdict.get('protocol','').strip(),evdict.get('sensorgroup','').strip(),evdict.get('sensordesc','').strip(),evdict.get('ptime','').strip() )
                    self.client.publish(topic+"/dict", add, qos=self.qos)
                    self.client.publish(topic+"/meta", head, qos=self.qos)

                cnt += 1
                #self.count += 1
                if cnt >= self.metacnt:
                    cnt = 0

                # update counter in dict 
                self.counter[sensorid] = cnt
"""
