#!/usr/bin/env python

from magpy.stream import *
from magpy.core.methods import is_number
from magpy.opt import cred as mpcred
from martas.core import methods as mm
from martas.version import __version__
import dash
from dash import html, dash_table, dcc, Output, Input, callback
import dash_daq as daq
from plotly.subplots import make_subplots
from martas.app.monitor import _latestfile
from crontab import CronTab
import paho.mqtt
import paho.mqtt.client as mqtt
import threading
import socket
import ssl


"""
Required packages
dash
plotly
pip install dash_daq
"""
# Configuration information
mainpath = os.path.dirname(os.path.realpath(__file__))
configpath = os.path.join(mainpath, "..", "..", "conf", "martas.cfg")
defaultpage = "/" # set default

livedata = {}
# livedata = { sensorid : { data : { 'x' : array, 'y' : array, ... },
#                           head

#configpath = "/home/leon/.martas/conf/martas.cfg"


statusdict = {"mqtt" : {"space" : 400, "used": 150 },
              "base" : {"space" : 100, "used": 100 }
              }


def get_sensors(path="/home/leon/.martas/conf/sensors.cfg", debug=False):
    """
    DESCRIPTION
        read SensorIDs from sensors
    """
    sl = []
    sensorlistmain = mm.get_sensors(path, "")
    sensorlist = mm.get_sensors(path, "!")
    if len(sensorlist) > 0:
        # drop OW group input from main list if OW sensors found
        sensorlistmain = [el for el in sensorlistmain if not el.get("sensorid","").find("OW") > -1]
    for line in sensorlist:
        sl.append(line.get('sensorid',''))
    sensorlist = mm.get_sensors(path, "?")
    if len(sensorlist) > 0:
        sensorlistmain = [el for el in sensorlistmain if not el.get("sensorid","").find("ARDUINO") > -1]
    for line in sensorlist:
        sl.append(line.get('sensorid',''))
    sensorlist = mm.get_sensors(path, "$")
    if len(sensorlist) > 0:
        sensorlistmain = [el for el in sensorlistmain if not el.get("name","").find("MySQL") > -1]
    for line in sensorlist:
        sl.append(line.get('sensorid',''))
    for line in sensorlistmain:
        sl.append(line.get('sensorid',''))
    if debug:
        print ("Activated sensors in sensors.cfg", sl)
    return sl

def get_new_data(path="/home/leon/MARTAS/mqtt", duration=600, debug=False):
    """
    DESCRIPTION
        Get all current data files from mqtt path
    """
    data2show = []
    dirs=[x[0] for x in os.walk(path)]
    if debug:
        print ("Found the following directories:", dirs)
    for d in dirs:
        ld = _latestfile(os.path.join(d,'*'),date=True)
        lf = _latestfile(os.path.join(d,'*'))
        if os.path.isfile(lf):
            # check white and blacklists
            performtest = False
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            diff = (now-ld).total_seconds()
            if debug:
                print ("File and time diff from now:", lf, diff, duration)
            if diff < duration/2.:
                data2show.append(lf)
    return data2show

def get_sensor_table(sensorpath="/home/leon/.martas/conf/sensors.cfg", bufferpath="/home/leon/MARTAS/mqtt", duration=600, debug=False):
    """
    DESCRIPTION
        Get all current data files from mqtt path
    """
    sl = get_sensors(path=sensorpath, debug=False)
    #data2show = get_new_data(path=bufferpath, duration=duration)
    scols = ['SensorID','Components','Active']
    stable = []
    if len(sl) > 0:
        for s in sl:
            options=[]
            values=[]
            #htmllist.append(html.Span('{}'.format(s), style=style))
            active = False
            for d in sl:
                if d.find(s) >= 0:
                    active = True
                    ndd = livedata.get(d, {})
                    for elem in ndd.get('allnames',''):
                        values.append(str(elem))
            stable.append({'SensorID' : s, 'Components':",".join(values),'Active':str(active)})
    return stable, scols

def getspace(path="/srv"): # path = '/srv'
    """
    DESCRIPTION
        get space from monitor
    """
    statvfs = os.statvfs(path)
    total = (statvfs.f_frsize * statvfs.f_blocks / (1024.*1024.))     # Size of filesystem in bytes
    remain = (statvfs.f_frsize * statvfs.f_bavail / (1024.*1024.))     # Number of free bytes that ordinary users
    usedper=100-(remain/total*100.)
    used = total-remain
    return total, used

