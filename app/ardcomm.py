#!/usr/bin/env python
"""
Small program to send commands to an Arduino.
Used to interact with MARTAS supported scripts on Arduinos.
"""

from __future__ import print_function
import sys, time, os, socket
import getopt
import serial
import struct, binascii, re, csv
from datetime import datetime, timedelta
from matplotlib.dates import date2num, num2date
import numpy as np
import time


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

    response = ''
    command = command+eol
    if(ser.isOpen() == False):
        ser.open()
    ser.write(command)
    while response == '':
        response = ser.readline()
    return response.strip()


def main(argv):
    port = '/dv/ttyACM0'  # default
    baudrate = '9600'
    parity='N'
    bytesize=8
    stopbits=1
    timeout=2
    command = 'Status'
    port = '/dev/ttyACM0'
    eol = '\r\n'

    usagestring = 'ardcomm.py -c <command> -p <port> -b <baudrate> -a <parity> -y <bytesize> -s <stopbits> -t <timeout> -e <eol>'
    try:
        opts, args = getopt.getopt(argv,"hc:p:b:a:y:s:te:",["command=","port=","baudrate=","parity=","bytesize=","stopbits=","timeout=","eol="])
    except getopt.GetoptError:
        print ('Check your options:')
        print (usagestring)
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print ('------------------------------------------------------')
            print ('Usage:')
            print (usagestring)
            print ('------------------------------------------------------')
            print ('Options:')
            print ('-h                             help')
            print ('-c                             command to send:')
            print ('                               Status          : return the current switch status')
            print ('                               P:switch:pin  : e.g. ACMpin:0:4 = switch off pin 4')
            print ('-p                             set port - default is /dev/ttyACM0')
            print ('-b                             baudrate - default is 9600')
            print ('-a                             parity - default is "N"')
            print ('-y                             bytesize - default is 8')
            print ('-s                             stopbits - default is 1') 
            print ('-t                             timeout - default is 2')
            print ('-e                             end of line - default is /r')
            print ('------------------------------------------------------')
            print ('Examples:')
            print ('1. Switch on pin 4')
            print ('   python ardcomm.py -c "AMCpin:1:4')
            sys.exit()
        elif opt in ("-c", "--command"):
            command = arg
            n = command.count(":")
            miss=-(n-2)
            for n in range(miss):
                command += ':'
        elif opt in ("-a", "--parity"):
            parity = arg
        elif opt in ("-y", "--bytesize"):
            bytesize = arg
        elif opt in ("-e", "--eol"):
            eol = arg
        elif opt in ("-b", "--baudrate"):
            baudrate = arg
        elif opt in ("-p", "--port"):
            port = arg
        elif opt in ("-t", "--timeout"):
            try:
                timeout = int(arg)
            except:
                timeout = arg
        elif opt in ("-y", "--bytesize"):
            try:
                bytesize = int(arg)
            except:
                bytesize = arg
        elif opt in ("-s", "--stopbits"):
            try:
                stopbits = int(arg)
            except:
                stopbits = arg

    ser = serial.Serial(port, baudrate=baudrate , parity=parity, bytesize=bytesize, stopbits=stopbits, timeout=timeout)

    print("Sending command: {} ...".format(command))
    answer = send_command(ser,command,eol)
    print("Answer: {}".format(answer))

if __name__ == "__main__":
   main(sys.argv[1:])

