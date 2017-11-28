#!/usr/bin/env python
"""
MQTT collector routine of MARCOS: 
MQTT protocol to be used in the Conrad Observatory.
written by by Roman Leonhardt
 
How should it work:
PURPOSE:
collector_mqtt.py subscribes to published data from MQTT clients.

REQUIREMENTS:
1.) install a MQTT broker (e.g. ubuntu: sudo apt-get install mosquitto mosquitto-clients)
2.) Secure comm and authencation: https://www.digitalocean.com/community/tutorials/how-to-install-and-secure-the-mosquitto-mqtt-messaging-broker-on-ubuntu-16-04

METHODS:
collector_mqtt.py contains the following methods:

GetSensors: read a local definition file (sensors.txt) which contains information
            on SensorID, Port, Bausrate (better Serial communication details), active/passive, 
            init requirements, optional SensorDesc

GetDefaults: read initialization file with local paths, publishing server, ports, etc.

SendInit: send eventually necessary initialization data as defined in sensors.txt

GetActive: Continuously obtain serial data from instrument and convert it to an binary 
           information line to be published (using libraries)

GetPassive: Send scheduled request to serial port to obtain serial data from instrument 
            and convert it to an binary information line to be published (using libraries)

Usage:
python colector_mqtt.py -x -y -z

"""

from __future__ import print_function
from __future__ import absolute_import

# ###################################################################
# Import packages
# ###################################################################

## Import MagPy
## -----------------------------------------------------------
local = True
if local:
    import sys
    sys.path.insert(1,'/home/leon/Software/magpy-git/')

from magpy.stream import *
from magpy.database import *
from magpy.opt import cred as mpcred
#from magpy.collector import collectormethods as cm
# For file export
import StringIO
from magpy.acquisition.acquisitionsupport import dataToFile

## Import MQTT
## -----------------------------------------------------------
import paho.mqtt.client as mqtt
import sys, getopt

# Some global variables
global identifier
identifier = {}
streamdict = {}
stream = DataStream()
headdict = {} # store headerlines for file
headstream = {}

verifiedlocation = False
destination = 'stdout'
location = '/tmp'
credentials = 'cred'
stationid = 'wic'

def append_file(path, array):
    # use data2file method
    pass

def analyse_meta(header,sensorid):
    """
    Interprete header information
    """
    header = header.decode('utf-8')
    
    # some cleaning actions for false header inputs
    header = header.replace(', ',',')
    header = header.replace('deg C','deg')
    h_elem = header.strip().split()
    packstr = '<'+h_elem[-2]+'B'
    packstr = packstr.encode('ascii','ignore')
    lengthcode = struct.calcsize(packstr)
    si = h_elem[2]
    if not si == sensorid:
        print ("Different sensorids in publish address and header - please check - aborting")
        sys.exit()
    keylist = h_elem[3].strip('[').strip(']').split(',')
    elemlist = h_elem[4].strip('[').strip(']').split(',')
    unitlist = h_elem[5].strip('[').strip(']').split(',')
    multilist = list(map(float,h_elem[6].strip('[').strip(']').split(',')))
    if debug:
        print ("Packing code", packstr)
        print ("keylist", keylist)
    identifier[sensorid+':packingcode'] = packstr
    identifier[sensorid+':keylist'] = keylist
    identifier[sensorid+':elemlist'] = elemlist
    identifier[sensorid+':unitlist'] = unitlist
    identifier[sensorid+':multilist'] = multilist

