#!/usr/bin/env python
"""
MQTT collector routine of MARCOS:
MQTT protocol as used at the Conrad Observatory.
written by Roman Leonhardt
"""
# ###################################################################
# Import packages
# ###################################################################

## Import MagPy
## -----------------------------------------------------------

from magpy.stream import DataStream, KEYLIST, NUMKEYLIST, subtract_streams
from magpy.core import database
from magpy.opt import cred as mpcred

## Import Twisted for websocket and logging functionality
from twisted.python import log
from twisted.web.server import Site
from twisted.web.static import File
from twisted.internet import reactor

import threading
from multiprocessing import Process
import struct
from datetime import datetime
from matplotlib.dates import num2date
import numpy as np
import json
import socket
from io import StringIO

## Import specific MARTAS packages
## -----------------------------------------------------------
from martas.core import methods as mm
from martas.version import __version__
from martas.core.methods import martaslog as ml
from martas.core.websocket_server import WebsocketServer

## Import MQTT
## -----------------------------------------------------------
import paho.mqtt
import paho.mqtt.client as mqtt
import sys, getopt, os
import ssl
try:
    from sslpsk2.sslpsk2 import _ssl_set_psk_server_callback, _ssl_set_psk_client_callback
except:
    pass


## Python Version
## -----------------------------------------------------------
import platform
pyversion = platform.python_version()

## Import Webserver for displaying data
## -----------------------------------------------------------
ws_available = True

# Some variable initialization
## -----------------------------------------------------------
#global counter  # use for diffcalc

qos = 0
streamdict = {}
stream = DataStream()
st = []
senslst = []
headdict = {} # store headerlines for all sensors (headerline are firstline for BIN files)
headstream = {}
verifiedlocation = False
destination = 'stdout'
location = '/tmp'
credentials = 'cred'
stationid = 'WIC'
stid = stationid
webpath = './web'
webport = 8080
socketport = 5000
diffsens = "G823"
blacklist = []
counter = 0

## SSL PSK tools
def _ssl_setup_psk_callbacks(sslobj):
    psk = sslobj.context.psk
    hint = sslobj.context.hint
    identity = sslobj.context.identity
    if psk:
        if sslobj.server_side:
            cb = psk if callable(psk) else lambda _identity: psk
            _ssl_set_psk_server_callback(sslobj, cb, hint)
        else:
            cb = psk if callable(psk) else lambda _hint: psk if isinstance(psk, tuple) else (psk, identity)
            _ssl_set_psk_client_callback(sslobj, cb)


class SSLPSKContext(ssl.SSLContext):
    @property
    def psk(self):
        return getattr(self, "_psk", None)

    @psk.setter
    def psk(self, psk):
        self._psk = psk

    @property
    def hint(self):
        return getattr(self, "_hint", None)

    @hint.setter
    def hint(self, hint):
        self._hint = hint

    @property
    def identity(self):
        return getattr(self, "_identity", None)

    @identity.setter
    def identity(self, identity):
        self._identity = identity


class SSLPSKObject(ssl.SSLObject):
    def do_handshake(self, *args, **kwargs):
        if not hasattr(self, '_did_psk_setup'):
            _ssl_setup_psk_callbacks(self)
            self._did_psk_setup = True
        super().do_handshake(*args, **kwargs)


class SSLPSKSocket(ssl.SSLSocket):
    def do_handshake(self, *args, **kwargs):
        if not hasattr(self, '_did_psk_setup'):
            _ssl_setup_psk_callbacks(self)
            self._did_psk_setup = True
        super().do_handshake(*args, **kwargs)


SSLPSKContext.sslobject_class = SSLPSKObject
SSLPSKContext.sslsocket_class = SSLPSKSocket


class protocolparameter(object):
    def __init__(self):
        self.identifier = {}
        #self.counter = 0

po = protocolparameter()

## WebServer Methods
## -----------------------------------------------------------
def wsThread(wsserver):
    wsserver.set_fn_new_client(new_wsclient)
    wsserver.set_fn_message_received(message_received)
    wsserver.run_forever()

if ws_available:
    global wsserver

# TODO: find a way how to use these two functions:
def new_wsclient(ws_client,server):
    pass
    # for debug: see which threads are running:
    #print(str(threading.enumerate()))

def message_received(ws_client,server,message):
    pass

def webProcess(webpath,webport):
    """
    These few lines will be started as an own process.
    When the main process is killed, also this child process is killed
    because of having it started as a daemon
    """
    resource = File(webpath)
    print ("TESTING", webpath, resource)
    factory = Site(resource)
    #endpoint = endpoints.TCP4ServerEndpoint(reactor, 8888)
    #endpoint.listen(factory)
    # args! -> make an integer out of it
    webport = int(webport)
    reactor.listenTCP(webport,factory)
    reactor.run()

