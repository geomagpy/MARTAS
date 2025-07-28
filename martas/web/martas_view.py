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
configpath = "../conf/martas.cfg"


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
sensorpath = cfg.get('sensorsconf')
bufferpath = cfg.get('bufferdirectory')
data2show = get_new_data(path=bufferpath)
nd={}
for d in data2show:
    data, names = extract_data(d)
    nd[d] = {'names': names }

app = Dash(__name__)


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
                                      html.H4('Sensors'),
                                      html.Div(id='live-update-text')
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
                                      html.P('written by R. Leonhardt, R. Bailey, R. Mandl'),
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
