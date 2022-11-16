#!/usr/bin/env python
"""
a script to communicate with ObsDAQ assuming:
    connected to a PalmAcq
    PalmAcq is in Transparent mode (see manual)
    supported only baud rate 57600
"""
from __future__ import print_function
import sys, os, socket, getopt
import serial
import struct, binascii, re, csv
from datetime import datetime, timedelta
from matplotlib.dates import date2num, num2date
import numpy as np
import time

# Relative import of core methods as long as martas is not configured as package
scriptpath = os.path.dirname(os.path.realpath(__file__))
coredir = os.path.abspath(os.path.join(scriptpath, '..', 'core'))
sys.path.insert(0, coredir)
from acquisitionsupport import GetConf2 as GetConf2


# settings for PalmDaq
PORT = '/dev/ttyUSB0'
BAUDRATE='57600'
eol = '\r'


# settings for ObsDAQ:

#   baudrate 19200 is the default after power on
#   test e.g. by minicom after plugged in

# default clock frequency. There'll be a warning if it is different
    #   98 .. 9.8304MHz
FCLK = '98'

# set 24-bit channel configuration
    # assuming crystal frequency is 9.8304MHz
    # command  $AAnWS0201ccdd 
    # cc ... Range mode (gain)
    #   02 ...  +/-10V
    #   03 ...  +/-5V
    #   04 ...  +/-2.5V
CC = '02'
    # dd ... Data output rate (here examples, see Table 6 and Table 9)
    #   03 .. 3.2 Hz
    #   13 .. 6.4 Hz
    #   23 .. 12.8 Hz
    #   33 .. 19.2 Hz
    #   43 .. 32.0 Hz
    #   53 .. 38.4 Hz
    #   63 .. 64 Hz
    #   72 .. 76.8 Hz
    #   82 .. 128 Hz
    #   92 .. 640 Hz
    #   A1 .. 1280 Hz

DD = '23'
#DD = '63'

# setting internal trigger timing
    # command $AAPPeeeeffff
    # eeee ... triggering interval
    # ffff ... low-level time
    # recommended by Mingeo (9.8304MHz quartz crystal, see Table 9)
    #   DD EEEE FFFF Samples/s FilterFrequency
    #   63 0BFF 026D 50Hz      64Hz 
    #   72 09FF 01FD 60Hz      76.8Hz 
    #   82 05FF 011D 100Hz     128Hz 
    #   92 04AF 038D 128Hz     640Hz 
    #   92 03FF 02DD 150Hz     640Hz 
    #   92 02FF 01DD 200Hz     640Hz
EEEE = '3C00'
FFFF = '0600'
#EEEE = '0BFF'
#FFFF = '026D'

# program offset calibration constants
    # command $AAnWOaaaaaa
#OFFSET = ['','','']
OFFSET = ['FFF19A','FFF41B','FFF70C']

# program full-scale calibration constants
    # command $AAnWFffffff
#FULLSCALE = ['','','']
FULLSCALE = ['3231C0','32374B','323A7E']

# ----------------------------------
# please don't edit beyond this line
# ----------------------------------

global ser
global QUIET
QUIET = False

def lineread(ser,eol):
            # FUNCTION 'LINEREAD'
            # Does the same as readline() plus timeout
            ser_str = ''
            timeout = time.time()+2
            if sys.version_info >= (3, 0):
                eol=eol.encode('ascii')
                while True:
                    byte = ser.read()
                    if byte == eol:
                        break
                    if time.time() > timeout:
                        print ('Timeout')
                        break
                    try:
                        ser_str += byte.decode('ascii')
                    except:
                        print('obsdaq.py: decode error, got '+str(byte))

            else:
                while True:
                    char = ser.read()
                    if char == eol:
                        break
                    if time.time() > timeout:
                        print ('Timeout')
                        break
                    ser_str += char
            return ser_str

def send_command(ser,command,eol,hex=False):
    #command = eol+command+eol
    command = command+eol
    #print 'Command:  %s \n ' % command.replace(eol,'')
    sendtime = date2num(datetime.utcnow())
    #print "Sending"
    if sys.version_info >= (3, 0):
        ser.write(command.encode('ascii'))
    else:
        ser.write(command)
    #print "Received something - interpretation"
    response = lineread(ser,eol)
    #print "interprete"
    receivetime = date2num(datetime.utcnow())
    meantime = np.mean([receivetime,sendtime])
    #print "Timediff", (receivetime-sendtime)*3600*24
    return response, num2date(meantime).replace(tzinfo=None)