def connectclient(broker='localhost', port=1883, timeout=60, credentials='', user='', password='', qos=0, mqttcert="", mqttpsk="", mqttversion=2, destinationid='',debug=False):
        """
    connectclient method
    used to connect to a specific client as defined by the input variables
    eventually add multiple client -> {"clients":[{"broker":"192.168.178.42","port":"1883"}]} # json type
                import json
                altbro = json.loads(altbrocker)
        """
        ## create a unique clientid consisting of broker, client and destination
        client = None
        hostname = socket.gethostname()
        clientid = "{}{}{}".format(broker,hostname,destinationid)

        ## create MQTT client
        ##  ----------------------------
        pahovers = paho.mqtt.__version__
        pahomajor = int(pahovers[0])
        print(" paho-mqtt version ", pahovers)
        try:
            client = mqtt.Client(clientid, False)
        except:
            try:
                client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=clientid)
            except:
                client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=clientid)

        # TLS encryption part
        if int(port) == 8883 and not mqttpsk:
            if mqttcert:
                if debug:
                    print("MQTT: TLS encryption based on certificate")
                    print(mqttcert)
                client.tls_set(ca_certs=mqttcert)
            else:
                if debug:
                    print("MQTT: basic TLS")
                client.tls_set(ca_certs=None, certfile=None, keyfile=None, cert_reqs=ssl.CERT_REQUIRED,
                               tls_version=ssl.PROTOCOL_TLS,
                               ciphers=None)
        if int(port) in [8884, 8883] and mqttpsk:
            if debug:
                print("MQTT: TLS encrytion based in PSK")
            # making use of discussions in https://github.com/eclipse-paho/paho.mqtt.python/issues/451
            pskidentity = mpcred.lc(mqttpsk, 'user')
            pskpwd = mpcred.lc(mqttpsk, 'passwd')
            #context = SSLPSKContext(ssl.PROTOCOL_TLS_CLIENT) # This does bot work for beaglebone (python3.11 clients)
            print ("MARTAS: Deprecation warning - but necessary for old clients")
            context = SSLPSKContext(ssl.PROTOCOL_TLSv1_2)
            context.set_ciphers('PSK')
            context.psk = bytes.fromhex(pskpwd)
            context.identity = pskidentity.encode()
            client.tls_set_context(context)  # Here we apply the new `SSLPSKContext`

        # Authentication part
        if not credentials in ['','-']:
            # use user and pwd from credential data if not yet set
            if user in ['',None,'None','-']:
                user = mpcred.lc(credentials,'user')
            if password  in ['','-']:
                password = mpcred.lc(credentials,'passwd')
        if not user in ['',None,'None','-']:
            #client.tls_set(tlspath)  # check http://www.steves-internet-guide.com/mosquitto-tls/
            client.username_pw_set(user, password=password)  # defined on broker by mosquitto_passwd -c passwordfile user
        client.on_connect = on_connect
        # on message needs: stationid, destination, location
        client.on_message = on_message
        client.connect(broker, port, timeout)

        return client


def analyse_meta(header,sensorid,debug=False):
    """
    source:mqtt:
    Interprete header information
    """
    if debug:
        print ("Analyzing {}: {}".format(sensorid,header))
    if pyversion.startswith('2'):
        header = header.decode('utf-8')
    # some cleaning actions for false header inputs
    header = header.replace(', ',',')
    header = header.replace('deg C','deg')
    header = header.replace('T (out','T(out')
    h_elem = header.strip().split()
    if not h_elem[-2].startswith('<'): # e.g. LEMI
        packstr = '<'+h_elem[-2]+'B'
    else:
        packstr = h_elem[-2]
    packstr = packstr.encode('ascii','ignore')
    lengthcode = struct.calcsize(packstr)
    si = h_elem[2]
    if not si == sensorid:
        log.msg("Different sensorids in publish address {} and header {} - please check - aborting".format(sensorid,si))
        sys.exit()
    keylist = h_elem[3].strip('[').strip(']').split(',')
    elemlist = h_elem[4].strip('[').strip(']').split(',')
    unitlist = h_elem[5].strip('[').strip(']').split(',')
    multilist = list(map(float,h_elem[6].strip('[').strip(']').split(',')))
    if debug:
        log.msg("Packing code: {}".format(packstr))
        log.msg("keylist: {}".format(keylist))
    po.identifier[sensorid+':packingcode'] = packstr
    po.identifier[sensorid+':keylist'] = keylist
    po.identifier[sensorid+':elemlist'] = elemlist
    po.identifier[sensorid+':unitlist'] = unitlist
    po.identifier[sensorid+':multilist'] = multilist


