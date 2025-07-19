#!/usr/bin/env python

from magpy.stream import *
import pandas as pd
from dash import Dash, html, dash_table, dcc, Output, Input
#import plotly.express as px
import plotly
from martas.app.monitor import _latestfile


def magpy2pandas(stream):
    d = {}
    for key in stream.KEYLIST:
        col = stream._get_column(key)
        colname = stream.header.get('col-{}'.format(key), key)
        if len(col) > 0:
            d[colname] = col
    dataset = pd.DataFrame(d)
    return dataset

data2show = []
duration=600

def get_new_data(path="/home/leon/MARTAS/mqtt"):
# Get all current data files from mqtt path
    data2show = []
    dirs=[x[0] for x in os.walk(path)]
    print (dirs)
    for d in dirs:
        ld = _latestfile(os.path.join(d,'*'),date=True)
        lf = _latestfile(os.path.join(d,'*'))
        if os.path.isfile(lf):
            # check white and blacklists
            print (lf)
            performtest = False
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            diff = (now-ld).total_seconds()
            print (diff)
            if diff < duration:
                data2show.append(lf)
    return data2show

def extract_data(f):
    print(f)
    stream = read(f, starttime=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=duration))
    # convert to pandas
    print(len(stream))
    keys = stream._get_key_headers()
    print(keys)
    # df = magpy2pandas(data)
    # names = list(df)
    data = {}
    names = []
    data['time'] = stream.ndarray[0]
    for key in keys:
        name = stream.get_key_name(key)
        data[name] = stream._get_column(key)
        names.append(name)
    # print (data, names)
    return data, names


app = Dash()

app.layout = html.Div(
    html.Div([
        html.H4('MARTAS Live Feed'),
        html.Div(id='live-update-text'),
        dcc.Graph(id = 'live-graph', animate = True),
        dcc.Interval(
            id='graph-update',
            interval=5*1000, # in milliseconds
            n_intervals=0
        )
    ])
)

@app.callback(Output('live-update-text', 'children'),
              Input('graph-update', 'n_intervals'))
def update_metrics(n):
    style = {'padding': '5px', 'fontSize': '16px'}
    htmllist = []
    data2show = get_new_data()
    for f in data2show:
        htmllist.append(html.Span('Dataset: {}'.format(f), style=style))
    return htmllist


@app.callback(
    Output('live-graph', 'figure'),
    [ Input('graph-update', 'n_intervals') ]
)
def update_graph(n):
    # read data
    print ("Doing something")
    data2show = get_new_data()

    f = data2show[0]
    data, names = extract_data(f)
    ok = True
    if ok:
        fig = plotly.tools.make_subplots(rows=len(names), cols=1, vertical_spacing=0.2)
        fig['layout']['margin'] = {
            'l': 30, 'r': 10, 'b': 30, 't': 10
        }
        fig['layout']['legend'] = {'x': 0, 'y': 1, 'xanchor': 'left'}

        for i,name in enumerate(names):
            fig.append_trace({
                'x': data['time'],
                'y': data[name],
                'name': name,
                'mode': 'lines+markers',
                'type': 'scatter'
            }, i+1, 1)

    return fig

if __name__ == '__main__':
    app.run(debug=True)