def get_storage_usage(statusdict=None, mqttpath="", logpath="", debug=False):
    if not statusdict:
        statusdict = {}
    txt = ""
    atotal, aused = 0, 0
    mtotal, mused = 0, 0
    if mqttpath:
        if os.path.exists(mqttpath):
            atotal, aused = getspace(path=mqttpath)
    if logpath:
        logpath = os.path.dirname(logpath)
        if os.path.exists(logpath):
            mtotal, mused = getspace(path=logpath)
    ad = statusdict.get('mqtt',{})
    if ad:
        ad["space"] = np.round(atotal/1000.,0)
        ad["used"] = np.round(aused/1000.,0)
    md = statusdict.get('base',{})
    if md:
        md["space"] = np.round(mtotal/1000.,0)
        md["used"] = np.round(mused/1000.,0)
    if debug:
        print ("SPACE", atotal, aused)
        print("SPACE", mtotal, mused)
    return statusdict


def get_cron_jobs(debug=False):
    """
    DESCRIPTION
        get active Cron jobs once per minute
    """
    crontable = []

    mycron = CronTab(user=True)
    for job in mycron:
        if debug:
            print ("Testing job:", job)
        comm = job.comment
        cand = job.command
        en = job.is_enabled()
        cl = cand.split()
        logstatus = False
        active = False
        jobcommand = cl[1]
        lf = ""
        ctime = ""
        if len(jobcommand) < 3:
            jobcommand = cl[2]
        jc = jobcommand.split("/")[-1]
        for el in cl:
            if el.find(".log") >= 0:
                te = el.split("/")
                if debug:
                    print ("Found basic cron job", te)
                try:
                    ctime = os.path.getctime(el)
                    ctime = datetime.fromtimestamp(ctime)
                    logstatus = True
                    if ctime > datetime.now()-timedelta(days=8):
                        active = True
                    ctime = ctime.strftime("%Y-%m-%dT%H:%M:%S")
                    jn = jc.split(".")[0]
                except:
                    pass
                lf = te[-1]
        resd = {"job" : jc, "enabled":str(en), "logfile":lf, "last log":ctime}
        crontable.append(resd)
    croncols = ["job", "enabled", "logfile", "last log"]

    return crontable, croncols

def extract_data(f, duration=600, debug=False):
    if debug:
        print("Extracting data from:", f)
    mindisplayrate = 5
    t1 = datetime.now()
    stream = read(f, starttime=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=duration))
    if stream.samplingrate() < 0.99:
        mindisplayrate = 60
        if debug:
            print ("Sampling rate to high for rendering display - downsampling to 1 sec")
        stream = stream.filter()
    # convert to pandas
    keys = stream._get_key_headers()
    if debug:
        print(" - got {} datapoints for keys {}".format(len(stream), keys))
    data = {}
    names = []
    allnames = []
    data['time'] = stream.ndarray[0]
    for key in keys:
        # Limit to numerical keys for selection
        name = stream.get_key_name(key)
        if key in DataStream().NUMKEYLIST and len(names) < 3:
            # limit to three components for each sensor
            data[name] = stream._get_column(key)
            names.append(name)
        allnames.append(name)
    # print (data, names)
    t2 = datetime.now()
    #tdiff = (t2-t1).total_seconds()
    #if tdiff > mindisplayrate/2:
    #    mindisplayrate = int(np.ceil(tdiff*2))
    return data, names, allnames, stream.samplingrate(), stream.header.get("SensorID")


def live_timer(client, stop_event, stream):
        """"
        DESCRIPTION
            timer for live data monitoring
        :param typus:
        :param stop_event:
        :return:
        """

        debug = False
        while(not stop_event.is_set()):
            #_live_update_martas(client, stream)
            if debug:
                # use a green light to indicate it is running
                print ("Running ... {} {}".format(datetime.now(timezone.utc).replace(tzinfo=None), stream.ndarray))
            stop_event.wait(srate)
        ###
        client.loop_stop()


