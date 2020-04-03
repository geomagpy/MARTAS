from __future__ import print_function
from __future__ import absolute_import

# ###################################################################
# Import packages
# ###################################################################

import re     # for interpretation of lines
import struct # for binary representation
import socket # for hostname identification
import string # for ascii selection
from datetime import datetime, timedelta
from twisted.protocols.basic import LineReceiver
from twisted.python import log
from core import acquisitionsupport as acs
import numpy as np

## GEM -GP20S3 protocol
##
class GP20S3Protocol(LineReceiver):
    """
    Protocol to read GP20S3 data
    This protocol defines the individual sensor related read process. 
    It is used to dipatch url links containing specific data.
    Sensor specific coding is contained in method "processData".

    Treatment of GPS and NTP time:
    The protocol determines two times: 1) GPS time provided by the data logger
    2) NTP time of the PC when data is received by serial comm.
    Primary time is selected in sensor.cfg (either NTP or GPS)
    Timediff between GPS and NTP is recorded, and a 1000 line median average is send
    within the DataDictionary (DataNTPTimeDelay).
    Besides, a waring message is generated if NTP and GPS times differ by more than 3 seconds.
    For this comparison (and only here) a typical correction (delay) value is applied to NTP.
    e.g. 6.2 sec for POS1.
    """
    def __init__(self, client, sensordict, confdict):
        """
        'client' could be used to switch between different publishing protocols
                 (e.g. MQTT or WS-MCU gateway factory) to publish events
        'sensordict' contains a dictionary with all sensor relevant data (sensors.cfg)
        'confdict' contains a dictionary with general configuration parameters (martas.cfg)
        """
        self.client = client
        self.sensordict = sensordict    
        self.confdict = confdict
        self.count = 0  ## counter for sending header information
        self.sensor = sensordict.get('sensorid')
        self.hostname = socket.gethostname()
        self.printable = set(string.printable)
        #log.msg("  -> Sensor: {}".format(self.sensor))
        self.datalst = []
        self.datacnt = 0
        self.metacnt = 10
        self.errorcnt = {'time':0}

        self.delaylist = []  # delaylist contains up to 1000 diffs between gps and ntp
                             # the median of this values is used for ntp timedelay
        self.timedelay = 0.0
        self.timethreshold = 3 # secs - waring if timedifference is larger the 3 seconds

        # QOS
        self.qos=int(confdict.get('mqttqos',0))
        if not self.qos in [0,1,2]:
            self.qos = 0
        log.msg("  -> setting QOS:", self.qos)

        # Debug mode
        debugtest = confdict.get('debug')
        #self.debug = False
        #self.debug = True
        if debugtest == 'True':
            log.msg('DEBUG - {}: Debug mode activated.'.format(self.sensordict.get('protocol')))
            self.debug = True    # prints many test messages
        else:
            log.msg('  -> Debug mode = {}'.format(debugtest))


    def connectionMade(self):
        log.msg('  -> {} connected.'.format(self.sensor))

    def connectionLost(self, reason):
        log.msg('  -> {} lost.'.format(self.sensor))

    def processData(self, data):
        """ GP20S3 data """
        """
        Data looks like--- (with GPS lines every minute):
        -- vertical sensor - Old software
        3,3,12.00 111 field1 field2 field3  
        3,3,12.00 111 field1 field2 field3 
        GPS 16.00 111 field1 field2 field3  
        -- horizontal sensor - New software
        time 111 field1 field2 field3                                            (every sec or faster)
        $$$                                                         (every hour, preceeds status line)
        10071506 A 13 250 492 496 329 150 1023 39 39 39 30 29 30 YYYyyyEEENNN 148 149 117 (every hour)
        time 111 field1 field2 field3                                            (every sec or faster)
        time 111 field1 field2 field3                                            (every sec or faster)
        """

        currenttime = datetime.utcnow()
        outdate = datetime.strftime(currenttime, "%Y-%m-%d")
        actualtime = datetime.strftime(currenttime, "%Y-%m-%dT%H:%M:%S.%f")
        outtime = datetime.strftime(currenttime, "%H:%M:%S")
        timestamp = datetime.strftime(currenttime, "%Y-%m-%d %H:%M:%S.%f")
        filename = outdate
        sensorid = self.sensor
        headerlinecoming = False
        datearray = []
        headarray = []
        statusname = "Status_123_0001"

        sensororientation = self.sensor.split('_')[0].replace(self.sensordict.get('protocol'),'')
        if len(sensororientation) > 1:
            sens1 = sensororientation
            sens2 = sensororientation[0]
            sens3 = sensororientation[1]
        else:
            sens1 = 'TA'
            sens2 = 'B'
            sens3 = 'TB'
        celem =  '[{},{},{},{}{},{}{},{}{},None]'.format(sens1,sens2,sens3, sens3,sens1, sens3,sens2, sens2,sens1)
        packcode = '6hLQQQqqq6hL'
        header = "# MagPyBin %s %s %s %s %s %s %d" % (self.sensor, '[x,y,z,dx,dy,dz,sectime]', celem, '[pT,pT,pT,pT,pT,pT,None]', '[1000,1000,1000,1000,1000,1000,1]', packcode, struct.calcsize('<'+packcode))

        try:
            # Extract data
            data_array = data
            if len(data_array) == 5:
                intensity1 = float(data_array[2])
                intensity2 = float(data_array[3])
                intensity3 = float(data_array[4])
                grad1 = intensity3-intensity1
                grad2 = intensity3-intensity2
                grad3 = intensity2-intensity1
                try:
                    gpstime = float(data[0]) # will fail for old dataformat -> NTP
                    if gpstime > 235900.0: # use date of last day if gpstime > 235900 to prevent next day date for 235959 gps when pctime already is on next day
                        cdate = dateprev
                    else:
                        cdate = outdate
                        dateprev = outdate
                    try:
                        internal_t = datetime.strptime(cdate+'T'+data[0], "%Y-%m-%dT%H%M%S.%f")
                    except:
                        internal_t = datetime.strptime(cdate+'T'+data[0], "%Y-%m-%dT%H%M%S")
                    internal_time = datetime.strftime(internal_t, "%Y-%m-%d %H:%M:%S.%f")
                except:
                    internal_time = timestamp #datetime.strftime(datetime.utcnow(), "%Y-%m-%d %H:%M:%S.%f")

            elif len(data_array) == 19:
                """
                        10071506 A 13 250 492 496 329 150 1023 39 39 39 30 29 30 YYYyyyEEENNN 148 149 117

			<GPS> day/month/year/hour A - locked, V unlocked
			<13> Console outside air temperature (13C)
			<250> Battery voltage (25.0V)
			<492> +5V supply voltage (4.92V)
			<496> -5V supply voltage (-4.96)
			<3.3V> +3.3V supply voltage (3.3V)
			<15.0> silver box power supply (15.0V)
			<1023> OCXO internal trimpot adjustment level, automatically adjusted via GPS
			<39> Sensor 1 temperature in C
			<39>  Sensor 2 temperature in C
			<39> Sensor 3 temperature in C
			<30> Light current sensor 1 (3.0uA)
			<29> Light current sensor 2 (2.9uA)
			<30> Light current sensor 3 (3.0uA)
			<YYY>  Sensor 1, sensor 2 sensor 3 lock status Y- locked, N - unlocked
			<yyy>  Sensor 1 heater status, sensor 2 heater status, sensor 3 heater status y-on, n-off
			<EEE> Sensor 1 heater, sensor 2 heater, sensor 3 heater E-enabled, D-disabled (used for over heat protection)
			<NNN> RF sensor 1, RF sensor 2, RF sensor 3, N -on, F-off
			<148> Sensor 1 RF dc voltage (14.8V)
			<149> Sensor 2 RF dc voltage (14.9V)
			<117> Sensor 3 RF dc voltage (11.7V)
                """
                headerlinecoming = True

                try:
                    gpstime = str(data_array[0])
                    internal_t = datetime.strptime(gpstime, "%d%m%y%H")
                    gpstimestamp = datetime.strftime(internal_t, "%Y-%m-%d %H:%M:%S.%f")
                except:
                    gpstimestamp = timestamp
                internal_time = gpstimestamp

                gpstatus = data_array[1]			# str1
                telec = int(data_array[2])			# t2
                Vbat = float(data_array[3])/10.			# f
                Vsup1 = float(data_array[4])/100.		# var4
                Vsup2 = float(data_array[5])/100.		# var5
                Vlow = float(data_array[6])/100.		# t1
                PowerSup = float(data_array[7])/10.		# df
                level = data_array[8]				# str3
                tsens1 = int(data_array[9])			# x
                tsens2 = int(data_array[10])			# y
                tsens3 = int(data_array[11])			# z
                lightcurrent1 = float(data_array[12])/10.	# dx
                lightcurrent2 = float(data_array[13])/10.	# dy
                lightcurrent3 = float(data_array[14])/10.	# dz
                statusstring = data_array[15]			# str2
                Vsens1 = float(data_array[16])/10.		# var1
                Vsens2 = float(data_array[17])/10.		# var2
                Vsens3 = float(data_array[18])/10.		# var3 

            elif len(data_array) == 1 and data_array[0] == '$$$':
                return "","",""
            else:
                log.msg('{} protocol: data line could not be interpreted: ({}) of length {}'.format(self.sensordict.get('protocol'),data, len(data_array)))
        except:
            log.err('{} protocol: Data formatting error. Data looks like: {}'.format(self.sensordict.get('protocol'),data))

        try:
            # Analyze time difference between GSM internal time and utc from PC
            timelist = sorted([internal_t,currenttime])
            timediff = timelist[1]-timelist[0]
            delta = timediff.total_seconds()
            if not delta in [0.0, float('NAN'), None]:
                self.delaylist.append(timediff.total_seconds())
                if len(self.delaylist) > 600:
                    self.delaylist = self.delaylist[-600:]
            if len(self.delaylist) > 100:
                try:
                    self.timedelay = np.abs(np.median(np.asarray(self.delaylist)))
                except:
                    self.timedelay = 0.0
            if self.timedelay > self.timethreshold:
                self.errorcnt['time'] +=1
                if self.errorcnt.get('time') < 2:
                    log.msg("{} protocol: large time difference observed for {}: {} sec".format(self.sensordict.get('protocol'), sensorid, self.timedelay))
                if self.errorcnt.get('time') > 1000:
                    self.errorcnt['time'] = 1000
            else:
                self.errorcnt['time'] = 0 
        except:
            pass

        if self.sensordict.get('ptime','') in ['NTP','ntp']:
            secondtime = internal_time
            maintime = timestamp
        else:
            maintime = internal_time
            secondtime = timestamp

        if not headerlinecoming:
          try:
            ## GP20S3 provides info on whether the GPS reading is OK  - use it

            # extract time data
            datearray = acs.timeToArray(maintime)
            try:
                datearray.append(int(intensity1*1000.))
                datearray.append(int(intensity2*1000.))
                datearray.append(int(intensity3*1000.))
                datearray.append(int(grad1*1000.))
                datearray.append(int(grad2*1000.))
                datearray.append(int(grad3*1000.))
                internalarray = acs.timeToArray(secondtime)
                datearray.extend(internalarray)
                data_bin = struct.pack('<'+packcode,*datearray)
            except:
                log.msg('{} protocol: Error while packing binary data'.format(self.sensordict.get('protocol')))

            if not self.confdict.get('bufferdirectory','') == '':
                acs.dataToFile(self.confdict.get('bufferdirectory'), sensorid, filename, data_bin, header)
          except:
            log.msg('{} protocol: Error with binary save routine'.format(self.sensordict.get('protocol')))

        if headerlinecoming:
            if self.debug:
                print (" now writing header info")
            headpackcode = '6hL15ls12s4s' #'6hLlllllllllllllllsss'
            statusname = "Status_123_0001"
            try:
                # extract time data
                headarray = acs.timeToArray(maintime)
                try:
                    headarray.append(int(tsens1))			# x
                    headarray.append(int(tsens2))			# y
                    headarray.append(int(tsens3))			# z
                    headarray.append(int(Vbat*10.))			# f
                    headarray.append(int(Vlow*100.))		# t1
                    headarray.append(int(telec))			# t2
                    headarray.append(int(lightcurrent1*10.))	# dx
                    headarray.append(int(lightcurrent2*10.))	# dy
                    headarray.append(int(lightcurrent3*10.))	# dz
                    headarray.append(int(PowerSup*10.))		# df
                    headarray.append(int(Vsens1*10.))		# var1
                    headarray.append(int(Vsens2*10.))		# var2
                    headarray.append(int(Vsens3*10.))		# var3 
                    headarray.append(int(Vsup1*100.))		# var4
                    headarray.append(int(Vsup2*100.))		# var5
                    headarray.append(gpstatus)			# str1
                    headarray.append(statusstring)			# str2
                    headarray.append(level)				# str3

                    data_bin = struct.pack('<'+headpackcode,*headarray)
                    statuslst = self.sensor.split('_')
                    if self.debug:
                        print ("Headerdata has been packed")
                    if len(statuslst) == 3:
                        statusname = '_'.join([statuslst[0]+'status',statuslst[1],statuslst[2]])
                    headheader = "# MagPyBin %s %s %s %s %s %s %d" % (statusname, '[x,y,z,f,t1,t2,dx,dy,dz,df,var1,var2,var3,var4,var5,str1,str2,str3]', '[Ts1,Ts2,Ts3,Vbat,V3,Tel,L1,L2,L3,Vps,V1,V2,V3,V5p,V5n,GPSstat,Status,OCXO]', '[degC,degC,degC,V,V,degC,A,A,A,V,V,V,V,V,V,None,None,None]', '[1,1,1,10,100,1,10,10,10,10,10,10,10,100,100,1,1,1]', headpackcode, struct.calcsize('<'+headpackcode))
                    if self.debug:
                        print ("Header looks like: {} ".format(headheader))
                        print ("Writing to file: {}, {}, {}".format(statusname,filename,headheader))
                    if not self.confdict.get('bufferdirectory','') == '':
                        acs.dataToFile(self.confdict.get('bufferdirectory'), statusname, filename, data_bin, headheader)
                except:
                    log.msg('GSMP20 - Protocol: Error while packing binary data')
            except:
                pass

        if len(datearray) > 0:
            topic = self.confdict.get('station') + '/' + self.sensordict.get('sensorid')
            return ','.join(list(map(str,datearray))), header, topic
        elif len(headarray) > 0:
            topic = self.confdict.get('station') + '/' + statusname
            return ','.join(list(map(str,headarray))), headheader, topic


    def lineReceived(self, line):

        # Defaulttopic
        topic = self.confdict.get('station') + '/' + self.sensordict.get('sensorid')
        # extract only ascii characters 
        line = ''.join(filter(lambda x: x in string.printable, line))

        ok = True
        try:
            splitline = line.split()
            data, head, topic = self.processData(splitline)
        except:
            data = ''
            print('{}: Data seems not be correct data: Looks like {}'.format(self.sensordict.get('protocol'),line))
            ok = False

        if data =="":
            ok = False

        if ok:
            senddata = False
            coll = int(self.sensordict.get('stack'))
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
                self.client.publish(topic+"/data", data, qos=self.qos)
                if self.count == 0:
                    add = "SensorID:{},StationID:{},DataPier:{},SensorModule:{},SensorGroup:{},SensorDecription:{},DataTimeProtocol:{}".format( self.sensordict.get('sensorid',''),self.confdict.get('station',''),self.sensordict.get('pierid',''),self.sensordict.get('protocol',''),self.sensordict.get('sensorgroup',''),self.sensordict.get('sensordesc',''),self.sensordict.get('ptime','') )
                    self.client.publish(topic+"/dict", add, qos=self.qos)
                    self.client.publish(topic+"/meta", head, qos=self.qos)
                self.count += 1
                if self.count >= self.metacnt:
                    self.count = 0

