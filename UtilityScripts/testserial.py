#!/usr/bin/env python

from __future__ import print_function
import sys, time, os, socket
import serial
import struct, binascii, re, csv
from datetime import datetime, timedelta
from matplotlib.dates import date2num, num2date
import numpy as np
import time

port = '/dev/ttyS0'
baudrate='115200'
eol = '\r'

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
                char = ser.read()
                if char == eol:
                    break
                if time.time() > timeout:
                    break
                ser_str += char
            return ser_str

def send_command(ser,command,eol,hex=False):

    command = eol+command+eol
    #print 'Command:  %s \n ' % command.replace(eol,'')
    sendtime = date2num(datetime.utcnow())
    #print "Sending"
    ser.write(command)
    #print "Received something - interpretation"
    response = lineread(ser,eol)
    #print "interprete"
    receivetime = date2num(datetime.utcnow())
    meantime = np.mean([receivetime,sendtime])
    #print "Timediff", (receivetime-sendtime)*3600*24
    return response, num2date(meantime).replace(tzinfo=None)

ser = serial.Serial(port, baudrate=baudrate , parity='N', bytesize=8, stopbits=1, timeout=2)
for i in range(99):
    call = str(i).zfill(2)+'TR00002'
    print(call)
    answer, actime = send_command(ser,call,eol)
    print(answer)