def create_head_dict(header,sensorid):
    """
    Interprete header information
    """
    head_dict={}
    header = header.decode('utf-8')
    # some cleaning actions for false header inputs
    header = header.replace(', ',',')
    header = header.replace('deg C','deg')
    h_elem = header.strip().split()
    packstr = '<'+h_elem[-2]+'B'
    packstr = packstr.encode('ascii','ignore')
    lengthcode = struct.calcsize(packstr)
    si = h_elem[2]
    if not si == sensorid:
        print ("Different sensorids in publish address and header - please check - aborting")
        sys.exit()
    keylist = h_elem[3].strip('[').strip(']').split(',')
    elemlist = h_elem[4].strip('[').strip(']').split(',')
    unitlist = h_elem[5].strip('[').strip(']').split(',')
    multilist = list(map(float,h_elem[6].strip('[').strip(']').split(',')))
    if debug:
        print ("Packing code", packstr)
        print ("keylist", keylist)
    head_dict['SensorID'] = sensorid
    sensl = sensorid.split('_')
    head_dict['SensorName'] = sensl[0]
    head_dict['SensorSerialNumber'] = sensl[1]
    head_dict['SensorRevision'] = sensl[2]
    head_dict['SensorKeys'] = ','.join(keylist)
    head_dict['SensorElements'] = ','.join(elemlist)
    head_dict['StationID'] = stationid
    # possible additional data in header (because in sensor.cfg)
    #head_dict['DataPier'] = ...
    #head_dict['SensorModule'] = ...
    #head_dict['SensorGroup'] = ...
    #head_dict['SensorDescription'] = ...
    l1 = []
    l2 = []
    for idx,key in enumerate(KEYLIST):
        if key in keylist:
            l1.append(elemlist[keylist.index(key)])
            l2.append(unitlist[keylist.index(key)])
        else:
            l1.append('')
            l2.append('')
    head_dict['ColumnContents'] = ','.join(l1[1:])
    head_dict['ColumnUnits'] = ','.join(l2[1:])
    return head_dict

def interprete_data(payload, ident, stream, sensorid):
    lines = payload.split(';') # for multiple lines send within one payload
    # allow for strings in payload !!
    array = [[] for elem in KEYLIST]
    keylist = identifier[sensorid+':keylist']
    multilist = identifier[sensorid+':multilist']
    for line in lines:
        data = line.split(',')
        timear = list(map(int,data[:7]))
        #print (timear)
        time = datetime(timear[0],timear[1],timear[2],timear[3],timear[4],timear[5],timear[6])
        array[0].append(date2num(time))
        for idx, elem in enumerate(keylist):
            index = KEYLIST.index(elem)
            if not elem.endswith('time'):
                if elem in NUMKEYLIST:
                    array[index].append(float(data[idx+7])/float(multilist[idx]))
                else:
                    array[index].append(data[idx+7])

    return np.asarray([np.asarray(elem) for elem in array])

def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    #qos = 1
    print("Setting QOS (Quality of Service): {}".format(qos))
    if str(rc) == '0':
        print ("Everything fine - continuing")
    # important obtain subscription from some config file or provide it directly (e.g. collector -a localhost -p 1883 -t mqtt -s wic)
    substring = stationid+'/#'
    client.subscribe(substring,qos=qos)

