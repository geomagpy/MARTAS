#!/usr/bin/python

"""
Simple method to initialize GSM sensors (GSM19, GSM90)
"""
from __future__ import print_function

import serial
from datetime import datetime
import binascii
import sys, getopt

import time


def lineread(ser,eol=None):
    """
    DESCRIPTION:
       Does the same as readline(), but does not require a standard 
       linebreak character ('\r' in hex) to know when a line ends.
       Variable 'eol' determines the end-of-line char: '\x00'
       for the POS-1 magnetometer, '\r' for the envir. sensor.
       (Note: required for POS-1 because readline() cannot detect
       a linebreak and reads a never-ending line.)
    PARAMETERS:
       eol:   (string) lineend character(s): can be any kind of lineend
                           if not provided, then standard eol's are used
    """
    if not eol:
        eollist = ['\r','\x00','\n']
    else:
        eollist = [eol]

    ser_str = ''
    while True:
        char = ser.read()
        #if char == '\x00':
        if sys.version_info >= (3,0):
            char = char.decode()
        if char in eollist:
            break
        ser_str += char
    return ser_str


def hexify_command(command,eol):
    """
    DESCRIPTION:
       This function translates the command text string into a hex
       string that the serial device can read. 'eol' is the 
       end-of-line character. '\r' for the environmental sensor,
       '\x00' for the POS-1 magnetometer.
    """
    commandstr = []
    for character in command:
        hexch = binascii.hexlify(character)
        commandstr.append(('\\x' + hexch).decode('string_escape'))

    command_hex = ''.join(commandstr) + (eol)

    return command_hex


def send_command(ser,command,eol=None,hexify=False,bits=0):
    """
    DESCRIPTION:
        General method to send commands to a e.g. serial port.
        Returns the response
    PARAMETER:
        bits: (int) provide the amount of bits to be read
        eol:  (string) end-of-line string
    Options:
        POS1:           hexify=True, line=True, eol= '\x00'
        ENV05:          hexify=True, line=True, eol='\r'
        GSM90Sv6:       hexify=False, line=False, eol=''
        GSM90Sv7:       hexify=False, line=False, eol
        GSM90Fv7:       hexify=False, line=False, eol
    """
    print('-- Sending command:  ', command)
    if sys.version_info >= (3,0):
        command = command.encode('ascii')
        if eol:
            eol = eol.encode('ascii')
    if hexify:
        command = hexify_command(command,eol)
        ser.write(command)
    else:
        if not eol:
            ser.write(command)
        else:
            ser.write(command+eol)
    if bits==0:
        response = lineread(ser,eol)
    else:
        response = ser.read(bits)
        if sys.version_info >= (3,0):
            response = response.decode()
    print('-- Response: ', response)
    return response