def create_head_dict(header,sensorid):
    """
    source:mqtt:
    Interprete header information
    """
    head_dict={}
    try:
        # python2.7
        header = header.decode('utf-8')
    except:
        pass
    # some cleaning actions for false header inputs
    header = header.replace(', ',',')
    header = header.replace('deg C','deg')
    h_elem = header.strip().split()
    if not h_elem[-2].startswith('<'):
        packstr = '<'+h_elem[-2]+'B'
    else: # LEMI
        packstr = h_elem[-2]
    packstr = packstr.encode('ascii','ignore')
    lengthcode = struct.calcsize(packstr)
    si = h_elem[2]
    if not si == sensorid:
        log.msg("Different sensorids in publish address {} and header {} - please check - aborting".format(si,sensorid))
        sys.exit()
    keylist = h_elem[3].strip('[').strip(']').split(',')
    elemlist = h_elem[4].strip('[').strip(']').split(',')
    unitlist = h_elem[5].strip('[').strip(']').split(',')
    multilist = list(map(float,h_elem[6].strip('[').strip(']').split(',')))
    if debug:
        log.msg("Packing code: {}".format(packstr))
        log.msg("keylist: {}".format(keylist))
    head_dict['SensorID'] = sensorid
    sensl = sensorid.split('_')
    head_dict['SensorName'] = sensl[0]
    head_dict['SensorSerialNum'] = sensl[1]
    head_dict['SensorRevision'] = sensl[2]
    head_dict['SensorKeys'] = ','.join(keylist)
    head_dict['SensorElements'] = ','.join(elemlist)
    head_dict['StationID'] = stid.upper()
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

def interprete_data(payload, sensorid):
    """
    source:mqtt:
    """
    # future: check for json payload first

    lines = payload.split(';') # for multiple lines send within one payload
    # allow for strings in payload !!
    array = [[] for elem in KEYLIST]
    keylist = po.identifier[sensorid+':keylist']
    multilist = po.identifier[sensorid+':multilist']
    for line in lines:
        data = line.split(',')
        timear = list(map(int,data[:7]))
        #log.msg(timear)
        time = datetime(timear[0],timear[1],timear[2],timear[3],timear[4],timear[5],timear[6])
        array[0].append(time)
        for idx, elem in enumerate(keylist):
            try:
                index = KEYLIST.index(elem)
                if not elem.endswith('time'):
                    if elem in NUMKEYLIST:
                        array[index].append(float(data[idx+7])/float(multilist[idx]))
                    else:
                        array[index].append(data[idx+7])
            except:
                # might fail with list index out of range - take all others
                pass

    return np.asarray([np.asarray(elem) for elem in array],dtype=object)

def merge_two_dicts(x, y):
        z = x.copy()   # start with x's keys and values
        z.update(y)    # modifies z with y's keys and values & returns None
        return z

def on_connect(client, userdata, flags, rc, properties=None):
    global concount
    global debug
    if debug or not concount:
        log.msg("Connected with result code {}".format(str(rc)))
    global qos
    if debug or not concount:
        log.msg("Setting QOS (Quality of Service): {}".format(qos))
    if str(rc) == '0':
        pass
    elif str(rc) == '5':
        log.msg("Broker eventually requires authentication - use options -u and -P")
    # important obtain subscription from some config file or provide it directly (e.g. collector -a localhost -p 1883 -t mqtt -s wic)
    if stationid in ['all','All','ALL']:
        substring = '#'
    else:
        substring = stationid+'/#'
    if debug or not concount:
        log.msg("Subscribing to {} with qos {}".format(substring,qos))
    concount += 1
    client.subscribe(substring,qos=qos)

