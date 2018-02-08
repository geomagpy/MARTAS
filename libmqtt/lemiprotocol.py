'''
Filename:               lemiprotocol
Part of package:        acquisition
Type:                   Part of data acquisition library

PURPOSE:
        This package will initiate LEMI025 / LEMI036 data acquisition and streaming
        and saving of data.

CONTAINS:
        *LemiProtocol:  (Class - twisted.protocols.basic.LineReceiver)
                        Class for handling data acquisition of LEMI variometers.
                        Includes internal class functions: processLemiData
        _timeToArray:   (Func) ... utility function for LemiProtocol.
        h2d:            (Func) ... utility function for LemiProtocol.
                        Convert hexadecimal to decimal.

IMPORTANT:
        - According to data sheet: 300 millseconds are subtracted from each gps time step
        provided GPStime = GPStime_sent - timedelta(microseconds=300000)
        - upcoming year 3000 bug
DEPENDENCIES:
        twisted, autobahn

CALLED BY:
        magpy.bin.acquisition
'''
from __future__ import print_function
from __future__ import absolute_import


# ###################################################################
# Import packages
# ###################################################################

import re     # for interpretation of lines
import struct # for binary representation
import socket # for hostname identification
import string # for ascii selection
import numpy as np
from datetime import datetime, timedelta
from twisted.protocols.basic import LineReceiver
from twisted.python import log
from magpy.acquisition import acquisitionsupport as acs

#import sys, time, os
#import binascii, csv


## Lemi protocol (Lemi025 and Lemi036)
## -------------

