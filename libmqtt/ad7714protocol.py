"""
ad7714protocol version 1.2
for board v0.1 and v0.2 or higher

Purpose:
    reads data from an AD7714 (Analog Devices) AD converter

Requirements:
    SPI interface on a RaspberryPi2 or higher
    
Called by:
    acquisition from MARTAS (magpy)
"""

from __future__ import print_function
import sys, time, os, socket
import struct, binascii, re, csv, math
from datetime import datetime, timedelta

from twisted.python import log

try:
    from core import acquisitionsupport as acs
except:
    # Relative import of core methods as long as martas is not configured as package
    scriptpath = os.path.dirname(os.path.realpath(__file__))
    coredir = os.path.abspath(os.path.join(scriptpath, '..', 'core'))
    sys.path.insert(0, coredir)
    import acquisitionsupport as acs
import threading

# Raspberry Pi specific
try:
    import spidev
    import RPi.GPIO as GPIO
except:
    log.msg('sorry, equipment not prepared to communicate over SPI')
    raise

def datetime2array(t):
    return [t.year,t.month,t.day,t.hour,t.minute,t.second,t.microsecond]

print("setup comm interface to AD7714:")
print("GPIO warnings are not disabled intentionally")
# set GPIO mode to pinnumbers
GPIO.setmode(GPIO.BOARD)

# board specific settings
# define pin32 as input for /DRDY
DRDY=32
GPIO.setup(DRDY,GPIO.IN)
# define pin7 as output for /RESET
RESET=7
GPIO.setup(RESET,GPIO.OUT,initial=GPIO.HIGH)
# next line not needed anymore - 'initial' prevents a reset when starting a second instance of ad7714protocol
#GPIO.output(RESET,GPIO.HIGH)

# setup spi
SPI=spidev.SpiDev()
SPI.open(0, 0)
# no difference of SPI speed for RaspberryPi and AD7714
# makes sense when using an oszilloscope
# RPi3B+ supports higher speeds, limiting for proper transmission
SPI.max_speed_hz=500000
print("max_speed_hz", SPI.max_speed_hz)

# AD7714

# specific SPI settings
# CPOL 0, CPHA 1 
SPI.mode=1

# board specific settings
# AD7714's system clock
# *** board v0.1 ***
#CLK=1000000
# *** board v0.2 and higher ***
CLK=2457600
print("system clock", CLK)
# *** board v0.1 ***
# using channel 5: differential input AIN3-AIN4 (pin9-pin10)
#   set NAME_Y in ad7714.cfg
#   depricated: CHANNEL = 5
# *** board v0.2 ***
# using channel 4: differential input AIN1-AIN2 (pin7-pin8)

# wordlength 16bit:0 24bit:1
global WL
WL = 1
# polarity 0:bipolar, 1:unipolar
global POL
POL = 0
# Filter sets sampling rate. Depends on system clock
global FILTER
FILTER = 0x0c0

nameofchannel = ['1','2','3','4','X','Y','Z']

# GAIN between 0 and 7
#  nr    amplification
#   0 .. 1
#   1 .. 2
#   2 .. 4
#   ......
#   6 .. 64
#   7 .. 128
global GAIN
GAIN = 0
# NAME_1, NAME_2, ..., NAME_Z
global NAME
NAME = ['','','','','X','Y','Z']
global KEY
KEY = ['','','','','x','y','z']
global UNIT
UNIT = ['','','','','mV','mV','mV']
global SCALE
SCALE = [0,0,0,0,1000,1000,1000]
global DIFF
DIFF = [0,0,0,0,0,0,0]

# calibration constants from file
#   0 .. get calibration constants from file
#   1 .. calibrate as defined below
global CALMODE
CALMODE = 1
# calibration for single channels
#    (zero calibration removes offset)
#   0 .. no calibration
#   1 .. self calibration for offset and scale factor
#   2 .. zero calibration using input voltage
#   3 .. full scale calibration (input voltage has to be provided!)
#   4 .. zero cal. using input voltage + self full calibration
#   5 .. background calibration - see data sheet
#   6 .. offset self calibration
#   7 .. scale factor self calibration
global CAL
CAL = [0,0,0,0,1,1,1]

# constants for calibration registers (only 6)
global OFFSETX
global OFFSETY
global OFFSETZ
global FULLSCALEX
global FULLSCALEY
global FULLSCALEZ

