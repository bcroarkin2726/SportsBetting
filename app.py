# -*- coding: utf-8 -*-
"""
Created on Wed Oct  9 23:16:41 2019

@author: Brandon Croarkin
"""

import dash
import dash_core_components as dcc
import dash_html_components as html

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div(children = 
                      [html.H1('BOFA Sports Betting Tool'),
                       dcc.Graph(id = 'Week 6 Player Props',
                                 figure = {
                                         'data': [
                                                 {'x': implied_points.index, 'y': implied_points['ImpliedPoints'].values,
                                                   'type': 'bar', 'name': 'boats'},
                                                  ],
                                            'layout': {
                                                    'title': 'Basic Dash Example'
                                                    }
                                         })
                      ])

if __name__ == '__main__':
    app.run_server(debug=True)