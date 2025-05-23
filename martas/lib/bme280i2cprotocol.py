from __future__ import print_function
from __future__ import absolute_import

# ###################################################################
# Import packages
# ###################################################################

import time
import struct # for binary representation
import socket # for hostname identification
import string # for ascii selection
from datetime import datetime
from twisted.python import log
from martas.core import methods as mm
import subprocess

try:
    import board
    import busio
    from adafruit_bme280 import basic as adafruit_bme280
except:
    log.msg("   bme280 ic2 requires board, busio and adafruit packages - install first")

## I2C BME280 protocol
## -----------------------

class BME280I2CProtocol(object):
    """
    Protocol to read BME280 data attached to I2C pins of i.e. an raspberry
    This protocol makes use of the Adafruit library.

    special configuration data:
    sea_level_pressure  :  1013.25  # to correctly determine altitude
    """

    def __init__(self, client, sensordict, confdict):
        self.client = client
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
        self.initi2c = True

        # extract data from configuration dictionary
        debugtest = confdict.get('debug')

        # QOS
        self.qos=int(confdict.get('mqttqos',0))
        if not self.qos in [0,1,2]:
            self.qos = 0
        log.msg("  -> setting QOS:", self.qos)

        # Obtain sea level:
        try:
            self.sea_level_p = float(confdict.get('sea_level_pressure',1013.25))
        except:
            self.sea_level_p = 1013.25

        # switch on debug mode
        self.debug = False
        if debugtest in ['true','True','TRUE']:
            log.msg('DEBUG - {}: Debug mode activated.'.format(self.sensordict.get('protocol')))
            self.debug = True    # prints many test messages
        else:
            log.msg('  -> Debug mode = {}'.format(debugtest))


    def datetime2array(self,t):
        return [t.year,t.month,t.day,t.hour,t.minute,t.second,t.microsecond]

    def open_connection(self):
        #log.msg("connecting to I2C ...")
        i2c = busio.I2C(board.SCL, board.SDA)
        bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c,address=0x76)
        bme280.mode = adafruit_bme280.MODE_NORMAL
        time.sleep(1)
        #log.msg("... done")
        return bme280

    def define_sea_level(self,bme280,sea_level_pressure=1013.25):
        bme280.sea_level_pressure = sea_level_pressure
        return bme280

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


    def processBME280Data(self, sensorid, meta, data):
        """Convert raw ADC counts into SI units as per datasheets"""
        currenttime = datetime.now(timezone.utc).replace(tzinfo=None)
        outdate = datetime.strftime(currenttime, "%Y-%m-%d")
        filename = outdate

        datearray = self.datetime2array(currenttime)

        packcode = '6hL'

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

        header = "# MagPyBin %s %s %s %s %s %s %d" % (sensorid, key, ele, unit, multplier, packcode, struct.calcsize(packcode))

        if not self.confdict.get('bufferdirectory','') == '':
            mm.data_to_file(self.confdict.get('bufferdirectory'), sensorid, filename, data_bin, header)

        return ','.join(list(map(str,datearray))), header

    def get_bme280_data(self,bme280):
        temp = bme280.temperature
        hum = bme280.humidity
        relhum = bme280.relative_humidity
        pressure = bme280.pressure
        altitude = bme280.altitude
        data = [temp,hum,relhum,pressure,altitude]
        return data

    def define_bme280_meta(self):
        meta = {}
        meta['SensorKeys'] = 't1,var1,var2,var3,var4'
        meta['SensorElements'] = 'T,Humidity,rh,P,altitude'
        meta['SensorUnits'] = 'degC,percent,percent,hPa,m'
        return meta

    def sendRequest(self):

        # connect to i2c
        conn = self.open_connection()
        # define sea level
        conn = self.define_sea_level(conn,self.sea_level_p)
        # request data
        data = self.get_bme280_data(conn)
        # request meta
        meta = self.define_bme280_meta()
        self.publish_data(data,meta)

    def publish_data(self, data, meta):

        if len(data) > 0:
            topic = self.confdict.get('station') + '/' + self.sensor
            pdata, head = self.processBME280Data(self.sensor, meta, data)

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
                if self.counter.get(self.sensor,'') == '':
                    self.counter[self.sensor] = 0
                cnt = self.counter.get(self.sensor)

                if cnt == 0:
                    ## 'Add' is a string containing dict info like:
                    ## SensorID:ENV05_2_0001,StationID:wic, PierID:xxx,SensorGroup:environment,...
                    add = "SensorID:{},StationID:{},DataPier:{},SensorModule:{},SensorGroup:{},SensorDecription:{},DataTimeProtocol:{}".format( self.sensordict.get('sensorid',''),self.confdict.get('station',''),self.sensordict.get('pierid',''),self.sensordict.get('protocol',''),self.sensordict.get('sensorgroup',''),self.sensordict.get('sensordesc',''),self.sensordict.get('ptime','') )
                    self.client.publish(topic+"/dict", add, qos=self.qos)
                    self.client.publish(topic+"/meta", head, qos=self.qos)

                cnt += 1
                #self.count += 1
                if cnt >= self.metacnt:
                    cnt = 0

                # update counter in dict
                self.counter[self.sensor] = cnt