def on_message(client, userdata, msg):
    if not stationid in ['all','All','ALL']:
        if not msg.topic.startswith(stationid):
            return

    if not pyversion.startswith('2'):
       msg.payload= msg.payload.decode('ascii')

    global qos
    global verifiedlocation
    global debug
    global stid
    digit = 0
    arrayinterpreted = False
    wsarrayinterpreted = False
    diarrayinterpreted = False
    siarrayinterpreted = False
    soarrayinterpreted = False
    dbarrayinterpreted = False
    if stationid in ['all','All','ALL']:
        stid = msg.topic.split('/')[0]
    else:
        stid = stationid
    try:
        sensorind = msg.topic.split('/')[1]
        sensorid = sensorind.replace('meta','').replace('data','').replace('dict','')
    except:
        # Above will fail if msg.topic does not contain /
        # TODO (previous version was without 1, first occurrence -> the following line should work as well although the code above is more general)
        sensorid = msg.topic.replace(stid,"",1).replace('/','').replace('meta','').replace('data','').replace('dict','')
    # define a new data stream for each non-existing sensor
    if not instrument == '':
        if not sensorid.find(instrument) > -1:
            return

    if sensorid in blacklist:
        if debug:
            print ("Sensor {} in blacklist - not collecting".format(sensorid))
        return

    ## ################################################################################
    ## ####            Eventually check for additional format libraries       #########
    ## ################################################################################
    identdic = {}

    if addlib and len(addlib) > 0:
            # Currently only one additional library is supported
            lib = addlib[0]
            #for lib in addlib:
            elemlist = []
            for elem in topic_identifiers[lib]:
                strelem = "msg.topic.{}('{}')".format(elem,topic_identifiers[lib][elem])
                elemlist.append(strelem)
            if len(elemlist) > 1:
                teststring = " and ".join(elemlist)
            else:
                teststring = "".join(elemlist)
            if eval(teststring):
                classref = class_reference.get(lib)
                #print ("1", msg.payload)
                try:
                    msg.payload, sensorid, headerline, headerdictionary, identdic = classref.GetPayload(msg.payload,msg.topic)
                except:
                    print ("Interpretation error for {}".format(msg.topic))
                    return
                #print (payload, sensorid, headerline)
                headdict[sensorid] = headerline
                headstream[sensorid] = create_head_dict(headerline,sensorid)
                headstream[sensorid] = merge_two_dicts(headstream[sensorid], headerdictionary)
                msg.topic = msg.topic+'/data'
                for el in identdic:
                    po.identifier[el] = identdic[el]

    metacheck = po.identifier.get(sensorid+':packingcode','')


    ## ################################################################################

    if msg.topic.endswith('meta') and metacheck == '':
        log.msg("Found basic header:{}".format(str(msg.payload)))
        log.msg("Quality of Service (QOS):{}".format(str(msg.qos)))
        analyse_meta(str(msg.payload),sensorid,debug=debug)
        if not sensorid in headdict:
            headdict[sensorid] = msg.payload
            # create stream.header dictionary and it here
            headstream[sensorid] = create_head_dict(str(msg.payload),sensorid)
            if debug:
                log.msg("New headdict: {}".format(headdict))
    elif msg.topic.endswith('dict') and sensorid in headdict:
        #log.msg("Found Dictionary:{}".format(str(msg.payload)))
        head_dict = headstream[sensorid]
        for elem in str(msg.payload).split(','):
            keyvaluespair = elem.split(':')
            try:
                if not keyvaluespair[1] in ['-','-\n','-\r\n']:
                    head_dict[keyvaluespair[0]] = keyvaluespair[1].strip()
            except:
                pass
        if debug:
            log.msg("Dictionary now looks like {}".format(headstream[sensorid]))
    elif msg.topic.endswith('data'):  # or readable json
        #if readable json -> create stream.ndarray and set arrayinterpreted :
        #    log.msg("Found data:", str(msg.payload), metacheck)
        if not metacheck == '':
            if 'file' in destination:
                # Import module for writing data from acquistion
                # -------------------
                #if debug:
                #    log.msg(sensorid, metacheck, msg.payload)  # payload can be split
                # Check whether header is already identified
                # -------------------
                if sensorid in headdict:
                    header = headdict.get(sensorid)
                    if sys.version_info >= (3,0):
                        metacheck = metacheck.decode()
                    if metacheck.endswith('B'):
                        packcode = metacheck.strip('<')[:-1] # drop leading < and final B
                    else:
                        packcode = metacheck.strip('<') # drop leading <
                    # temporary code - too be deleted when lemi protocol has been updated
                    if packcode.find('4cb6B8hb30f3Bc') >= 0:
                        header = header.replace('<4cb6B8hb30f3BcBcc5hL 169\n','6hLffflll {}'.format(struct.calcsize('<6hLffflll')))
                        packcode = '6hLffflll' 
                    arrayelem = msg.payload.split(';')
                    for ar in arrayelem:
                        datearray = ar.split(',')
                        # identify string values in packcode
                        # -------------------
                        # convert packcode numbers
                        cpack = []
                        for c in packcode:
                            if c.isdigit():
                                digit = int(c)
                            else:
                                cpack.extend([c] * digit)
                                digit=1
                        cpackcode = "".join(cpack)
                        for i in range(len(cpackcode)):
                            if cpackcode[-i] == 's':
                                datearray[-i] = datearray[-i]
                            elif cpackcode[-i] == 'f':
                                datearray[-i] = float(datearray[-i])
                            else:
                                datearray[-i] = int(float(datearray[-i]))
                        # pack data using little endian byte order
                        data_bin = struct.pack('<'+packcode,*datearray)
                        # Check whether destination path has been verified already
                        # -------------------
                        if not verifiedlocation:
                            if not location in [None,''] and os.path.exists(location):
                                verifiedlocation = True
                            else:
                                log.msg("File: destination location {} is not accessible".format(location))
                                log.msg("      -> please use option l (e.g. -l '/my/path') to define") 
                        if verifiedlocation:
                            filename = "{}-{:02d}-{:02d}".format(datearray[0],datearray[1],datearray[2])
                            mm.data_to_file(location, sensorid, filename, data_bin, header)
            if 'websocket' in destination:
                if not wsarrayinterpreted:
                    stream.ndarray = interprete_data(msg.payload, sensorid)
                    #streamdict[sensorid] = stream.ndarray  # to store data from different sensors
                    wsarrayinterpreted = True
                for idx,dt in enumerate(stream.ndarray[0]):
                    msecSince1970 = int((dt - datetime(1970,1,1)).total_seconds()*1000)
                    datastring = ','.join([str(val[idx]) for i,val in enumerate(stream.ndarray) if len(val) > 0 and not i == 0])
                    if debug:
                        print ("Sending {}: {},{} to webserver".format(sensorid, msecSince1970,datastring))
                    wsserver.send_message_to_all("{}: {},{}".format(sensorid,msecSince1970,datastring))
            if 'diff' in destination:
                global counter
                global number
                counter+=1
                amount = int(number)
                cover = 5
                if sensorid.find(diffsens) >= 0:
                    if not diarrayinterpreted:
                        ar = interprete_data(msg.payload, sensorid)
                        if not sensorid in senslst:
                            senslst.append(sensorid)
                            ds = DataStream(header={"SensorID":sensorid}, ndarray=ar)
                            ds = ds.cut(5,1,0)
                            st.append(ds)
                        diarrayinterpreted = True

                    if len(st) < 2:
                         print ("Not enough streams for subtraction yet")
                    try:
                        if counter > amount and len(st) > 2:
                            counter = 0
                            sub = subtract_streams(st[0],st[1])
                            print (sub)
                            try:
                                part1 = (st[0].header.get('SensorID').split('_')[1])
                            except:
                                part1 = 'unkown'
                            try:
                                part2 = (st[1].header.get('SensorID').split('_')[1])
                            except:
                                part2 = 'unkown'
                            name = "Diff_{}{}_0001".format(part1,part2)
                            # get head line for pub
                            keys = sub._get_key_headers(numerical=True)
                            ilst = [KEYLIST.index(key) for key in keys]
                            keystr = "[{}]".format(",".join(keys))
                            #takeunits =  ### take from st[0]
                            packcode = "6hL{}".format("".join(['l']*len(keys)))
                            multi = "[{}]".format(",".join(['1000']*len(keys)))
                            unit = "[{}]".format(",".join(['arb']*len(keys)))
                            head = "# MagPyBin {} {} {} {} {} {} {}".format(name, keystr, keystr, unit, multi, packcode, struct.calcsize('<'+packcode))
                            #print (head)
                            # get data line for pub
                            time = sub.ndarray[0][-1]
                            timestr = (datetime.strftime(time, "%Y,%m,%d,%H,%M,%S,%f"))
                            val = [sub.ndarray[i][-1] for i in ilst]
                            if len(val) > 1:
                                valstr = ",".join(int(val*1000))
                            else:
                                valstr = int(val[0]*1000)
                            data = "{},{}".format(timestr,valstr)
                            #print (data)
                            topic = "{}/{}".format(stid,name)
                            client.publish(topic+"/data", data, qos=qos)
                            client.publish(topic+"/meta", head, qos=qos)
                            if debug:
                                print (" -> diff {} published".format(name))
                    except:
                        print ("Found error in subtraction")
            if 'stdout' in destination:
                if not soarrayinterpreted:
                    stream.ndarray = interprete_data(msg.payload, sensorid)
                    #streamdict[sensorid] = stream.ndarray  # to store data from different sensors
                    soarrayinterpreted = True
                for idx,dt in enumerate(stream.ndarray[0]):
                    datastring = ','.join([str(val[idx]) for i,val in enumerate(stream.ndarray) if len(val) > 0 and not i == 0])
                    log.msg("{}: {},{}".format(sensorid, dt, datastring))
            elif 'db' in destination:
                if not dbarrayinterpreted:
                    stream.ndarray = interprete_data(msg.payload, sensorid)
                    #streamdict[sensorid] = stream.ndarray  # to store data from different sensors
                    dbarrayinterpreted = True
                # create a stream.header
                if debug:
                    log.msg(stream.ndarray)
                stream.header = headstream[sensorid]
                if debug:
                    log.msg("writing header: {}".format(headstream[sensorid]))
                if revision != 'free':
                    db.write(stream,tablename="{}_{}".format(sensorid,'0001'))
                else:
                    db.write(stream)
            elif 'stringio' in destination:
                if not siarrayinterpreted:
                    stream.ndarray = interprete_data(msg.payload, sensorid)
                    #streamdict[sensorid] = stream.ndarray  # to store data from different sensors
                    siarrayinterpreted = True
                for idx,dt in enumerate(stream.ndarray[0]):
                    date = datetime.strftime(dt,"%Y-%m-%d %H:%M:%S.%f")
                    linelist = list(map(str,[dt,date]))
                    linelist.extend([str(val[idx]) for i,val in enumerate(stream.ndarray) if len(val) > 0 and not i == 0])
                    line = ','.join(linelist)
                    eol = '\r\n'
                    output.write(line+eol)
            else:
                pass
        else:
            log.msg("Non-interpreted format: {}  {}".format(msg.topic, str(msg.payload)))
    elif msg.topic and msg.topic.find('statuslog') > 0:
        # json style statusinfo is coming
        hostname = msg.topic.split('/')[-1]
        #log.msg("---------------------------------------------------------------")
        #log.msg("Receiving updated status information from {}".format(hostname))
        #log.msg("---------------------------------------------------------------")
        print ("FOUND STATUS CHANGE", telegramconf)
        statusdict = json.loads(msg.payload)
        for elem in statusdict:
            logmsg = "{}: {} - {}".format(hostname, elem, statusdict[elem])
            # For Nagios - add in marcos.log
            log.msg(logmsg)
        # For Telegram
        try:
            # try to import telegram and telegram.cfg
            ##### Add the configuration to input and marcos.cfg
            ## Please note: requires anaconda2/bin/python on my test PC
            ## !!! Requires network connection !!!
            if telegramconf and os.path.isfile(telegramconf):
                martaslog = ml(receiver='telegram')
                martaslog.receiveroptions('telegram',options={'conf':telegramconf})
                statusdict['Hostname'] = hostname
                martaslog.notify(statusdict)
        except:
            pass

        #telegram.send(msg)

    if msg.topic.endswith('meta') and 'websocket' in destination:
        # send header info for each element (# sensorid   nr   key   elem   unit)
        analyse_meta(str(msg.payload),sensorid)
        for (i,void) in enumerate(po.identifier[sensorid+':keylist']):
            jsonstr={}
            jsonstr['sensorid'] = sensorid
            jsonstr['nr'] = i
            jsonstr['key'] = po.identifier[sensorid+':keylist'][i]
            jsonstr['elem'] = po.identifier[sensorid+':elemlist'][i]
            jsonstr['unit'] = po.identifier[sensorid+':unitlist'][i]
            payload = json.dumps(jsonstr)
            wsserver.send_message_to_all('# '+payload)


