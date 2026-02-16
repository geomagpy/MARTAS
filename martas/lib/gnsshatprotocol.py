
# ###################################################################
# Import packages
# ###################################################################

import time
# ###################################################################
# Import packages
# ###################################################################

import serial
import time
import sys
import operator
from functools import reduce
from datetime import datetime, timezone

import struct # for binary representation
import socket # for hostname identification
import string # for ascii selection
from twisted.python import log
from martas.core import methods as mm
import subprocess

## GNSSHAT protocol
## -----------------------

class GNSSHATProtocol(object):
    """
    Protocol to read Waveshare GNSS HAT data attached to a raspberry.
    https://www.waveshare.com/wiki/GSM/GPRS/GNSS_HAT
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

        self.commands = ["AT+CGNSPWR=1", "AT+CGNSSEQ=\"RMC\"", "AT+CGNSINF", "AT+CGNSURC=2", "AT+CGNSTST=1"]
        self.eol = "\r\n"

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


    def datetime2array(self,t):
        return [t.year,t.month,t.day,t.hour,t.minute,t.second,t.microsecond]

    def serwrite(ser, command, eol="\r\n"):
        fc = command + eol
        ffc = fc.encode()
        if sys.version.startswith('3'):
            ser.write(ffc)
        else:
            ser.write(fc)

    def open_connection(self):
        log.msg("connecting to serial port")
        ser = serial.Serial(self.port, baudrate=int(self.baudrate), parity=self.parity, bytesize=int(self.bytesize), stopbits=int(self.stopbits), timeout=self.timeout)
        time.sleep(2)
        self.serwrite(ser, self.commands[0])
        ser.flushInput()
        self.data = b""
        self.num = 0

        self.ser = ser
        return ser


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


    def processGNSSData(self, sensorid, res):
        """
        res =
        {'time': '134353.000', 'lat': 48.08448035, 'lon': 10.848522516666666, 'date': '150226', 'status': 'A',
        'speed': '1.29', 'course': '110.32', 'declination': '', 'dec_orient': '', 'integrity': 'A*72',
        'datetime': '2026-02-15T13:43:54.000000', 'quality': '1', 'N': '5', 'horizontal_prescision': '1.23',
        'altitude': '583.395', 'altitude_unit': 'M', 'geoidal_separation': '47.864',
        'geoidal_separation_unit': 'M', 'age_dgps': '', 'dgps_reference': '*4A'}
        """
        currenttime = datetime.now(timezone.utc).replace(tzinfo=None)
        gnsstime = res.get("datetime", currenttime)
        outdate = datetime.strftime(gnsstime,"%Y-%m-%d")
        filename = outdate

        datearray = self.datetime2array(gnsstime)
        fullkeylist = ['lat', 'lon']  # 1000000000
        numkeylist = ['altitude', 'speed', 'course', 'horizontal_prescision', 'geoidal_separation'] # 1000
        intkeylist = ['quality', 'N'] # 1
        strkeylist = ['dgps_reference', 'status', 'integrity']
        keys = '[x,y,z,f,var1,dx,dz,var2,var3,str1,str2,str3]'

        packcode = '6hL'

        values = []
        multiplier = []

        keys = []
        unit = []
        data_bin = None

        for key in fullkeylist:
            dat = res.get(key, 0.000)
            try:
                values.append(float(dat))
                datearray.append(int(float(dat)*1000000000))
                packcode = packcode + 'l'
                multiplier.append(1000000000)
                unit.append("deg")
            except:
                log.msg('{} protocol: Error while appending data to file (non-float?): {}'.format(self.sensordict.get('protocol'),dat) )
        for key in numkeylist:
            dat = res.get(key, 0.000)
            try:
                values.append(float(dat))
                datearray.append(int(float(dat)*1000))
                packcode = packcode + 'l'
                multiplier.append(1000)
                if key == "altitude":
                    unit.append(res.get('altitude_unit','').lower())
                elif key == "geoidal_separation":
                    unit.append(res.get('geoidal_separation_unit', '').lower())
                else:
                    unit.append("-")
            except:
                log.msg('{} protocol: Error while appending data to file (non-float?): {}'.format(self.sensordict.get('protocol'),dat) )
        for key in intkeylist:
            dat = res.get(key, 0)
            try:
                values.append(int(dat))
                datearray.append(int(dat))
                packcode = packcode + 'l'
                multiplier.append(1)
                unit.append("")
            except:
                log.msg('{} protocol: Error while appending data to file (non-float?): {}'.format(self.sensordict.get('protocol'),dat) )
        for key in strkeylist:
            dat = res.get(key, "")
            try:
                values.append(int(dat))
                datearray.append(int(dat))
                packcode = packcode + 's'
                multiplier.append(0)
                unit.append("-")
            except:
                log.msg('{} protocol: Error while appending data to file (non-float?): {}'.format(self.sensordict.get('protocol'),dat) )

        try:
            data_bin = struct.pack('<'+packcode,*datearray) #little endian
        except:
            log.msg('{} protocol: Error while packing binary data'.format(self.sensordict.get('protocol')))
            pass

        ele = str(fullkeylist+numkeylist+strkeylist+strkeylist).replace(" ","")
        unit = str(unit).replace(" ","")
        multplier = str(multiplier).replace(" ","")
        # Correct some common old problem
        unit = unit.replace('deg C', 'degC')

        header = "# MagPyBin %s %s %s %s %s %s %d" % (sensorid, keys, ele, unit, multplier, packcode, struct.calcsize(packcode))

        if not self.confdict.get('bufferdirectory','') == '':
            mm.data_to_file(self.confdict.get('bufferdirectory'), sensorid, filename, data_bin, header)

        return ','.join(list(map(str,datearray))), header

    def get_nmea(self, datastr, debug=False):
        """
        Extract dictionaries from RMC and GGA Strings
        RMC:
        GGA:
        When returning: GGA inputs will overwrite similar key from RMC
        """
        lines = datastr.split()
        rd, gd = {}, {}
        for line in lines:
            if line.startswith('$GNGGA'):
                if debug:
                    print("GGA:", line)
                gd = self.analyse_gga(line)
            if line.startswith('$GNRMC'):
                if debug:
                    print("RMC:", line)
                rd = self.analyse_rmc(line)
        return {**rd, **gd}

    def checksum_nmea(self, line):
        """
        Checking NMEA strings by checksum
        """
        tline = line.strip("$\n")
        nmea, cont_checksum = tline.split("*", 1)
        calc_checksum = reduce(operator.xor, (ord(s) for s in nmea), 0)
        if int(cont_checksum, base=16) == calc_checksum:
            return True
        else:
            print("NMEA: calculated and contained checksums differ")
            return False

    def convert_ddmm(self, ddmm, orientation="", debug=False):
        """
        latitude/loingitude format: (D)DDMM.MMMMM
        orientation = N/S or E/W
        """
        sign = 1

        if not ddmm in ['']:
            DD = int(float(ddmm) / 100)
            MM = float(ddmm) - DD * 100
            if debug:
                print(DD)
                print(MM)
            if orientation in ["S", "W"]:
                sign = -1
            decimals = sign * (DD + MM / 60.)
        else:
            decimals = 999.99

        return decimals

    def analyse_gga(self, ggaline):
        ggasplit = ggaline.split(',')
        gd = {}
        if len(ggasplit) >= 15 and self.checksum_nmea(ggaline):
            gd['time'] = ggasplit[1]
            gd['lat'] = self.convert_ddmm(ggasplit[2], ggasplit[3])
            gd['lon'] = self.convert_ddmm(ggasplit[4], ggasplit[5])
            gd['quality'] = ggasplit[6]
            gd['N'] = ggasplit[7]
            gd['horizontal_prescision'] = ggasplit[8]
            gd['altitude'] = ggasplit[9]
            gd['altitude_unit'] = ggasplit[10]
            gd['geoidal_separation'] = ggasplit[11]
            gd['geoidal_separation_unit'] = ggasplit[12]
            gd['age_dgps'] = ggasplit[13]
            gd['dgps_reference'] = ggasplit[14]
            # gd['checksum'] = ggasplit[15]
        return gd

    def analyse_rmc(self, rmcline):
        rmcsplit = rmcline.split(',')
        rd = {}
        if len(rmcsplit) >= 13 and self.checksum_nmea(rmcline):
            rd['time'] = rmcsplit[1]
            rd['lat'] = self.convert_ddmm(rmcsplit[3], rmcsplit[4])
            rd['lon'] = self.convert_ddmm(rmcsplit[5], rmcsplit[6])
            rd['date'] = rmcsplit[9]
            rd['status'] = rmcsplit[2]
            rd['speed'] = rmcsplit[7]
            rd['course'] = rmcsplit[8]
            rd['declination'] = rmcsplit[10]
            rd['dec_orient'] = rmcsplit[11]
            rd['integrity'] = rmcsplit[12]
            datetime_str = "{} {}".format(rmcsplit[9], rmcsplit[1])
            datetime_obj = datetime.strptime(datetime_str, '%d%m%y %H%M%S.%f')
            rd['datetime'] = datetime.strftime(datetime_obj, '%Y-%m-%dT%H:%M:%S.%f')
        return rd


    def sendRequest(self):

        # connect to serial
        ser = self.ser
        if not ser or not ser.isOpen():
            ser = self.open_connection()

        while ser.inWaiting() > 0:
            self.data += ser.read(ser.inWaiting())
        #print ("data", data.decode())
        if not self.data == b"":
            result = self.data.decode()
            res = self.get_nmea(result)
            print ("Obtained:", res)
            time.sleep(0.5)
            print ("Sending next command:", self.num+1)
            self.serwrite(ser,self.commands[self.num+1])
            self.num = self.num+1
            if self.num == 4:
                num = 0
                time.sleep(0.5)
                print ("Sending final command 4")
                self.serwrite(ser,self.commands[4])
            self.data = b""
            #publish it
            #self.publish_data(res)

    def publish_data(self, res):

        if res and len(res) > 0:
            topic = self.confdict.get('station') + '/' + self.sensor
            pdata, head = self.processGNSSData(self.sensor, res)

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
                    add = "SensorID:{},StationID:{},DataPier:{},SensorModule:{},SensorGroup:{},SensorDescription:{},DataTimeProtocol:{}".format( self.sensordict.get('sensorid',''),self.confdict.get('station',''),self.sensordict.get('pierid',''),self.sensordict.get('protocol',''),self.sensordict.get('sensorgroup',''),self.sensordict.get('sensordesc',''),self.sensordict.get('ptime','') )
                    self.client.publish(topic+"/dict", add, qos=self.qos)
                    self.client.publish(topic+"/meta", head, qos=self.qos)

                cnt += 1
                #self.count += 1
                if cnt >= self.metacnt:
                    cnt = 0

                # update counter in dict
                self.counter[self.sensor] = cnt
