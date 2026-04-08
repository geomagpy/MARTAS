# ###################################################################
# Import packages
# ###################################################################

import socket  # for hostname identification
import string  # for ascii selection
import struct  # for binary representation
import subprocess
import time
from datetime import datetime, timezone

from twisted.python import log

from martas.core import methods as mm

try:
    import adafruit_bn08x
    import board
    from adafruit_bno08x import (
        BNO_REPORT_ACCELEROMETER,
        BNO_REPORT_GYROSCOPE,
        BNO_REPORT_MAGNETOMETER,
    )
    from adafruit_bno08x.i2c import BNO08X_I2C
except:
    log.msg(
        "   bno085 i2c requires the following packages: board, and adafruit-circuitpython-bno08x"
    )

    ## I2C BNO08x protocol
## -----------------------


class BNO085I2CProtocol(object):
    """
    Protocol to read BNO08x data attached to I2C pins of i.e. an raspberry
    This protocol makes use of the Adafruit library.
    pip3 install adafruit-circuitpython-bno08x

    """

    def __init__(self, client, sensordict, confdict):
        self.client = client
        self.sensordict = sensordict
        self.confdict = confdict
        self.count = 0  ## counter for sending header information
        self.sensor = sensordict.get("sensorid")
        self.hostname = socket.gethostname()
        self.printable = set(string.printable)
        self.datalst = []
        self.datacnt = 0
        self.metacnt = 10
        self.counter = {}
        self.initi2c = True

        # extract data from configuration dictionary
        debugtest = confdict.get("debug")

        # QOS
        self.qos = int(confdict.get("mqttqos", 0))
        if not self.qos in [0, 1, 2]:
            self.qos = 0
        log.msg("  -> setting QOS:", self.qos)

        # switch on debug mode
        self.debug = False
        if debugtest in ["true", "True", "TRUE"]:
            log.msg(
                "DEBUG - {}: Debug mode activated.".format(
                    self.sensordict.get("protocol")
                )
            )
            self.debug = True  # prints many test messages
        else:
            log.msg("  -> Debug mode = {}".format(debugtest))

        # connect to i2c
        self.conn = self.init_sensor()

    def datetime2array(self, t):
        return [t.year, t.month, t.day, t.hour, t.minute, t.second, t.microsecond]

    def init_sensor(self):
        # log.msg("connecting to I2C ...")
        REPORT_INTERVAL = 100000  # 100 Hz
        i2c = board.I2C()  # uses board.SCL and board.SDA
        sensor = BNO08X_I2C(i2c)
        sensor.enable_feature(BNO_REPORT_ACCELEROMETER, REPORT_INTERVAL)
        sensor.enable_feature(BNO_REPORT_GYROSCOPE, REPORT_INTERVAL)
        sensor.enable_feature(BNO_REPORT_MAGNETOMETER, REPORT_INTERVAL)
        sensor.soft_reset()
        sensor.begin_calibration()
        return sensor

    def processBNO085Data(self, sensorid, meta, data):
        """"""
        currenttime = datetime.now(timezone.utc).replace(tzinfo=None)
        outdate = datetime.strftime(currenttime, "%Y-%m-%d")
        filename = outdate

        datearray = self.datetime2array(currenttime)

        packcode = "6hL"

        values = []
        multiplier = []
        for dat in data:
            try:
                values.append(float(dat))
                datearray.append(int(float(dat) * 10000))
                packcode = packcode + "q"
                multiplier.append(10000)
            except:
                log.msg(
                    "{} protocol: Error while appending data to file (non-float?): {}".format(
                        self.sensordict.get("protocol"), dat
                    )
                )

        try:
            data_bin = struct.pack("<" + packcode, *datearray)  # little endian
        except:
            log.msg(
                "{} protocol: Error while packing binary data".format(
                    self.sensordict.get("protocol")
                )
            )
            pass

        key = "[" + str(meta.get("SensorKeys")).replace("'", "").strip() + "]"
        ele = "[" + str(meta.get("SensorElements")).replace("'", "").strip() + "]"
        unit = "[" + str(meta.get("SensorUnits")).replace("'", "").strip() + "]"
        multplier = str(multiplier).replace(" ", "")
        # Correct some common old problem
        unit = unit.replace("deg C", "degC")

        header = "# MagPyBin %s %s %s %s %s %s %d" % (
            sensorid,
            key,
            ele,
            unit,
            multplier,
            packcode,
            struct.calcsize(packcode),
        )

        if not self.confdict.get("bufferdirectory", "") == "":
            mm.data_to_file(
                self.confdict.get("bufferdirectory"),
                sensorid,
                filename,
                data_bin,
                header,
            )

        return ",".join(list(map(str, datearray))), header

    def get_bno08x_data(self, sensor, debug=False):
        mag_x, mag_y, mag_z = sensor.magnetic
        accel_x, accel_y, accel_z = sensor.acceleration
        gyro_x, gyro_y, gyro_z = sensor.gyro
        if debug:
            print(f"X:{mag_x:10.3f}, Y:{mag_y:10.3f}, Z:{mag_z:10.3f} uT")
            print(f"X:{accel_x:10.3f}, Y:{accel_y:10.3f}, Z:{accel_z:10.3f} m/s^2")
            print(f"X:{gyro_x:10.3f}, Y:{gyro_y:10.3f}, Z:{gyro_z:10.3f} rad/s")
        data = [
            float(mag_x) * 1000.0,
            float(mag_y) * 1000.0,
            float(mag_z) * 1000.0,
            float(accel_x),
            float(accel_y),
            float(accel_z),
            float(gyro_x),
            float(gyro_y),
            float(gyro_z),
        ]
        return data

    def calibrate_bno08x_data(self, data, offsets=None, scales=None, debug=False):
        if not offsets:
            offsets = [0, 0, 0, 0, 0, 0, 0, 0, 0]
        if not scales:
            scales = [1, 1, 1, 1, 1, 1, 1, 1, 1]
        for i, el in enumerate(data):
            data[i] = el + offsets[i]
            data[i] = data[i] * scales[i]
        return data

    def define_bno08x_meta(self):
        meta = {}
        meta["SensorKeys"] = (
            "mag_x,mag_y,mag_z,accel_x,accel_y,accel_z,gyro_x,gyro_y,gyro_z"
        )
        meta["SensorElements"] = (
            "mag_X,mag_Y,mag_Z,accel_X,accel_Y,accel_Z,gyro_X,gyro_Y,gyro_Z"
        )
        meta["SensorUnits"] = "nT,nT,nT,m/s^2,m/s^2,m/s^2,rad/s,rad/s,rad/s,"
        return meta

    def sendRequest(self):

        if not self.conn:
            self.conn = self.init_sensor()
            # or put everything in a try except and reconnect on except
        # connect to i2c
        data = self.get_bno08x_data(self.conn, debug=self.debug)
        data = self.calibrate_bno08x_data(data, offsets=[0, 0, 0, 0, 0, 0, 0, 0, 0])
        meta = self.define_bno08x_meta()
        self.publish_data(data, meta)

    def publish_data(self, data, meta):

        if len(data) > 0:
            topic = self.confdict.get("station") + "/" + self.sensor
            pdata, head = self.processBNO085Data(self.sensor, meta, data)

            senddata = False
            try:
                coll = int(self.sensordict.get("stack"))
            except:
                coll = 0

            if coll > 1:
                self.metacnt = 1  # send meta data with every block
                if self.datacnt < coll:
                    self.datalst.append(pdata)
                    self.datacnt += 1
                else:
                    senddata = True
                    pdata = ";".join(self.datalst)
                    self.datalst = []
                    self.datacnt = 0
            else:
                senddata = True

            if senddata:
                self.client.publish(topic + "/data", pdata, qos=self.qos)
                # If multiple sensors are connected, self.count needs to be a dict (with topic)
                # Initialize counter for each topic
                if self.counter.get(self.sensor, "") == "":
                    self.counter[self.sensor] = 0
                cnt = self.counter.get(self.sensor)

                if cnt == 0:
                    ## 'Add' is a string containing dict info like:
                    ## SensorID:ENV05_2_0001,StationID:wic, PierID:xxx,SensorGroup:environment,...
                    add = "SensorID:{},StationID:{},DataPier:{},SensorModule:{},SensorGroup:{},SensorDescription:{},DataTimeProtocol:{}".format(
                        self.sensordict.get("sensorid", ""),
                        self.confdict.get("station", ""),
                        self.sensordict.get("pierid", ""),
                        self.sensordict.get("protocol", ""),
                        self.sensordict.get("sensorgroup", ""),
                        self.sensordict.get("sensordesc", ""),
                        self.sensordict.get("ptime", ""),
                    )
                    self.client.publish(topic + "/dict", add, qos=self.qos)
                    self.client.publish(topic + "/meta", head, qos=self.qos)

                cnt += 1
                # self.count += 1
                if cnt >= self.metacnt:
                    cnt = 0

                # update counter in dict
                self.counter[self.sensor] = cnt