# sync at startup
global int_comm
int_comm = ""
# array for saving values until they are sent
global allvalues
allvalues=[]
# array for storing which channels are used
global channellist
channellist = []
global currentchannel
currentchannel = 0

def reset():
    """
    reset AD7714
    AD7714 requires minimum 100ns on the /RESET pin
    RPi's sleep is not so fast anyhow...
    """
    GPIO.output(RESET,GPIO.LOW)
    time.sleep(0.01)
    GPIO.output(RESET,GPIO.HIGH)
    
def zo(r):
    """
    used by txreg and rxreg
    return value should there be [0] once
    if not, some sync is wrong
    """
    if not r==[0]:
        print("NOT ZERO!, but",r)

def zt(r):
    """
    used by txreg
    return value should there be 0 three times
    if not, some sync is wrong
    """
    if not r==[0,0,0]:
        print("NOT ZERO!, but",r)

def txreg(register,channel,value):
    # write to a register on AD7714
    x=(register<<4)|channel
    # send which register is next
    zo(SPI.xfer([x]))
    # write to register
    if not register in [6,7]:
        # transmit 1 byte
        zo(SPI.xfer([value]))
    else:
        # transmit 3 byte (24bit)
        v=[(value>>16)&0xff,(value>>8)&0xff,value&0xff]
        zt(SPI.xfer(v))

def rxreg(register,channel):
    # read from a register
    if register in [1,2,3,4]:
        nr_bytes=1
    if register==5:
        # WL 0:16bit 1:24bit
        nr_bytes=2+WL
    if register in [6,7]:
        nr_bytes=3
    x=(register<<4)|8|channel
    zo(SPI.xfer([x]))
    r=SPI.readbytes(nr_bytes)
    return r

def setMode(channel=4,MD=0,FSYNC=-1):
    """
    set mode: refer to AD7714s manual
    """
    # read unchanged values from mode register
    vm=rxreg(1,channel)
    if FSYNC == -1:
        vm=(vm[0]&0x1f)|(MD<<5)
    else:
        vm=(vm[0]&0x1e)|(MD<<5)|FSYNC
    txreg(1,channel,vm)

def setGain(channel=4,G=0):
    """
    set gain of AD7714s preamp in powers of two
    amplification = 2 ** G
    """
    # read unchanged values from mode register
    vm=rxreg(1,channel)
    vm=(vm[0]&0xe3)|(G<<2)
    txreg(1,channel,vm)

def setWL(wordlength=None,channel=4):
    """
    set wordlength
    WL 0:16bit, 1:24bit
    """
    # read unchanged values from filter high register
    vf=rxreg(2,channel)
    global WL
    WL=(vf[0]>>6)&0x1
    if wordlength is None:
        # WL is set, no need to change registers
        pass
    else:
        if wordlength in [0,1]:
            # write to WL bit on AD7714
            vf=(vf[0]&0xbf)|(wordlength<<6)
            txreg(2,channel,vf)
            print('...changing WL to ',wordlength)
            vf=rxreg(2,channel)
            WL=(vf[0]>>6)&0x1
            if not WL==wordlength:
                print("couldn't change wordlength!")
        else:
            print('wordlength must be 0 or 1')
    print('Wordlength is',(2+WL)*8,'bit')

def setPol(polarity=0,channel=4):
    """
    set polarity
    POL 0:bipolar, 1:unipolar
    """
    global POL
    vf=rxreg(2,channel)
    vf=(vf[0]&0x7f)|(polarity<<7)
    txreg(2,channel,vf)

def setFilter(FS=0xfa0,channel=4):
    """
    set filter: refer to AD7714s manual
    channel irrelevant
    """
    # read unchanged values from filter high register
    vf=rxreg(2,channel)
    vf=(vf[0]&0xf0)|(FS>>8)
    txreg(2,channel,vf)
    # write to filter low register
    vf=FS&0xff
    txreg(3,channel,vf)

def fsync(channel,f_sync):
    # f_sync is 0 or 1
    # 1 sampling stopped
    # 0 sampling started
    # mode 0 means normal mode (not calibrating mode)
    setMode(channel,MD=0,FSYNC=f_sync)

def calcSamp2Filt(samplingrate):
    """
    a small calculator to help the user in python's interpreter mode
    careful in normal operation, not every sampling rates are supported
    """
    filt=CLK/128./samplingrate
    print("FS has to be",filt,"rounded",round(filt))
    print("in hex:",hex(int(round(filt))))
    if round(filt)<19:
        print("...but this is too low!")
    elif round(filt)>4000:
        print("...but this is too high!")
    else:
        print("the resulting sampling rate is ",CLK/128./int(round(filt)))
    return int(round(filt))    