class LemiProtocol(LineReceiver):
    """
    Protocol to read GSM90 data
    This protocol defines the individual sensor related read process. 
    It is used to dipatch url links containing specific data.
    Sensor specific coding is contained in method "processData".
    """
    def __init__(self, client, sensordict, confdict):
        """
        'client' could be used to switch between different publishing protocols
                 (e.g. MQTT or WS-MCU gateway factory) to publish events
        'sensordict' contains a dictionary with all sensor relevant data (sensors.cfg)
        'confdict' contains a dictionary with general configuration parameters (martas.cfg)
        """
        print ("Initializing LEMI")
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
        self.delaylist = []  # delaylist contains up to 1000 diffs between gps and ntp
                             # the median of this values is used for ntp timedelay
        self.timedelay = 0.0
        self.ntp_gps_offset = 2.03 # sec - only used for time testing
        self.timethreshold = 3 # secs - waring if timedifference is larger the 3 seconds

        # LEMI Specific        
        self.soltag = self.sensor[0]+self.sensor[4:7]    # Start-of-line-tag
        self.errorcnt = {'gps':'A', 'time':'0', 'buffer':0}
        self.buffer = ''
        self.gpsstate1 = 'A'
        self.gpsstate2 = 'P'
        self.gpsstatelst = []
        flag = 0
        print ("Initializing LEMI finished")


    def connectionMade(self):
        log.msg('  -> {} connected.'.format(self.sensor))

    def connectionLost(self, reason):
        log.msg('  -> {} lost.'.format(self.sensor))

    def mediantimedelay(self, values):
        """
        Get the median of the provided list 'values'
        Used for calculating the median timedifference between GPS and NTP
        Median diff can be applied to NTP in case of GPS signal losses
        """
        if len(values) > 0:
            ar = np.asarray(values)
            try:
                med = np.median(ar)
            except:
                med = 0.0
        else:
            med = 0.0
        return med

    def h2d(self,x):
        '''
        Hexadecimal to decimal (for format LEMIBIN2)
        ... Because the binary for dates is in binary-decimal, not just binary.
        '''

        y = int(x/16)*10 + x%16
        return y

    def processLemiData(self, data):
        """Convert raw ADC counts into SI units as per datasheets"""
        if len(data) != 153:
            log.err('LEMI - Protocol: Unable to parse data of length %i' % len(data))

        print ("Processing data ...")
        """ TIMESHIFT between serial output (and thus NTP time) and GPS timestamp """
        # update median timedelay throughout
        timestamp = datetime.strftime(currenttime, "%Y-%m-%d %H:%M:%S.%f")

        currenttime = datetime.utcnow()
        date = datetime.strftime(currenttime, "%Y-%m-%d")
        timestamp = datetime.strftime(currenttime, "%Y-%m-%d %H:%M:%S.%f")
        outtime = datetime.strftime(currenttime, "%H:%M:%S")

        datearray = acs.timeToArray(timestamp)
        date_bin = struct.pack('6hL',datearray[0]-2000,datearray[1],datearray[2],datearray[3],datearray[4],datearray[5],datearray[6])

        # define pathname for local file storage (default dir plus hostname plus sensor plus year) and create if not existing
        path = os.path.join(self.confdict.get('bufferdirectory'), self.sensor)
        if not os.path.exists(path):
            os.makedirs(path)

        packcode = "<4cb6B8hb30f3BcBcc5hL"
        header = "LemiBin %s %s %s %s %s %s %d\n" % (self.sensor, '[x,y,z,t1,t2]', '[X,Y,Z,T_sensor,T_elec]', '[nT,nT,nT,deg_C,deg_C]', '[0.001,0.001,0.001,100,100]', packcode, struct.calcsize(packcode))

        # save binary raw data to buffer file ### please note that this file always contains GPS readings
        lemipath = os.path.join(path,self.sensor+'_'+date+".bin")
        if not os.path.exists(lemipath):
            with open(lemipath, "ab") as myfile:
                myfile.write(header)
        try:
            with open(lemipath, "ab") as myfile:
                myfile.write(data+date_bin)
            pass
        except:
            log.err('LEMI - Protocol: Could not write data to file.')

        # unpack data and extract time and first field values
        # This data is streamed via mqtt
        try:
            data_array = struct.unpack("<4cB6B8hb30f3BcB", data)
        except:
            log.err("LEMI - Protocol: Bit error while reading.")

        try:

            newtime = []
            #for i in range (5,11):
            #    newtime.append(self.correct_bin_time(data_array[i]))
            #time = datetime(2000+newtime[0],newtime[1],newtime[2],newtime[3],newtime[4],int(newtime[5]),int(newtime[6]*1000000))
            biasx = float(data_array[16])/400.
            biasy = float(data_array[17])/400.
            biasz = float(data_array[18])/400.
            x = (data_array[20])*1000.
            xarray = [elem * 1000. for elem in data_array[20:50:3]]
            y = (data_array[21])*1000.
            yarray = [elem * 1000. for elem in data_array[21:50:3]]
            z = (data_array[22])*1000.
            zarray = [elem * 1000. for elem in data_array[22:50:3]]
            temp_sensor = data_array[11]/100.
            temp_el = data_array[12]/100.
            vdd = float(data_array[52])/10.
            gpsstat = data_array[53]
            gps_array = datetime(2000+self.h2d(data_array[5]),self.h2d(data_array[6]),self.h2d(data_array[7]),self.h2d(data_array[8]),self.h2d(data_array[9]),self.h2d(data_array[10]))-timedelta(microseconds=300000)
            gps_time = datetime.strftime(gps_array, "%Y-%m-%d %H:%M:%S")
        except:
            log.err("LEMI - Protocol: Number conversion error.")

        # get the most frequent gpsstate of the last 10 secs
        # this avoids error messages for singular one sec state changes
        self.gpsstatelst.append(gpsstat)
        self.gpsstatelst = self.gpsstatelst[-10:]
        self.gpsstate1 = max(set(self.gpsstatelst),key=self.gpsstatelst.count)
        if not self.gpsstate1 == self.gpsstate2:
            log.msg('LEMI - Protocol: GPSSTATE changed to %s .'  % gpsstat)
        self.gpsstate2 = self.gpsstate1

        #update timedelay
        #delta = timediff.total_seconds()
        #if delta not in [np.nan, None, '']:
        #    self.delaylist.append(delta)
        #    self.delaylist = self.delaylist[-1000:]
        #    self.timedelay = self.mediantimedelay(self.delaylist)



        ### NNOOOO, always send GPS time - but provide median time delays with the dictionary
        ### check LEMI Records whether secondary time (NTP) is readable and extractable

        #if self.gpsstate2 == 'P':
        #    ## passive mode - no GPS connection -> use ntptime as primary with correction
        #    datearray = acs.timeToArray(timestamp)
        #else:
        #    ## active mode - GPS time is used as primary


        # Create a dataarray
        linelst = []
        for idx,el in enumerate(xarray):
            datalst = []
            tincr = idx/10.
            timear = gps_array+timedelta(seconds=tincr)
            gps_time = datetime.strftime(timear, "%Y-%m-%d %H:%M:%S")
            print ("Time", acs.timeToArray(gps_time))
            datalst = acs.timeToArray(gps_time)
            datalst.append(xarray[idx])
            datalst.append(yarray[idx])
            datalst.append(zarray[idx])
            datalst.append(temp_sensor)
            datalst.append(temp_el)
            datalst.append(vdd)
            linestr = ','.join(datalst)
            linelst.append(linestr)
            print ("Line looks like", linestr)
        dataarray = ';'.join(datalst)

        """
            try:
                datearray.append(int(intensity*1000.))
                datearray.append(err_code)
                #print timestamp, internal_time
        """

        print ("GPSSTAT", gpsstat)

        return dataarray, header, metadict


    def dataReceived(self, data):

        print ("HERE")
        #print ("Lemi data here!", self.buffer)

        topic = self.confdict.get('station') + '/' + self.sensordict.get('sensorid')

        flag = 0
        WSflag = 0
        debug = False

        """
        # Test range
        self.buffer = self.buffer + data
        if not (self.buffer).startswith(self.soltag):
            lemisearch = (self.buffer).find(self.soltag, 6)
            if not lemisearch == -1:
                print "Lemiserach", lemisearch, self.buffer
                self.buffer = self.buffer[lemisearch:len(self.buffer)]
        if len(self.buffer) == 153:
            # Process data
            print self.buffer
            self.buffer = ''
        """

        try:
            # 1. Found correct data length
            if (self.buffer).startswith(self.soltag) and len(self.buffer) == 153:
                currdata = self.buffer
                self.buffer = ''
                data, head = self.processLemiData(currdata)
                WSflag = 2

            # 2. Found incorrect data length

            ### Note: this code for fixing data is more complex than the POS fix code
            ### due to the LEMI device having a start code rather than an EOL code.
            ### It can handle and deal with multiple errors:
            ###  - multiple data parts arriving at once
            ###  - databits being lost. Bad string is then deleted.
            ###  - bad bits infiltrating the data. Bad string is deleted.

            if len(self.buffer) > 153:
                if debug:
                    log.msg('LEMI - Protocol: Warning: Bufferlength (%s) exceeds 153 characters, fixing...' % len(self.buffer))
                lemisearch = (self.buffer).find(self.soltag)
                #print '1', lemisearch
                if (self.buffer).startswith(self.soltag):
                    datatest = len(self.buffer)%153
                    dataparts = int(len(self.buffer)/153)
                    if datatest == 0:
                        if debug:
                            log.msg('LEMI - Protocol: It appears multiple parts came in at once, # of parts:', dataparts)
                        for i in range(dataparts):
                            split_data_string = self.buffer[0:153]
                            if (split_data_string).startswith(self.soltag):
                                if debug:
                                    log.msg('LEMI - Protocol: Processing data part # %s in string...' % (str(i+1)))
                                dataarray, head, metadict = self.processLemiData(split_data_string)
                                WSflag = 2
                                self.buffer = self.buffer[153:len(self.buffer)]
                            else:
                                flag = 1
                                break
                    else:
                        for i in range(dataparts):
                            lemisearch = (self.buffer).find(self.soltag, 6)
                            if lemisearch >= 153:
                                split_data_string = self.buffer[0:153]
                                dataarray, head, metadict = self.processLemiData(split_data_string)
                                WSflag = 2
                                self.buffer = self.buffer[153:len(self.buffer)]
                            elif lemisearch == -1:
                                log.msg('LEMI - Protocol: No header found. Deleting buffer.')
                                self.buffer = ''
                            else:
                                log.msg('LEMI - Protocol: String contains bad data (%s bits). Deleting.' % len(self.buffer[:lemisearch]))
                                self.buffer = self.buffer[lemisearch:len(self.buffer)]
                                flag = 1
                                break

                else:
                    log.msg('LEMI - Protocol: Incorrect header. Attempting to fix buffer... Bufferlength:', len(self.buffer))
                    lemisearch = (self.buffer).find(self.soltag, 6)
                    #lemisearch = repr(self.buffer).find(self.soltag)
                    if lemisearch == -1:
                        log.msg('LEMI - Protocol: No header found. Deleting buffer.')
                        self.buffer = ''
                    else:
                        log.msg('LEMI - Protocol: Bad data (%s bits) deleted. New bufferlength: %s' % (lemisearch,len(self.buffer)))
                        self.buffer = self.buffer[lemisearch:len(self.buffer)]
                        flag = 1

            if flag == 0:
                self.buffer = self.buffer + data

        except:
            log.err('LEMI - Protocol: Error while parsing data.')
            #Emtpying buffer
            self.buffer = ''

        ## publish events to all clients subscribed to topic
        if WSflag == 2:

            senddata = False
            coll = int(self.sensordict.get('stack'))
            if coll > 1:
                self.metacnt = 1 # send meta data with every block
                if self.datacnt < coll:
                    self.datalst.append(dataarray)
                    self.datacnt += 1
                else:
                    senddata = True
                    dataarray = ';'.join(self.datalst)
                    self.datalst = []
                    self.datacnt = 0
            else:
                senddata = True

            if senddata:
                self.client.publish(topic+"/data", dataarray)
                if self.count == 0:
                    add = "SensoriD:{},StationID:{},DataPier:{},SensorModule:{},SensorGroup:{},SensorDecription:{},DataTimeProtocol:{},DataNTPTimeDelay:{}".format( self.sensordict.get('sensorid',''),self.confdict.get('station',''),self.sensordict.get('pierid',''),self.sensordict.get('protocol',''),self.sensordict.get('sensorgroup',''),self.sensordict.get('sensordesc',''),self.sensordict.get('ptime',''),self.timedelay )
                    self.client.publish(topic+"/dict", add, qos=self.qos)
                    self.client.publish(topic+"/meta", head)
                self.count += 1
                if self.count >= self.metacnt:
                    self.count = 0