def main(argv):
    broker = 'localhost'  # default
    port = 1883
    timeout=60
    altbroker = ''
    user = ''
    password = ''
    logging = 'sys.stdout'
    global destination
    destination='stdout'
    global location
    location='/tmp'
    global credentials
    credentials=''
    global offset
    offset = ''
    global dbcred
    dbcred=''
    global stationid
    stationid = 'wic'
    global stid
    stid = stationid
    global webpath
    webpath = './web'
    global webport
    webport = 8080
    global instrument
    instrument = ''
    global revision
    revision = 'fix'
    global telegramconf
    telegramconf = ''
    global addlib
    addlib = []
    global source
    source='mqtt' # projected sources: mqtt (default), wamp, mysql, postgres, etc
    global debug
    debug = False
    global output
    global headstream
    headstream = {}
    global topic_identifiers
    topic_identifiers = {}
    global class_reference
    class_reference = {}
    #global verifiedlocation
    #verifiedlocation = False
    global dictcheck
    dictcheck = False
    global socketport
    global number
    number = 1
    global qos
    qos=0
    global blacklist
    blacklist = []
    global diffsens
    global concount
    concount = 0
    conf = {}


    usagestring = 'collector.py -b <broker> -p <port> -t <timeout> -o <topic> -i <instrument> -d <destination> -v <revision> -l <location> -c <credentials> -r <dbcred> -q <qos> -u <user> -P <password> -s <source> -f <offset> -m <marcos> -n <number> -e <telegramconf> -a <addlib>'
    try:
        opts, args = getopt.getopt(argv,"hb:p:t:o:i:d:vl:c:r:q:u:P:s:f:m:n:e:a:U",["broker=","port=","timeout=","topic=","instrument=","destination=","revision=","location=","credentials=","dbcred=","qos=","debug=","user=","password=","source=","offset=","marcos=","number=","telegramconf=","addlib="])
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
            print ('-b                             set broker address: default = localhost')
            print ('-p                             set port - default is 1883')
            print ('-t                             set timeout - default is 60')
            print ('-o                             set base topic - for MARTAS this corresponds')
            print ('                               to the station ID (e.g. wic)')
            print ('                               use "-o all" to get all stationids at a specific broker')
            print ('-i                             choose instrument(s) - only sensors containing')
            print ('                               the provided string are used: ')
            print ('                               -i GSM  will access GSM90_xxx and GSM19_xyz ')
            print ('                               Default is to use all')
            print ('-d                             set destination - std.out, db, file') 
            print ('                               default is std.out') 
            print ('-v                             (no option)') 
            print ('                               if provided: meta information will be added, revision') 
            print ('                                     automatically assigned.') 
            print ('                               if not set: revision 0001 will be used, no meta.') 
            print ('-l                             set location depending on destination')
            print ('                               if d="file": provide path')
            print ('                               if d="std.out": not used')
            print ('-c                             set mqtt communication credential keyword')
            print ('-q                             set mqtt quality of service (default = 0)')            
            print ('-r                             set db credential keyword')            
            print ('-s                             source protocol of data: default is mqtt')            
            print ('                               other options:')
            print ('                               -s wamp    not yet implemented.')
            print ('-f                             offset values. Can either be "db" for')
            print ('                               applying delta values from db or a string')
            print ('                               of the following format (key:value):')
            print ('                               -f "t1:3.234,x:45674.2"')
            print ('                               other options:')
            print ('-m                             marcos configuration file ')
            print ('                               e.g. "/home/cobs/marcos.cfg"')
            print ('-n                             provide a integer number ')
            print ('                               "-d diff -i GSM": difference of two GSM will')
            print ('                                                 be calculated every n th step.')
            print ('-e                             provide a path to telegram configuration for ')
            print ('                               sending critical log changes.')
            print ('-a                             additional MQTT translation library ')
            print ('------------------------------------------------------')
            print ('Examples:')
            print ('1. Basic')
            print ('   python collector.py -b "192.168.0.100" -o wic')
            print ('2. Writing to file in directory "/my/path/"')
            print ('   python collector.py -b "192.168.0.100" -d file -l "/my/path" -o wic')
            print ('3. Writing to file and stdout')
            print ('   python collector.py -b "192.168.0.100" -d file,stdout -l "/tmp" -o wic')
            print ('4. Writing to db')
            print ('   python collector.py -b "192.168.0.100" -d db -r mydb -o wic')
            print ('   python collector.py -d "db,file" -r testdb')
            print ('5. Using configuration file')
            print ('   python collector.py -m "/path/to/marcos.cfg"')
            print ('6. Overriding individual parameters from config file')
            print ('   python collector.py -m "/path/to/marcos.cfg" -b "192.168.0.100"')
            print ('   (make sure that config is called first)')
            print ('7. Calculating differences/gradients on the fly:')
            print ('   python collector.py -d diff -i G823A -n 10')
            print ('   (will calculate the diffs of two G823A every 10th record)')
            sys.exit()
        elif opt in ("-m", "--marcos"):
            marcosfile = arg
            print ("Getting all parameters from configration file: {}".format(marcosfile))
            conf = mm.get_conf(marcosfile)
            if not conf.get('logging','') == '':
                logging = conf.get('logging').strip()
            if not conf.get('broker','') == '':
                broker = conf.get('broker').strip()
            if not conf.get('mqttport','') in ['','-']:
                port = int(conf.get('mqttport'))
            if not conf.get('mqttdelay','') in ['','-']:
                timeout = int(conf.get('mqttdelay'))
            if not conf.get('mqttuser','') in ['','-']:
                user = conf.get('mqttuser').strip()
            if not conf.get('mqttqos','') in ['','-']:
                try:
                    qos = int(conf.get('mqttqos'))
                except:
                    qos = 0
            if not conf.get('mqttcredentials','') in ['','-']:
                credentials=conf.get('mqttcredentials').strip()
            if not conf.get('blacklist','') in ['','-']:
                blacklist=conf.get('blacklist').split(',')
                blacklist = [el.strip() for el in blacklist]
            if not conf.get('station','') in ['','-']:
                stationid = conf.get('station').strip().lower()
                stid = stationid
            if not conf.get('destination','') in ['','-']:
                destination=conf.get('destination')
            if not conf.get('filepath','') in ['','-']:
                location=conf.get('filepath').strip()
            if not conf.get('dbcredentials','') in ['','-']:
                dbcred=conf.get('dbcredentials').strip()
            if not conf.get('revision','') in ['','-']:
                destination=conf.get('revision').strip()
            if not conf.get('offset','') in ['','-']:
                offset = conf.get('offset').strip()
            if not conf.get('debug','') in ['','-']:
                debug = conf.get('debug').strip()
                if debug in ['True','true']:
                    debug = True
                else:
                    debug = False
            if not conf.get('socketport','') in ['','-']:
                try:
                    socketport = int(conf.get('socketport'))
                except:
                    print('socketport could not be extracted from  marcos config file')
                    socketport = 5000
            if not conf.get('webport','') in ['','-']:
                try:
                    webport = int(conf.get('webport'))
                except:
                    print('webport could not be extracted from marcos config file')
                    webport = 8080
            if not conf.get('webpath','') in ['','-']:
                webpath = conf.get('webpath').strip()
            if not conf.get('telegramconf','') in ['','-']:
                telegramconf = conf.get('telegramconf').strip()
            if not conf.get('addlib','') in ['','-']:
                addlib = conf.get('addlib').strip().split(',')
            source='mqtt'
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
        elif opt in ("-i", "--instrument"):
            instrument = arg
        elif opt in ("-s", "--source"):
            source = arg
        elif opt in ("-d", "--destination"):
            destination = arg
        elif opt in ("-l", "--location"):
            location = arg
        elif opt in ("-c", "--credentials"):
            credentials = arg
        elif opt in ("-v", "--revision"):
            revision = "free"
        elif opt in ("-r", "--dbcred"):
            dbcred = arg
        elif opt in ("-q", "--qos"):
            try:
                qos = int(arg)
            except:
                qos = 0
        elif opt in ("-u", "--user"):
            user = arg
        elif opt in ("-P", "--password"):
            password = arg
        elif opt in ("-f", "--offset"):
            offset = arg
        elif opt in ("-n", "--number"):
            number = arg
        elif opt in ("-e", "--telegramconf"):
            telegramconf = arg
        elif opt in ("-a", "--addlib"):
            addlib = arg.split(',')
        elif opt in ("-U", "--debug"):
            debug = True

    diffsens = conf.get('differencesensors',"G823")
    if debug:
        print ("collector starting with the following parameters:")
        print ("Logs: {}; Broker: {}; Topic/StationID: {}; QOS: {}; MQTTport: {}; MQTTuser: {}; MQTTcredentials: {}; Data destination: {}; Filepath: {}; DB credentials: {}; Offsets: {}".format(logging, broker, stationid, qos, port, user, credentials, destination, location, dbcred, offset))

    try:
        ##  Start Twisted logging system
        ##  ----------------------------
        if logging == 'sys.stdout':
            log.startLogging(sys.stdout)
        else:
            try:
                print (" -- Logging to {}".format(logging))
                log.startLogging(open(logging,'a'))
                log.msg("----------------")
                log.msg("  -> Logging to {}".format(logging))
            except:
                log.startLogging(sys.stdout)
                log.msg("Could not open {}. Switching log to stdout.".format(logging))
    except:
        print("Logging requires twisted module")
        sys.exit()

    try:
        ##  Eventually import additional libraries
        ##  ----------------------------
        if addlib and len(addlib) > 0:
            print ("Importing additional library")
            for lib in addlib:
                exec("from libmqtt.{} import {}".format(lib,lib))
                exec("c{} = {}()".format(lib,lib))
                class_reference[lib] = eval("c{}".format(lib))
                topic_identifiers[lib] = eval("c{}.topicidentifier".format(lib))
                print ("Imported library {}: Topic identifiers are {}".format(lib, topic_identifiers[lib]))
    except:
        pass


    if debug:
        log.msg("Logs: {}; Broker: {}; Topic/StationID: {}; QOS: {}; MQTTport: {}; MQTTuser: {}; MQTTcredentials: {}; Data destination: {}; Filepath: {}; DB credentials: {}; Offsets: {}".format(logging, broker, stationid, qos, port, user, credentials, destination, location, dbcred, offset))

    log.msg("----------------")
    log.msg(" Starting collector {}".format(__version__))
    log.msg("----------------")

    if not qos in [0,1,2]:
        qos = 1

    if 'stringio' in destination:
        #TODO seems to be unfinished - started that long ago without documentation and need to find out why ;)
        output = StringIO()
    if 'file' in destination:
        if location in [None,''] and not os.path.exists(location):
            log.msg('destination "file" requires a valid path provided as location')
            log.msg(' ... aborting ...')
            sys.exit()
    if 'websocket' in destination:
        if ws_available:
            # 0.0.0.0 makes the websocket accessable from anywhere
            global wsserver
            wsserver = WebsocketServer(socketport, host='0.0.0.0')
            wsThr = threading.Thread(target=wsThread,args=(wsserver,))
            # start websocket-server in a thread as daemon, so the entire Python program exits
            wsThr.daemon = True
            log.msg('starting WEBSOCKET on port '+str(socketport))
            wsThr.start()
            # start webserver as process, also as daemon (kills process, when main program ends)
            webPr = Process(target=webProcess, args=(webpath,webport))
            webPr.daemon = True
            webPr.start()
            log.msg('starting WEBSERVER on port '+str(webport))
        else:
            print("no webserver or no websocket-server available: remove 'websocket' from destination")
            sys.exit()
    if 'db' in destination:
        if dbcred in [None,'']:
            log.msg('destination "db" requires database credentials')
            log.msg('to create them use method "addcred"')
            log.msg('to provide use option -r like -r mydb')
            sys.exit()
        else:
            try:
                global db
                if debug:
                    log.msg("Connecting database {} at host {} with user {}".format(mpcred.lc(dbcred,'db'),mpcred.lc(dbcred,'host'),mpcred.lc(dbcred,'user')))
                #db = mysql.connect(host=mpcred.lc(dbcred,'host'),user=mpcred.lc(dbcred,'user'),passwd=mpcred.lc(dbcred,'passwd'),db=mpcred.lc(dbcred,'db'))
                db = database.DataBank(mpcred.lc(dbcred,'host'),mpcred.lc(dbcred,'user'),mpcred.lc(dbcred,'passwd'),mpcred.lc(dbcred,'db'))
                #db = dbcon.db
            except:
                log.msg('database {} at host {} with user {} could not be connected'.format(mpcred.lc(dbcred,'db'),mpcred.lc(dbcred,'host'),mpcred.lc(dbcred,'user')))
                log.msg(' ... aborting ...')
                sys.exit()

    if debug:
        log.msg("Option u: debug mode switched on ...")
        log.msg("------------------------------------")
        log.msg("Destination: {} {}".format(destination, location))

    if source == 'mqtt':
        mqttversion = int(conf.get("mqttversion", 2))
        mqttcert = conf.get("mqttcert", "")
        mqttpsk = conf.get("mqttpsk", "")
        client = connectclient(broker, port, timeout, credentials, user, password, qos, mqttcert=mqttcert, mqttpsk=mqttpsk, mqttversion=mqttversion, destinationid=dbcred, debug=debug) # dbcred is used for clientid
        client.loop_forever()

    elif source == 'wamp':
        log.msg("Not yet supported! -> check autobahn import, crossbario")
    else:
        log.msg("Additional protocols can be added in future...")


if __name__ == "__main__":
   main(sys.argv[1:])