def martas_live_monitor(config=None, debug=False):
        """
        DEFINITION:
            embbed matplotlib figure in canvas for mointoring

        PARAMETERS:
            kwargs:  - all plot args
        """
        global livedata
        values = []
        if not config:
            config = {}

        sensorpath = config.get('sensorsconf')
        sl = get_sensors(path=sensorpath, debug=debug)

        broker = config.get("broker","")
        martastopic = config.get("station","").lower()
        port = config.get("mqttport","")
        timeout = config.get("mqttdelay","")
        credentials=config.get('mqttcredentials',"").strip()
        qos = config.get("mqttqos","")
        user = config.get("user","")
        password = config.get("password","")
        martascert = config.get("mqttcert","")
        martaspsk = config.get("mqttpsk","")
        dbcred = ""

        print ("Sensors", sl, martastopic)

        #dataid = livedatadict.get("id")
        #coverage = livedatadict.get("coverage")
        #keys = livedatadict.get("keys")
        #limit = livedatadict.get("limit")
        

        # start monitoring parameters
        ok =True
        if ok:

                def connectclient(broker='localhost', port=1883, timeout=60, credentials='', user='', password='',
                                  qos=0, mqttcert="", mqttpsk="", mqttversion=2, destinationid='', debug=False):
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
                    clientid = "{}{}{}".format(broker, hostname, destinationid)

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
                        # context = SSLPSKContext(ssl.PROTOCOL_TLS_CLIENT) # This does bot work for beaglebone (python3.11 clients)
                        print("MARTAS: Deprecation warning - but necessary for old clients")
                        print ("PSK to be included")
                        """
                        context = SSLPSKContext(ssl.PROTOCOL_TLSv1_2)
                        context.set_ciphers('PSK')
                        context.psk = bytes.fromhex(pskpwd)
                        context.identity = pskidentity.encode()
                        client.tls_set_context(context)  # Here we apply the new `SSLPSKContext`
                        """

                    # Authentication part
                    if not credentials in ['', '-']:
                        # use user and pwd from credential data if not yet set
                        if user in ['', None, 'None', '-']:
                            user = mpcred.lc(credentials, 'user')
                        if password in ['', '-']:
                            password = mpcred.lc(credentials, 'passwd')
                    if not user in ['', None, 'None', '-']:
                        # client.tls_set(tlspath)  # check http://www.steves-internet-guide.com/mosquitto-tls/
                        client.username_pw_set(user,
                                               password=password)  # defined on broker by mosquitto_passwd -c passwordfile user
                    client.on_connect = on_connect
                    # on message needs: stationid, destination, location
                    client.on_message = on_message
                    client.connect(broker, port, timeout)

                    return client

                # Version 1 (valid for xxx)
                # -------------------------
                # The callback for when the client receives a CONNACK response from the server.
                # signature suitable for MQTT v5.0 client:
                def on_connect(client, userdata, flags, reason_code, properties=None):
                    # Subscribing in on_connect() means that if we lose the connection and
                    # reconnect then subscriptions will be renewed.
                    client.subscribe("{}/#".format(martastopic), qos)

                # The callback for when a PUBLISH message is received from the server.
                def on_message(client, userdata, msg):
                    #if debug:
                    #    print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
                    # create a result dictionary

                    sensorid = "{}".format(msg.topic).replace("{}/".format(martastopic),'')[:-5]
                    content = "{}".format(msg.topic)[-4:]
                    payload = "{}".format(msg.payload.decode())
                    #print ("DDD", sensorid, content)
                    if sensorid in sl:
                        sensorcont = {}
                        namelst = []
                        if not livedata.get(sensorid, {}) == {}:
                            sensorcont = livedata.get(sensorid)
                        keys = sensorcont.get('SensorKeys', '').split(',')
                        multi = sensorcont.get('Multipliers', '').split(',')
                        els = sensorcont.get('SensorElements','').split(',')
                        shown = sensorcont.get('shown_names',[])
                        uns = sensorcont.get('SensorUnits','').split(',')
                        sr = sensorcont.get("samplingrate",1)
                        pc = sensorcont.get('PackingCode', '')
                        array = sensorcont.get('Data', [[] for key in DataStream().KEYLIST])
                        datacont = sensorcont.get('data', {})
                        if content == 'meta':
                            #print ("FOUND META ---------------------------")
                            if not keys or keys == ['']:
                                payloadlist1 = payload.split(sensorid)
                                payloadlist2 = payloadlist1[1].split()
                                sensorcont['SensorKeys'] = payloadlist2[0][1:-1]
                                sensorcont['SensorElements'] = payloadlist2[1][1:-1]
                                sensorcont['SensorUnits'] = payloadlist2[2][1:-1]
                                sensorcont['Multipliers'] = payloadlist2[3][1:-1]
                                sensorcont['PackingCode'] = payloadlist2[4]
                                keys = sensorcont.get('SensorKeys').split(',')
                                els = sensorcont.get('SensorElements').split(',')
                                uns = sensorcont.get('SensorUnits').split(',')
                                for i, el in enumerate(keys):
                                    sensorcont[f"col-{el}"] = els[i]
                                    sensorcont[f"unit-col-{el}"] = uns[i]
                        elif content == 'dict':
                            payloadlist = payload.split(',')
                            for pl in payloadlist:
                                plc = pl.replace("\n", "").split(":")
                                sensorcont[plc[0]] = plc[1].replace('-', '')
                        elif content == 'data' and len(keys) > 0 and not keys==['']:
                            payloadlist = payload.split(';')
                            for dataline in payloadlist:
                                datalist = dataline.split(',')
                                datalist = [int(el) if is_number(el) else el for el in datalist]
                                #print (datalist, array)
                                timel = [int(t) for t in datalist[:7]]
                                ti = list(datacont.get('time',[]))
                                ti.append(datetime(*timel))
                                ti = ti[-36000:]
                                datacont['time'] = np.asarray(ti)
                                if pc.endswith('6hL'):
                                    sectimel = [int(t) for t in datalist[-7:]]
                                    sti = list(datacont.get('sectime',[]))
                                    sti.append(datetime(*sectimel))
                                    sti = sti[-36000:]
                                    datacont['time'] = np.asarray(sti)
                                for i, k in enumerate(keys):
                                    if not k == "sectime" and k in DataStream().KEYLIST:
                                        nam = els[i]
                                        namelst.append(nam)
                                        if k in DataStream().NUMKEYLIST:
                                            dat = list(datacont.get(nam, []))
                                            dat.append(float(datalist[7 + i]) / float(multi[i]))
                                            dat = dat[-36000:]
                                            datacont[nam] = np.asarray(dat)
                                        else:
                                            dat = list(datacont.get(nam, []))
                                            dat.append(datalist[7 + i])
                                            dat = dat[-36000:]
                                            datacont[nam] = np.asarray(dat)
                            # limit length of array
                            sensorcont['allnames'] = namelst
                            if not shown: # by default limit to three shown diagrams for each sensor
                                sensorcont['names'] = namelst[:3]
                            sensorcont['data'] = datacont
                        livedata[sensorid] = sensorcont
                        #print ("Live data", len(livedata))

                mqttversion = int(config.get("mqttversion", 2))
                mqttcert = config.get("mqttcert", "")
                mqttpsk = config.get("mqttpsk", "")
                client = connectclient(broker, port, timeout, credentials, user, password, qos, mqttcert=mqttcert,
                                           mqttpsk=mqttpsk, mqttversion=mqttversion, destinationid=dbcred,
                                           debug=debug)  # dbcred is used for clientid

                if debug:
                    print ("Connecting to:", broker, int(port), int(timeout))

                t1 = threading.Thread(target=live_timer, args=(client, t1_stop, DataStream()))
                t1.start()
                client.loop_start()
                # Display the plot


