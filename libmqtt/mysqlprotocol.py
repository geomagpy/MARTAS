from __future__ import print_function
from __future__ import absolute_import

# ###################################################################
# Import packages
# ###################################################################

import re     # for interpretation of lines
import struct # for binary representation
import socket # for hostname identification
import string # for ascii selection
import numpy as np
from datetime import datetime, timedelta
from twisted.protocols.basic import LineReceiver
from twisted.python import log

from magpy.acquisition import acquisitionsupport as acs
from magpy.stream import KEYLIST
import magpy.opt.cred as mpcred
import magpy.database as mdb


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

        self.sensorlist = []
        self.revision = self.sensordict.get('revision','')
        try:
            self.requestrate = int(self.sensordict.get('rate','-'))
        except:
            self.requestrate = 30


        # ------------------- IMPORTANT ------------------------- too be changed
        self.deltathreshold = 100 # only data not older then x seconds will be considered

        # debug mode
        debugtest = confdict.get('debug')
        self.debug = False
        if debugtest == 'True':
            log.msg('     DEBUG - {}: Debug mode activated.'.format(self.sensordict.get('protocol')))
            self.debug = True    # prints many test messages
        else:
            log.msg('  -> Debug mode = {}'.format(debugtest))

        # QOS
        self.qos=int(confdict.get('mqttqos',0))
        if not self.qos in [0,1,2]:
            self.qos = 0
        log.msg("  -> setting QOS:", self.qos)

        # Database specific
        self.db = self.sensor
        # get existing sensors for the relevant board
        log.msg("  -> IMPORTANT: MySQL assumes that database credentials ")
        log.msg("     are saved locally using magpy.cred with the same name as database")
        try:
            self.db = mdb.mysql.connect(host=mpcred.lc(self.sensor,'host'),user=mpcred.lc(self.sensor,'user'),passwd=mpcred.lc(self.sensor,'passwd'),db=self.sensor)
            self.connectionMade(self.sensor)
        except:
            self.connectionLost(self.sensor,"Database could not be connected - check existance/credentials")
            return

        sensorlist = self.GetDBSensorList(self.db, searchsql='')
        self.sensor = ''
        existinglist = acs.GetSensors(confdict.get('sensorsconf'),identifier='$')

        # if there is a sensor in existinglist which is not an active sensor, then drop it
        for sensdict in existinglist:
            if sensdict.get('sensorid','') in sensorlist:
                self.sensorlist.append(sensdict) 
        
        self.lastt = [None]*len(self.sensorlist)

        #print ("Existinglist")
        #print ("----------------------------------------------------------------")
        #print (self.sensorlist)


    def connectionMade(self, dbname):
        log.msg('  -> Database {} connected.'.format(dbname))

    def connectionLost(self, dbname, reason=''):
        log.msg('  -> Database {} lost/not connectect. ({})'.format(dbname,reason))
        # implement counter and add three reconnection events here


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

        senslist1, senslist2, senslist3 = [],[],[]
        # 1. Get search criteria (group and dataid):
        searchdataid = 'DataID LIKE "%{}"'.format(self.sensordict.get('revision',''))
        searchgroup = 'SensorGroup LIKE "%{}%"'.format(self.sensordict.get('sensorgroup',''))
        # 2. Perfom search for DataID:
        senslist1 = mdb.dbselect(db, 'SensorID', 'DATAINFO', searchdataid)
        if self.debug:
            log.msg("  -> DEBUG - Search DATAID {}: Found {} tables".format(self.sensordict.get('revision',''),len(senslist1))) 
        # 3. Perfom search for group:
        senslist2 = mdb.dbselect(db, 'SensorID', 'SENSORS', searchgroup)
        if self.debug:
            log.msg("  -> DEBUG - Searching for GROUP {}: Found {} tables".format(self.sensordict.get('sensorgroup',''),len(senslist2)))
        # 4. Combine searchlists
        senslist = list(set(senslist1).intersection(senslist2))
        if self.debug:
            log.msg("  -> DEBUG - Fullfilling both search criteria: Found {} tables".format(len(senslist)))

        # 5. Check tables with above search criteria for recent data:
        for sens in senslist:
            datatable = sens + "_" + self.sensordict.get('revision','')
            lasttime = mdb.dbselect(db,'time',datatable,expert="ORDER BY time DESC LIMIT 1")
            try:
                lt = datetime.strptime(lasttime[0],"%Y-%m-%d %H:%M:%S.%f")
                delta = now-lt
                if self.debug:
                    log.msg("  -> DEBUG - Sensor {}: Timediff = {} sec from now".format(sens, delta.total_seconds()))
                if delta.total_seconds() < self.deltathreshold:
                    senslist3.append(sens)
            except:
                if self.debug:
                    log.msg("No data table?")
                pass

        # 6. Obtaining relevant sensor data for each table
        print ("PART 6 --- putting together  -----")
        for sens in senslist3:
            values = {}
            values['sensorid'] = sens
            values['protocol'] = 'MySQL'
            values['port'] = '-'
            cond = 'SensorID = "{}"'.format(sens)
            vals = mdb.dbselect(db,'SensorName,SensorID,SensorSerialNum,SensorRevision,SensorGroup,SensorDescription,SensorTime','SENSORS',condition=cond)[0]
            vals = ['-' if el==None else el for el in vals]
            values['serialnumber'] = vals[2]
            values['name'] = vals[0]
            values['revision'] = vals[3]
            values['mode'] = 'active'
            pier = mdb.dbselect(db,'DataPier','DATAINFO',condition=cond)[0]
            values['pierid'] = pier
            values['ptime'] = vals[6]
            values['sensorgroup'] = vals[4]
            values['sensordesc'] = vals[5].replace(',',';')

            success = acs.AddSensor(self.confdict.get('sensorsconf'), values, block='SQL')

        return senslist3


    def sendRequest(self):
        """
        source:mysql:
        Method to obtain data from table
        """
        t1 = datetime.utcnow()
        outdate = datetime.strftime(t1, "%Y-%m-%d")
        filename = outdate

        if self.debug:
            log.msg("Sending periodic request ...")

        def getList(sql):
            cursor = self.db.cursor()
            try:
                cursor.execute(sql)
            except mysql.IntegrityError as message:
                return message
            except mysql.Error as message:
                return message
            except:
                return 'dbgetlines: unkown error'
            head = cursor.fetchall()
            keys = list(np.transpose(np.asarray(head))[0])
            return keys

        # get self.sensorlist
        # get last timestamps 
        # read all data for each sensor since last timestamp
        # send that and store last timestamp 
        for index,sensdict in enumerate(self.sensorlist):
            sensorid = sensdict.get('sensorid')
            if self.debug:
                log.msg("  -> DEBUG - dealing with sensor {}".format(sensorid))
            # 1. Getting header
            # -----------------
            # load keys, elements and units
            #header = "# MagPyBin %s %s %s %s %s %s %d" % (sensorid, key, ele, unit, multplier, packcode, struct.calcsize('<'+packcode))
            dataid = sensorid+'_'+self.revision
            keyssql = 'SHOW COLUMNS FROM %s' % (dataid)
            keystab = getList(keyssql)
            if 'time' in keystab:
                keystab.remove('time')
            if 'flag' in keystab:
                keystab.remove('flag')
            if 'typ' in keystab:
                keystab.remove('typ')
            if 'comment' in keystab:
                keystab.remove('comment')
            keys = ','.join(keystab)
            sql1 = 'SELECT SensorElements FROM SENSORS WHERE SensorID LIKE "{}"'.format(sensorid)
            sql2 = 'SELECT Sensorkeys FROM SENSORS WHERE SensorID LIKE "{}"'.format(sensorid)
            sql3 = 'SELECT ColumnUnits FROM DATAINFO WHERE SensorID LIKE "{}"'.format(sensorid)
            sql4 = 'SELECT ColumnContents FROM DATAINFO WHERE SensorID LIKE "{}"'.format(sensorid)
            elem = getList(sql1)[0].split(',')
            keyssens = getList(sql2)[0].split(',')
            unit = getList(sql3)[0].split(',')
            cont = getList(sql4)[0].split(',')
            units, elems = [], []
            for key in keystab:
                try:
                    pos1 = keyssens.index(key)
                    ele = elem[pos1]
                except:
                    ele = key
                elems.append(ele)
                try:
                    pos2 = cont.index(ele)
                    units.append(unit[pos2])
                except:
                    units.append('None')
            multplier = '['+','.join(map(str, [10000]*len(keystab)))+']'
            packcode = '6HL'+''.join(['q']*len(keystab))
            header = ("# MagPyBin {} {} {} {} {} {} {}".format(sensorid, '['+','.join(keystab)+']', '['+','.join(elems)+']', '['+','.join(units)+']', multplier, packcode, struct.calcsize('<'+packcode)))

            # 2. Getting dict
            sql = 'SELECT DataSamplingRate FROM DATAINFO WHERE SensorID LIKE "{}"'.format(sensorid)
            sr = float(getList(sql)[0])
            coverage = int(self.requestrate/sr)+5

            # 3. Getting data
            # get data data and create typical message topic
            # based on sampling rate and collection rate -> define coverage
            
            li = sorted(mdb.dbselect(self.db, 'time,'+keys, dataid, expert='ORDER BY time DESC LIMIT {}'.format(int(coverage))))
            if not self.lastt[index]:
                self.lastt[index]=li[0][0]

            # drop
            newdat = False
            newli = []
            for elem in li:
                if newdat:
                    newli.append(elem)
                if elem[0] == self.lastt[index]:
                    newdat = True

            for dataline in newli:
                timestamp = dataline[0]
                data_bin = None
                datearray = ''
                try:
                    datearray = acs.timeToArray(timestamp)
                    for i,para in enumerate(keystab):
                        try:
                            val=int(float(dataline[i+1])*10000)
                        except:
                            val=999990000
                        datearray.append(val)
                    data_bin = struct.pack('<'+packcode,*datearray)  # little endian
                except:
                    log.msg('Error while packing binary data')

                if not self.confdict.get('bufferdirectory','') == '' and data_bin:
                    acs.dataToFile(self.confdict.get('bufferdirectory'), sensorid, filename, data_bin, header)
                #print ("Sending", ','.join(list(map(str,datearray))), header)
                self.sendData(sensorid,','.join(list(map(str,datearray))),header,len(newli)-1)

            self.lastt[index]=li[-1][0]

        t2 = datetime.utcnow()
        if self.debug:
            log.msg("  -> DEBUG - Needed {}".format(t2-t1))


    def sendData(self, sensorid, data, head, stack=None):

        topic = self.confdict.get('station') + '/' + sensorid
        senddata = False
        if not stack:
            stack = int(self.sensordict.get('stack'))
        coll = stack

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
                if self.count == 0:
                    # get all values initially from the database
                    #add = "SensoriD:{},StationID:{},DataPier:{},SensorModule:{},SensorGroup:{},SensorDecription:{},DataTimeProtocol:{}".format( sensorid, self.confdict.get('station',''),self.sensordict.get('pierid',''), self.sensordict.get('protocol',''),self.sensordict.get('sensorgroup',''),self.sensordict.get('sensordesc',''), self.sensordict.get('ptime','') )
                    #self.client.publish(topic+"/dict", add, qos=self.qos)
                    self.client.publish(topic+"/meta", head, qos=self.qos)
                    if self.debug:
                        log.msg("  -> DEBUG - Publishing meta --", topic, head)
                self.client.publish(topic+"/data", data, qos=self.qos)
                if self.debug:
                    log.msg("  -> DEBUG - Publishing data")
                self.count += 1
                if self.count >= self.metacnt:
                    self.count = 0