def info():
    """
    lists content of AD7714's registers
    for test purposes
    """
    print("registers of AD7714:")
    print()
    mode=rxreg(1,0)
    MD=(mode[0]>>5)&7
    G=(mode[0]>>2)&7
    BO=(mode[0]>>1)&1
    FSYNC=(mode[0])&1
    print("mode register\t\tvalue\t",hex(mode[0]))
    print("mode\t\t\tMD\t",MD)
    print("gain\t\t\tG\t",G)
    print("\tmultiplier",2**G)
    print("burnout current\t\tBO\t",BO)
    print("filter synchronization\tFSYNC\t",FSYNC)
    print()
    filth=rxreg(2,0)
    filtl=rxreg(3,0)
    BU=(filth[0]>>7)&1
    WL=(filth[0]>>6)&1
    BST=(filth[0]>>5)&1
    CLKDIS=(filth[0]>>4)&1
    FS=((filth[0]&0xf)<<8)|filtl[0]
    print("filter high register\tvalue\t",hex(filth[0]))
    print("filter low register\tvalue\t",hex(filtl[0]))
    print("bi/unipolar operation\t/B_U\t",BU)
    print("word length\t\tWL\t",WL)
    print("\tword length",16+8*WL)
    print("master clk disable\tCLKDIS\t",CLKDIS)
    print("filter selection\tFS\t",FS)
    print("\tfirst notch freq",(CLK/128./FS),"Hz")
    print()
    print("zero-scale calibration registers")
    zs=[]
    for i in range(3):
        zs.append(rxreg(6,i))
        zs[i]=(zs[i][0]<<16)+(zs[i][1]<<8)+zs[i][2]
        print("\t",i,"\t",zs[i],"\t",hex(zs[i]))
    print()
    print("full-scale calibration registers")
    fs=[]
    for i in range(3):
        fs.append(rxreg(7,i))
        fs[i]=(fs[i][0]<<16)+(fs[i][1]<<8)+fs[i][2]
        print("\t",i,"\t",fs[i],"\t",hex(fs[i]))


def getRoundingFactor(lsb):
    # rounding factor is used for rounding reasonably
    return 10**(-1*round(math.log(lsb)/math.log(10)-1))

def calcHeaderString():
    """
    derive headerstring from config arrays
    NAME array determines which channels to use
    """
    global Objekt
    global NAME
    global KEY
    global UNIT
    global SCALE
    global GAIN
    global allvalues
    global channellist

    namelist = []
    keylist =[]
    unitlist = []
    Objekt.rfactorlist = []
    Objekt.factorlist = []
    channellist = []
 
    for i,name in enumerate(NAME):
        if NAME[i]:
            namelist.append(name)
            keylist.append(KEY[i])
            unitlist.append(UNIT[i])
            if WL:
                lsb = 2**(GAIN-24)* 5 * SCALE[i]
            else:
                lsb = 2**(GAIN-16)* 5 * SCALE[i]
            rfactor = getRoundingFactor(lsb)
            Objekt.rfactorlist.append(rfactor)
            factor = 1
            if rfactor > 1.:
                factor = int(rfactor)
            Objekt.factorlist.append(factor)
            channellist.append(i)
            allvalues.append(9999)
    l = len(namelist)
    #packcode = '6hLlllllll'
    # one l for each channel (l stands for long in C language, see python struct)
    # 6hL makes room for 6h: Y M D h min s L: milliseconds
    packcode = '6hL' + 'l'*l
    Objekt.packcode = packcode

    sensorid = Objekt.sensordict['sensorid']
    # bracketstring = '[{},{},{},{},{},{},{}]'
    bracketstring = '[{}' + ',{}'*(l-1)  + ']'
    nobracketstring = '{}' + ',{}'*(l-1)  # TODO needed for keys?

    # namelist = ['pseudo16','pseudo26','pseudo36','pseudo46','full12','full34','full56']
    # cast list to tupel: (don't know why like this..)
    namelist = (*namelist,)
    #headernames = '[{},{},{},{},{},{},{}]'.format('pseudo16','p26','p36','p46','full12','f34','f56')
    # this * asterix is very important!
    headernames = bracketstring.format(*namelist)

    # e.g. key Tupel: 'var1,var2,var3,var4,var5,dx,dy'
    keylist = (*keylist,)
    #headerkeys = nobracketstring.format(*keylist)
    headerkeys = bracketstring.format(*keylist)

    # headerunits = '[{},{},{},{},{},{},{}]'.format('mV','mV','mV','mV','mV','mV','mV')
    unitlist = (*unitlist,)
    headerunits = bracketstring.format(*unitlist)
    
    # headerfactors = '[{},{},{},{},{},{},{}]'.format(1000,1000,1000,1000,1000,1000,1000)
    factorlist = (*Objekt.factorlist,)
    headerfactors = bracketstring.format(*factorlist)

    header = "# MagPyBin %s %s %s %s %s %s %d" % (sensorid, headerkeys, headernames, headerunits, headerfactors, packcode, struct.calcsize(packcode))

    return header

