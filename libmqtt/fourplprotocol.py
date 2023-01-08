#!/usr/bin/env python

from __future__ import print_function
import sys, time, os, socket
import serial
import struct, binascii, re, csv
from datetime import datetime, timedelta
from matplotlib.dates import date2num, num2date
import numpy as np
import time

"""
init file with typus, distances, averaging parameters (i.e. 30), frequnecy and current

Alternatively, get commands from sensors.cfg just like for arduino
frequency and current would work with standard init
main routine reads init and then runs in passive mode
"""

"""
port = '/dev/ttyUSB0'
baudrate='19200'
eol = '\r'
commandlist = ["w","O","c","o","M"]
currdic = {"m":"1uA","n":"10uA","o":"100uA","p":"1mA","q":"5mA","r":"15mA","s":"50mA","t":"100mA"}
freqdic = {"a":"0.26Hz","b":"0.52Hz","c":"1.04Hz","d":"2.08Hz","e":"4.16Hz","f":"8.33Hz","g":"12.5Hz","h":"25Hz"}

commanddict = {"v":"Softwareversion","w":"external voltage","M":"single measurement","N":"Transmitter output voltage","O":"Battery Voltage","P":"Self potential","Q":"Cont measure start","R":"Cont measure stop","S":"Transmitter on","T":"Transmitter Off","W":"External electrodes on","X":"External electrodes off"}

def lineread(ser,eol):
            # FUNCTION 'LINEREAD'
            # Does the same as readline(), but does not require a standard
            # linebreak character ('\r' in hex) to know when a line ends.
            # Variable 'eol' determines the end-of-line char: '\x00'
            # for the POS-1 magnetometer, '\r' for the envir. sensor.
            # (Note: required for POS-1 because readline() cannot detect
            # a linebreak and reads a never-ending line.)
            ser_str = ''
            timeout = time.time()+2
            while True:
                char = ser.read().decode()
                if char == eol:
                    break
                if time.time() > timeout:
                    break
                ser_str += char
            return ser_str

def send_command(ser,command,eol,hex=False):

    command = command
    sendtime = date2num(datetime.utcnow())
    ser.write(command.encode())
    response = lineread(ser,eol)
    receivetime = date2num(datetime.utcnow())
    meantime = np.mean([receivetime,sendtime])

    return response, num2date(meantime).replace(tzinfo=None)

def rho(U,I,A,L=0,typus="wenner"):
    rh = 0.0
    if typus in ["schlumberger","Schlumberger","schlum"]:
        rh = np.pi * (((L/2)**2 - (A/2)**2) / A) * U / I
    elif typus in ["half-schlumberger","Half-Schlumberger","half-schlum"]:
        rh = 2 * np.pi * (((L/2)**2 - (A/2)**2) / A) * U / I
    elif typus in ["dipole-dipole","Dipol-Dipol","Dipole-Dipole","dipol-dipol"]:
        n = L/A
        rh = np.pi * n(n+1)(n+2) * A * U / I
    else:
        rh = 2* np.pi * A * U / I
    return rh

def phase(U0,U90):
    # return phase in mrad
    return U90/U0*1000.


ser = serial.Serial(port, baudrate=baudrate , parity='N', bytesize=8, stopbits=1, timeout=2)

A=0.65

test = 1
if test==2:
    commandlist = ["v","w","S","N","M","T","O"]
    for comm in commandlist:
        time.sleep(0.5)
        answer, actime = send_command(ser,comm,eol)
        print("Receiving {}: {}".format(commanddict.get(comm),answer))

if test==1:
    print ("Setting parameters:")
    print ("-------------------")
    meascom = ["v","w","O","c","o"]
    I = 0
    for comm in meascom:
        time.sleep(0.5)
        answer, actime = send_command(ser,comm,eol)
        print("Receiving {}: {}".format(commanddict.get(comm,"Not in list"),answer))
        if comm in ["m","n","o","p","q","r","s","t"]:
            Ist = currdic.get(comm)
            print (Ist)
            if Ist.find("mA") >0:
                I = float(Ist.replace("mA",""))/1000
            else:
                I = float(Ist.replace("uA",""))/1000000

    print (I)
    print ("Running measurement:")
    print ("-------------------")

    for n in range(0,1440):
        # 10 seconds break
        time.sleep(10)
        # start transmission
        comms = ["S","M","T"]
        sum0,sum90 = [],[]
        print ("------------------------")
        print ("Date:", datetime.utcnow())
        for comm in comms:
            #answer,actime = send_command(ser,comm,eol)
            if comm == "M":
                for o in range(1,30):
                    answer,actime = send_command(ser,comm,eol)
                    answer = answer.replace("M","")
                    #print ("Current {}: U0[mV]={},U90[mV]={}".format(currentdic[curr],answer.split(" ")[0],answer.split(" ")[1]))
                    #print ("U0[mV]={},U90[mV]={}".format(answer.split(" ")[0],answer.split(" ")[1]))
                    u0 = float(answer.split(" ")[0])
                    u90 = float(answer.split(" ")[1])
                    sum0.append(u0)
                    sum90.append(u90)
                    if o == 29:
                        print ("U0[mV]={:.3f}, std={:.3f}, percental error={:.2f}%".format(np.mean(sum0),np.std(sum0),np.std(sum0)/np.mean(sum0)/np.sqrt(29)*100.))
                        print ("U90[mV]={:.3f}, std={:.3f}, percental error={:.2f}%".format(np.mean(sum90),np.std(sum90),np.std(sum90)/np.mean(sum90)/np.sqrt(29)*100. ) )
                        print ("Rho[Ohm*m]={:.1f},Phase[mrad]={:.2f}".format(rho(np.mean(sum0)/1000.,I,A),phase(np.mean(sum0),np.mean(sum90))))
                    time.sleep(0.2)
            else:
                answer,actime = send_command(ser,comm,eol)
                print("Receiving {}: {}".format(commanddict.get(comm),answer))

"""

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
from magpy.stream import KEYLIST
import serial
import sys

