"""
ad7714protocol version 1.1
for board v0.1 and v0.2

Purpose:
    reads data from an AD7714 (Analog Devices)

Requirements:
    SPI interface on a RaspberryPi3
    
Called by:
    acquisition from magpy
"""

from __future__ import print_function

############    user definitions    ############

# select GAIN between 0 and 7
#  nr    amplification
#   0 .. 1
#   1 .. 2
#   2 .. 4
#   ......
#   6 .. 64
#   7 .. 128

GAIN = 1

###### please don't edit beyond this line ######


import struct
from datetime import datetime

from twisted.python import log
from martas.core import acquisitionsupport as acs
import time

# Raspberry Pi specific
try:
    import spidev
    import RPi.GPIO as GPIO
except:
    log.msg('sorry, equipment not prepared to communicate over SPI')
    raise

# TODO brauch ich das? und wenn, ab ins acs!
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
# *** board v0.2 ***
CLK=2457600
print("system clock", CLK)
# *** board v0.1 ***
# using channel 5: differential input AIN3-AIN4 (pin9-pin10)
#CHANNEL = 5
# *** board v0.2 ***
# using channel 4: differential input AIN1-AIN2 (pin7-pin8)
CHANNEL = 4
# wordlength 16bit:0 24bit:1
BIT = 1
# Filter sets sampling rate. Depends on system clock
FILTER = 0x0c0

# init watchdog
watchdog = {}
watchdog['count_repetitions'] = 0
watchdog['init_max_rep'] = 20
watchdog['max_repetitions'] = watchdog['init_max_rep']
watchdog['oldvalue'] = 999999

global int_comm
int_comm = ""

def reset():
    """
    reset AD7714
    AD7714 requires minimum 100ns on the /RESET pin
    RPi's sleep is not so fast anyhow...
    """
    GPIO.output(RESET,GPIO.LOW)
    # time.sleep(0.0000001)
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