def on_message(client, userdata, msg):
    global verifiedlocation
    arrayinterpreted = False
    sensorid = msg.topic.strip(stationid).replace('/','').strip('meta').strip('data').strip('dict')
    # define a new data stream for each non-existing sensor
    metacheck = identifier.get(sensorid+':packingcode','')
    if msg.topic.endswith('meta') and metacheck == '':
        print ("Found basic header:{}".format(str(msg.payload)))
        print ("Quality od Service (QOS):{}".format(str(msg.qos)))
        analyse_meta(str(msg.payload),sensorid)
        if not sensorid in headdict:
            headdict[sensorid] = msg.payload
            # create stream.header dictionary and it here
            headstream[sensorid] = create_head_dict(str(msg.payload),sensorid)
            if debug:
                print ("New headdict", headdict)
    elif msg.topic.endswith('dict') and sensorid in headdict:
        #print ("Found Dictionary:{}".format(str(msg.payload)))
        head_dict = headstream[sensorid]
        for elem in str(msg.payload).split(','):
            keyvaluespair = elem.split(':')
            try:
                if not keyvaluespair[1] in ['-','-\n','-\r\n']:
                    head_dict[keyvaluespair[0]] = keyvaluespair[1].strip()
            except:
                pass
        if debug:
            print ("Dictionary now looks like", headstream[sensorid])
    elif msg.topic.endswith('data'):
        #if debug:
        #    print ("Found data:", str(msg.payload), metacheck)
        if not metacheck == '':
            if 'file' in destination:
                # Import module for writing data from acquistion
                # -------------------
                #if debug:
                #    print (sensorid, metacheck, msg.payload)  # payload can be split
                # Check whether header is already identified 
                # -------------------
                if sensorid in headdict:
                    header = headdict.get(sensorid)
                    packcode = metacheck.strip('<')[:-1] # drop leading < and final B
                    arrayelem = msg.payload.split(';')
                    for ar in arrayelem:
                        datearray = ar.split(',')
                        # identify string values in packcode
                        # -------------------
                        if not 's' in packcode:
                            datearray = list(map(int, datearray))
                        else:
                            stringidx = []
                            for i in range(len(packcode)):
                                if packcode[-i] == 's':
                                    stringidx.append(i)
                            for i in range(len(datearray)):
                                if not i in stringidx:
                                    datearray[-i] = int(datearray[-i])
                        # pack data using little endian byte order
                        data_bin = struct.pack('<'+packcode,*datearray)
                        # Check whether destination path has been verified already 
                        # -------------------
                        if not verifiedlocation:
                            if not location in [None,''] and os.path.exists(location):
                                verifiedlocation = True
                            else:
                                print ("File: destination location {} is not accessible".format(location))
                                print ("      -> please use option l (e.g. -l '/my/path') to define") 
                        if verifiedlocation:
                            filename = "{}-{:02d}-{:02d}".format(datearray[0],datearray[1],datearray[2])
                            dataToFile(location, sensorid, filename, data_bin, header)
            if 'stdout' in destination:
                if not arrayinterpreted:
                    stream.ndarray = interprete_data(msg.payload, identifier, stream, sensorid)
                    #streamdict[sensorid] = stream.ndarray  # to store data from different sensors
                    arrayinterpreted = True
                for idx,el in enumerate(stream.ndarray[0]):
                    time = num2date(el).replace(tzinfo=None)
                    datastring = ','.join([str(val[idx]) for i,val in enumerate(stream.ndarray) if len(val) > 0 and not i == 0])
                    print ("{}: {},{}".format(sensorid,time,datastring))
            elif 'db' in destination:
                if not arrayinterpreted:
                    stream.ndarray = interprete_data(msg.payload, identifier, stream, sensorid)
                    #streamdict[sensorid] = stream.ndarray  # to store data from different sensors
                    arrayinterpreted = True
                # create a stream.header
                #if debug:
                #    print (stream.ndarray)
                stream.header = headstream[sensorid]
                #print ("header", stream.header)
                writeDB(db,stream)
                #sys.exit()
            elif 'stringio' in destination:
                if not arrayinterpreted:
                    stream.ndarray = interprete_data(msg.payload, identifier, stream, sensorid)
                    #streamdict[sensorid] = stream.ndarray  # to store data from different sensors
                    arrayinterpreted = True
                for idx,el in enumerate(stream.ndarray[0]):
                    time = num2date(el).replace(tzinfo=None)
                    date = datetime.strftime(time,"%Y-%m-%d %H:%M:%S.%f")
                    linelist = list(map(str,[el,date]))
                    linelist.extend([str(val[idx]) for i,val in enumerate(stream.ndarray) if len(val) > 0 and not i == 0])
                    line = ','.join(linelist)
                    eol = '\r\n'
                    output.write(line+eol)
            else:
                pass
        else:
            print(msg.topic + " " + str(msg.payload))

