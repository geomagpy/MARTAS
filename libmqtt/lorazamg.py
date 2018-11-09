from __future__ import print_function
from __future__ import absolute_import

# ###################################################################
# Import packages
# ###################################################################

from magpy.stream import DataStream, KEYLIST, NUMKEYLIST, subtractStreams
import struct
from datetime import datetime 
import json

def datetime2array(t):
        return [t.year,t.month,t.day,t.hour,t.minute,t.second,t.microsecond]

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
        loradict = json.loads(payload)
        # convert loradict to headdict (header) and data_bin
        newpayload, sensorid, headline, header =  self.loradict2datastruct(loradict)
        return newpayload, sensorid, headline, header, self.identifier

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
            #self.headstream[sensorid] = create_head_dict(self.headdict[sensorid],sensorid)
            #self.headstream[sensorid] = merge_two_dicts(self.headstream[sensorid], header)
            #print ("HEAD1", headdict[sensorid])
            #print ("HEAD2", headstream[sensorid])
            return dataline, sensorid, headline, header


