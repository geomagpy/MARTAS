#!/usr/bin/env python

from magpy.stream import *
import pandas as pd
from dash import Dash, html, dash_table, dcc
import plotly.express as px


def magpy2pandas(stream):
    d = {}
    for key in stream.KEYLIST:
        col = stream._get_column(key)
        colname = stream.header.get('col-{}'.format(key), key)
        if len(col) > 0:
            d[colname] = col
    dataset = pd.DataFrame(d)
    return dataset

# read data
data = read(example1)
# convert to pandas
df = magpy2pandas(data)

app = Dash()

# Requires Dash 2.17.0 or later
app.layout = [
    html.Div(children='My First App with Data and a Graph'),
    dcc.Graph(figure=px.line(df, x='time', y="H"))
]

if __name__ == '__main__':
    app.run(debug=True)