def mySettings():
    """
    used in __init__ of class AD7714Protocol
    and for test purposes
    """
    global WL
    global POL
    global FILTER
    global GAIN
    # setGain(4,0) same GAIN for all channels
    setGain(4, GAIN)
    # setWL: wordlength 0:16bit, 1:24bit
    setWL(WL)
    # set polarity: 0:bipolar, 1:unipolar
    setPol(POL)
    # setFilter(5,0xfa0) defines the sampling rate, in this example the minimal
    # setFilter depends on system clock, see calcSamp2Filt
    setFilter(FILTER)

def myCalibration():
    """
    called by interrupt routine
    """
    global CAL
    global CALMODE
    global OFFSETX
    global OFFSETY
    global OFFSETZ
    global FULLSCALEX
    global FULLSCALEY
    global FULLSCALEZ
    global channellist
    global currentchannel
    channel = channellist[currentchannel]

    if CALMODE == 0:
        # get constants from file

        # Register RS 6 .. Zero-Scale Cal. Reg.
        # Register RS 7 .. Full-Scale Cal. Reg.
        # Pseudo and Fully Differential channels use same Registers
        # see data sheet
        #  pseudo16 - pseudo36 same as full12 - full34
        #  pseudo36 = pseudo46 (Z-calibration registers)
        #  (pseudo56 is the same as full56, so Z as well)
        txreg(6,4,OFFSETX)
        txreg(6,5,OFFSETY)
        txreg(6,6,OFFSETZ)
        txreg(7,4,FULLSCALEX)
        txreg(7,5,FULLSCALEY)
        txreg(7,6,FULLSCALEZ)
        # "calibration" finished
        return True
    else:
        calibration_mode = CAL[channel]
        setMode(channel,calibration_mode)
        # preparing for calibrating next channel 
        currentchannel = currentchannel + 1
        if currentchannel == len(channellist):
            currentchannel = 0
            return True
        else:
            return False


