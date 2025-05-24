
# ###################################################################
# Import packages
# ###################################################################

import struct # for binary representation
import socket # for hostname identification
import string # for ascii selection
from datetime import datetime, timezone
from twisted.python import log
import serial
import os, csv
import sys

def send_command_ascii(ser,command,eol):
    #use printable here
    response = ''
    command = eol+command+eol
    if(ser.isOpen() == False):
        ser.open()
    sendtime = datetime.now(timezone.utc).replace(tzinfo=None)
    # encode to binary if python3
    if sys.version_info >= (3, 0):
        ser.write(command.encode('ascii'))
    else:
        ser.write(command)
    #ser.write(command)
    # skipping all empty lines
    while response == '':
        response = ser.readline()
    responsetime = datetime.now(timezone.utc).replace(tzinfo=None)
    # decode from binary if py3
    if sys.version_info >= (3, 0):
        response = response.decode('ascii')
    # return only ascii
    line = ''.join(filter(lambda x: x in string.printable, response))
    line = line.strip()
    return line, responsetime

def dataToCSV(outputdir, sensorid, filedate, asciidata, header):
                # Will be part of acquisitionsupport from MagPy 0.4.5
                #try:
                path = os.path.join(outputdir,sensorid)
                if not os.path.exists(path):
                    os.makedirs(path)
                savefile = os.path.join(path, sensorid+'_'+filedate+".asc")
                asciilist = asciidata.split(';')
                if not os.path.isfile(savefile):
                    with open(savefile, "wb") as csvfile:
                        writer = csv.writer(csvfile,delimiter=';')
                        writer.writerow(header)
                        writer.writerow(asciilist)
                else:
                    with open(savefile, "a") as csvfile:
                        writer = csv.writer(csvfile,delimiter=';')
                        writer.writerow(asciilist)
                #except:
                #log.err("datatoCSV: Error while saving file")        


def datetime2array(t):
    return [t.year,t.month,t.day,t.hour,t.minute,t.second,t.microsecond]

## Arduino active request protocol
## --------------------

