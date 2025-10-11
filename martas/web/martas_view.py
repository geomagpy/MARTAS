#!/usr/bin/env python

from magpy.stream import *
from martas.core import methods as mm
from martas.version import __version__
from dash import Dash, html, dash_table, dcc, Output, Input
import dash_daq as daq
from plotly.subplots import make_subplots
from martas.app.monitor import _latestfile


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
    sensorlist = mm.get_sensors(path, "")
    for line in sensorlist:
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
            if diff < duration:
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
                for elem in ndd.get('names'):
                    values.append(elem)
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


def extract_data(f, duration=600, debug=False):
    if debug:
        print("Extracting data from:", f)
    stream = read(f, starttime=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=duration))
    # convert to pandas
    keys = stream._get_key_headers()
    if debug:
        print(" - got {} datapoints for keys {}".format(len(stream), keys))
    data = {}
    names = []
    data['time'] = stream.ndarray[0]
    for key in keys:
        name = stream.get_key_name(key)
        data[name] = stream._get_column(key)
        names.append(name)
    # print (data, names)
    return data, names

# Read configuration data and initialize amount of plots
cfg = mm.get_conf(configpath)
logpath = os.path.dirname(cfg.get('logging'))
sensorpath = cfg.get('sensorsconf')
bufferpath = cfg.get('bufferdirectory')
data2show = get_new_data(path=bufferpath)
statusdict = get_storage_usage(statusdict=statusdict, mqttpath=bufferpath, logpath=logpath, debug=False)

nd={}
for d in data2show:
    data, names = extract_data(d)
    nd[d] = {'names': names }
stable, scols = get_sensor_table(sensorpath=sensorpath, bufferpath=bufferpath)

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
                                      dash_table.DataTable( data=stable,
                                                            id='sensors-table',
                                                            sort_action='native',
                                                            columns=[{'id': c, 'name': c} for c in scols],
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
                                          label='Buffer',
                                          max=statusdict['mqtt'].get('space'),
                                          min=0,
                                      ),
                                      dcc.Interval(
                                          id='gauge-update',
                                          interval=60 * 1000,  # in milliseconds
                                          n_intervals=0
                                      )
                                  ])
                              ),
                              html.Div(
                                  className='box graphs',
                                  children=html.Div([
                                      dcc.Graph(id='live-graph', animate=False),
                                      dcc.Interval(
                                          id='graph-update',
                                          interval=5 * 1000,  # in milliseconds
                                          n_intervals=0
                                      )
                                  ])
                              ),
                              html.Div(
                                  className="box about",
                                  children=html.Div([
                                      html.H4('About'),
                                      html.P('MARTAS (MagPys automatic real time acquisition system)'),
                                      html.P('Version {}'.format(__version__)),
                                      html.P('written by R. Leonhardt, R. Bailey, R. Mandl, P. Arneitz, V. Haberle'),
                                  ])
                              ),
                             html.Div(
                                 className="box link",
                                 children=html.Div([
                                     html.H4('Links'),
                                     html.P(['MARTAS on GitHUB:', html.A('click here', href='https://github.com/geomagpy/MARTAS')]),
                                     html.P(['MARTAS manual:',
                                                 html.A('click here', href='https://github.com/geomagpy/MARTAS?tab=readme-ov-file#martas')]),
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
              Input('graph-update', 'n_intervals'))
def update_config(n):
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

@app.callback(Output('live-update-gauge', 'children'),
              Input('gauge-update', 'n_intervals'))
def update_gauge_status(n):
    statusdict = get_storage_usage(statusdict={}, mqttpath=bufferpath, logpath=logpath, debug=False)
    stable, scols = get_sensor_table(sensorpath=sensorpath, bufferpath=bufferpath)
    return

@app.callback(Output('live-update-text', 'children'),
              Input('graph-update', 'n_intervals'))
def update_metrics(n):
    style = {'padding': '5px', 'fontSize': '16px'}
    pos = {}
    htmllist = []
    sl = get_sensors(path=sensorpath, debug=False)
    data2show = get_new_data(path=bufferpath, duration=600)
    for s in sl:
        options=[]
        values=[]
        #htmllist.append(html.Span('{}'.format(s), style=style))
        active = False
        for d in data2show:
            if d.find(s) >= 0:
                active = True
                ndd = nd.get(d)
                #print ("XXX", nd.get(d))
                for elem in ndd.get('names'):
                    options.append({'label': elem, 'value': elem})
                    values.append(elem)
        htmllist.append(html.Div([ daq.BooleanSwitch(id='my-boolean-switch', on=active, label={'label':s,
                                                                                               'style':style}, color="#008003",style=pos),
                                   ])
                        )
        htmllist.append(html.Div([ dcc.Checklist(
                                 id='{}-checklist'.format(s),
                                 options=options,
                                 value=values)
                                 ])
                        )
    return htmllist


@app.callback(
    Output('live-graph', 'figure'),
    Input('graph-update', 'n_intervals'),
    Input('heightslider', 'value'),
    Input('durationslider', 'value'),
    prevent_initial_call=True
)
def update_graph(n, hvalue, duration):
    # read data
    cov = int(duration)*60
    data2show = get_new_data(path=bufferpath,duration=cov)
    all_names =[]
    for f in data2show:
        data, names = extract_data(f,duration=cov)
        nd[f] = {'names': names, 'data':data}
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