def interruptRead(s):
    """
    interrupt routine of class AD7714Protocol
    triggered by AD7714 /DRDY signal
    """
    # at first get the time...
    currenttime = datetime.utcnow()

    global Objekt
    global SCALE
    global DIFF
    global GAIN
    global POL
    global WL

    global allvalues
    global channellist
    global currentchannel
    channel = channellist[currentchannel]

    # TIME TO COMMUNICATE!
    global int_comm
    if int_comm == "myCalibration":
        finished = myCalibration()
        if finished:
            int_comm = "ok"
        return
    if int_comm == "info":
        info()
        int_comm = "ok"
        return
    if int_comm == "ok":
        # start sampling with first channel
        int_comm = "read"
        # reset FSYNC to change channel
        fsync(channel,1)
        # trigger conversion of next channel
        fsync(channel,0)
        return
    if not int_comm == "read":
        print ('error in interruptRead')
        return

    # collect samples
    # read from data register
    arrvalue=rxreg(5,channel)
    if len(arrvalue)==2:
        # 16 -> 24bit
        arrvalue.append(0)
    if WL:
        intvalue=(arrvalue[0]<<16) | (arrvalue[1]<<8) | arrvalue[2]
        voltvalue=float(intvalue*5)/2**24 - 2.500 + 2.5*POL
    else:
        intvalue= (arrvalue[0]<<8) | arrvalue[1]
        voltvalue=float(intvalue*5)/2**16 - 2.500 + 2.5*POL
    voltvalue = voltvalue / 2**GAIN

    scale = SCALE[channellist[currentchannel]]
    diff = DIFF[channellist[currentchannel]]
    rfactor = Objekt.rfactorlist[currentchannel]
    factor = Objekt.factorlist[currentchannel]
    # calculate value in the desired unit
    # and round reasonably depending on the least significant bit LSB
    value = round (voltvalue * scale * rfactor) / rfactor + diff
    try:
        allvalues[currentchannel] = value 
    except:
        print('ad7714protocol: could not read from channel')
        print(channel)

    if len(channellist) > 1:
        # prepare next sample
        # reset FSYNC to change channel
        fsync(channel,1)
        currentchannel = currentchannel + 1
        if currentchannel == len(channellist):
            currentchannel = 0
        channel = channellist[currentchannel]
        # trigger conversion of next channel
        fsync(channel,0)
    else:
        # in one channel mode AD7714 triggers by itself
        pass
    # if all channels are converted
    if currentchannel == 0:
        #timestamp=datetime.strftime(currenttime, "%Y-%m-%d %H:%M:%S.%f")
        timestamp = datetime2array(currenttime)
        darray = timestamp
        for chan,channel in enumerate(channellist):
            # TODO better
            darray.append(int(round(allvalues[chan]*Objekt.factorlist[chan])))

        # TO FILE 
        packcode = Objekt.packcode
        sensorid = Objekt.sensordict['sensorid']
        header = Objekt.header
        data_bin = struct.pack(packcode,*darray)
        filedate = datetime.strftime(datetime(darray[0],darray[1],darray[2]), "%Y-%m-%d")
        if not Objekt.confdict.get('bufferdirectory','') == '':
            acs.dataToFile(Objekt.confdict.get('bufferdirectory'), sensorid, filedate, data_bin, header)
    
        # VIA MQTT
        # instead of external program file TODO: better!
        #def sendData(self, sensorid, data, head, stack=None):
        #sendData.sendData(Objekt,sensorid, ','.join(list(map(str,darray))), header)
        data=','.join(list(map(str,darray)))
        head=header
        # TODO: implement stack correctly!
        stack=1

        topic = Objekt.confdict.get('station') + '/' + sensorid
        senddata = False
        if not stack:
            stack = int(Objekt.sensordict.get('stack'))
        coll = stack

        if coll > 1:
            Objekt.metacnt = 1 # send meta data with every block
            if Objekt.datacnt < coll:
                Objekt.datalst.append(data)
                Objekt.datacnt += 1
            else:
                senddata = True
                data = ';'.join(Objekt.datalst)
                Objekt.datalst = []
                Objekt.datacnt = 0
        else:
            senddata = True

        if senddata:
                if Objekt.count == 0:
                    # get all values initially from the database
                    #add = "SensoriD:{},StationID:{},DataPier:{},SensorModule:{},SensorGroup:{},SensorDecription:{},DataTimeProtocol:{}".format( sensorid, self.confdict.get('station',''),self.sensordict.get('pierid',''), self.sensordict.get('protocol',''),self.sensordict.get('sensorgroup',''),self.sensordict.get('sensordesc',''), self.sensordict.get('ptime','') )
                    #self.client.publish(topic+"/dict", add, qos=self.qos)
                    Objekt.client.publish(topic+"/meta", head, qos=Objekt.qos)
                    if Objekt.debug:
                        log.msg("  -> DEBUG - Publishing meta --", topic, head)
                Objekt.client.publish(topic+"/data", data, qos=Objekt.qos)
                if Objekt.debug:
                    log.msg("  -> DEBUG - Publishing data")
                Objekt.count += 1
                if Objekt.count >= Objekt.metacnt:
                    Objekt.count = 0



def readData(channel=4):
    """
    only for test purposes (i.e. in def show)
    not used in normal mode
    """
    GPIO.wait_for_edge(DRDY, GPIO.FALLING)
    return rxreg(5,channel)

def show(channel=4,samples=1):
    """
    shows some samples, for test purposes
    """
    values=[]
    for i in range(samples):
        arrvalue=readData(channel)
        if len(arrvalue)==2:
            # 16 -> 24bit
            arrvalue.append(0)
        print(arrvalue)
        intvalue=(arrvalue[0]<<16) | (arrvalue[1]<<8) | arrvalue[2]
        print(intvalue)
        voltvalue=float(intvalue)/2**24*5-2.5
        print(voltvalue)
        values.append(voltvalue)
    return(values)

def stat(values):
    """
    for test purposes, plausibility of values
    
    """
    mean=0
    for v in values:
        mean=mean+v
    mean=mean/len(values)
    var=0
    for v in values:
        var=var+(v-mean)**2
    var=var/len(values)
    print("mean value",mean)
    print("variance",var)

