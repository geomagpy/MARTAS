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


def send_command(ser,command,eol,hex=False):

    #use printable here
    response = ''
    fullresponse = ''
    maxcnt = 50
    cnt = 0
    command = command+eol
    if(ser.isOpen() == False):
        ser.open()
    ser.flush()
    if sys.version_info >= (3, 0):
        ser.write(command.encode('ascii'))
    else:
        ser.write(command)
    #time.sleep(0.1)
    # skipping all empty lines
    while response == '':
        response = ser.readline()
        if sys.version_info >= (3, 0):
            response = response.decode()
    # read until end-of-messageblock signal is obtained (use some break value)
    while not response.startswith('<MARTASEND>') and not cnt == maxcnt:
        cnt += 1
        fullresponse += response
        response = ser.readline()
        if sys.version_info >= (3, 0):
            response = response.decode()
    if cnt == maxcnt:
        fullresponse = 'Maximum count {} was reached'.format(maxcnt)
    return fullresponse


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
    time.sleep(2)
    print("Sending command: {} ...".format(command))
    answer = send_command(ser,command,eol)
    print("Answer: {}".format(answer))
    ser.close()

if __name__ == "__main__":
   main(sys.argv[1:])

