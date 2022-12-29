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
from core import acquisitionsupport as acs
from magpy.stream import KEYLIST
import serial
import subprocess
import sys
import time

## Aktive Arduino protocol
## -----------------------

class ActiveArduinoProtocol(object):
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
        self.client = client #self.wsMcuFactory = wsMcuFactory
        self.sensordict = sensordict
        self.confdict = confdict
        self.count = 0  ## counter for sending header information
        self.sensor = sensordict.get('sensorid')
        self.hostname = socket.gethostname()
        self.printable = set(string.printable)
        self.datalst = []
        self.datacnt = 0
        self.metacnt = 10
        self.counter = {}
        self.initserial = True

        # Commands (take them sensordesc)
        # i.e. sensordesc : owT-swD
        commandlist = sensordict.get('sensordesc').strip().replace('\n','').split('-')
        if not 'arduino sensors' in commandlist:
            cdict = {}
            for idx,com in enumerate(commandlist):
                cdict['data{}'.format(idx)] = com
            self.commands = [cdict]
            print ("Commands from sensordesc:", self.commands)
        else:
            self.commands = [{'data1':'owT','data2':'swD'}]
            print ("Default commands selected")
        self.hexcoding = False
        self.eol = '\r\n'

        # Serial communication data (from confdict)
        self.sensor = sensordict.get('sensorid')
        self.baudrate=int(sensordict.get('baudrate'))
        self.port = confdict['serialport']+sensordict.get('port')
        self.parity=sensordict.get('parity')
        self.bytesize=sensordict.get('bytesize')
        self.stopbits=sensordict.get('stopbits')
        self.timeout=2 # should be rate depended

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
        self.ser = None

        # none is verified when initializing
        self.verifiedids = []
        self.infolist = []
        self.headlist = []

    def datetime2array(self,t):
        return [t.year,t.month,t.day,t.hour,t.minute,t.second,t.microsecond]

    def open_connection(self):
        log.msg("connecting to serial port")
        ser = serial.Serial(self.port, baudrate=int(self.baudrate), parity=self.parity, bytesize=int(self.bytesize), stopbits=int(self.stopbits), timeout=self.timeout)
        # wait for arduino (tested: 2 sec are necessary)
        time.sleep(2)
        self.ser = ser
        return ser

    def restart(self):
        try:
            subprocess.check_call(['/etc/init.d/martas', 'restart'])
        except subprocess.CalledProcessError:
            log.msg('SerialCall: check_call didnt work')
            pass # handle errors in the called executable
        except:
            log.msg('SerialCall: check call problem')
            pass # executable not found
        log.msg('SerialCall: Restarted martas process')


    def processArduinoData(self, sensorid, meta, data):
        """Convert raw ADC counts into SI units as per datasheets"""
        currenttime = datetime.utcnow()
        outdate = datetime.strftime(currenttime, "%Y-%m-%d")
        #actualtime = datetime.strftime(currenttime, "%Y-%m-%dT%H:%M:%S.%f")
        #outtime = datetime.strftime(currenttime, "%H:%M:%S")
        #timestamp = datetime.strftime(currenttime, "%Y-%m-%d %H:%M:%S.%f")
        filename = outdate

        datearray = self.datetime2array(currenttime)

        #datearray = acs.timeToArray(timestamp)
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

        key = '['+str(meta.get('SensorKeys')).replace("'","").strip()+']'
        ele = '['+str(meta.get('SensorElements')).replace("'","").strip()+']'
        unit = '['+str(meta.get('SensorUnits')).replace("'","").strip()+']'
        multplier = str(multiplier).replace(" ","")
        # Correct some common old problem
        unit = unit.replace('deg C', 'degC')

        header = "# MagPyBin %s %s %s %s %s %s %d" % (sensorid, key, ele, unit, multplier, packcode, struct.calcsize('<'+packcode))

        if not self.confdict.get('bufferdirectory','') == '':
            acs.dataToFile(self.confdict.get('bufferdirectory'), sensorid, filename, data_bin, header)

        return ','.join(list(map(str,datearray))), header


    def analyzeHeader(self, line):
        log.msg("  -> Received unverified header data")
        if self.debug:
            log.msg("DEBUG -> Header looks like: {}".format(line))
        headdict = {}

        head = line.strip().split(':')
        headernum = int(head[0].strip('H'))
        header = head[1].split(',')

        try:
            varlist = []
            keylist = []
            unitlist = []
            for elem in header:
                an = elem.strip(']').split('[')
                try:
                    if len(an) < 1:
                        log.err("Arduino: error when analyzing header")
                        return {}
                except:
                    log.err("Arduino: error when analyzing header")
                    return {}
                var = an[0].split('_')
                key = var[0].strip().lower()
                variable = var[1].strip()
                unit = an[1].strip()
                keylist.append(key)
                varlist.append(variable)
                unitlist.append(unit)
            headdict['ID'] = headernum
            headdict['SensorKeys'] = ','.join(keylist)
            headdict['SensorElements'] = ','.join(varlist)
            headdict['SensorUnits'] = ','.join(unitlist)
        except:
            # in case an incomplete header is available
            # will be read next time completely
            return {}

        return headdict


    def getSensorInfo(self, line):
        log.msg("  -> Received unverified sensor information")
        if self.debug:
            log.msg("DEBUG -> Sensor information line looks like: {}".format(line))
        metadict = {}
        try:
            metaident = line.strip().split(':')
            metanum = int(metaident[0].strip('M'))
            meta = line[3:].strip().split(',')
            for elem in meta:
                el = elem.split(':')
                metadict[el[0].strip()] = el[1].strip()
        except:
            log.err('  -> Could not interprete sensor information - skipping')
            return {}

        if not 'SensorRevsion' in metadict:
            metadict['SensorRevision'] = '0001' # dummy value
        if not 'SensorID' in metadict:
            metadict['SensorID'] = '12345' # dummy value
        if not 'SensorName' in metadict:
            print("No Sensorname provided - aborting")
            return {}
        metadict['ID'] = metanum
        return metadict


    def GetArduinoSensorList(self, line):
        """
         DESCRIPTION:
             Will analysze data line and a list of existing IDs.
             Please note: when initializing, then existing data will be taken from
             Arduino Block.
             - If ID is existing, this method will return its ID, sensorid, meta info
               as used by process data, and data.
             - If ID not yet existing: line will be scanned until all meta info is
               available. Method will return ID 0 and empty fields.
             - If meta info is coming: sensorids will be quickly checked against existing.
               If not existing and not yet used - ID will be added to sensors.cfg and existing
               If not existing but used so far - ID in file is wrong -> warning
               If existing and ID check OK: continue
        TODO: path number might change if a sensor is disconnected
              problem with sensorID and ID number...

        PARAMETER:
            existinglist: [list] [[1,2,...],['BM35_xxx_0001','SH75_xxx_0001',...]]
                          idnum is stored in sensordict['path'] (like ow)
        """
        #existingpathlist = [line.get('path') for line in existinglist]

        evdict = {}
        meta = 'not known'
        data = '1.0'

        lineident = line.split(':')
        try:
            idnum = int(lineident[0][1:])
        except:
            idnum = 999
        if not idnum == 999:
            if not idnum in self.verifiedids:
                if line.startswith('H'):
                    # analyse header
                    headdict = self.analyzeHeader(line)
                    self.headlist.append(headdict)
                elif line.startswith('M'):
                    # analyse sensorinformation
                    infodict = self.getSensorInfo(line)
                    self.infolist.append(infodict)
                    # add values to metadict
                # at this stage i have the correct sensorid in infodict
                if idnum in [idict.get('ID') for idict in self.infolist] and idnum in [hdict.get('ID') for hdict in self.headlist]:
                    # idnums found in line, present in head and meta data
                    sensoridenti = [idict.get('SensorName') for idict in self.infolist if str(idict.get('ID')) == str(idnum)]
                    # get sensorid as well for the identificationnumner
                    sensoridininfo = [idict.get('SensorID') for idict in self.infolist if str(idict.get('ID')) == str(idnum)]
                    # board is already selected
                    seldict2 = [edict for edict in self.existinglist if str(edict.get('path')) == str(idnum)]
                    # if a single sensor id is found:
                    # it might happen that idnum (path in existinglist) is not referring
                    # to the correct sensorid. This might happen if e.g. one ow temperature
                    # sensor is disconnected, when previously two have been attached.
                    # after restart the remaining sensor will have the lowest id, not
                    # necessarily matching the originally stored one.
                    # Therefor we check it and eventually assign a new id/path
                    if len(sensoridininfo) == 1:
                        sensid = sensoridininfo[0]
                        seldict1 = [edict for edict in self.existinglist if edict.get('sensorid').find(sensid) > -1]
                    else:
                        seldict1 = seldict2
                    if not seldict1==seldict2:
                        # sensorid not matching the sensoid stored with this idnum/path
                        seldict2 = seldict1
                        # therefore update pathid in selfexistinglist
                        self.existinglist = [e for e in self.existinglist if not str(e.get('path')) == str(idnum)]
                        seldicttmp = seldict1[-1]
                        seldicttmp['path'] = str(idnum)
                        self.existinglist.append(seldicttmp)
                    seldict3 = [edict for edict in seldict2 if str(edict.get('name')) == str(sensoridenti[0])]
                    # Select correct idnum, so that sesnorid's are fitting
                    if not len(seldict3) > 0 and len(sensoridenti) > 0:
                        log.msg("Arduino: Sensor {} not yet existing -> adding to existinglist".format(sensoridenti[0]))
                        relevantdict = [idict for idict in self.infolist if str(idict.get('ID')) == str(idnum)][0]
                        values = {}
                        values['path'] = idnum
                        values['serialnumber'] = relevantdict.get('SensorID')
                        values['name'] = relevantdict.get('SensorName')
                        values['protocol'] = 'Arduino'
                        values['port'] = self.board
                        values['ptime'] = relevantdict.get('DataTimeProtocol','-')
                        values['pierid'] = relevantdict.get('DataPier','-')
                        values['sensordesc'] = relevantdict.get('SensorDecription','-')
                        values['sensorgroup'] = relevantdict.get('SensorGroup','-')
                        values['revision'] = relevantdict.get('SensorRevision')
                        values['stack'] = 0
                        values['sensorid'] = sensoridenti[0]+'_'+relevantdict.get('SensorID')+'_'+relevantdict.get('SensorRevision')
                        log.msg("Arduino: Writing new sensor input to sensors.cfg ...")
                        success = acs.AddSensor(self.confdict.get('sensorsconf'), values, block='Arduino')
                        #success = acs.AddSensor(self.confdict.get('sensorsconf'), values, block='Arduino')
                        print ("Add sensor done")
                        self.existinglist.append(values)
                        print ("sensor added to arduino list")

                    elif len(seldict3) > 0:
                        log.msg("Arduino: Sensor {} identified and verified".format(sensoridenti[0]))
                        self.verifiedids.append(idnum)
                    else:
                        log.err('Apparently a sensor is connected which does not correspond to the provided information in sensors.cfg - Please clarify (either delete sensor.cfg input for {} or check your arduino code'.format(sensoridenti[0]))

            else:
                if line.startswith('D'):
                    dataar = line.strip().split(':')
                    dataident = int(dataar[0].strip('D'))
                    meta = [headdict for headdict in self.headlist if str(headdict.get('ID')) == str(dataident)][0]
                    evdict = [edict for edict in self.existinglist if str(edict.get('path')) == str(idnum)][0]
                    data = dataar[1].strip().split(',')

        else:
            # invalid return value found
            if self.debug:
                log.msg("DEBUG - Invalid return value found: {}".format(line))

        return evdict, meta, data


    def sendRequest(self):

        # connect to serial
        ser = self.ser
        if not ser or not ser.isOpen():
            ser = self.open_connection()
        #ser = serial.Serial(self.port, baudrate=int(self.baudrate), parity=self.parity, bytesize=int(self.bytesize), stopbits=int(self.stopbits), timeout=self.timeout)
        # wait for arduino (tested: 2 sec are necessary)
        #time.sleep(2)

        def write_read(ser,command,end="MARTASEND",maxcnt=20,debug=False):
            data = b""
            dedata = ""
            all = ""
            cnt=0
            ser.flush()
            try:
                ser.write(command)
                #responsetime1 = datetime.utcnow()
                time.sleep(.1)
                while not dedata.find(end) > -1 and not cnt == maxcnt:
                   cnt+=1
                   data = ser.readline()
                   #responsetime2 = datetime.utcnow()
                   if sys.version_info >= (3, 0):
                       dedata = str(data.decode("utf-8"))
                   else:
                       dedata = str(data)
                   if not dedata:
                       if debug:
                           log.msg("DEBUG - got empty line")
                   else:
                       all += dedata
                # time estimate: mean(resp1,resp2)-0.1sec
                return all
            except serial.SerialException as e:
                if debug:
                    log.msg("SerialException found ({})".format(e)) # - restarting martas ...")
                time.sleep(0.1)
                #self.restart()
            except:
                log.msg("Other exception found")
                raise

            if cnt == maxcnt:
                if debug:
                    log.msg('Maximum count {} was reached without MARTASEND'.format(maxcnt))
            return all


        def get_commands(condition="data"):
            # create a command list from given values in sensors.cfg
            # also check for python2 and py3
            coms=[]
            for sensordict in self.commands:
                for item in sensordict:
                    command = sensordict.get(item)
                    n = command.count(":")
                    miss=-(n-2)
                    for n in range(miss):
                        command += ':'
                    command = command+self.eol
                    if sys.version_info >= (3, 0):
                        command = command.encode('utf-8')
                    if item.startswith(condition):
                        coms.append(command)
            return coms

        def run_analysis(answer):
            lines = answer.split("\n")
            for line in lines:
                try:
                    if line and len(line)>2 and (line[2] == ':' or line[3] == ':'):
                        self.analyzeline(line)
                except:
                    pass

        coms = get_commands()
        if self.debug:
            log.msg("DEBUG - sending the following commands to serial port: {}".format(coms))

        if ser.isOpen():
            for command in coms:
                answer = write_read(ser,command,debug=self.debug)
                if self.debug:
                    log.msg("DEBUG - received the following answer for command {}: {}".format(command,answer))
                run_analysis(answer)
            #ser.close()
        else:
            print ("lib activearduino: Could not open serial port")

    def analyzeline(self, line):

        if self.debug:
            log.msg("Received line: {}".format(line))

        # extract only ascii characters
        line = ''.join(filter(lambda x: x in string.printable, str(line)))

        # Create a list of sensors like for OW
        # dispatch with the appropriate sensor
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