def main(argv):
    # Communication parameter defaults
    baudrate = 115200
    port = '/dev/ttyS0'
    parity='N'
    bytesize=8
    stopbits=1
    timeout=5
    #flowcontrol=  ## Not used so far

    # General defaults (time, etc)
    command = ''
    commands = []
    responseaction = []
    hexify = False
    eol = None
    bits = 0
    timeformat = None

    try:
        opts, args = getopt.getopt(argv,"hb:p:f:y:a:s:o:c:r:xe:d:i:k:",["baudrate=","port=","flowcontrol=","bytesize=","parity=","stopbits=","timeout=","command=","responseaction=", "eol=", "eol-ord=", "bits2read=", "timeformat=",])
    except getopt.GetoptError:
        print('Check your options:')
        print('serial-init.py -b <baudrate> -p <port> -f <flowcontrol> -y <bytesize> -a <parity> -s <stopbits> -o <timeout> -c <commands> -r <responseaction> -x <hexify> -e <eol> -d <eol-ord> -i <bits2read> -k <timeformat>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('------------------------------------------------------')
            print('Usage:')
            print('serial-init.py -b <baudrate> -p <port> -f <flowcontrol> -y <bytesize> -a <parity> -s <stopbits> -o <timeout> -c <commands> -r <responseaction> -x <hexify> -e <eol> -d <eol-ord> -i <bits2read> -k <timeformat>')
            print('------------------------------------------------------')
            print('Options:')
            print('-h                             help')
            print('-b                             set baudrate - default is 115200')
            print('-p                             set port - default is /dev/ttyS0')
            print('-f                             set flowcontrol (not yet supported)')
            print('-y  e.g. SEVENBITS             set bytesize - default is 8     ') 
            print('-a  e.g. PARITY_EVEN           set parity   - default is N     ')
            print('-s                             set stopbits - default is 1     ')
            print('-o                             set timeout  - default is 5 (sec) ')
            print('-c  e.g.C,1611104142567,T48    comma separated string with commands')
            print('-r  e.g. z-save,z              comma separated list of two items: ')
            print('                               if the first item is found within ')
            print('                               the response of a command, then the ')
            print('                               second item is send')
            print('-x                             hexify commands                 ')
            print('-e                             end-of-line characters to be used')
            print('-d                             end-of-line character as ascii number')
            print('                               defaults are: ')
            print('-i                             define the bits size of the response')
            print('                               default is to read until eol (option e)')
            print('-k  e.g. "%y%m%d%w%H%M%S"      set timestamp-format, if provided and placeholder')
            print('                               "datetime" is found in commands, then it is replaced')
            print('                               by a current UTC timestamp of the provided format')
            print('                               e.g. -c C,datetime,T48 -> -c C,1611104153425,T48')
            
            print('------------------------------------------------------')
            print('Examples:')
            print('1. Initializing POS1:')
            print('   python serialinit.py -p "/dev/ttyS1" -b 9600 -c "mode text,time datetime,date 11-22-16,range 48500,auto 5" -k "%H:%M:%S" -x -d 0')
            print('2. Initializing GSM90Sv6:')
            print('   python serialinit.py -p "/dev/ttyUSB0" -c S,5,T048,C,datetime,R -k "%y%m%d%w%H%M%S" -i 1024')
            print('3. Initializing GSM90Sv7:')
            print('   python serialinit.py -p "/dev/ttyUSB0" -c S,5,T048.5,C,datetime,D,R -k "%y%m%d%w%H%M%S" -r "z-save,z" -i 1024') 
            print('4. Initializing BM35:')
            print('   python serialinit.py -b 2400 -p "/dev/ttyS1" -c "A00d03000" -d 13')
            sys.exit()
        elif opt in ("-b", "--baudrate"):
            baudrate = arg
        elif opt in ("-p", "--port"):
            port = arg
        elif opt in ("-y", "--bytesize"):
            try:
                bytesize = int(arg)
            except:
                bytesize = arg
        elif opt in ("-a", "--parity"):
            parity = arg
        elif opt in ("-s", "--stopbits"):
            try:
                stopbits = int(arg)
            except:
                stopbits = arg
        elif opt in ("-o", "--timeout"):
            try:
                timeout = int(arg)
            except:
                timeout = arg
        elif opt in ("-e", "--eol"):
            eol = arg
        elif opt in ("-d", "--eol-ord"):
            eol = chr(int(arg))
        elif opt in ("-c", "--commands"):
            command = arg
        elif opt in ("-r", "--responseaction"):
            respac = arg
            responseaction = respac.split(',')
            if not len(responseaction) == 2:
                print ("serial-init: warning... cannot interpret (r) responseaction - skipping this option")
                responseaction = []
        elif opt in ("-x", "--hexify"):
            hexify = True
        elif opt in ("-i", "--bits2read"):
            try:
                bits = int(arg)
            except:
                bits = 0
                print ("serial-init: warning... integer number expected for (i) - skipping this option")
        elif opt in ("-k", "--timeformat"):
            timeformat = arg

    # Re-format command sequence
    if command.find('datetime') > 0:
        if not timeformat:
            print ("serial-init: warning... found 'datetime' placeholder in command sequence, but no timeformat is provided (-k):")
            print ("             ... skipping option")

        else:
            try:
                currenttime = datetime.utcnow()
                timestamp = str(datetime.strftime(currenttime,timeformat))
                command = command.replace('datetime',timestamp)
            except:
                print ("serial-init: warning... could not interpret datetimeformat provided by (-k) ... skipping this")
                pass
    commands = command.split(',')

    # Connecting
    print ("Welcome to serial-init")
    print ("------------------------------------------")
    print ("Establishing connection to serial port:")
    try:
        print ("TEST", baudrate,parity,bytesize,stopbits,timeout)
        ser = serial.Serial(port, baudrate=baudrate, parity=parity, bytesize=bytesize, stopbits=stopbits, timeout=timeout)
        print('.... Connection made.')
    except: 
        print('.... Connection flopped.')
        print('--- Aborting ---')
        sys.exit(2)
    print('')

    # Sending/Receiving
    print ("------------------------------------------")
    if len(commands) > 0:
        print ("Sending command sequence:")
        for item in commands:
            response = send_command(ser, item, eol=eol, hexify=hexify, bits=bits)
            if len(responseaction) == 2:
                if response.find(responseaction[0]) > 0:
                    print ("TEST:", responseaction)
                    print ("... found matching response - performing response-action")
                    response = send_command(ser, responseaction[1], eol=eol, hexify=hexify, bits=bits)
        print('')
        print ("... Done ... good bye")
    else:
        print ("No commands provided:")
        amount = 1024
        print ("... reading {} bits to check whether data is send on port {}:".format(amount,port))
        response = ser.read(amount)
        print (response)
        print('')
        print ("... Done ... good bye")
        sys.exit(2)

if __name__ == "__main__":
   main(sys.argv[1:])