# Read configuration data and initialize amount of plots
cfg = mm.get_conf(configpath)
logpath = os.path.dirname(cfg.get('logging'))
sensorpath = cfg.get('sensorsconf')
bufferpath = cfg.get('bufferdirectory')
data2show = get_new_data(path=bufferpath)

sensors_to_plot = get_sensors(path=sensorpath, debug=False)

statusdict = get_storage_usage(statusdict=statusdict, mqttpath=bufferpath, logpath=logpath, debug=False)

#nd={}
srate = 5 # displayrate - needs to be large enough, dynamically adjusted
for d in data2show:
    data, names, anames, sr, sensorid = extract_data(d)
    livedata[sensorid] = {'samplingrate': sr, 'names': names, 'allnames': anames, 'data': data }

stable, scols = get_sensor_table(sensorpath=sensorpath, bufferpath=bufferpath)
ctable, ccols = get_cron_jobs(debug=False)
cron_columns = [{'id': c, 'name': c} for c in ccols]
sens_columns = [{'id': c, 'name': c} for c in scols]
initially_selected_rows = list(range(0,len(stable)))

print ("Display refresh rate: {} sec".format(srate))


# The following method will update the global variable livedata with new mqtt readings
t1_stop = threading.Event()
martas_live_monitor(config=cfg, debug=True)


