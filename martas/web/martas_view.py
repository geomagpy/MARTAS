#!/usr/bin/env python

from magpy.stream import *
from martas.core import methods as mm
from martas.version import __version__
from dash import Dash, html, dash_table, dcc, Output, Input
import dash_daq as daq
from plotly.subplots import make_subplots
from martas.app.monitor import _latestfile
from crontab import CronTab


"""
Required packages
dash
plotly
pip install dash_daq
"""
# Configuration information
mainpath = os.path.dirname(os.path.realpath(__file__))
configpath = os.path.join(mainpath,"..","conf","martas.cfg")

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
    data2show = get_new_data(path=bufferpath, duration=duration)
    scols = ['SensorID','Components','Active']
    stable = []
    for s in sl:
        options=[]
        values=[]
        #htmllist.append(html.Span('{}'.format(s), style=style))
        active = False
        for d in data2show:
            if d.find(s) >= 0:
                active = True
                ndd = nd.get(d)
                for elem in ndd.get('allnames'):
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
    tdiff = (t2-t1).total_seconds()
    if tdiff > mindisplayrate/2:
        mindisplayrate = int(np.ceil(tdiff*2))
    return data, names, allnames, mindisplayrate

# Read configuration data and initialize amount of plots
cfg = mm.get_conf(configpath)
logpath = os.path.dirname(cfg.get('logging'))
sensorpath = cfg.get('sensorsconf')
bufferpath = cfg.get('bufferdirectory')
data2show = get_new_data(path=bufferpath)
statusdict = get_storage_usage(statusdict=statusdict, mqttpath=bufferpath, logpath=logpath, debug=False)

nd={}
srate = 5 # displayrate - needs to be large enough, dynamically adjusted
for d in data2show:
    data, names, anames, mdr = extract_data(d)
    nd[d] = {'names': names, 'allnames': anames  }
    if mdr > srate:
        srate = mdr
stable, scols = get_sensor_table(sensorpath=sensorpath, bufferpath=bufferpath)
ctable, ccols = get_cron_jobs(debug=False)
cron_columns = [{'id': c, 'name': c} for c in ccols]
sens_columns = [{'id': c, 'name': c} for c in scols]

print ("Display refresh rate: {} sec".format(srate))

app = Dash(__name__, assets_ignore='marcos.css')

app.layout = (html.Div(
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
                                      dcc.Slider(id='durationslider', min=5, max=60, step=5, value=10,
                                                 marks={x: str(x) for x in [10, 20, 30, 40, 50, 60]}),
                                      html.P('Height of the graph display (px):'),
                                      dcc.Slider(id='heightslider', min=200, max=1000, step=25, value=450,
                                                 marks={x: str(x) for x in [200, 400, 600, 800, 1000]}),
                                  ])
                              ),
                              html.Div(
                                  className="box sensors",
                                  children=html.Div([
                                      dcc.Interval(
                                          id='sensors-update',
                                          interval=5*srate*1000,  # in milliseconds - use 60 sec to allow even LEMI 10Hz data to loaded
                                          n_intervals=0
                                      ),
                                      dash_table.DataTable(id='sensors-table',
                                                            data=stable,
                                                            sort_action='native',
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
                                      dcc.Interval('gauge-update', interval=10*srate*1000, n_intervals=0),
                                      daq.Gauge(
                                          id='buffer-gauge',
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
                                      dcc.Graph(id='live-graph', animate=False),
                                      dcc.Interval(
                                          id='graph-update',
                                          interval=srate * 1000,  # in milliseconds - use 60 sec to allow even LEMI 10Hz data to loaded
                                          n_intervals=0
                                      )
                                  ])
                              ),
                              html.Div(
                                  className="box link",
                                  children=html.Div([
                                      dcc.Interval('cron-update', interval=10*srate*1000, n_intervals=0),
                                      dash_table.DataTable(id='cron-table',
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
                                       html.H4('MARTAS (MagPys automatic real time acquisition system)'),
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
                                     html.H4('Configuration'),
                                     html.Div(id='live-update-config')
                                  ])
                             )
                 ]
            )
)


@app.callback(Output('live-update-config', 'children'),
              Input('gauge-update', 'n_intervals'))
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


@app.callback([Output('sensors-table', 'data'),
               Output('sensors-table', 'columns')],
              Input('sensors-update', 'n_intervals'))
def update_table(n):
    #print ("updating sensor table")
    global sensorpath
    global bufferpath
    stable, scols = get_sensor_table(sensorpath=sensorpath, bufferpath=bufferpath)
    sens_columns = [{'id': c, 'name': c} for c in scols]
    #print ("sens ok")
    return stable, sens_columns


@app.callback(Output('buffer-gauge', 'value'),
              Input('gauge-update', 'n_intervals'))
def update_gauge_status(n):
    #print ("updating gauge")
    global statusdict
    statusdict = get_storage_usage(statusdict=statusdict, mqttpath=bufferpath, logpath=logpath, debug=False)
    #print ("gauge ok")
    return statusdict['mqtt'].get('used')


@app.callback([Output('cron-table', 'data'),
               Output('cron-table', 'columns')],
              Input('cron-update', 'n_intervals'))
def update_cron(n):
    #print ("updating cron table")
    ctable, ccols = get_cron_jobs()
    cron_columns = [{'id': c, 'name': c} for c in ccols]
    #print ("cron ok")
    return ctable, cron_columns


@app.callback(
    Output('live-graph', 'figure'),
    Input('graph-update', 'n_intervals'),
    Input('heightslider', 'value'),
    Input('durationslider', 'value'),
    prevent_initial_call=True
)
def update_graph(n, hvalue, duration):
    # read data
    #print ("Updating graph")
    global bufferpath
    cov = int(duration)*60
    data2show = get_new_data(path=bufferpath,duration=cov)
    all_names =[]
    for f in data2show:
        data, names, anames, mdr = extract_data(f,duration=cov)
        nd[f] = {'allnames': anames, 'names': names, 'data':data}
        all_names.extend(names)

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
        ndd = nd[f]
        data = ndd.get('data')
        names = ndd.get('names')
        for name in names:
            i += 1
            fig.add_trace({
                'x': data['time'],
                'y': data[name],
                'name': name,
                'mode': 'lines+markers',
                'type': 'scatter'
            }, i, 1)

    return fig

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=False)
