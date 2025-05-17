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
    ZAMG/adeunis {"DateTime":"2018-11-28T16:17:47.517412Z","Modell":"Adeunis RF","Name":"Adeunis7 - Museumsstr","issue":{"appeui":"00-18-b2-43-45-4e-53-33","deveui":"00-18-b2-20-00-00-02-6b","code":66,"status_nr":224,"channelA mA":11.09218,"channelB mA":11.09218,"status":0},"data":{"corr":0,"tl":14.326125000000005,"rf":41.194874999999996,"msg_payload":[66,224,18,16,236,226,34,16,41,46]}}

    ZAMG/bees {"DatumSec":"2018-11-28T17:02:59.352375Z","Name":"Unknown bees","issue":{"appeui":"48-83-c7-df-30-0d-00-00","deveui":"48-83-c7-df-30-0d-12-74","breite":48.2483,"laenge":16.357428,"hoehe":198,"st":0},"data":{"tl":21.75,"rf":36.9,"saved_payload":[1,127,8,106,14,92,0]}}

    ZAMG/ikt/isd/test/jf/adeunis07_beelike {"DateTime":"2018-11-28T16:17:47.517412Z","deveui":"00-18-b2-20-00-00-02-6b","breite":48.2483,"laenge":16.357428,"hoehe":148,"status":0,"tl":14.326125000000005,"rf":41.194874999999996}



    content suggestion: appeui, deveui, sensorname, locationname, sensormodell, -> rest beelike

    topic suggestions:
    headline/station/sensor

    ideally, headline is a unique formatidentifier
    e.g.
    loraz/schwarzenbergplatz/adeunis  od 
    warum: so kann man relativ systematisch stationen abfragen
    mobile sensoren ohne festen standort:
    loraz/mobile/adeunis


    """

    def __init__(self):
        """
        """
        print ("  -> Initializing lora zamg routines ...")
        #self.payload = payload
        #self.topic = topic
        self.topicidentifier = {'startswith':'ZAMG','endswith':'s'}
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
                if loradict.get('Name','').find('bee') > 0:
                    header['StationID'] = 'ZAMG bees'
                    header['StationName'] = 'ZAMG bees'
                header['StationID'] = loradict.get('Name').strip().split(' - ')[1]
                header['StationName'] = loradict.get('Name').strip().split(' - ')[1]
            except:
                header['StationID'] = "Not defined"
            #header['SensorName'] = loradict.get('Name').split(' - ').strip()[0]
            header['SensorSerialNum'] = issuedict.get('deveui','').replace('-','')
            header['SensorDataLoggerSerNum'] = issuedict.get('appeui','').replace('-','')
            header['SensorGroup'] = loradict.get('Modell','')
            sensorid = header['SensorName'].split(' ')[0] + '_' + header['SensorSerialNum'] + '_0001'
            header['SensorID'] = sensorid
            header['StationLongitude'] = issuedict.get('laenge','')
            header['StationLatitude'] = issuedict.get('breite','')
            if not issuedict.get('laenge','') == '':
                header['StationLocationReference'] = 'WGS84, EPSG: 4326'
            header['StationElevation'] = issuedict.get('hoehe','')
            if not issuedict.get('hoehe','') == '':
                header['StationElevationRef'] = issuedict.get('hoehe','')

            # needs to return headstream[sensorid] = header (global)
            # identifier dictionary  (global)
            # sensorid
            # headdict[sensorid] = "MagPy line"  (global)
            # and data payload

            keylist, elemlist, unitlist, multilist = [],[],[],[]
            if not loradict.get('DateTime','') == '':
                time = datetime.strptime(loradict.get('DateTime'),"%Y-%m-%dT%H:%M:%S.%fZ")
            elif not loradict.get('DatumSec','') == '':
                time = datetime.strptime(loradict.get('DatumSec'),"%Y-%m-%dT%H:%M:%S.%fZ")
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