def seeDRDY():
    """
    only for test purposes
    """
    t=time.time()+1
    i=0
    while time.time()<t:
        GPIO.wait_for_edge(DRDY, GPIO.FALLING)
        i = i + 1
    print("difftime: ",t-time.time())
    print("samples per second: ",i)

print("ad7714protocol")



class ad7714Protocol():
    """
    The AD7714 protocol for reading from the AD converter over spi
    """

    def __init__(self, client, sensordict, confdict):

        # set defaults for mqtt
        #sendData.setDefaults(self, client, sensordict, confdict)
        self.qos = 0
        self.debug = False
        self.client = client
        self.sensordict = sensordict
        self.confdict = confdict
        # variables for broadcasting via mqtt:
        self.count=0
        self.datalst = []
        self.datacnt = 0
        self.metacnt = 10
        self.ad7714conf = acs.GetConf2(self.confdict.get('ad7714confpath'))
        # variables needed in defs and interrupt routine        
        self.packcode = ''
        self.rfactorlist = []
        self.factorlist = []

        global Objekt
        Objekt=self

        global NAME
        global KEY
        global UNIT
        global SCALE
        global DIFF
        global CAL
        # get constants for used channels
        #   nameofchannel: 1, 2, 3, 4, X, Y, Z
        for i in range(7):
            # NAME is the name of the signal
            NAME[i] = self.ad7714conf.get('NAME_'+nameofchannel[i])
            # magpy keys (x, y, ... var1, var2, ...)
            KEY[i] = self.ad7714conf.get('KEY_'+nameofchannel[i])
            # unit for each channel
            UNIT[i] = self.ad7714conf.get('UNIT_'+nameofchannel[i])
            # scale values e.g. SCALE_X = 1000 (mV/V) would yield values in mV
            try:
                SCALE[i] = float(self.ad7714conf.get('SCALE_'+nameofchannel[i]))
            except:
                SCALE[i] = None
            # offset e.g. measurement = SCALE_X * value + DIFF_X
            try:
                DIFF[i] = float(self.ad7714conf.get('DIFF_'+nameofchannel[i]))
            except:
                DIFF[i] = None
            # calibration mode for each channel if used (0-7)
            try:
                CAL[i] = int(self.ad7714conf.get('CAL_'+nameofchannel[i]))
            except:
                CAL[i] = None
        global GAIN
        GAIN = int(self.ad7714conf.get('GAIN'))
        global WL
        WL = int(self.ad7714conf.get('WL'))
        global POL
        POL = int(self.ad7714conf.get('POL'))
        global FILTER
        FILTER = int(str(self.ad7714conf.get('FILTER')),16)
        global CALMODE
        CALMODE = int(self.ad7714conf.get('CALMODE'))
        global OFFSETX
        OFFSETX = int(str(self.ad7714conf.get('OFFSETX')),16)
        global OFFSETY
        OFFSETY = int(str(self.ad7714conf.get('OFFSETY')),16)
        global OFFSETZ
        OFFSETZ = int(str(self.ad7714conf.get('OFFSETZ')),16)
        global FULLSCALEX
        FULLSCALEX = int(str(self.ad7714conf.get('FULLSCALEX')),16)
        global FULLSCALEY
        FULLSCALEY = int(str(self.ad7714conf.get('FULLSCALEY')),16)
        global FULLSCALEZ
        FULLSCALEZ = int(str(self.ad7714conf.get('FULLSCALEZ')),16)

        self.header = calcHeaderString()
        print('calculated header:')
        print(self.header)
        
        # reset AD7714
        print('AD7714Protocol: resetting AD7714...')
        reset()
        time.sleep(0.1)

        # store settings into AD7714's registers
        mySettings()

        # GPIO.add_event_detect(DRDY, GPIO.FALLING, callback = AD7714Protocol.interruptReadObj(self))
        # did never work...
        GPIO.add_event_detect(DRDY, GPIO.FALLING, callback = interruptRead)

        global int_comm
        # zero calibration
        int_comm = "myCalibration"
        if self.debug:
            print ('myCalibration...')
        while not int_comm == "ok":
            # wait for interrupt routine
            time.sleep(0.001)
        # display AD7714s register values
        int_comm = "info"
        while not int_comm == "ok":
            time.sleep(0.001)

        print("connection to AD7714 via SPI initialized")

