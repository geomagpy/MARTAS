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
import magpy.opt.cred as mpcred
import magpy.database as mdb

#from methodstobemovedtoacs import *



## MySQL protocol
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

        print ("here")

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
        print ("  -> MySQL assumes that database credentials are saved locally using magpy.cred with the same name as database")
        db = mdb.mysql.connect(host="localhost",user=mpcred.lc(self.sensor,'user'),passwd=mpcred.lc(self.sensor,'passwd'),db=self.sensor)
        print ("here")
        sensorlist = self.GetDBSensorList(db, searchsql='')
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


    """
    def processMySQLData(self, sensorid, meta, data):
        #Convert raw ADC counts into SI units as per datasheets
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
        metadict = {}
        return metadict
    """


    def GetDBSensorList(self, db, searchsql=''):
        """
         DESCRIPTION:
             Will connect to data base and download all data id's satisfying 
             searchsql and containing data less then 5*sampling rate old. 

        PARAMETER:
            existinglist: [list] [[1,2,...],['BM35_xxx_0001','SH75_xxx_0001',...]]
                          idnum is stored in sensordict['path'] (like ow)
        """

        now = datetime.utcnow()

        if not searchsql == '':
            """
            if searchsql is list:
                for item in searchsql:
                    if not sql.endswith("WHERE ") and not item == searchsql[-1]:
                        sql = sql + " AND "
                    sql = sql + item
            else:
                sql = sql + searchsql
            """
        print (self.sensordict.get('revision',''),self.sensordict.get('sensorgroup',''))
        searchsql = 'DataID LIKE "%{}"'.format(self.sensordict.get('revision',''))

        # Perfom search:
        print (searchsql)
        senslist1 = mdb.dbselect(db, 'SensorID', 'DATAINFO', searchsql)
        print ("Found", senslist1)
        """
        searchsql = 'SensorGroup LIKE "%{}%"'.format(self.sensordict.get('sensorgroup',''))
        senslist2 = mdb.dbselect(db, 'SensorID', 'SENSORS', searchsql)

        senslist = list(set(senslist1).intersection(senslist2))
        print (senslist)
        """
        senslist = senslist1

        # Check tables for recent data:
        for sens in senslist:
            datatable = sens + "_" + self.sensordict.get('revision','')
            lasttime = mdb.dbselect(db,'time',datatable,expert="ORDER BY time DESC LIMIT 1")
            print (sens, lasttime)
            try:
                lt = datetime.strptime(lasttime[0],"%Y-%m-%d %H:%M:%S.%f")
                print (now-lt)
            except:
                print ("No data table?")

        # Check existing data
        #print ("Exist", self.sensordict)

        # Append sensors with recent data to sensordict if the sensor is either not already existing (also uncommented):
        # send warning if data in existinglist but not found now.

        for sens in senslist:
            print (sens)
            values = {}
            values['sensorid'] = sens
            values['protocol'] = 'MySQL'
            values['port'] = '-'
            cond = 'SensorID = "{}"'.format(sens)
            vals = mdb.dbselect(db,'SensorName,SensorID,SensorSerialNum,SensorRevision,SensorGroup,SensorDescription','SENSORS',condition=cond)[0]
            vals = ['-' if el==None else el for el in vals]
            print (vals)
            values['serialnumber'] = vals[2]
            values['name'] = vals[0]
            values['revision'] = vals[3]
            values['pierid'] = 'fromPIERS'
            values['ptime'] = 'NTP'
            values['sensorgroup'] = vals[4]
            values['sensordesc'] = vals[5].replace(',',';')

            #SENSORELEMENTS =  ['sensorid','port','baudrate','bytesize','stopbits', 'parity','mode','init','rate','stack','protocol','name','serialnumber','revision','path','pierid','ptime','sensorgroup','sensordesc']

            #success = acs.AddSensor(self.confdict.get('sensorsconf'), values, block='Arduino')
            #success = acs.AddSensor(self.confdict.get('sensorsconf'), values, block='MySQL')

            print (values)
            """
                        values['path'] = idnum
                        values['stack'] = 0
                        log.msg("Arduino: Writing new sensor input to sensors.cfg ...")
                        success = AddSensor(self.confdict.get('sensorsconf'), values, block='Arduino')
            """

    def sendRequest(self):
        log.msg("Sending periodic request ...")

        # get self.sensorlist
        # get last timestamps 
        # read all data for each sensor since last timestamp
        # send that and store last timestamp 

    """
        # Append sensors with recent data to sensordict if not existing and not uncommentet:
        # send warning if data in existinglist but not found now.
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

    """
