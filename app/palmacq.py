#!/usr/bin/env python
"""
a small tool for PalmAcq and ObsDAQ (Mingeo, Hungary)
palmobs.py has these options:
    forwarding mode
        get data from obsDAQ
    command mode
        talk to Palmdacq
    transparent mode
        talk to ObsDAQ
    -h for help
"""

from __future__ import print_function
import sys, time, os, socket, getopt
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


# settings for PalmAcq
PORT = '/dev/ttyUSB0'
BAUDRATE='57600'
eol = '\r'
# since beginning of 2017 there are 18 leap seconds. PalmAcq starts with 15 leap seconds.
LEAPSECOND = 18

# settings for ObsDAQ
#   only baudrate 19200 supported here 
obsbaud = '19200'
escFromTranspChars = '\x00\x1b'
# GAINMAX is 10 for +/-10V (cc=02) and 5 for +/-5V (cc=03), see WS command
# needed only for option -o --output, no affect on data
GAINMAX = 10

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
                    ser_str += byte.decode('ascii')
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
        opts, args = getopt.getopt(argv,"hvm:tpfd:gsoiq",[])
    except getopt.GetoptError:
        print ('unknown option')
        sys.exit(2)

    global ser
    port = PORT
    baudrate = BAUDRATE
    targetleapsecond = LEAPSECOND
    for opt, arg in opts:
        if opt == '-h':
            print ('-------------------------------------')
            print ('Description:')
            print ('Sending data to PalmAcq resp. ObsDAQ')
            print ('-------------------------------------')
            print ('Usage:')
            print ('palmobs.py -q -v -t -m config-file -p -f -d [R/P/G] -g -s -i -o')
            print ('-------------------------------------')
            print ('Options:')
            print ('-v          : show version of PalmAcq and quit')
            print ('-m          : MARTAS compatible config file')
            print ('') 
            print ('-t          : enter Transparent mode')
            print ("-p          : exit Transparent mode, return to PalmAcq's Command mode")
            print ('-f          : enter Forwarding mode')
            print ('    -d R    : enter to ObsDAQ stream') 
            print ('    -d G    : enter to GPS info') 
            print ('    -d P    : enter to PPS') 
            print ('-g          : get GPS leap seconds')
            print ('') 
            print ('-s          : show output from serial line')
            print ('-o          : show the formatted output')
            print ('-i          : show info about PalmAcq settings')
            print ("-q          : quiet: don't show commands and answers. Has to be first option.")

            print ('-------------------------------------')
            print ('Examples:')
            print ('python palmobs.py -f R')
            sys.exit()
        if opt in ("-m"):
            configfile = os.path.abspath(arg)
            conf = GetConf2(configfile)
            port = conf.get('port')
            if 'LEAPSECOND' in conf:
                try:
                    targetleapsecond = int(conf.get('LEAPSECOND'))
                except:
                    print('could not read LEAPSECOND from config file '+configfile)

        ser = serial.Serial(port, baudrate=baudrate , parity='N', bytesize=8, stopbits=1, timeout=2)

        if opt in ("-q", "--quiet"):
            global QUIET
            QUIET = True
        if opt in ("-v", "--version"):
            # e.g. PALMACQ fw. v4.2.2 SM
            command('GV')
            # there come two lines, this cannot be handled here correctly
            print (lineread(ser,eol))
            # programmed not perfectly, so better quit here...
            #quit() 
        elif opt in ("-t", "--transparent"):
            # Transparent mode - this connects only to RS-485 port
            command('SP:R:'+obsbaud+',8,n,1,1')
            command('ST:R')
            a=command('SM:TRP')
            if a=='AM:TRP,001B':
                print ("PalmAcq: going to transparent mode...")
            else:
                # this does not mean, that the connection wasn't made
                # due to a timing problem
                print ("PalmAcq: probably no connection when trying to enter transparent mode")
            # print firmware version and firmware date
            command('$01F')
        elif opt in ("-p", "--program"):
            print ('PalmAcq: trying to enter command mode')
            # return from Transparent mode to PalmDAQ's Command mode
            if sys.version_info >= (3, 0):
                ser.write(escFromTranspChars.encode('ascii'))
            else:
                ser.write(escFromTranspChars)
            command('SM:CMD')
            # if in Forward mode, return from there, if not, doesn't matter
            command('SF:-')
        elif opt in ("-f", "--forward"):
            command('SF')
        elif opt in ("-d"):
            if arg == '':
                command('SF')
            elif arg in ['R','P','G','M','C']:
                command('SF:'+arg)
                print ('PalmAcq: entering forward mode "'+arg+'"')
            else:
                print ('PalmAcq: forward mode: SF: '+arg+': bad argument')
                quit()
        elif opt in ("-g", "--gpsinfo"):
            # GPS sends amount of leap seconds, 2017 it was 18
            leapsecond = 0
            while leapsecond < targetleapsecond:
                command('TP:G:L,$PMTK457*34')
                command('GB')
                result = ''
                while not result == ':END':
                    result = lineread(ser,eol)
                    l = result.split('$PMTK557,')
                    if len(l) == 2:
                        leapsecond = int(l[1].split('.')[0])
                        print ('PalmAcq: Leapsecond according to GPS signal: '+ str(leapsecond))
                time.sleep(2)
                if leapsecond < targetleapsecond:
                    print ('..trying once again')
        elif opt in ("-i", "--info"):
            command('GI:PORTS')
            command('GI:MC')
            command('GI:TF')
            command('GI:MLL')
            command('GI:BUFF')
            command('GI:SCH')
            command('GI:BC')
            command('GI:CRD')
            command('GI:GPS')
            quit()
        elif opt in ("-s", "--show"):
            while True:
                print (lineread(ser,eol))
            sys.exit()
        elif opt in ("-o", "--output"):
            while True:
                l = lineread(ser,eol).strip()
                if l.startswith(':R'):
                    # :R,00,200131.143739.617,*0259FEFFF1BFFFFCEDL:04AC11CC000B000B000B
                    # :R,00,YYMMDD.hhmmss.sss,*xxxxxxyyyyyyzzzzzzt:vvvvttttppppqqqqrrrr
                    d = l.split(',')
                    Y = int('20'+d[2][0:2])
                    M = int(d[2][2:4])
                    D = int(d[2][4:6])
                    h = int(d[2][7:9])
                    m = int(d[2][9:11])
                    s = int(d[2][11:13])
                    us = int(d[2][14:17]) * 1000
                    timestamp = datetime(Y,M,D,h,m,s,us)
                    if d[3][0] == '*':
                        x = (int('0x'+d[3][1:7],16) ^ 0x800000) - 0x800000
                        x = float(x) * 2**-23 * GAINMAX
                        y = (int('0x'+d[3][7:13],16) ^ 0x800000) - 0x800000
                        y = float(y) * 2**-23 * GAINMAX
                        z = (int('0x'+d[3][13:19],16) ^ 0x800000) - 0x800000
                        z = float(z) * 2**-23 * GAINMAX
                        triggerflag = d[3][19]
                    else:
                        pass
                    sup = d[3].split(':')
                    if len(sup) == 2:
                        voltage = int(sup[1][0:4],16) ^ 0x8000 - 0x8000
                        voltage = float(voltage) * 2.6622e-3 + 9.15
                        temp = int(sup[1][4:8],16) ^ 0x8000 - 0x8000
                        temp = float(temp) / 128.
                        p = (int('0x'+sup[1][8:12],16) ^ 0x8000) - 0x8000
                        p = float(p) / 8000.0
                        q = (int('0x'+sup[1][12:16],16) ^ 0x8000) - 0x8000
                        q = float(q) / 8000.0
                        r = (int('0x'+sup[1][16:20],16) ^ 0x8000) - 0x8000
                        r = float(r) / 8000.0
                    print (str(timestamp)+'\t',end='')
                    print (str(x)+'\t',end='')
                    print (str(y)+'\t',end='')
                    print (str(z)+'\t',end='')
                    print (str(triggerflag))
                    if len(sup) == 2:
                        print ('supplementary:\t',end='')
                        print (str(voltage)+' V\t',end='')
                        print (str(temp)+' degC\t',end='')
                        print (str(p)+'\t',end='')
                        print (str(q)+'\t',end='')
                        print (str(r)+'\t')
                else:
                    print (l)
            sys.exit()

if __name__ == "__main__":
    main(sys.argv[1:])