def main(argv):
    #broker = '192.168.178.75'
    broker = 'localhost'  # default
    #broker = '192.168.178.84'
    #broker = '192.168.0.14'
    port = 1883
    timeout=60
    global destination
    destination='stdout'
    global location
    location='/tmp'
    global credentials
    credentials=''
    global dbcred
    dbcred=''
    global stationid
    stationid = 'wic'
    global qos
    qos=0
    global debug
    debug = False
    global output
    global headstream
    headstream = {}
    #global verifiedlocation
    #verifiedlocation = False
    global dictcheck
    dictcheck = False

    usagestring = 'collector.py -b <broker> -p <port> -t <timeout> -o <topic> -d <destination> -l <location> -c <credentials> -r <dbcred> -q <qos>'
    try:
        opts, args = getopt.getopt(argv,"hb:p:t:o:d:l:c:r:q:u",["broker=","port=","timeout=","topic=","destination=","location=","credentials=","dbcred=","qos=","debug=",])
    except getopt.GetoptError:
        print('Check your options:')
        print(usagestring)
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('------------------------------------------------------')
            print('Usage:')
            print(usagestring)
            print('------------------------------------------------------')
            print('Options:')
            print('-h                             help')
            print('-b                             set broker address: default = localhost')
            print('-p                             set port - default is 1883')
            print('-t                             set timeout - default is 60')
            print('-o                             set base topic - for MARTAS this corresponds')
            print('                               to the station ID (e.g. wic)')
            print('-d                             set destination - std.out, db, file') 
            print('                               default is std.out') 
            print('-l                             set location depending on destination')
            print('                               if d="file": provide path')
            print('                               if d="db": provide db credentials')
            print('                               if d="std.out": not used')
            print('-c                             set mqtt communication credential keyword')
            print('-q                             set mqtt quality of service (default = 0)')            
            print('-r                             set db credential keyword')            
            print('------------------------------------------------------')
            print('Examples:')
            print('1. Basic')
            print('   python collector.py -b "192.168.0.100" -o wic')
            print('2. Writing to file in directory "/my/path/"')
            print('   python collector.py -b "192.168.0.100" -d file -l "/my/path" -o wic')
            print('3. Writing to file and stdout')
            print('   python collector.py -b "192.168.0.100" -d file,stdout -l "/tmp" -o wic')
            print('4. Writing to db')
            print('   python collector.py -b "192.168.0.100" -d db -r mydb -o wic')
            print('   python collector.py -d "db,file" -r testdb')
            sys.exit()
        elif opt in ("-b", "--broker"):
            broker = arg
        elif opt in ("-p", "--port"):
            try:
                port = int(arg)
            except:
                port = arg
        elif opt in ("-t", "--timeout"):
            try:
                timeout = int(arg)
            except:
                timeout = arg
        elif opt in ("-o", "--topic"):
            stationid = arg
        elif opt in ("-d", "--destination"):
            destination = arg
        elif opt in ("-l", "--location"):
            location = arg
        elif opt in ("-c", "--credentials"):
            credentials = arg
        elif opt in ("-r", "--dbcred"):
            dbcred = arg
        elif opt in ("-q", "--qos"):
            try:
                qos = int(arg)
            except:
                qos = 0
        elif opt in ("-u", "--debug"):
            debug = True

    if not qos in [0,1,2]:
        qos = 0
    if 'stringio' in destination:
        output = StringIO.StringIO()
    if 'file' in destination:
        if location in [None,''] and not os.path.exists(location):
            print ('destination "file" requires a valid path provided as location')
            print (' ... aborting ...')
            sys.exit()
    if 'db' in destination:
        if dbcred in [None,'']:
            print ('destination "db" requires database credentials')
            print ('to create them use method "addcred"')
            print ('to provide use option -r like -r mydb')
            sys.exit()
        else:
            try:
                global db
                if debug:
                    print ("Connecting database {} at host {} with user {}".format(mpcred.lc(dbcred,'db'),mpcred.lc(dbcred,'host'),mpcred.lc(dbcred,'user')))
                db = mysql.connect(host=mpcred.lc(dbcred,'host'),user=mpcred.lc(dbcred,'user'),passwd=mpcred.lc(dbcred,'passwd'),db=mpcred.lc(dbcred,'db'))
            except:
                print ('database coul not be connected')
                print (' ... aborting ...')
                sys.exit()            

    if debug:
        print ("Option u: debug mode switched on ...")
        print ("------------------------------------")
        print ("Destination", destination, location)
    client = mqtt.Client()

    # Authentication part
    #client.tls_set(tlspath)  # check http://www.steves-internet-guide.com/mosquitto-tls/
    #client.username_pw_set(user, password=password)  # defined on broker by mosquitto_passwd -c passwordfile user

    client.on_connect = on_connect

    # on message needs: stationid, destination, location
    client.on_message = on_message

    client.connect(broker, port, timeout)

    client.loop_forever()



if __name__ == "__main__":
   main(sys.argv[1:])

