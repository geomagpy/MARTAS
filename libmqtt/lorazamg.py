from __future__ import print_function
from __future__ import absolute_import

# ###################################################################
# Import packages
# ###################################################################

from magpy.stream import DataStream, KEYLIST, NUMKEYLIST, subtractStreams
#from magpy.database import mysql,writeDB
#from magpy.opt import cred as mpcred

## Import Twisted for websocket and logging functionality
#from twisted.python import log
#from twisted.web.server import Site
#from twisted.web.static import File
#from twisted.internet import reactor

#import threading
#from multiprocessing import Process
#import struct
from datetime import datetime 
#from matplotlib.dates import date2num, num2date
#import numpy as np
import json

# For file export
## -----------------------------------------------------------
#import StringIO
#from magpy.acquisition import acquisitionsupport as acs

## Import specific MARTAS packages
## -----------------------------------------------------------
#from doc.version import __version__
#from doc.martas import martaslog as ml

## Import MQTT
## -----------------------------------------------------------
#import paho.mqtt.client as mqtt
#import sys, getopt, os


## LORA-ZAMG - protocol
##
class lorazamg(object):
    """
    """

    def __init__(self):
        """
        """
        print ("  -> Initializing lora zamg routines ...")
        #self.payload = payload
        #self.topic = topic
        self.topicidentifier = {'startswith':'ZAMG','endswith':'adeunis'}
        self.datakeytranslator = {'tl':['t1','degC'], 'rf':['var1','per'], 'corr':['var5','none']}
        self.identifier = {}
        self.headdict = {}
        self.headstream = {}

    def GetPayload(self, payload, topic):
        loradict = json.loads(msg.payload)

        # convert loradict to headdict (header) and data_bin
        msg.payload, sensorid =  self.loradict2datastruct(loradict)
        msg.topic = msg.topic+'/data'

    def loradict2datastruct(self, loradict):
            datakeytranslator = {'tl':['t1','degC'], 'rf':['var1','per'], 'corr':['var5','none']}
            datadict = loradict.get('data')
            issuedict = (loradict.get('issue'))
            header = {}
            header['SensorName'] = loradict.get('Name').split(' ')[0]
            try:
                header['StationID'] = loradict.get('Name').strip().split(' - ')[1]
            except:
                header['StationID'] = "Not defined"
            #header['SensorName'] = loradict.get('Name').split(' - ').strip()[0]
            header['SensorSerialNum'] = issuedict.get('deveui','').replace('-','')
            header['SensorDataLoggerSerNum'] = issuedict.get('appeui','').replace('-','')
            header['SensorGroup'] = loradict.get('Modell')
            sensorid = header['SensorName'].split(' ')[0] + '_' + header['SensorSerialNum'] + '_0001'
            header['SensorID'] = sensorid

            # needs to return headstream[sensorid] = header (global)
            # identifier dictionary  (global)
            # sensorid
            # headdict[sensorid] = "MagPy line"  (global)
            # and data payload

            keylist, elemlist, unitlist, multilist = [],[],[],[]
            time = datetime.strptime(loradict.get('DateTime'),"%Y-%m-%dT%H:%M:%S.%fZ")
            datalst = datetime2array(time)
            packstr = '6hL'
            for elem in datadict:
                if elem in datakeytranslator:
                    key = datakeytranslator[elem][0]
                    unit = datakeytranslator[elem][1]
                    keylist.append(key)
                    elemlist.append(elem)
                    unitlist.append(unit)
                    multilist.append(1000)
                    packstr += "l"
                    datalst.append(int(datadict[elem]*1000))   
                #print (elem, datadict[elem])

            datalst = [str(elem) for elem in datalst]
            dataline =','.join(datalst)
            #print ("DATA", dataline)
            identifier[sensorid+':packingcode'] = packstr
            identifier[sensorid+':keylist'] = keylist
            identifier[sensorid+':elemlist'] = elemlist
            identifier[sensorid+':unitlist'] = unitlist
            identifier[sensorid+':multilist'] = multilist
            def identifier2line(dic, sensorid):
                p1 = identifier.get(sensorid+':packingcode')
                p2 = identifier.get(sensorid+':keylist')
                p3 = identifier.get(sensorid+':elemlist')
                p4 = identifier.get(sensorid+':unitlist')
                p5 = identifier.get(sensorid+':multilist')
                p5 = [str(elem) for elem in p5]
                size = struct.calcsize(p1)
                line = "# MagPyBin {} [{}] [{}] [{}] [{}] {} {}".format(sensorid,','.join(p2),','.join(p3),','.join(p4),','.join(p5),p1,size)
                return line

            def merge_two_dicts(x, y):
                z = x.copy()   # start with x's keys and values
                z.update(y)    # modifies z with y's keys and values & returns None
                return z

            headdict[sensorid] = identifier2line(identifier, sensorid)
            headstream[sensorid] = create_head_dict(headdict[sensorid],sensorid)
            headstream[sensorid] = merge_two_dicts(headstream[sensorid], header)
            #print ("HEAD1", headdict[sensorid])
            #print ("HEAD2", headstream[sensorid])
            return dataline, sensorid


