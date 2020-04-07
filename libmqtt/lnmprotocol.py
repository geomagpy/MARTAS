
from __future__ import print_function
from __future__ import absolute_import

# ###################################################################
# Import packages
# ###################################################################

import re     # for interpretation of lines
import struct # for binary representation
import socket # for hostname identification
import string # for ascii selection
from datetime import datetime, timedelta
from twisted.protocols.basic import LineReceiver
from twisted.python import log
from core import acquisitionsupport as acs

import os

COMMANDS=['01TR00002']

"""
import sys, time, os, socket
import serial
import struct, binascii, re, csv
from datetime import datetime, timedelta
from matplotlib.dates import date2num, num2date
import numpy as np
from subprocess import check_call

# Twisted
from twisted.protocols.basic import LineReceiver
from twisted.internet import reactor
from twisted.python import usage, log
from twisted.internet.serialport import SerialPort
from twisted.web.server import Site
from twisted.web.static import File
"""

class LnmProtocol(LineReceiver):
    """
    Protocol to read Laser Niederschlags-Monitor data.
    Basic example for a active protocol
    """
    def __init__(self, client, sensordict, confdict):
        """
        'client' could be used to switch between different publishing protocols
                 (e.g. MQTT or WS-MCU gateway factory) to publish events
        'sensordict' contains a dictionary with all sensor relevant data (sensors.cfg)
        'confdict' contains a dictionary with general configuration parameters (martas.cfg)
        """
        self.client = client
        self.sensordict = sensordict    
        self.confdict = confdict
        self.count = 0  ## counter for sending header information
        self.sensor = sensordict.get('sensorid')
        self.hostname = socket.gethostname()
        self.printable = set(string.printable)
        #log.msg("  -> Sensor: {}".format(self.sensor))
        self.datalst = []
        self.datacnt = 0
        self.metacnt = 10
        self.qos=int(confdict.get('mqttqos',0))
        if not self.qos in [0,1,2]:
            self.qos = 0
        log.msg("  -> setting QOS:", self.qos)

        """
        Required info:
        - address (if several systems on one rs422)
        - eol
        - commands (to get data and meta)
        """
        specific = True
        if specifc:
            self.source = source
            self.addressanemo = '01'
            self.commands = ['11TR00005',self.addressanemo+'TR00002']
            self.eol = '\r'
            self.errorcnt = 1
            self.writeerrorcnt = 0


    def connectionMade(self):
        log.msg('  -> {} connected.'.format(self.sensor))

    def connectionLost(self, reason):
        log.msg('  -> {} lost.'.format(self.sensor))


    # MOVE SEND COMMAND to acquisition support
    #def sendCommands(sensordict, commands):
    def sendCommands(self):
        try:
            ser = serial.Serial(sensordict.get('port'), baudrate=sensordict.get('baudrate'), parity=sensordict.get('parity'), bytesize=sensordict.get('bytesize'),  stopbits=sensordict.get('stopbits'), parity='N', bytesize=8, stopbits=1, timeout=10)
            #print 'Connection made.'
        except:
            log.msg('SerialCall: Connection flopped.')

        for item in self.commands:
            #print "sending command", item
            firsttime = date2num(datetime.utcnow())
            answer = acs.send_command(ser,item,self.eol,hex=False)
            receivetime = date2num(datetime.utcnow())
            meantime = np.mean([receivetime,sendtime])
            success = self.processData(answer, meantime)
            time.sleep(2)
            if not success and self.errorcnt < 5:
                self.errorcnt = self.errorcnt + 1
                log.msg('SerialCall: Could not interpret response of system when sending %s' % m)
            elif not success and self.errorcnt == 5:
                try:
                    check_call(['/etc/init.d/martas', 'restart'])
                except subprocess.CalledProcessError:
                    log.msg('SerialCall: check_call didnt work')
                except:
                    log.msg('SerialCall: check call problem')

                log.msg('SerialCall: Restarted martas process')

            ser.close()


    def processData(self, line, time):

        if not len(answer.split(';'))==525:
            return False
        else:
            filename = datetime.strftime(actime, "%Y-%m-%d")
            timestamp = datetime.strftime(actime, "%Y-%m-%d %H:%M:%S.%f")
            outtime = datetime.strftime(actime, "%H:%M:%S")
            try:
                data = line.split(';')

                # Extract data
                sensor = 'LNM'
                serialnum = data[1]
                cumulativerain = float(data[15]) 	# x
                if cumulativerain > 9000:
                    #send_command(reset)
                    pass
                visibility = int(data[16])		# y
                reflectivity = float(data[17])	 	# z
                intall = float(data[12]	)	 	# var1
                intfluid = float(data[13])	 	# var2
                intsolid = float(data[14])	 	# var3
                quality = int(data[18])
                haildiameter = float(data[19])		# var4
                insidetemp = float(data[36])	 	# t2
                lasertemp = float(data[37])
                lasercurrent = data[38]
                outsidetemp = float(data[44])		# t1
                Ptotal= int(data[49])			# f
                Pslow = int(data[51])		 	# dx
                Pfast= int(data[53])		 	# dy
                Psmall= int(data[55])		 	# dz
                synop = data[6]                         # str1
                revision = '0001' # Software version 2.42
                sensorid = sensor + '_' + serialnum + '_' + revision
            except:
                log.err('SerialCall - writeDisdro: Could not assign data values')

            shortcut = sensorid[:3].lower()

            try:
                ##### Write ASCII data file with full output and timestamp
                # extract time data
                # try:
                #print "Writing"
                timestr = timestamp.replace(' ',';')
                #print "1", line.encode('ascii','ignore')
                asciiline = ''.join([i for i in line if ord(i) < 128])
                asciidata = timestr + ';' + asciiline.strip('\x03').strip('\x02')
                #print "2", asciidata
                header = '# LNM - Telegram5 plus NTP date and time at position 0 and 1'
                acs.dataToCSV(self.confdict.get('bufferdirectory'), sensorid, filename, asciidata, [header])
            except:
                log.msg('SerialCall - writeDisdro: Error while saving ascii data')


            # Send data method