def lineread(ser,eol):
            # FUNCTION 'LINEREAD'
            # Does the same as readline(), but does not require a standard
            # linebreak character ('\r' in hex) to know when a line ends.
            # Variable 'eol' determines the end-of-line char: '\x00'
            # for the POS-1 magnetometer, '\r' for the envir. sensor.
            # (Note: required for POS-1 because readline() cannot detect
            # a linebreak and reads a never-ending line.)
            ser_str = ''
            timeout = time.time()+2
            while True:
                char = ser.read().decode()
                if char == eol:
                    break
                if time.time() > timeout:
                    break
                ser_str += char
            return ser_str


def send_command(ser,command,eol,hex=False):

    command = command
    sendtime = date2num(datetime.utcnow())
    ser.write(command.encode())
    response = lineread(ser,eol)
    receivetime = date2num(datetime.utcnow())
    meantime = np.mean([receivetime,sendtime])

    return response, num2date(meantime).replace(tzinfo=None)


def datetime2array(t):
    return [t.year,t.month,t.day,t.hour,t.minute,t.second,t.microsecond]

## Arduino active request protocol
## --------------------

class FourPLProtocol(object):
    """
    Protocol to read Lippmann 4PL

    Active protocol

    Example sensor.cfg
    4PL_0009009195_0001,USB0,19200,8,1,N,active,None,60,1,FourPL,4PL,0009009195,0001,...

    """

    ## need a reference to our WS-MCU gateway factory to dispatch PubSub events
    ##
    def __init__(self, client, sensordict, confdict):
        self.client = client #self.wsMcuFactory = wsMcuFactory
        self.sensordict = sensordict
        self.confdict = confdict
        self.count = 0  ## counter for sending header information
        self.sensorname = sensordict.get('name')
        self.sensorid = sensordict.get('sensorid')
        # serial
        self.baudrate=int(sensordict.get('baudrate'))
        self.port = confdict['serialport']+sensordict.get('port')
        self.parity=sensordict.get('parity')
        self.bytesize=sensordict.get('bytesize')
        self.stopbits=sensordict.get('stopbits')
        self.timeout=2

        self.hostname = socket.gethostname()
        self.printable = set(string.printable)
        self.datalst = []
        self.datacnt = 0
        # Sampling rate specific data
        rate = sensordict.get('rate','0')
        self.metacnt = 1
        try:
            self.rate = int(rate)
        except:
            self.rate = 10 #(a minimum of 10 secs is used)
        if self.rate < 10:
            log.msg('4PLprotocol: Minimum sampling period for 4PL in MARTAS is 10 sec. Adjusting rate...')
            self.rate = 10 # send header at reduced rate
            self.metacnt = 10 # send header at reduced rate
        self.N = int(self.rate/2.)
        log.msg('4PLprotocol: Recording {} individual measurements for mean resistivity.'.format(self.N))
        self.counter = {}

        # QOS
        self.qos=int(confdict.get('mqttqos',0))
        if not self.qos in [0,1,2]:
            self.qos = 0
        log.msg("  -> setting QOS:", self.qos)

        # switch on debug mode
        debugtest = confdict.get('debug')
        self.debug = False
        if debugtest == 'True':
            log.msg('DEBUG - {}: Debug mode activated.'.format(self.sensordict.get('protocol')))
            self.debug = True    # prints many test messages
        else:
            log.msg('  -> Debug mode = {}'.format(debugtest))

        # 4PL specific
        #self.sensorid = ''
        self.serialnum = ''
        self.currdic = {"m":"1uA","n":"10uA","o":"100uA","p":"1mA","q":"5mA","r":"15mA","s":"50mA","t":"100mA"}
        self.freqdic = {"a":"0.26Hz","b":"0.52Hz","c":"1.04Hz","d":"2.08Hz","e":"4.16Hz","f":"8.33Hz","g":"12.5Hz","h":"25Hz"}
        self.commanddict = {"v":"Softwareversion","w":"external voltage","M":"single measurement","N":"Transmitter output voltage","O":"Battery Voltage","P":"Self potential","Q":"Cont measure start","R":"Cont measure stop","S":"Transmitter on","T":"Transmitter Off","W":"External electrodes on","X":"External electrodes off"}
        # Specific commands for ultrasonic wind sensor
        # self.addressanemo = '01'
        self.commands = [{'data':'11TR00005'},{'meta':''},{'head':''}] # ,self.addressanemo+'TR00002']
        self.commands = [{'data':'01TR00002','c1':'01SH','c2':'01SL'}]
        self.eol = '\r'
        # call "setcurrandfrequ", requires curret and frequency from commands
        self.A = 0.65 # get from sensorsconf
        self.L = None # get from sensorsconf
        #self.N = 30 # get from sensorsconf (samplingrate must be twice as high) (i.e. take sampling rate and use half of it)
        self.ser = self.connectserial()
        self.I,self.F = self.setcurrandfrequ("c","o")

    def connectserial(self):
        ser = serial.Serial(self.port, baudrate=int(self.baudrate), parity=self.parity, bytesize=int(self.bytesize), stopbits=int(self.stopbits), timeout=int(self.timeout))
        if not ser.isOpen():
            ser.open()
        return ser

    def setcurrandfrequ(self,freq,curr):
        """
        Obtain frequency and current from code
        """
        I,F = 0,0
        ser = self.ser
        ok = True
        if ok:
            log.msg('4PLprotocol: Initializing frequency and current')
            meascom = ["v","w","O",freq,curr]
            for comm in meascom:
                answer, actime = send_command(ser,comm,self.eol)
                if self.commanddict.get(comm,""):
                    log.msg("Receiving {}: {}".format(self.commanddict.get(comm,""),answer))
                if comm in ["a","b","c","d","e","f","g","h"]:
                    Fst = self.freqdic.get(comm)
                    log.msg("Setting frequency: {}".format(Fst))
                    F = float(Fst.replace("Hz",""))
                if comm in ["m","n","o","p","q","r","s","t"]:
                    Ist = self.currdic.get(comm)
                    log.msg("Setting current: {}".format(Ist))
                    if Ist.find("mA") >0:
                        I = float(Ist.replace("mA",""))/1000
                    else:
                        I = float(Ist.replace("uA",""))/1000000
                time.sleep(0.5)
            log.msg('4PLprotocol: Initializing complete')

        return I,F

    def rho(self,U,I,A,L=0,typus="wenner"):
        """
        """
        rh = 0.0
        if typus in ["schlumberger","Schlumberger","schlum"]:
            rh = np.pi * (((L/2)**2 - (A/2)**2) / A) * U / I
        elif typus in ["half-schlumberger","Half-Schlumberger","half-schlum"]:
            rh = 2 * np.pi * (((L/2)**2 - (A/2)**2) / A) * U / I
        elif typus in ["dipole-dipole","Dipol-Dipol","Dipole-Dipole","dipol-dipol"]:
            n = L/A
            rh = np.pi * n(n+1)(n+2) * A * U / I
        else:
            rh = 2* np.pi * A * U / I
        return rh

    def phase(self,U0,U90):
        # return phase in mrad
        return U90/U0*1000.

    def error(self,sigma,mean,N):
        # return phase in mrad
        return sigma/np.sqrt(N)/mean*100.

    def gettime(self,st,et):
        # calculate mean time and eventually round to minute or hour

        def roundTime(dt=None, roundTo=60):
            """
            Round a datetime object to any time lapse in seconds
            dt : datetime.datetime object, default now.
            roundTo : Closest number of seconds to round to, default 1 minute.
            Author: Thierry Husson 2012
            """
            if dt == None:
                dt = datetime.datetime.now()
            seconds = (dt.replace(tzinfo=None) - dt.min).seconds
            rounding = (seconds+roundTo/2) // roundTo * roundTo
            return dt + datetime.timedelta(0,rounding-seconds,-dt.microsecond)

        dmean = num2date(np.mean([date2num(st),date2num(et)]))
        actime = None
        if self.rate >= 60:
            actime = roundTime(dmean,roundTo=60)
        elif self.rate >= 3600:
            actime = roundTime(dmean,roundTo=60*60)
        else:
            actime = num2date(dmean)
        return actime

    def processData(self, vals, ntptime):
        """
        processing and storing data - requires sensorid and meta info:
        Writing the following info as data:
        x,y,z,f,dx,dy,t1,t2,var1,var2,var3
        U0,U90,rho,phase,U0error,U90error,4PL voltage,external voltage,current,frequency, N
        MetaInformation:
        SensorID,Softwareversion,
        """
        # currenttime = datetime.utcnow()
        outdate = datetime.strftime(ntptime, "%Y-%m-%d")
        filename = outdate
        sensorid = self.sensorid
        header = ''
        datearray = datetime2array(ntptime)
        packcode = '6hLlllllllllll'
        multiplier = [10000,10000,1000,10000,10000,10000,1000,1000,1000,1000,1]

        # convert vals to fullresult
        fullres = [vals[0],vals[1],self.rho(vals[0]/1000.,self.I,self.A,self.L),self.phase(vals[0],vals[1]),self.error(vals[2],vals[0],self.N),self.error(vals[3],vals[0],self.N),vals[4],vals[5],self.I,self.F,self.N]
        #print ("U0[mV]={:.3f}, std={:.3f}, percental error={:.2f}%".format(np.mean(sum0),np.std(sum0),np.std(sum0)/np.mean(sum0)/np.sqrt(29)*100.))
        #print ("U90[mV]={:.3f}, std={:.3f}, percental error={:.2f}%".format(np.mean(sum90),np.std(sum90),np.std(sum90)/np.mean(sum90)/np.sqrt(29)*100. ) )
        #print ("Rho[Ohm*m]={:.1f},Phase[mrad]={:.2f}".format(rho(np.mean(sum0)/1000.,I,A),phase(np.mean(sum0),np.mean(sum90))))

        if self.debug:
            print ("Processing results for {}: {}".format(sensorid, vals))
        if len(fullres) > 3:
            errormark = False
            for idx,el in enumerate(fullres):
                try:
                    datearray.append(int(el*multiplier[idx]))
                except:
                    log.msg('{} protocol: Error while appending data to file - data looks like {}'.format(self.sensordict.get('protocol'),vals))
                    errormark = True
            try:
                data_bin = struct.pack('<'+packcode,*datearray) #little endian
            except:
                log.msg('{} protocol: Error while packing binary data'.format(self.sensordict.get('protocol')))
                errormark = True

            if not errormark:
                #asseble header from available global information - write only if information is complete
                key = '[x,y,z,f,dx,dy,t1,t2,var1,var2,var3]'
                ele = '[U0,U90,Rho,Phase,eU0,eU90,Vint,Vext,I,F,N]'
                unit = '[mV,mV,Ohm*m,mrad,per,per,V,V,uA,Hz,]'
                multplier = "[{}]".format(",".join([str(el) for el in multiplier]))
                # Correct some common old problem
                unit = unit.replace('deg C', 'degC')

                header = "# MagPyBin {} {} {} {} {} {} {}".format(sensorid, key, ele, unit, multplier, packcode, struct.calcsize('<'+packcode))
                data = ','.join(list(map(str,datearray)))

                if not self.confdict.get('bufferdirectory','') == '':
                    acs.dataToFile(self.confdict.get('bufferdirectory'), sensorid, filename, data_bin, header)
            else:
                data = ''
                header = ''
        else:
            data = ''

        return data, header


    def sendRequest(self):

        ser = self.ser
        # connect serial
        if not ser.isOpen():
            ser.open()

        if not self.I > 0:
            log.msg("4PLprotocol: initialization didnt work: current is zero")
            return False
        success = True

        if self.debug:
            print ("Running measurement:")
            print ("-------------------")

        ok = True
        if ok:
            #
            st = datetime.utcnow()
            # start transmission
            comms = ["w","O","S","M","T"]
            sum0,sum90 = [],[]
            if self.debug:
                print ("------------------------")
                print ("Date:", datetime.utcnow())
            for comm in comms:
                if comm == "M":
                    for o in range(0,self.N):
                        answer,actime = send_command(ser,comm,self.eol)
                        answer = answer.replace("M","")
                        #print ("Current {}: U0[mV]={},U90[mV]={}".format(currentdic[curr],answer.split(" ")[0],answer.split(" ")[1]))
                        #print ("U0[mV]={},U90[mV]={}".format(answer.split(" ")[0],answer.split(" ")[1]))
                        u0 = float(answer.split(" ")[0])
                        u90 = float(answer.split(" ")[1])
                        sum0.append(u0)
                        sum90.append(u90)
                        if o == (self.N-1):
                            meanU0=np.mean(sum0)
                            meanU90=np.mean(sum90)
                            stdU0=np.std(sum0)
                            stdU90=np.std(sum90)
                else:
                    answer,actime = send_command(ser,comm,self.eol)
                    if self.debug:
                        print("Receiving {}: {}".format(self.commanddict.get(comm),answer))
                    if comm=="w":
                        Vext=float(answer.replace("w",""))
                    if comm=="O":
                        Vint=float(answer.replace("O",""))
            et = datetime.utcnow()
            actime = self.gettime(st,et)
            result = [meanU0,meanU90,stdU0,stdU90,Vint,Vext]
            if self.debug:
                print ("Processing data: {}".format(result))
            data, head = self.processData(result, actime)
            # send data via mqtt
            if not data == '':
                self.sendmqtt(data,head)

        # disconnect from serial
        #ser.close()


    def sendmqtt(self,data,head):
        """
            call this method after processing data
        """
        sensorid=self.sensorid
        ok = True
        if ok:

            topic = self.confdict.get('station') + '/' + sensorid

            senddata = False
            try:
                coll = int(self.sensordict.get('stack'))
            except:
                coll = 0

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
                if self.debug:
                    print ("publishing...")
                self.client.publish(topic+"/data", data, qos=self.qos)
                # If multiple sensors are connected, self.count needs to be a dict (with topic)
                # Initialize counter for each topic
                if self.counter.get(sensorid,'') == '':
                    self.counter[sensorid] = 0
                cnt = self.counter.get(sensorid)

                if cnt == 0:
                    ## 'Add' is a string containing dict info like:
                    ## SensorID:ENV05_2_0001,StationID:wic, PierID:xxx,SensorGroup:environment,...
                    add = "SensorID:{},StationID:{},DataPier:{},SensorModule:{},SensorGroup:{},SensorDescription:{},DataTimeProtocol:{}".format( sensorid,self.confdict.get('station','').strip(),self.sensordict.get('pierid','').strip(),self.sensordict.get('protocol','').strip(),self.sensordict.get('sensorgroup','').strip(),self.sensordict.get('sensordesc','').strip(),self.sensordict.get('ptime','').strip() )
                    self.client.publish(topic+"/dict", add, qos=self.qos)
                    self.client.publish(topic+"/meta", head, qos=self.qos)

                cnt += 1
                if cnt >= self.metacnt:
                    cnt = 0
                # update counter in dict
                self.counter[sensorid] = cnt