def command(call):
    global ser
    global QUIET
    if not QUIET:
        print(call)
    answer, actime = send_command(ser,call,eol)
    if not QUIET:
        print(answer)
    return answer


def main(argv):
    try:
        opts, args = getopt.getopt(argv,"hvm:cn:f:apsodiq",[])
    except getopt.GetoptError:
        print ('unknown option')
        sys.exit(2)

    global ser
    port = PORT
    baudrate = BAUDRATE
    cc = CC
    dd = DD
    eeee = EEEE
    ffff = FFFF
    offset = OFFSET
    fullscale = FULLSCALE
    for opt, arg in opts:
        if opt == '-h':
            print ('-------------------------------------')
            print ('Description:')
            print ('Sending data to ObsDAQ via PalmAcq')
            print ('  therefore it is necessary to bring PalmAcq in Transparent mode')
            print ('  i.e. by using the palmacq.py script:')
            print ('  python palmacq.py -t')
            print ('-------------------------------------')
            print ('Usage:')
            print ('obsdaq.py -q -v -m config-file -c -n channel -f channel -a -p -s -o -d -i')
            print ('-------------------------------------')
            print ('Options:')
            print ('-v          : show version of ObsDAQ and quit')
            print ('-m          : MARTAS compatible config file')
            print ('')
            print ('-c          : define calibration constants')
            print ('-n channel  : perform an offset system calibration (input must be 0) of channel 1-3')
            print ('-f channel  : perform a full-scale calibration (input must be maximum) of channel 1-3')
            print ('')
            print ('-a          : start acquisition (calibrate first!)')
            print ("-p          : exit free run or triggered mode - stop acquisition")
            print ('-s          : show output from serial line')
            print ('-o          : show the formatted output')
            print ('')
            print ('-d          : show definitions made in the code resp. config file')
            print ('-i          : show info about ObsDAQ settings')
            print ("-q          : quiet: don't show commands and answers. Has to be first option.")
            print ('-------------------------------------')
            print ('Examples:')
            print ('python obsdaq.py -t')
            sys.exit()
        if opt in ("-m"):
            configfile = os.path.abspath(arg)
            conf = GetConf2(configfile)
            port = conf.get('port')
            baudrate = conf.get('baudrate')
            cc = str(conf.get('CC')).zfill(2)
            dd = str(conf.get('DD')).zfill(2)
            eeee = str(conf.get('EEEE')).zfill(4)
            ffff = str(conf.get('FFFF')).zfill(4)
            offset = [str(conf.get('OFFSETX')),str(conf.get('OFFSETY')),str(conf.get('OFFSETZ'))]
            fullscale = [str(conf.get('FULLSCALEX')),str(conf.get('FULLSCALEY')),str(conf.get('FULLSCALEZ'))]

        ser = serial.Serial(port, baudrate=baudrate , parity='N', bytesize=8, stopbits=1, timeout=2)

        # some calculations
        FCLKdic = {'98':9.8304e6,'92':9.216e6,'76':7.68e6}
        fclkFreq = FCLKdic[FCLK]
        # factor for trigger timing parameters eeee and ffff
        micros = 64./fclkFreq
        CCdic = {'02':10.,'03':5.,'04':2.5}
        gain = CCdic[cc]
        DDdic = {'03':3.2,'13':6.4,'23':12.8,'33':19.2,'43':32.,'53':38.4,'63':64.,'72':76.8,'82':128.,'92':640.,'A1':1280.}
        # data output rate
        drate = DDdic[dd] * FCLKdic[FCLK] / FCLKdic['98']
        eeeeTime = int('0x'+eeee,16)*micros
        ffffTime = int('0x'+ffff,16)*micros

        if opt in ("-v", "--version"):
            answer = ser.read(10)
            if answer:
                print ('ObsDaq: it seems, that acquisition is in progress.')
                print ('ObsDaq: please stop acquisition using -p or --stop option first!')
                exit(2)
            print ('ObsDaq: Firmware version and firmware date')
            command('$01F')
            print ('ObsDaq: Module name (firmware version)')
            command('$01M')
        if opt in ("-q", "--quiet"):
            global QUIET
            QUIET = True
        if opt in ("-p", "--stop"):
            # stop acquisition
            print('ObsDaq: trying to stop acquisition...')
            command('#01ST')
            stopped = False
            while not stopped:
                # quick stop
                answer, actime = send_command(ser,'||||||||||||||||||||||','')
                if answer:
                    print ('Answer from ObsDAQ:')
                    print (answer)
                    print ('ObsDaq: please wait!')
                    for i in range(100):
                        ser.write('|||||||||||||||||||||||||||||||||||\r')
                else:
                    print ('ObsDaq: stopped')
                    stopped = True    
            # stop free run or triggered mode, enter idle mode
            command('#01ST')
        elif opt in ("-i", "--info"):
            answer = ser.read(10)
            if answer:
                print ('ObsDaq: it seems, that acquisition is in progress.')
                print ('ObsDaq: please stop acquisition using -p or --stop option first!')
                exit(2)
            print ('Information - please refer to ObsDAQ manual')
            print ('Serial number')
            sn = command('$01SN')
            sn = sn.split('SN')[1]
            print ('S/N: '+sn)
            # turn off triggering to enable getting 24 bit configuration
            print ('turning off triggering')
            command('#01PP00000000')
            # wait a second
            time.sleep(1)
            print ('baud rate code')
            command('$012')
            print ('quarz frequency')
            ans = command('$01QF')
            ans = ans.split('R')[1]
            if not ans == FCLK:
                print ('WARNING: this code is not written for this crystal frequency.')
                print ('   please adopt python code!')
                print ('')
            print ('first EEPROM command')
            print ('  *ERR indicates there is no EEPROM programmed for autostart')
            command('$01IR0')
            print ('24bit channel 0 config') 
            command('$010RS')
            print ('24bit channel 1 config')
            command('$011RS')
            print ('24bit channel 2 config') 
            command('$012RS')
            
            # get 24-bit channel configuration
            print ('channel configuration')
            command('$010RS')
            command('$011RS')
            command('$012RS')
            time.sleep(1)

            # get offset calibration constants
            print ('offset calibration constants')
            command('$010RO')
            command('$011RO')
            command('$012RO')

            # get full-scale calibration constants
            print ('full scale calibration constants')
            command('$010RF')
            command('$011RF')
            command('$012RF')

        elif opt in ("-s", "--show"):
            while True:
                print (lineread(ser,eol))

        elif opt in ("-c", "--calib"):
            answer = ser.read(10)
            if answer:
                print ('ObsDaq: it seems, that acquisition is in progress.')
                print ('ObsDaq: please stop acquisition using -p or --stop option first!')
                exit(2)

            print ('ObsDaq: turning off triggering')
            command('#01PP00000000')
            # wait a second
            time.sleep(1)

            print ('ObsDaq: setting 24-bit channel configuration')
            # cc=02..+/-10V
            # dd=23..12.8Hz
            command('$010WS0201'+cc+dd)
            time.sleep(1)
            command('$011WS0201'+cc+dd)
            time.sleep(1)
            command('$012WS0201'+cc+dd)
            time.sleep(1)

            # calibration constants
            for i in range(3):
                if offset[i]:
                    print ('programming given offset calibration constant for channel '+str(i+1))
                    command('$01'+str(i)+'WO'+offset[i])
            for i in range(3):
                if fullscale[i]:
                    print ('programming given full-scale calibration constant for channel '+str(i+1))
                    command('$01'+str(i)+'WF'+fullscale[i])
            time.sleep(1)
            # execute an offset and full-scale self-calibration if necessary
            for i in range(3):
                if not offset[i] or not fullscale[i]:
                    print ('executing an offset and full-scale self-calibration for channel '+str(i+1))
                    command('$01'+str(i)+'WCF0')
                    print ('calibrating...')
                    # check calibration finished?
                    calfin = False
                    while not calfin:
                        time.sleep(0.5)
                        ans = command('$01'+str(i)+'RR')
                        ans = ans.split('R')[1]
                        if ans == '0':
                            print ('ObsDaq: finished calibration')
                            calfin = True
            
            # get 24-bit channel configuration
            print ('channel configuration')
            a=command('$010RS')
            b=command('$011RS')
            c=command('$012RS')
            if QUIET:
                print('\t'+a+'\t'+b+'\t'+c)
                accdd='\t+/-'+str(CCdic[a[7:9]])+'V  '+str(DDdic[a[9:11]])+'Hz'
                bccdd='\t+/-'+str(CCdic[b[7:9]])+'V  '+str(DDdic[b[9:11]])+'Hz'
                cccdd='\t+/-'+str(CCdic[c[7:9]])+'V  '+str(DDdic[c[9:11]])+'Hz'
                print(accdd+'\t'+bccdd+'\t'+cccdd)
            time.sleep(1)

            # get offset calibration constants
            print ('offset calibration constants')
            a=command('$010RO')
            b=command('$011RO')
            c=command('$012RO')
            if QUIET:
                print('\t'+a+'\t'+b+'\t'+c)

            # get full-scale calibration constants
            print ('full scale calibration constants')
            a=command('$010RF')
            b=command('$011RF')
            c=command('$012RF')
            if QUIET:
                print('\t'+a+'\t'+b+'\t'+c)

        elif opt in ("-n", "--offsetcal"):
            try:
                ch = int(arg)-1
                ch = str(ch)
            except:
                print ("channel must be in 1..3")
                exit(2)
            answer = ser.read(10)
            if answer:
                print ('it seems, that acquisition is in progress.')
                print ('please stop acquisition using -p or --stop option first!')
                exit(2)
            
            print ('turning off triggering')
            command('#01PP00000000')
            # wait a second
            time.sleep(1)

            print ('setting 24-bit channel configuration')
            # cc=02..+/-10V
            # dd=23..12.8Hz
            command('$01'+ch+'WS0201'+cc+dd)
            time.sleep(1)

            print ('performing offset calibration of channel '+arg)
            command('$01'+ch+'WCF3')
            time.sleep(1)
            print ('get the constants from python obsdac.py -i')

        elif opt in ("-f", "--fullscalecal"):
            try:
                ch = int(arg)-1
                ch = str(ch)
            except:
                print ("channel must be in 1..3")
                exit(2)
            answer = ser.read(10)
            if answer:
                print ('it seems, that acquisition is in progress.')
                print ('please stop acquisition using -p or --stop option first!')
                exit(2)
            
            print ('turning off triggering')
            command('#01PP00000000')
            # wait a second
            time.sleep(1)

            print ('setting 24-bit channel configuration')
            # cc=02..+/-10V
            # dd=23..12.8Hz
            command('$010WS0201'+cc+dd)
            time.sleep(1)
            command('$011WS0201'+cc+dd)
            time.sleep(1)
            command('$012WS0201'+cc+dd)
            time.sleep(1)

            print ('performing full-scale calibration of channel '+arg)
            command('$01'+ch+'WCF4')
            time.sleep(1)
            print ('get the constants from python obsdac.py -i')



        elif opt in ("-d", "--defs"):
            # show user settings human readable
            print ("Definitions for ObsDAQ made in this file:")
            print ('')
            print ('Clock frequency:')
            print ('FCLK:\t'+FCLK)
            print ('\t'+str(fclkFreq/1000000.)+'MHz')
            print ('Gain:')
            print ('CC:\t'+cc)
            print ('\t+/-'+str(gain)+'V')
            print ('Data output rate:')
            print ('DD:\t'+dd)
            print ('\t'+str(1./drate)+" s")
            print ('\t'+str(drate)+' Hz')
            print ('triggering interval')
            print ('EEEE:\t'+eeee)
            print ('\t'+str(eeeeTime)+" s")
            print ('\t'+str(1./eeeeTime)+" Hz")
            print ('low-level time')
            print ('FFFF:\t'+ffff)
            print ('\t'+str(ffffTime)+" s")
            print ('\t'+str(1./ffffTime)+" Hz")
            # there are limitations in choosing DD, EEEE and FFFF:
            if drate < 1./eeeeTime:
                print ('WARNING: Digital filter output rate is smaller than the triggering frequency!')
                print ('drate '+str(drate)+'Hz < 1./eeeeTime '+str(1./eeeeTime)+'Hz')
            if 1./drate - 0.0011 > eeeeTime:
                print ('WARNING: The difference of triggering interval and digital filter interval is smaller than 1.1ms!')
                print ('1./drate '+str(1./drate)+'s - 0.0011s > eeeeTime '+str(eeeeTime)+'s')
            if eeeeTime - ffffTime < 0.00019:
                print ('WARNING: Difference between triggering interval and low-level time is '+str(eeeeTime-ffffTime)+'!')
            if eeeeTime - ffffTime < 1./drate:
                print ('WARNING: Triggering interval - Low-level time is higher than the Digital filter output rate!')

        elif opt in ("-a", "--start"):
            print ('ObsDaq: starting acquisition')
            # set internal trigger timing (Table 9)
            command('#01PP'+eeee+ffff)
            # wait a second
            time.sleep(2)

            # start acquisition (plus supplementary data every second)
            command('#01CS')
            
            time.sleep(2)



if __name__ == "__main__":
    main(sys.argv[1:])
            






    
