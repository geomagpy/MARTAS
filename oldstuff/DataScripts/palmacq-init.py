#!/usr/bin/python

"""
Simple method to initialize PALMACQ
"""

import serial
import time
import csv
from datetime import datetime
import binascii
import sys, getopt, os


def send_command(ser,rbits,command,eol):
    #print "Sending", command
    ser.write(command+eol)
    buffer = ser.read(rbits)
    print "Found:", buffer
    return buffer

def get_commands(filename):
    with open(filename, 'rb') as f:
        reader = csv.reader(f,delimiter='\t')
        commandlist = [row for row in reader]
        return commandlist

def execute_command(ser, commandline, rbits=32, eol='\r', delay=1, repeat=5):

    def sendcom (ser, command, rbits, eol, rts, delay):
        response = ""
        if rts == 1:
            rts = True
        else:
            rts = False
        ser.setRTS(level=rts)
        time.sleep(delay)
        if not command == "":
            #print "Test", rbits, command, rts, delay
            response = send_command(ser,rbits,command,eol)
        print ''
        return response

    response = ""
    count = 0
    errorcount = 0

    print "Running command:", commandline

    if len(commandline) > 0:
        if not int(commandline[0]) in [0,1]:
            print "Check your commands file format - aborting"
            return

    if len(commandline) > 2:
        while response.find(commandline[2]) == -1:
            #print "Count", count
            if count >= 1:
                print "... repeating ..."
            if not count > repeat:
                response = sendcom(ser,commandline[1],rbits=rbits,eol=eol,rts=int(commandline[0]),delay=delay)                
            else:
                errorcount += 1
                print "-------------------------------------------------------------"
                print "Did not find expected response after %d repetions - moving on" % repeat
                print "-------------------------------------------------------------"
                response = commandline[2]
            count = count+1
        print "... command successful"
    elif len(commandline) > 1:
        response = sendcom(ser,commandline[1],rbits=rbits,eol=eol,rts=int(commandline[0]),delay=delay)
        print "... command successful"
    elif len(commandline) > 0:
        response = sendcom(ser,"",rbits=rbits,eol=eol,rts=int(commandline[0]),delay=delay)
        print "... command successful"
    return errorcount

def main(argv):
    filename = "/home/leon/MARTAS/DataScripts/commands.txt"

    eol = "\r"   # can also be "\n" or "\x00" 
    rbits = 1024
    delay = 1 # 1 second
    repeat = 5

    adds = False
    starttime = datetime.utcnow()
    commands = []

    try:
        opts, args = getopt.getopt(argv,"hf:r:",["filename=","repeat=",])
    except getopt.GetoptError:
        print 'palmacq-init.py -f <filename> -r <repeat>'
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print '------------------------------------------------------'
            print 'Usage:'
            print 'palmacq-init.py -f <filename> -r <repeat>'
            print '------------------------------------------------------'
            print 'Options:'
            print '-f                       filename with commands'
            print '-r                       repeat cycles if expected response is not met'
            print '------------------------------------------------------'
            print 'Examples:'
            print 'palmacq-init.py -f "/home/cobs/MARTAS/DataScripts/commands.txt" -r 5'

            sys.exit()
        elif opt in ("-f", "--filename"):
            filename = arg
        elif opt in ("-r", "--repeat"):
            repeat = arg

    try:
        if not os.path.isfile(filename):
            print "Command file is not existing - please specify"
            sys.exit(0)
    except:
        print "Could not interprete filename - please check"
        sys.exit(0)

    try:
        if not repeat > 1:
            print "Repeat variable needs to be larger than 1 - please correct"
            sys.exit(0)
    except:
        print "Repeat variable needs to be an integer - please check"
        sys.exit(0)

    print "Starting initialization at", starttime
 
    try:
        ser = serial.Serial('/dev/ttyUSB0', baudrate=38400, parity='N', bytesize=8, stopbits=1, timeout=5)
        print 'Connection made.'
    except: 
        print 'Connection flopped.'
    print ''

    print "Loading commands ..."
    
    clist = get_commands(filename)
    errorcount = 0
 
    for cline in clist:
        if len(cline) == 2:
            rebits = 32 # Arbitrary
            if '|' in cline[1]:
                delay = 0
                for elem in cline[1]:
                    com = ['1',elem]
                    execute_command(ser, com, rbits=rbits, eol=eol, delay=delay, repeat=repeat)
            else:
                execute_command(ser, cline, rbits=rbits, eol=eol, delay=delay, repeat=repeat)
        else:
            delay = 1
            rebits = 1024
        errorcount = execute_command(ser, cline, rbits=rbits, eol=eol, delay=delay, repeat=repeat)

    if not errorcount > 2:
        print "All processes started - acquisition mode %s active" % clist[-1][1]
    else:
        print "Several error encountered during system init - check and eventually repeat"

    now = datetime.utcnow()
    print "Finished initialization at", now


if __name__ == "__main__":
   main(sys.argv[1:])