dash.register_page(__name__, path=defaultpage, top_nav=True, assets_ignore='marcos.css')

#app = Dash(__name__, assets_ignore='marcos.css')

layout = (html.Div(
                 className="wrapper",
                 children=[
                              html.Div(
                                  className="box martas",
                                  children=html.Div([
                                      html.Img(src='/assets/header.png',style={'width': '30%'}),
                                      ])
                              ),
                              html.Div(
                                  className="box setup",
                                  children=html.Div([
                                      html.P('Time coverage (minutes):'),
                                      dcc.Slider(id='martas-durationslider', min=5, max=60, step=5, value=10,
                                                 marks={x: str(x) for x in [10, 20, 30, 40, 50, 60]}),
                                      html.P('Height of the graph display (px):'),
                                      dcc.Slider(id='martas-heightslider', min=200, max=1000, step=25, value=450,
                                                 marks={x: str(x) for x in [200, 400, 600, 800, 1000]}),
                                  ])
                              ),
                              html.Div(
                                  className="box sensors",
                                  children=html.Div([
                                      dcc.Interval(
                                          id='martas-sensors-update',
                                          interval=5*srate*1000,  # in milliseconds - use 60 sec to allow even LEMI 10Hz data to loaded
                                          n_intervals=0
                                      ),
                                      dash_table.DataTable(id='martas-sensors-table',
                                                            data=stable,
                                                            sort_action='native',
                                                            row_selectable="multi",
                                                            selected_rows=initially_selected_rows,
                                                            columns=sens_columns,
                                                            style_cell={'minWidth': 95, 'width': 95, 'maxWidth': 95,
                                                                        'padding': '5px'},
                                                            style_cell_conditional=[
                                                                {
                                                                    'if': {'column_id': c},
                                                                    'textAlign': 'left'
                                                                } for c in ['SensorID', 'Components']
                                                            ],
                                                            style_data={
                                                                'color': 'rgb(230, 230, 250)',
                                                                'fontSize': '14px',
                                                                'backgroundColor': 'rgb(112, 128, 144)'
                                                            },
                                                            style_data_conditional=[
                                                                {
                                                                    'if': {'row_index': 'odd'},
                                                                    'backgroundColor': 'rgb(119, 149, 163)',
                                                                },
                                                                {
                                                                    'if': {
                                                                        'filter_query': '{Active} = True',
                                                                        'column_id': 'Active'
                                                                    },
                                                                    'backgroundColor': "#008003"
                                                                },
                                                                {
                                                                    'if': {
                                                                        'filter_query': '{Active} = False',
                                                                        'column_id': 'Active'
                                                                    },
                                                                    'backgroundColor': 'tomato'
                                                                }
                                                            ],
                                                            style_header={
                                                                'backgroundColor': '#4D4D4D',
                                                                'color': 'rgb(230, 230, 250)',
                                                                'fontWeight': 'bold',
                                                                'fontSize': '16px',
                                                                'border': '1px solid black'
                                                            }
                                      )
                                  ])
                              ),
                              html.Div(
                                  className="box gauges",
                                  children=html.Div([
                                      dcc.Interval('martas-gauge-update', interval=10*srate*1000, n_intervals=0),
                                      daq.Gauge(
                                          id='martas-buffer-gauge',
                                          size=120,
                                          color={"gradient": True,
                                                 "ranges": {"green": [0, statusdict['mqtt'].get('space') * 0.8],
                                                            "yellow": [statusdict['mqtt'].get('space') * 0.8,
                                                                       statusdict['mqtt'].get('space') * 0.9],
                                                            "red": [statusdict['mqtt'].get('space') * 0.9,
                                                                    statusdict['mqtt'].get('space')]}},
                                          value=statusdict['mqtt'].get('used'),
                                          label='Buffer [GB]',
                                          max=statusdict['mqtt'].get('space'),
                                          min=0,
                                      )
                                  ])
                              ),
                              html.Div(
                                  className='box graphs',
                                  children=html.Div([
                                      dcc.Graph(id='martas-live-graph', animate=False),
                                      dcc.Interval(
                                          id='martas-graph-update',
                                          interval=srate * 1000,  # in milliseconds - use 60 sec to allow even LEMI 10Hz data to loaded
                                          n_intervals=0
                                      )
                                  ])
                              ),
                              html.Div(
                                  className="box link",
                                  children=html.Div([
                                      dcc.Interval('martas-cron-update', interval=10*srate*1000, n_intervals=0),
                                      dash_table.DataTable(id='martas-cron-table',
                                                           data=ctable,
                                                           columns=cron_columns,
                                                           sort_action='native',
                                                           fixed_rows={'headers': True},
                                                           style_cell={'minWidth': 95, 'width': 95, 'maxWidth': 95,
                                                                       'padding': '5px'},
                                                           style_table={'height': 200},  # default is 500
                                                           style_cell_conditional=[
                                                               {
                                                                   'if': {'column_id': c},
                                                                   'textAlign': 'left'
                                                               } for c in ['job', 'enabled']
                                                           ],
                                                           style_data={
                                                               'whiteSpace': 'normal',
                                                               'color': 'rgb(230, 230, 250)',
                                                               'fontSize': '14px',
                                                               'backgroundColor': 'rgb(112, 128, 144)'
                                                           },
                                                           style_data_conditional=[
                                                               {
                                                                   'if': {'row_index': 'odd'},
                                                                   'backgroundColor': 'rgb(119, 149, 163)',
                                                               },
                                                               {
                                                                   'if': {
                                                                       'filter_query': '{enabled} = False',
                                                                       'column_id': 'enabled'
                                                                   },
                                                                   'backgroundColor': '#eaf044',
                                                                   'color': 'black'
                                                               },
                                                           ],
                                                           style_header={
                                                               'backgroundColor': '#4D4D4D',
                                                               'color': 'rgb(230, 230, 250)',
                                                               'fontWeight': 'bold',
                                                               'fontSize': '16px',
                                                               'border': '1px solid black'
                                                           },
                                                           )
                                  ])
                              ),
                              html.Div(
                                  className="box about",
                                  children=html.Div([
                                       html.B('MARTAS (MagPys automatic real time acquisition system)'),
                                       html.P('Version {}'.format(__version__)),
                                       html.P('written by R. Leonhardt, R. Bailey, R. Mandl, N. Kompein, P. Arneitz, V. Haberle'),
                                       html.P(['MARTAS on GitHUB:',
                                               html.A('click here', href='https://github.com/geomagpy/MARTAS')]),
                                       html.P(['MARTAS manual:',
                                               html.A('click here',
                                                      href='https://github.com/geomagpy/MARTAS?tab=readme-ov-file#martas')]),
                                   ])
                              ),
                              html.Div(
                                  className="box stats",
                                  children=html.Div([
                                     html.B('Configuration'),
                                     html.Div(id='martas-live-update-config')
                                  ])
                             )
                 ]
            )
)

