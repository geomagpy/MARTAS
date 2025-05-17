from __future__ import print_function
from __future__ import absolute_import

# ###################################################################
# Import packages
# ###################################################################

from magpy.stream import DataStream, KEYLIST, NUMKEYLIST, subtractStreams
import struct
from datetime import datetime 
import json
import base64
import binascii

def datetime2array(t):
        return [t.year,t.month,t.day,t.hour,t.minute,t.second,t.microsecond]

## LORA-ZAMG - protocol
##
class lorawanserver_status(object):
    """
       ********************************
       *                              *
       *   Gateway Status Meldungen   *
       *                              *
       ********************************

       Debugging: adding once after the other

       mosquitto_sub -h 138.22.165.37 -t "#" -v |grep stats
       gateway/00800000a0001285/stats {"mac":"00800000a0001285","time":"2018-12-14T16:06:46Z","rxPacketsReceived":1,"rxPacketsReceivedOK":1,"txPacketsReceived":0,"txPacketsEmitted":0,"customData":{"ip":"138.22.165.40"}}
       gateway/00800000a0001285/stats {"mac":"00800000a0001285","time":"2018-12-14T16:07:16Z","rxPacketsReceived":1,"rxPacketsReceivedOK":0,"txPacketsReceived":0,"txPacketsEmitted":0,"customData":{"ip":"138.22.165.40"}}
       gateway/00800000a0001285/stats {"mac":"00800000a0001285","time":"2018-12-14T16:07:46Z","rxPacketsReceived":0,"rxPacketsReceivedOK":0,"txPacketsReceived":0,"txPacketsEmitted":0,"customData":{"ip":"138.22.165.40"}}
       gateway/00800000a0001285/stats {"mac":"00800000a0001285","time":"2018-12-14T16:08:16Z","rxPacketsReceived":0,"rxPacketsReceivedOK":0,"txPacketsReceived":0,"txPacketsEmitted":0,"customData":{"ip":"138.22.165.40"}}
       gateway/00800000a0001285/stats {"mac":"00800000a0001285","time":"2018-12-14T16:08:46Z","rxPacketsReceived":0,"rxPacketsReceivedOK":0,"txPacketsReceived":0,"txPacketsEmitted":0,"customData":{"ip":"138.22.165.40"}}
       gateway/00800000a0001285/stats {"mac":"00800000a0001285","time":"2018-12-14T16:09:16Z","rxPacketsReceived":0,"rxPacketsReceivedOK":0,"txPacketsReceived":0,"txPacketsEmitted":0,"customData":{"ip":"138.22.165.40"}}
       gateway/00800000a0001285/stats {"mac":"00800000a0001285","time":"2018-12-14T16:09:46Z","rxPacketsReceived":0,"rxPacketsReceivedOK":0,"txPacketsReceived":0,"txPacketsEmitted":0,"customData":{"ip":"138.22.165.40"}}
       gateway/00800000a0001285/stats {"mac":"00800000a0001285","time":"2018-12-14T16:10:16Z","rxPacketsReceived":0,"rxPacketsReceivedOK":0,"txPacketsReceived":0,"txPacketsEmitted":0,"customData":{"ip":"138.22.165.40"}}
       gateway/00800000a0001285/stats {"mac":"00800000a0001285","time":"2018-12-14T16:10:46Z","rxPacketsReceived":0,"rxPacketsReceivedOK":0,"txPacketsReceived":0,"txPacketsEmitted":0,"customData":{"ip":"138.22.165.40"}}
       gateway/00800000a0001285/stats {"mac":"00800000a0001285","time":"2018-12-14T16:11:16Z","rxPacketsReceived":2,"rxPacketsReceivedOK":0,"txPacketsReceived":0,"txPacketsEmitted":0,"customData":{"ip":"138.22.165.40"}}
       gateway/00800000a0001285/stats {"mac":"00800000a0001285","time":"2018-12-14T16:11:46Z","rxPacketsReceived":2,"rxPacketsReceivedOK":0,"txPacketsReceived":0,"txPacketsEmitted":0,"customData":{"ip":"138.22.165.40"}}
       gateway/00800000a0001285/stats {"mac":"00800000a0001285","time":"2018-12-14T16:12:16Z","rxPacketsReceived":0,"rxPacketsReceivedOK":0,"txPacketsReceived":0,"txPacketsEmitted":0,"customData":{"ip":"138.22.165.40"}}
       gateway/00800000a0001285/stats {"mac":"00800000a0001285","time":"2018-12-14T16:12:46Z","rxPacketsReceived":0,"rxPacketsReceivedOK":0,"txPacketsReceived":0,"txPacketsEmitted":0,"customData":{"ip":"138.22.165.40"}}
       gateway/00800000a0001285/stats {"mac":"00800000a0001285","time":"2018-12-14T16:13:16Z","rxPacketsReceived":1,"rxPacketsReceivedOK":1,"txPacketsReceived":0,"txPacketsEmitted":0,"customData":{"ip":"138.22.165.40"}}
       gateway/00800000a0001285/stats {"mac":"00800000a0001285","time":"2018-12-14T16:13:46Z","rxPacketsReceived":2,"rxPacketsReceivedOK":2,"txPacketsReceived":0,"txPacketsEmitted":0,"customData":{"ip":"138.22.165.40"}}
       gateway/00800000a0001285/stats {"mac":"00800000a0001285","time":"2018-12-14T16:14:16Z","rxPacketsReceived":0,"rxPacketsReceivedOK":0,"txPacketsReceived":0,"txPacketsEmitted":0,"customData":{"ip":"138.22.165.40"}}
       gateway/00800000a0001285/stats {"mac":"00800000a0001285","time":"2018-12-14T16:14:46Z","rxPacketsReceived":1,"rxPacketsReceivedOK":0,"txPacketsReceived":0,"txPacketsEmitted":0,"customData":{"ip":"138.22.165.40"}}
       gateway/00800000a0001285/stats {"mac":"00800000a0001285","time":"2018-12-14T16:15:16Z","rxPacketsReceived":0,"rxPacketsReceivedOK":0,"txPacketsReceived":0,"txPacketsEmitted":0,"customData":{"ip":"138.22.165.40"}}
       gateway/00800000a0001285/stats {"mac":"00800000a0001285","time":"2018-12-14T16:15:46Z","rxPacketsReceived":0,"rxPacketsReceivedOK":0,"txPacketsReceived":0,"txPacketsEmitted":0,"customData":{"ip":"138.22.165.40"}}
       gateway/00800000a0001285/stats {"mac":"00800000a0001285","time":"2018-12-14T16:16:16Z","rxPacketsReceived":0,"rxPacketsReceivedOK":0,"txPacketsReceived":0,"txPacketsEmitted":0,"customData":{"ip":"138.22.165.40"}}
       gateway/00800000a0001285/stats {"mac":"00800000a0001285","time":"2018-12-14T16:16:46Z","rxPacketsReceived":0,"rxPacketsReceivedOK":0,"txPacketsReceived":0,"txPacketsEmitted":0,"customData":{"ip":"138.22.165.40"}}
       gateway/00800000a0001285/stats {"mac":"00800000a0001285","time":"2018-12-14T16:17:16Z","rxPacketsReceived":1,"rxPacketsReceivedOK":1,"txPacketsReceived":0,"txPacketsEmitted":0,"customData":{"ip":"138.22.165.40"}jj}
       gateway/00800000a0001285/stats {"mac":"00800000a0001285","time":"2018-12-14T16:17:46Z","rxPacketsReceived":0,"rxPacketsReceivedOK":0,"txPacketsReceived":0,"txPacketsEmitted":0,"customData":{"ip":"138.22.165.40"}}

    """
    
    def __init__(self):
        """
        """
        print ("  -> Initializing loraWAN server routines status 'stats' ...")
        self.topicidentifier = {'startswith':'gateway','endswith':'stats'}
        self.stats_datakeytranslator = {
                'rxPacketsReceived':['rxPR1','int'], 
                'rxPacketsReceivedOK':['rxPRO','int'], 
                'txPacketsReceived':['txPR','int'], 
                'txPacketsEmitted':['txPE','int'],
                'customData':[{'ip':'ip'}]
                }
        self.identifier = {}
        self.headdict = {}
        self.headstream = {}
    
    def GetPayload(self, payload, topic):
        # NO: only with paho: loradict = json.loads(payload)
        # JF alread dictionary if is json formated: type(payload) => dict
        # JF only at comandline with python *.py: loradict = payload
        loradict = json.loads(payload)
        newpayload, sensorid, headline, header =  self.loradict2datastruct(loradict)
        return newpayload, sensorid, headline, header, self.identifier
    
    def loradict2datastruct(self, loradict):
        # JF NO string: stats_datakeytranslator = { 'rxPacketsReceived':['rxPR1','int'], 'rxPacketsReceivedOK':['rxPRO','int'], 'txPacketsReceived':['txPR','int'], 'txPacketsEmitted':['txPE','int'], 'customData':['ip','ipv4']}
            stats_datakeytranslator = { 'rxPacketsReceived':['rxPR1','int'], 'rxPacketsReceivedOK':['rxPRO','int'], 'txPacketsReceived':['txPR','int'], 'txPacketsEmitted':['txPE','int']}
            # customdatadict = loradict.get('customData')[0]
            # JF NO is no object => removed: [0]
            customdatadict = loradict.get('customData')
            mac = str(loradict.get('mac'))
            header = {}
            header['mac'] = loradict.get('mac')
            header['ip']  = customdatadict.get('ip')
            # sensorid = header['SensorName'][:5].replace('-','') + '_' + header['SensorSerialNum'] + '_0001'
            # header['SensorID'] = sensorid
            sensorid = "Gateway_" + mac + "_" + self.topicidentifier['endswith'] + '_1000'
            header['SensorID'] = sensorid
            rxPR   = loradict.get('rxPacketsReceived')
            rxPROK = loradict.get('rxPacketsReceivedOK')
            txPR   = loradict.get('txPacketsReceived')
            txPE   = loradict.get('txPacketsEmitted')
            ip = '.'.join([i.zfill(3) for i in customdatadict.get('ip').split('.')])
            dataline      = {"rxPacketsReceived":rxPR,"rxPacketsReceivedOK":rxPROK,"txPacketsReceived":txPR,"txPacketsEmitted":txPE}
            """
            """
            # JF NO string: datadict = {"rxPacketsReceived":rxPR, "rxPacketsReceivedOK":rxPROK, "txPacketsReceived":txPR, "txPacketsEmitted":txPE, customData':["ip",ip]}
            datadict = {"rxPacketsReceived":rxPR, "rxPacketsReceivedOK":rxPROK, "txPacketsReceived":txPR, "txPacketsEmitted":txPE]}
            keylist, elemlist, unitlist, multilist = [],[],[],[]
            if not loradict.get('time','') == '':
                """ 2018-12-14T16:10:16Z """
                time = datetime.strptime(loradict.get('time'),"%Y-%m-%dT%H:%M:%SZ")
            elif not loradict.get('version','') == '':
                time = datetime.strptime(loradict.get('DatumTime'),"%Y-%m-%dT%H:%M:%S.%fZ")
            else:
                time = datetime.utcnow()
            
            datalst = datetime2array(time)
            packstr = '6hL'
            for elem in datadict:
                if elem in stats_datakeytranslator:
                    key = stats_datakeytranslator[elem][0]
                    unit = stats_datakeytranslator[elem][1]
                    keylist.append(key)
                    elemlist.append(elem)
                    unitlist.append(unit)
                    multilist.append(1000)
                    packstr += "l"
                    if type(datadict[elem]) == int:
                        datalst.append(int(datadict[elem]*1000))   
                    else:
                        datalst.append(str(datadict[elem]))   
                # print (elem, datadict[elem])
            
            datalst = [str(elem) for elem in datalst]
            dataline =','.join(datalst)
            self.identifier[sensorid+':packingcode'] = packstr
            self.identifier[sensorid+':keylist'] = keylist
            self.identifier[sensorid+':elemlist'] = elemlist
            self.identifier[sensorid+':unitlist'] = unitlist
            self.identifier[sensorid+':multilist'] = multilist
            
            def identifier2line(dic, sensorid):
                p1 = dic.get(sensorid+':packingcode')
                p2 = dic.get(sensorid+':keylist')
                p3 = dic.get(sensorid+':elemlist')
                p4 = dic.get(sensorid+':unitlist')
                p5 = dic.get(sensorid+':multilist')
                p5 = [str(elem) for elem in p5]
                size = struct.calcsize(p1)
                line = "# MagPyBin {} [{}] [{}] [{}] [{}] {} {}".format(sensorid,','.join(p2),','.join(p3),','.join(p4),','.join(p5),p1,size)
                return line
            
            headline = identifier2line(self.identifier, sensorid)
            print ('dataline', dataline)
            print ('sensorid', sensorid)
            print ('headline', headline)
            print ('header', header)
            print ("success")
            
            return dataline, sensorid, headline, header
