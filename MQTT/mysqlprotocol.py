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
import magpy.database as mdb

from methodstobemovedtoacs import *



## Arduino protocol
## --------------------

class MySQLProtocol(object):
    """
    Protocol to read SQL data (usually from ttyACM0)
    MySQL protocol reads data from a MagPy database.
    All Sensors which receive continuous data updates are identified and added 
    to the sensors.cfg list (marked as inactive). 
    Here data can be selected and deselected. Update requires the removal of all 
    data of a specific database from sensors.cfg.
    MySQL is an active protocol, requesting data at defined periods. 
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

        # switch on debug mode
        debugtest = confdict.get('debug')
        self.debug = False
        if debugtest == 'True':
            log.msg('DEBUG - {}: Debug mode activated.'.format(self.sensordict.get('protocol')))
            self.debug = True    # prints many test messages
        else:
            log.msg('  -> Debug mode = {}'.format(debugtest))

        # Database specific
        self.db = self.sensor
        if self.debug:
            log.msg("DEBUG - Running on board {}".format(self.board))
        # get existing sensors for the relevant board
        self.existinglist = GetSensors(confdict.get('sensorsconf'),identifier='?',secondidentifier=self.board)
        self.sensor = ''

        # none is verified when initializing
        self.verifiedids = []
        self.infolist = []
        self.headlist = []


    def connectionMade(self):
        log.msg('  -> Database {} connected.'.format(self.db))

    def connectionLost(self, reason):
        log.msg('  -> Database {} lost.'.format(self.db))
        # implement counter and add three reconnection events here

    def processMySQLData(self, sensorid, meta, data):
        """Convert raw ADC counts into SI units as per datasheets"""
        currenttime = datetime.utcnow()
        outdate = datetime.strftime(currenttime, "%Y-%m-%d")
        actualtime = datetime.strftime(currenttime, "%Y-%m-%dT%H:%M:%S.%f")
        outtime = datetime.strftime(currenttime, "%H:%M:%S")
        timestamp = datetime.strftime(currenttime, "%Y-%m-%d %H:%M:%S.%f")
        filename = outdate

        datearray = acs.timeToArray(timestamp)
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
                variable = var[1].strip().lower()
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


    def GetDBSensorList(self, line):
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
                if idnum in [idict.get('ID') for idict in self.infolist] and idnum in [hdict.get('ID') for hdict in self.headlist]:
                    # get critical info: sensorname, idnum and board
                    sensoridenti = [idict.get('SensorName') for idict in self.infolist if str(idict.get('ID')) == str(idnum)]
                    # board is already selected
                    seldict2 = [edict for edict in self.existinglist if str(edict.get('path')) == str(idnum)]
                    seldict3 = [edict for edict in seldict2 if str(edict.get('name')) == str(sensoridenti[0])]
                    if not len(seldict3) > 0 and len(sensoridenti) > 0:
                        log.msg("Arduino: Sensor {} not yet existing -> adding to existinglist".format(sensoridenti[0]))
                        relevantdict = [idict for idict in self.infolist if str(idict.get('ID')) == str(idnum)][0]
                        values = {}
                        values['path'] = idnum
                        values['serialnumber'] = relevantdict.get('SensorID')
                        values['name'] = relevantdict.get('SensorName')
                        values['protocol'] = 'Arduino'
                        values['port'] = self.board
                        values['revision'] = relevantdict.get('SensorRevision')
                        values['stack'] = 0
                        values['sensorid'] = sensoridenti[0]
                        log.msg("Arduino: Writing new sensor input to sensors.cfg ...")
                        success = AddSensor(self.confdict.get('sensorsconf'), values, block='Arduino')
                        #success = acs.AddSensor(self.confdict.get('sensorsconf'), values, block='Arduino')
                        self.existinglist.append(values)
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
                self.client.publish(topic+"/data", pdata)
                if self.count == 0:
                    self.client.publish(topic+"/meta", head)
                    ## 'Add' is a string containing dict info like: 
                    ## SensorID:ENV05_2_0001,StationID:wic, PierID:xxx,SensorGroup:environment,... 
                    add = "SensoriD:{},StationID:{},DataPier:{},SensorModule:{},SensorGroup:{},SensorDecription:{},DataTimeProtocol:{}".format( evdict.get('sensorid',''),self.confdict.get('station',''),evdict.get('pierid',''),evdict.get('protocol',''),evdict.get('sensorgroup',''),evdict.get('sensordesc',''),evdict.get('ptime','') )
                    self.client.publish(topic+"/dict", add)

                self.count += 1
                if self.count >= self.metacnt:
                    self.count = 0