@callback(
    Input('martas-sensors-table', "derived_virtual_data"),
    Input('martas-sensors-table', "derived_virtual_selected_rows"))
def update_graphs(rows, derived_virtual_selected_rows):
    # When the table is first rendered, `derived_virtual_data` and
    # `derived_virtual_selected_rows` will be `None`. This is due to an
    # idiosyncrasy in Dash (unsupplied properties are always None and Dash
    # calls the dependent callbacks when the component is first rendered).
    # So, if `rows` is `None`, then the component was just rendered
    # and its value will be the same as the component's dataframe.
    # Instead of setting `None` in here, you could also set
    # `derived_virtual_data=df.to_rows('dict')` when you initialize
    # the component.
    if derived_virtual_selected_rows is None:
        derived_virtual_selected_rows = []
    global sensors_to_plot
    print (rows, derived_virtual_selected_rows)
    sensors_to_plot = [rows[i].get('SensorID','') for i in derived_virtual_selected_rows]
    print (sensors_to_plot)


@callback(Output('martas-live-update-config', 'children'),
              Input('martas-gauge-update', 'n_intervals'))
def update_config(n):
    #print ("updating conf")
    global configpath
    style = {'padding': '5px', 'fontSize': '16px'}
    pos = {}
    htmllist = []
    cfg = mm.get_conf(configpath)
    #print (cfg)
    htmllist.append(html.P(['Station code: {}'.format(cfg.get('station'))]))
    htmllist.append(html.P(['Sensor configuration: {}'.format(cfg.get('sensorsconf'))]))
    htmllist.append(html.P(['Buffer directory: {}'.format(cfg.get('bufferdirectory'))]))
    htmllist.append(html.P(['MQTT broker: {}'.format(cfg.get('broker'))]))
    return htmllist


