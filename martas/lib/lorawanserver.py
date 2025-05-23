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
class lorawanserver(object):
    """
    application/3/node/0018b2200000034a/rx {"applicationID":"3","applicationName":"Temperature-and-Humidity","deviceName":"TITEC-Multisensor","devEUI":"0018b2200000034a","rxInfo":[{"gatewayID":"00800000a0001285","name":"MTCDT_AEPGW2","rssi":-49,"loRaSNR":7.2,"location":{"latitude":48.248422399999995,"longitude":16.3520512,"altitude":0}}],"txInfo":{"frequency":868500000,"dr":5},"adr":true,"fCnt":457,"fPort":1,"data":"QgASEzQVIg/HVA=="}

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
        print ("  -> Initializing loraWAN server routines ...")
        #self.payload = payload
        #self.topic = topic
        self.topicidentifier = {'startswith':'application','endswith':'rx'}
        self.datakeytranslator = {'tl':['t1','degC'], 'rf':['var1','per'], 'corr':['var5','none']}
        self.identifier = {}
        self.headdict = {}
        self.headstream = {}

    def GetPayload(self, payload, topic):
        loradict = json.loads(payload)
        # convert loradict to headdict (header) and data_bin
        newpayload, sensorid, headline, header =  self.loradict2datastruct(loradict)
        return newpayload, sensorid, headline, header, self.identifier

    def b2v7(self,b1,b2,div):
                val = ((b2 << 8) + b1)/ float(div)
                return val

    def b2v(self,b1,b2,b3,off):
                v = ((b1 << 8) + b2 << 8) + b3
                val = (v/100000. *6.25) - off
                return val

    def loradict2datastruct(self, loradict):
            datakeytranslator = {'tl':['t1','degC'], 'rf':['var1','per'], 'corr':['var5','none'], 'bat':['var4','per']}
            rxdict = loradict.get('rxInfo')[0]
            locdict = rxdict.get('location')
            header = {}

            header['SensorName'] = loradict.get('deviceName','LORA')
            header['SensorDescription'] = loradict.get('applicationName','not specified')
            header['SensorSerialNum'] = loradict.get('devEUI','')
            header['SensorGroup'] = loradict.get('deviceName','LORA')
            sensorid = header['SensorName'][:5].replace('-','') + '_' + header['SensorSerialNum'] + '_0001'
            header['SensorID'] = sensorid
            header['StationID'] = rxdict.get('gatewayID','undefined')
            header['StationName'] = rxdict.get('name','undefined')

            header['StationLongitude'] = locdict.get('longitude','')
            header['StationLatitude'] = locdict.get('latitude','')
            if not locdict.get('longitude','') == '':
                header['StationLocationReference'] = 'WGS84, EPSG: 4326'
            if locdict.get('altitude','') in ['',0,'0']:
                alt = ''
            else:
                alt = locdict.get('altitude')
            header['StationElevation'] = alt
            if not alt == '':
                header['StationElevationRef'] = 'm NN'

            datacode = loradict.get('data')
            # convert to something like datadict = {"tl":21.75,"rf":36.9}
            barray = bytearray(base64.b64decode(datacode))

            print ("Device:", loradict.get('deviceName'))
            print ("Length Bytearray:", len(barray))

            if len(barray) == 10:
                temp = self.b2v(barray[3],barray[4],barray[5],55)
                rf = self.b2v(barray[7],barray[8],barray[9],25)
                datadict = {"tl":temp, "rf":rf}
            elif len(barray) == 7:
                print ("Found Bytearray 7 with code", datacode)
                temp = self.b2v7(barray[1],barray[2],100)
                rf = self.b2v7(barray[3],barray[4],100)
                bat = self.b2v7(barray[5],barray[6],1)
                datadict = {"tl":temp, "rf":rf, "bat":bat}
            else:
                print ("Found Bytearray of length {} with code", len(barray), datacode)
                print ("Payload looks like", loradict)
                temp = 999.0
                rf = -10.0
                datadict = {"tl":temp, "rf":rf}

            keylist, elemlist, unitlist, multilist = [],[],[],[]
            if not loradict.get('DateTime','') == '':
                time = datetime.strptime(loradict.get('DateTime'),"%Y-%m-%dT%H:%M:%S.%fZ")
            elif not loradict.get('DatumSec','') == '':
                time = datetime.strptime(loradict.get('DatumSec'),"%Y-%m-%dT%H:%M:%S.%fZ")
            else:
                time = datetime.now(timezone.utc).replace(tzinfo=None)
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
            print ("success")
            return dataline, sensorid, headline, header


