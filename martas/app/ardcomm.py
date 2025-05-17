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
# get core functions to extract sensorcfg
scriptpath = os.path.dirname(os.path.realpath(__file__))
coredir = os.path.abspath(os.path.join(scriptpath, '..', 'core'))
sys.path.insert(0, coredir)
import acquisitionsupport as acs

def get_arduino_cfg(mpath="/etc/martas/martas.cfg",debug=False):
    if debug:
        print ("Getting arduino config from sensors.cfg")
    serialcfg = {"port":"/dev/ttyACM0","baudrate":9600,"parity":"N","bytesize":8,"stopbits":1}
    try:
        conf = acs.GetConf(mpath)
        sensors = acs.GetSensors(conf.get('sensorsconf'))
        for sensordict in sensors:
            if sensordict.get("sensorid").find("ARDUINO")>-1:
                serialcfg["baudrate"]=int(sensordict.get('baudrate'))
                serialcfg["port"]=conf['serialport']+sensordict.get('port')
                serialcfg["parity"]=sensordict.get('parity')
                serialcfg["bytesize"]=int(sensordict.get('bytesize'))
                serialcfg["stopbits"]=int(sensordict.get('stopbits'))
        if debug:
            print ("Obtained the following parameters: {}".format(serialcfg))
    except:
        if debug:
            print ("Failed to obtain parameters from sensor.cfg file")
    return serialcfg


def send_command(ser,command,eol,hex=False):

    #use printable here
    response = ''
    fullresponse = ''
    maxcnt = 50
    cnt = 0
    command = command+eol
    #if(ser.isOpen() == False):
    #    ser.open()
    ser.flush()
    if sys.version_info >= (3, 0):
        ser.write(command.encode('ascii'))
    else:
        ser.write(command)
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
    port = ""  # default
    baudrate=None
    parity=""
    bytesize=None
    stopbits=None
    timeout=2   # 0 for non-blocking read, does not work
    command = 'Status'
    eol = '\r\n'
    martaspath="/etc/martas/martas.cfg"
    debug = False
    travistestrun = False

    usagestring = 'ardcomm.py -c <command> -p <port> -b <baudrate> -a <parity> -y <bytesize> -s <stopbits> -t <timeout> -e <eol> -m <martaspath>'
    try:
        opts, args = getopt.getopt(argv,"hc:p:b:a:y:s:te:m:DT",["command=","port=","baudrate=","parity=","bytesize=","stopbits=","timeout=","eol=","martaspath=","debug=","Test=",])
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
            print ('                               P:switch:pin  : e.g. swP:0:4 = switch off pin 4')
            print ('-p                             set port - default is /dev/ttyACM0')
            print ('-b                             baudrate - default is 9600')
            print ('-a                             parity - default is "N"')
            print ('-y                             bytesize - default is 8')
            print ('-s                             stopbits - default is 1')
            print ('-t                             timeout - default is 0')
            print ('-e                             end of line - default is /r/n')
            print ('-m                             martas.cfg location - default is /etc/martas/martas.cfg')
            print ('------------------------------------------------------')
            print ('Examples:')
            print ('1. Switch on pin 4')
            print ('   python ardcomm.py -c "swP:1:4')
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
        elif opt in ("-m", "--martaspath"):
            martaspath = arg
        elif opt in ("-D", "--debug"):
            debug = True
        elif opt in ("-T", "--Test"):
            travistestrun = True

    serialcfg = get_arduino_cfg(mpath=martaspath,debug=debug)
    if not baudrate:
         baudrate=serialcfg.get("baudrate",9600)
    if not port:
         port=serialcfg.get("port","/dev/ttyACM0")
    if not parity:
         parity=serialcfg.get("parity","N")
    if not bytesize:
         bytesize=serialcfg.get("bytesize",8)
    if not stopbits:
         stopbits=serialcfg.get("stopbits",1)

    ser = serial.Serial(port, baudrate=baudrate , parity=parity, bytesize=bytesize, stopbits=stopbits, timeout=timeout)
    time.sleep(2)

    # Additional configs:
    ser.writeTimeout = 2     #timeout for write or write_timeout
    ser.write_timeout = 2

    # Open Connection
    # try it 10 time, then close and reopen serial - likely not necessary
    count = 0
    portopened = False
    while count < 10:
        try:
            ser.open()
            count = 10
            if debug:
                print ("ardcomm: serial port opened")
            portopened = True
        except Exception as e:
            count += 1
            #print ("ardcomm: error open serial port {}: {}".format(count,str(e)))
            if count == 8:
                try:
                    #closing if already open, so that it is reopenning for last try...
                    ser.close()
                except:
                    pass

    if not portopened and travistestrun:
        print ("ardcomm: serial port not available in testrun - finishing")
        sys.exit(0)


    if ser.isOpen():
        #try:
        #if debug:
        print("Sending command: {} ...".format(command))
        answer = send_command(ser,command,eol)
        #if debug:
        print("Answer: {}".format(answer))
        ser.close()
        #except Exception as e1:
        #    print ("ardcomm: communication error: {}".format(e1))
    else:
        print ("ardcomm: cannot open serial port - aborting")
        sys.exit(0)

if __name__ == "__main__":
   main(sys.argv[1:])