def setMode(channel=4,MD=0):
    """
    set mode: refer to AD7714s manual
    """
    # read unchanged values from mode register
    vm=rxreg(1,channel)
    vm=(vm[0]&0x1f)|(MD<<5)
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
    ensure not to disturb SPI communication!
    (not yet implemented)
    """
    #GPIO.wait_for_edge(DRDY, GPIO.RISING)
    # TODO war naechste Zeile Grund fuer Probleme?
    #GPIO.wait_for_edge(DRDY, GPIO.FALLING)
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

def setFilter(FS=0xfa0,channel=4):
    """
    set filter: refer to AD7714s manual
    """
    # read unchanged values from filter high register
    vf=rxreg(2,channel)
    vf=(vf[0]&0xf0)|(FS>>8)
    txreg(2,channel,vf)
    # write to filter low register
    vf=FS&0xff
    txreg(3,channel,vf)

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

def mySettings():
    """
    used in __init__ of class AD7714Protocol
    and for test purposes
    """
    # using channel 5: differential input AIN3-AIN4 (pin9-pin10)
    # setGain: G = 2^(given value) e.g. setGain(channel=5,G=1) results in an amplification of 2^1 = 2
    setGain(CHANNEL,GAIN)
    # setWL: wordlength 0:16bit, 1:24bit
    setWL(BIT)
    # setFilter(5,0xfa0) defines the sampling rate, in this example the minimal
    # setFilter depends on system clock, see calcSamp2Filt
    setFilter(FILTER)

def myCalibration():
    """
    zero calibration removes offset
    """
    # "self calibration" 
    # mode 1, see AD7714 manual, zero scale and full scale cal internally 
    # - apparently not good enough
    #setMode(5,1)
    # mode 5: permanent calibration 
    # - not so "beautiful", similar apearance not before setting double sampling rate 
    #setMode(5,5)
    # mode 4: zero scale cal from input (should be stable), full scale cal internally
    # - should be best, but mode 2 is better
    # mode 2: only zero scale cal from input (should be stable)
    # - best for offset
    setMode(CHANNEL,2)
    # doing zero scale cal again, especially when the sensor is not locked
    time.sleep(0.3)
    setMode(CHANNEL,2)
    # immediate communication would crash settings --> TODO better sync!
    time.sleep(0.01)

def interruptRead(s):
    """
    interrupt routine of class AD7714Protocol
    triggered by AD7714 /DRDY signal
    """
    # at first get the time...
    currenttime = datetime.utcnow()
    # read from data register
    arrvalue=rxreg(5,CHANNEL)
    if len(arrvalue)==2:
        # 16 -> 24bit
        arrvalue.append(0)
    intvalue=(arrvalue[0]<<16) | (arrvalue[1]<<8) | arrvalue[2]
    voltvalue=float(intvalue)/2**24*5-2.5
    # mV better for display
    voltvalue=voltvalue*1000
    
    # TIME TO COMMUNICATE!
    global int_comm
    if int_comm == "mySettings":
        mySettings()
        int_comm = "ok"
    if int_comm == "myCalibration":
        myCalibration()
        int_comm = "ok"
    if int_comm == "info":
        info()
        int_comm = "ok"
    

    # watchdog
    global watchdog
    global Objekt
    if watchdog['oldvalue'] == 999999:
        print('watchdog active')
    if watchdog['oldvalue'] == intvalue:
        watchdog['count_repetitions'] = watchdog['count_repetitions'] + 1
    else:
        if watchdog['count_repetitions'] > 5:
            # avoid a lot of log entries - filter double and triple values in a row
            print('watchdog resetted, count_repetitions:',watchdog['count_repetitions'],'oldvalue:',watchdog['oldvalue'],'intvalue:',intvalue)
        watchdog['count_repetitions'] = 0
        watchdog['max_repetitions'] = watchdog['init_max_rep']
    if watchdog['count_repetitions'] == watchdog['max_repetitions']:
        # probably hung up, too many same values
        print('watchdog ad7714protocol:')
        print('  ',watchdog['max_repetitions'],'same values (intvalue:',intvalue,') in one row - hung up?')
        print('  trying to reset AD7714...')
        # sending LOW to /RESET pin
        reset()
        time.sleep(0.01)
        # loading settings
        mySettings()
        # zero calibration
        myCalibration()
        watchdog['max_repetitions'] = watchdog['max_repetitions'] * 2
        watchdog['count_repetitions'] = 0
    watchdog['oldvalue'] = intvalue
    packcode = "6hLl"
    sensorid = Objekt.sensordict['sensorid']
    header = "# MagPyBin %s %s %s %s %s %s %d" % (sensorid,'[var1]','[U]','[mV]','[1000]',packcode,struct.calcsize(packcode))
    #timestamp=datetime.strftime(currenttime, "%Y-%m-%d %H:%M:%S.%f")
    timestamp = datetime2array(currenttime)
    darray = timestamp
    darray.append(int(round(voltvalue*1000)))


    # TO FILE 
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


# word length should be set in __init__ of class AD7714Protocol
# WL=0: 16bit, WL=1: 24bit
# here WL is set by setWL reading the AD7714 register (default after reset is 0)
# this guaranties that the global variable WL has the correct value
setWL()
# alternatively calculate FILTER from the sampling rate, careful!
# this will override the setting from before:
#FILTER = calcSamp2Filt(15)
print("setup done")



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


        # reset AD7714
        print('AD7714Protocol: resetting AD7714...')
        reset()
        time.sleep(0.1)


        # display first samples
        # TODO too dangerous:
        #show(channel=CHANNEL,samples=3)
        # due to difficulties setting up an interrupt routine within this object...
        # TODO avoid global variables
        global Objekt
        Objekt=self
#       GPIO.add_event_detect(DRDY, GPIO.FALLING, callback = AD7714Protocol.interruptReadObj(self))
        GPIO.add_event_detect(DRDY, GPIO.FALLING, callback = interruptRead)
        
        # *** indirectly TODO make it better!
        # load settings, zero calibration
        #mySettings()
        global int_comm
        int_comm = "mySettings"
        while not int_comm == "ok":
            time.sleep(0.001)
        # zero calibration
        #myCalibration()
        int_comm = "myCalibration"
        while not int_comm == "ok":
            time.sleep(0.001)
        # display AD7714s register values
        #info()
        #int_comm = "info"
        while not int_comm == "ok":
            time.sleep(0.001)
        # ***

        print("connection to AD7714 via SPI initialized")