class DisdroProtocol(object):
    """
    Protocol to read data from a Disdrometer

    Active protocol to periodically request data 
    Example sensor.cfg:
    LNM_0351_0001,S0,115200,8,1,N,active,None,60,1,Disdro,LNM,0351,0001,-,MeteoTower,NTP,environment,Thiess LNM Disdrometer
    """

    ## need a reference to our WS-MCU gateway factory to dispatch PubSub events
    ##
    def __init__(self, client, sensordict, confdict):
        # Specific commands for Disdrometer
        self.commands = [{'data':'11TR00005'}]

        #self.commands = [{'data':'01TR00002','c1':'01SH','c2':'01SL'}]
        self.hexcoding = False
        self.eol = '\r'


        self.client = client #self.wsMcuFactory = wsMcuFactory
        self.sensordict = sensordict
        self.confdict = confdict
        self.count = 0  ## counter for sending header information

        self.sensorid = ''
        self.sensorname = sensordict.get('name')
        self.baudrate=int(sensordict.get('baudrate'))
        self.port = confdict['serialport']+sensordict.get('port')
        self.parity=sensordict.get('parity')
        self.bytesize=sensordict.get('bytesize')
        self.stopbits=sensordict.get('stopbits')
        self.timeout=2 # should be rate depended

        self.hostname = socket.gethostname()
        self.printable = set(string.printable)
        self.datalst = []
        self.datacnt = 0
        rate = sensordict.get('rate','0')
        try:
            rate = int(rate)
        except:
            rate = 1
        if rate < 5:
            self.metacnt = 10 # send header at reduced rate
        else:
            self.metacnt = 1
        self.counter = {}

        # QOS
        self.qos=int(confdict.get('mqttqos',0))
        if not self.qos in [0,1,2]:
            self.qos = 0
        log.msg("  -> setting QOS:", self.qos)

        # switch on debug mode
        debugtest = confdict.get('debug')
        self.debug = False
        if debugtest == 'True':
            log.msg('DEBUG - {}: Debug mode activated.'.format(self.sensordict.get('protocol')))
            self.debug = True    # prints many test messages
        else:
            log.msg('  -> Debug mode = {}'.format(debugtest))

        # DISDROMETER specific
        self.sensorid = self.sensorname


    def processData(self, line, ntptime):
        """processing and storing data - requires sensorid and meta info
           data looks like (TR00005):

           The MARTAS code reads only some parameters and sends them in realtime. The full raw data
           is saved into a ascii file with the bufferdirectory
        """
        # currenttime = datetime.now(timezone.utc).replace(tzinfo=None)
        outdate = datetime.strftime(ntptime, "%Y-%m-%d")
        timestamp = datetime.strftime(ntptime, "%Y-%m-%d %H:%M:%S.%f")
        filename = outdate
        header = ''
        datearray = datetime2array(ntptime)
        packcode = '6hL'
        multiplier = []
        pc = []
        key = '[x,y,z,f,t1,t2,var1,var2,var3,var4,dx,dy,dz,str1]'
        ele = '[rainfall,visibility,reflectivity,P_tot,T,T_el,I_tot,I_fluid,I_solid,d(hail),P_slow,P_fast,P_small,SYNOP-4680-code]'
        unit = '[mm,m,dBZ,None,degC,degC,None,None,None,mm,None,None,None,None]'  ### check database
        #print ("Processing line for {}: {}".format(sensorid, line))
        data = line.split(';')

        def addpara(para, mu, c='l',pc=pc, multplier=multiplier):
            datearray.append(int(para*mu))
            pc.append(c)
            multiplier.append(mu)
            return pc, multiplier

        if len(data) > 10:
            if self.debug:
                print ("Received data - amount of elements: {}".format(len(data)))
            try:
                # Extract data
                #sensor = 'LNM'
                serialnum = data[1] # I guess that this is the serial connectors ID...
                cumulativerain = float(data[15]) 	# x
                pc, multiplier = addpara(cumulativerain,100,c='l')
                if cumulativerain > 9000:
                    log.msg('SerialCall - writeDisdro: Resetting percipitation counter')
                    self.commands = [{'setconfmod':'11KY00001'},{'reset':'11RA00001'},{'setworkmode':'11KY00000'}]
                visibility = int(data[16])		# y
                pc, multiplier = addpara(visibility,1,c='l')
                reflectivity = float(data[17])	 	# z
                pc, multiplier = addpara(reflectivity,100)
                Ptotal= int(data[49])			# f
                pc, multiplier = addpara(Ptotal,1)
                outsidetemp = float(data[44])		# t1
                pc, multiplier = addpara(outsidetemp,100)
                insidetemp = float(data[36])	 	# t2
                pc, multiplier = addpara(insidetemp,100)
                intall = float(data[12]	)	 	# var1
                pc, multiplier = addpara(intall,100)
                intfluid = float(data[13])	 	# var2
                pc, multiplier = addpara(intfluid,100)
                intsolid = float(data[14])	 	# var3
                pc, multiplier = addpara(intsolid,100)
                quality = int(data[18])
                haildiameter = float(data[19])		# var4
                pc, multiplier = addpara(haildiameter,100)
                lasertemp = float(data[37])
                lasercurrent = data[38]
                Pslow = int(data[51])		 	# dx
                pc, multiplier = addpara(Pslow,1)
                Pfast= int(data[53])		 	# dy
                pc, multiplier = addpara(Pfast,1)
                Psmall= int(data[55])		 	# dz
                pc, multiplier = addpara(Psmall,1)
                synop = data[6]                         # str1
                pc, multiplier = addpara(synop,1,c='s')
                revision = '0001' # Software version 2.42
                self.sensorid = self.sensorname + '_' + serialnum + '_' + revision
                data = ','.join(list(map(str,datearray)))
                packcode = packcode+''.join(list(pc))
                header = "# MagPyBin {} {} {} {} {} {} {}".format (self.sensorid, key, ele, unit, '['+','.join(list(map(str,multiplier)))+']', packcode, struct.calcsize('<'+packcode))
                if self.debug:
                    print ("Header", header)
            except:
                log.err('SerialCall - writeDisdro: Could not assign data values')
                data = ''


            if not self.confdict.get('bufferdirectory','') == '':
                timestr = timestamp.replace(' ',';')
                asciiline = ''.join([i for i in line if ord(i) < 128])
                asciidata = timestr + ';' + asciiline.strip('\x03').strip('\x02')
                fheader = '# LNM - Telegram5 plus NTP date and time at position 0 and 1'
                try:
                    dataToCSV(self.confdict.get('bufferdirectory'),self.sensorid, filename, asciidata, [fheader])
                except:
                    log.msg("Writing data failed")
                #if self.debug:
                #    print ("  -> writing data successfull: {}".format(self.sensorid))
        else:
            data = ''

        return data, header


    def sendRequest(self):

        success = True
        # connect to serial
        ser = serial.Serial(self.port, baudrate=int(self.baudrate), parity=self.parity, bytesize=int(self.bytesize), stopbits=int(self.stopbits), timeout=int(self.timeout))
        for commdict in self.commands:
            for item in sorted(commdict):
                comm = commdict.get(item)
                if self.debug:
                    print ("sending item {} with command {}".format(item, comm))
                # eventually more frequently ask for 'data'
                answer, actime = send_command_ascii(ser,comm,self.eol)
                answerok = True
                if item in ['setworkmode','setconfmode','reset']:
                    answerok = False
                if item == 'setworkmode':
                    log.msg('SerialCall: Continuing normal acquisition')
                    self.commands = [{'data':'11TR00005'}]
                # disconnect from serial
                ser.close()
                #if self.debug:
                #    print ("got answer: {}".format(answer))
                # check answer
                if answerok:
                    data, head = self.processData(answer, actime)
                    # send data via mqtt
                    if not data == '':
                        self.sendmqtt(self.sensorid,data,head)

                # ##########################################################
                # answer is a string block with eventually multiple lines
                # apply the old linereceived method to each line of the answer
                # thats it ...

                #answer = ''.join(filter(lambda x: x in string.printable, answer))
                """
                if not success and self.errorcnt < 5 and not item=='reset':
                    self.errorcnt = self.errorcnt + 1
                    log.msg('SerialCall: Could not interprete response of system when sending %s' % item) 
                elif not success and self.errorcnt == 5:
                    try:
                        check_call(['/etc/init.d/martas', 'restart'])
                    except subprocess.CalledProcessError:
                        log.msg('SerialCall: check_call didnt work')
                        pass # handle errors in the called executable
                    except:
                        log.msg('SerialCall: check call problem')
                        pass # executable not found
                    #os.system("/etc/init.d/martas restart")
                    log.msg('SerialCall: Restarted martas process')
                """
        # disconnect from serial
        #ser.close()

    def sendmqtt(self,sensorid,data,head):
        """
            call this method after processing data
        """

        ok = True
        if ok:

            topic = self.confdict.get('station') + '/' + sensorid

            senddata = False
            try:
                coll = int(self.sensordict.get('stack'))
            except:
                coll = 0

            if coll > 1:
                self.metacnt = 1 # send meta data with every block
                if self.datacnt < coll:
                    self.datalst.append(data)
                    self.datacnt += 1
                else:
                    senddata = True
                    data = ';'.join(self.datalst)
                    self.datalst = []
                    self.datacnt = 0
            else:
                senddata = True

            if senddata:
                if self.debug:
                    print ("publishing...")
                self.client.publish(topic+"/data", data, qos=self.qos)
                # If multiple sensors are connected, self.count needs to be a dict (with topic)
                # Initialize counter for each topic
                if self.counter.get(sensorid,'') == '':
                    self.counter[sensorid] = 0
                cnt = self.counter.get(sensorid)

                if cnt == 0:
                    ## 'Add' is a string containing dict info like: 
                    ## SensorID:ENV05_2_0001,StationID:wic, PierID:xxx,SensorGroup:environment,... 
                    add = "SensorID:{},StationID:{},DataPier:{},SensorModule:{},SensorGroup:{},SensorDescription:{},DataTimeProtocol:{}".format( sensorid,self.confdict.get('station','').strip(),self.sensordict.get('pierid','').strip(),self.sensordict.get('protocol','').strip(),self.sensordict.get('sensorgroup','').strip(),self.sensordict.get('sensordesc','').strip(),self.sensordict.get('ptime','').strip() )
                    self.client.publish(topic+"/dict", add, qos=self.qos)
                    self.client.publish(topic+"/meta", head, qos=self.qos)

                cnt += 1
                if cnt >= self.metacnt:
                    cnt = 0
                # update counter in dict 
                self.counter[sensorid] = cnt

