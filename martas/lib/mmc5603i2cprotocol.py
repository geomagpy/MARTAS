
# ###################################################################
# Import packages
# ###################################################################

import time
import struct # for binary representation
import socket # for hostname identification
import string # for ascii selection
from datetime import datetime, timezone
from twisted.python import log
from martas.core import methods as mm
import subprocess


try:
    import board
    import adafruit_mmc56x3
except:
    log.msg("   mmc5603 i2c requires the following packages: board, adafruit-blinka and adafruit-circuitpython-mmc56x3")

    ## I2C MMC5603 protocol
## -----------------------

class MMC5603I2CProtocol(object):
    """
    Protocol to read MMC5603 data attached to I2C pins of i.e. an raspberry
    This protocol makes use of the Adafruit library.
    pip3 install adafruit-circuitpython-mmc56x3

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


        # switch on debug mode
        self.debug = False
        if debugtest in ['true','True','TRUE']:
            log.msg('DEBUG - {}: Debug mode activated.'.format(self.sensordict.get('protocol')))
            self.debug = True    # prints many test messages
        else:
            log.msg('  -> Debug mode = {}'.format(debugtest))

        # connect to i2c
        conn = self.open_connection()


    def datetime2array(self,t):
        return [t.year,t.month,t.day,t.hour,t.minute,t.second,t.microsecond]

    def open_connection(self):
        #log.msg("connecting to I2C ...")
        i2c = board.I2C()  # uses board.SCL and board.SDA
        # i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
        sensor = adafruit_mmc56x3.MMC5603(i2c)
        sensor.data_rate = 10  # in Hz, from 1-255 or 1000
        sensor.continuous_mode = True
        while True:
            data = self.get_mmc5603_data(sensor)
            # request meta
            meta = self.define_mmc5603_meta()
            self.publish_data(data,meta)

    def restart(self):
        try:
            subprocess.check_call(['/etc/init.d/martas', 'restart'])
        except subprocess.CalledProcessError:
            log.msg('SerialCall: check_call did not work')
            pass # handle errors in the called executable
        except:
            log.msg('SerialCall: check call problem')
            pass # executable not found
        log.msg('SerialCall: Restarted martas process')


    def processMMC5603Data(self, sensorid, meta, data):
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

    def get_mmc5603_data(self,sensor):
        mag_x, mag_y, mag_z = sensor.magnetic
        print(f"X:{mag_x:10.2f}, Y:{mag_y:10.2f}, Z:{mag_z:10.2f} uT")

        data = [mag_x, mag_y, mag_z]
        return data

    def define_mmc5603_meta(self):
        meta = {}
        meta['SensorKeys'] = 'x,y,z'
        meta['SensorElements'] = 'X,Y,Z'
        meta['SensorUnits'] = 'uT,uT,uT'
        return meta

    def publish_data(self, data, meta):

        if len(data) > 0:
            topic = self.confdict.get('station') + '/' + self.sensor
            pdata, head = self.processMMC5603Data(self.sensor, meta, data)

            senddata = False
            try:
                coll = int(self.sensordict.get('stack'))
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
