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

from core import acquisitionsupport as acs
from magpy.stream import read,KEYLIST,num2date
import glob
import os


## MySQL protocol
## --------------------

class imfileProtocol(object):
    """
    DESCRIPTION
       Protocol to read INTERMAGNET (actually MagPy) file data
       and broadcast/publish it in a MQTT stream.
       The selected data source (directory) is scanned for most
       recent data files matching a defined format.
       IMFile requires a path and a sensorid (if not contained in the file)
       IMFile is an active protocol, requesting data at defined periods.
       DataID name generation-is using sensorid and revision number (if provided)
    EXAMPLE
       sensors.cfg:
       WICadjusted,/home/leon/Cloud/Daten,-,-,-,-,active,None,30,1,IMfile,*.min,-,0001,-,-,-,magnetism,-

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
        self.revision = self.sensordict.get('revision','')
        try:
            self.requestrate = int(self.sensordict.get('rate','-'))
        except:
            self.requestrate = 30

        if self.requestrate < 30:
            log.msg('  -> Requestrate below 30 not accepted for IMFile. Setting 30sec')
            self.requestrate = 30

        self.deltathreshold = confdict.get('timedelta')

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

        # IMFile specific
        self.lastt=None
        self.filewildcard = sensordict.get('name')
        self.pathname = sensordict.get('port')
        if not self.filewildcard:
            self.filewildcard = '*'
        log.msg("  -> checking for files:", self.pathname, self.filewildcard)
        filepath = self.get_latest_file(self.pathname,self.filewildcard)
        # get existing sensors for the relevant board
        if filepath:
            # check whether files as defined by the filename are existing at all
            log.msg("  -> SUCCESS: most recent file in given path-filename structure is {}".format(filepath))
            self.connectionMade(self.sensor)
        else:
            self.connectionLost(self.sensor,"Files corresponding to filestructure not found - check path")
            return

    def connectionMade(self, imfile):
        log.msg('  -> Filestructure {} connected.'.format(imfile))

    def connectionLost(self, imfile, reason=''):
        log.msg('  -> Filestructure access {} lost/not connectect. ({})'.format(imfile,reason))
        # implement counter and add three reconnection events here

    def get_latest_file(self,path,source):
        latest = ""
        fullpath = os.path.join(path,source)
        if self.debug:
            log.msg("  -> DEBUG - checking for files: {}".format(fullpath))
        filelist = glob.glob(fullpath)
        latest = max(filelist,key=os.path.getctime)
        return latest

    def get_headline_info(self,data):
        keys = data._get_key_headers()
        units, elements = [], []
        for key in keys:
            ele = data.header.get("col-{}".format(key),"")
            if not ele:
                ele = key
            un = data.header.get("unit-col-{}".format(key),"")
            if not un:
                un = "None"
            elements.append(ele)
            units.append(un)

        return keys, units, elements

    def sendRequest(self):
        """
        source:mysql:
        Method to obtain data from table
        """
        t1 = datetime.utcnow()
        outdate = datetime.strftime(t1, "%Y-%m-%d")
        bufferfilename = outdate

        if self.debug:
            log.msg("  -> DEBUG - Sending periodic request ...")

        # get source and identify latest filepath
        filepath = self.get_latest_file(self.pathname,self.filewildcard)
        if self.revision:
            sensorid = self.sensor+"_"+self.revision
        else:
            sensorid = self.sensor
        if self.debug:
            log.msg("  -> DEBUG - dealing with sensor {}".format(sensorid))

        if self.debug:
            log.msg("  -> DEBUG - reading {}".format(filepath))
        try:
            data = read(filepath)
            if self.debug:
                log.msg("  -> DEBUG - read {}, with {}".format(filepath,data.length()[0]))
        except:
            log.msg("  -> ERROR - accessing file at {}".format(filepath))

        if not data.length()[0] > 0:
            if self.debug:
                log.msg("  -> DEBUG - obtained empty file structure")
            return

        # Trim data set and only work with most recent data dependend on request
        # get sampling rate
        ts,te = data._find_t_limits()
        now = datetime.utcnow()
        # always deal with a timerange twice of the requestrate
        tlow = now-timedelta(seconds=self.requestrate*2)
        #TODO define a suitable startcondition for tlow
        tlow = ts
        if not self.lastt:
            self.lastt=tlow

        if te<=tlow:
            if self.debug:
                log.msg("  -> DEBUG - no new data at {} - file covers until {}".format(now,te))
            return
        if self.debug:
            log.msg("  -> DEBUG - triming data from {}".format(tlow))
        data = data.trim(starttime=self.lastt)
        self.lastt = te

        # obtain header information
        # required are lists from keys, elements and units
        keystab, units, elems = self.get_headline_info(data)
        if self.debug:
            log.msg("  -> DEBUG - creating head line with {}, {}, {}, {}".format(sensorid,keystab,units,elems))

        multplier = '['+','.join(map(str, [10000]*len(keystab)))+']'
        packcode = '6HL'+''.join(['q']*len(keystab))
        header = ("# MagPyBin {} {} {} {} {} {} {}".format(sensorid, '['+','.join(keystab)+']', '['+','.join(elems)+']', '['+','.join(units)+']', multplier, packcode, struct.calcsize('<'+packcode)))

        #transpose
        dataarray = data.ndarray
        orglist = [col for col in dataarray if len(col) == len(dataarray[0])]
        newli = np.transpose(orglist)

        for dataline in newli:
                timestamp = datetime.strftime(num2date(dataline[0]), "%Y-%m-%d %H:%M:%S.%f")
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
                    acs.dataToFile(self.confdict.get('bufferdirectory'), sensorid, bufferfilename, data_bin, header)
                if self.debug:
                    log.msg("  -> DEBUG - sending ... {}".format(','.join(list(map(str,datearray))), header))
                self.sendData(sensorid,','.join(list(map(str,datearray))),header,len(newli)-1)

        if self.debug:
            t2 = datetime.utcnow()
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