@callback([Output('martas-sensors-table', 'data'),
               Output('martas-sensors-table', 'columns')],
              Input('martas-sensors-update', 'n_intervals'))
def martas_update_table(n):
    #print ("updating sensor table")
    global sensorpath
    global bufferpath
    stable, scols = get_sensor_table(sensorpath=sensorpath, bufferpath=bufferpath)
    sens_columns = [{'id': c, 'name': c} for c in scols]
    #print ("sens ok")
    return stable, sens_columns


@callback(Output('martas-buffer-gauge', 'value'),
              Input('martas-gauge-update', 'n_intervals'))
def martas_update_gauge_status(n):
    #print ("updating gauge")
    global statusdict
    statusdict = get_storage_usage(statusdict=statusdict, mqttpath=bufferpath, logpath=logpath, debug=False)
    #print ("gauge ok")
    return statusdict['mqtt'].get('used')


@callback([Output('martas-cron-table', 'data'),
               Output('martas-cron-table', 'columns')],
              Input('martas-cron-update', 'n_intervals'))
def martas_update_cron(n):
    #print ("updating cron table")
    ctable, ccols = get_cron_jobs()
    cron_columns = [{'id': c, 'name': c} for c in ccols]
    #print ("cron ok")
    return ctable, cron_columns


@callback(
    Output('martas-live-graph', 'figure'),
    Input('martas-graph-update', 'n_intervals'),
    Input('martas-heightslider', 'value'),
    Input('martas-durationslider', 'value'),
    prevent_initial_call=True
)
def martas_update_graph(n, hvalue, duration):
    # read data
    #print ("Updating graph")
    """
    global bufferpath
    cov = int(duration)*60
    data2show = get_new_data(path=bufferpath,duration=cov)
    print ("Data2show", data2show)
    all_names =[]
    for f in data2show:
        data, names, anames, mdr = extract_data(f,duration=cov)
        nd[f] = {'allnames': anames, 'names': names, 'data':data}
        all_names.extend(names)
    print (nd)
    """
    global livedata
    global sr
    global sensors_to_plot
    #print ("ON update", livedata) # no modification, therefore no global definition
    cov = int(duration) * 60
    #print ("Coverage ", cov)
    nd = livedata
    all_names = []
    for el in livedata:
        sensdict = livedata.get(el)
        shown = sensdict.get('names',[])
        all_names.extend(shown)

    if len(all_names)>0:
        fig = make_subplots(rows=len(all_names), cols=1, vertical_spacing=0.1)
        fig.update_layout(
            plot_bgcolor='#4D4D4D',
            paper_bgcolor='#EDE9E8',
        )
        fig.update_xaxes(
            mirror=True,
            ticks='outside',
            showline=True,
            linecolor='black',
            gridcolor='lightgrey'
        )
        fig.update_yaxes(
            mirror=True,
            ticks='outside',
            showline=True,
            linecolor='black',
            gridcolor='lightgrey'
        )
        fig['layout']['margin'] = {
            'l': 20, 'r': 10, 'b': 10, 't': 10
        }
        fig['layout']['legend'] = {'x': 0, 'y': 1, 'xanchor': 'left'}
        fig.update_layout(height=int(hvalue))

        i = 0
        for f in nd:
            if f in sensors_to_plot:
                ndd = nd[f]
                sr = ndd.get('samplingrate')
                amount = int(cov/sr)
                #print (amount)
                data = ndd.get('data')
                names = ndd.get('names')
                for name in names:
                    i += 1
                    fig.add_trace({
                        'x': data['time'][-amount:],
                        'y': data[name][-amount:],
                        'name': name,
                        'mode': 'lines+markers',
                        'type': 'scatter'
                    }, i, 1)

        return fig

#if __name__ == '__main__':
#    app.run(host="0.0.0.0", debug=False)
