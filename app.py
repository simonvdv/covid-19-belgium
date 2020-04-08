#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr  1 17:27:37 2020

@author: simonvdv
"""
import pandas as pd
import numpy as np

from bokeh.models import ColumnDataSource, Column
from bokeh.models.tools import HoverTool
from bokeh.plotting import figure
from bokeh.io import show, output_file, output_notebook, curdoc
from bokeh.models.widgets import CheckboxGroup
from bokeh.layouts import row, WidgetBox
from bokeh.application.handlers import FunctionHandler
from bokeh.application import Application
from bokeh.server.server import Server
from bokeh.embed import server_document
from tornado.ioloop import IOLoop

import datetime as dt
import random

from scipy import optimize

#Gather only used datas/other for eventual future uses:
cases = pd.read_csv("https://epistat.sciensano.be/Data/COVID19BE_CASES_AGESEX.csv", encoding="ISO-8859-1", index_col="DATE", parse_dates=True)
#muni = pd.read_csv("https://epistat.sciensano.be/Data/COVID19BE_CASES_MUNI.csv", encoding="ISO-8859-1", index_col="DATE", parse_dates=True)
#muni_cum = pd.read_csv("https://epistat.sciensano.be/Data/COVID19BE_CASES_MUNI_CUM.csv", encoding="ISO-8859-1")
hosp = pd.read_csv("https://epistat.sciensano.be/Data/COVID19BE_HOSP.csv", encoding="ISO-8859-1", index_col="DATE", parse_dates=True)
deaths = pd.read_csv("https://epistat.sciensano.be/Data/COVID19BE_MORT.csv", encoding="ISO-8859-1", index_col="DATE", parse_dates=True)
#tests = pd.read_csv("https://epistat.sciensano.be/Data/COVID19BE_tests.csv", encoding="ISO-8859-1", index_col="DATE", parse_dates=True)

french = pd.read_csv("https://raw.githubusercontent.com/opencovid19-fr/data/master/data-sources/sante-publique-france/covid_hospit.csv",\
                     sep=";", index_col="jour", parse_dates=True)

tmp = pd.DataFrame(cases.groupby('DATE').sum()['CASES'])
df2 = deaths.groupby("DATE").sum().merge(hosp.groupby("DATE").sum(), on="DATE")
df2 = tmp.merge(df2, on="DATE", how='left').fillna(0).astype(int)
df2 = df2[['CASES', 'DEATHS', 'TOTAL_IN', 'TOTAL_IN_ICU', 'NEW_IN', 'NEW_OUT']]

bar_cat = ['CASES', 'DEATHS', 'TOTAL_IN', 'TOTAL_IN_ICU']
line_cat = ['NEW_IN', 'NEW_OUT']

df_line = df2[line_cat]

#easier to work with an un-tidy dataset in Bokeh
def make_dataset(list_cat):
    #only chosen cat

    plot_df_bar = df2[list_cat].reset_index().melt(['DATE']).set_index('DATE').sort_index() #adios tidy data :/

    #new format as typical melted DF/"multi-index without being multiindexed" :
    #DATE  variable value
    #day-1 CASES     28
    #day-1 DEATHS    1
    #day-2 CASES (...)
        
    colors = {'CASES':'grey', 'DEATHS':'darkgrey', 'TOTAL_IN':'orange', 'TOTAL_IN_ICU':'yellow'}
    
    plot_df_bar["color"] = plot_df_bar["variable"].map(colors)
    
    #for better visibility : order 
    
    plot_df_bar['variable'] = pd.Categorical(plot_df_bar['variable'],\
                        ['TOTAL_IN', 'CASES', 'TOTAL_IN_ICU','DEATHS'])
    plot_df_bar = plot_df_bar.sort_values(['variable'])
    

    
    return ColumnDataSource(plot_df_bar)


def make_plot(src_bar):
  
    # create a new plot with a datetime axis type
    p = figure(plot_width=700, plot_height=700, x_axis_type="datetime", title = "Belgique")
        
    p.vbar(x='DATE', top='value', source = src_bar, fill_alpha = 1,\
           hover_fill_alpha = 1.0, line_color = 'black', width=dt.timedelta(1), \
               color='color', legend='variable', name="vbars")

    
    colors = {'NEW_IN':'red', 'NEW_OUT':'green'}
    names = df_line.columns
    for i in names:
        p.line(x=df_line.index, y=df_line[i], legend_label=i, line_width=4, color=colors[i], name=i)
        


    #define tooltips    
    p.add_tools(HoverTool(tooltips = [('Date', '@DATE{%F}'), ('', '@variable: @value')],\
                          formatters={'@DATE': 'datetime'}, point_policy="follow_mouse", mode="vline", names=["vbars"]))
        
    p.add_tools(HoverTool(tooltips = [('', '$name: @value')],\
                          point_policy="follow_mouse", mode="vline", names=list(names)))

    # attributes
    p.legend.location = "top_left"
    p.grid.grid_line_alpha = 0
    p.xaxis.axis_label = 'Date'
    p.yaxis.axis_label = 'Value'
    p.ygrid.band_fill_color = "olive"
    p.ygrid.band_fill_alpha = 0.1

    f = figure(plot_width=700, plot_height=700, x_axis_type="datetime", title = "France")
    list_cat = ['hosp', 'rea', 'dc']
    french_bar = french[list_cat].reset_index().melt(['jour']).set_index('jour').sort_index() #adios tidy data :/
    colors = {'hosp':'grey', 'rea':'darkgrey', 'dc':'orange', 'rad':'yellow'}
    french_bar["color"] = french_bar["variable"].map(colors)

    french_bar['variable'] = pd.Categorical(french_bar['variable'],\
                        ['hosp', 'rad', 'rea','dc'])
    french_bar = french_bar.sort_values(['variable'])

    french_bar = ColumnDataSource(french_bar)

    f.vbar(x='jour', top='value', source = french_bar, fill_alpha = 1,\
           hover_fill_alpha = 1.0, width=dt.timedelta(1), \
              line_color='black', color='color', legend='variable', name='french_bar')
        
    f.legend.location = "top_left"
    f.grid.grid_line_alpha = 0
    f.xaxis.axis_label = 'Date'
    f.yaxis.axis_label = 'Value'
    f.ygrid.band_fill_color = "olive"
    f.ygrid.band_fill_alpha = 0.1
    
    return p, f

def update(attr, old, new):
    #chosen cat
    cat_to_plot = [cat_selection.labels[i] for i in cat_selection.active]
    new_bar = make_dataset(cat_to_plot)
    src_bar.data.update(new_bar.data)


cat_selection = CheckboxGroup(labels=bar_cat, active=[1, 2, 3])
cat_selection.on_change('active', update)

init_cat = [cat_selection.labels[i] for i in cat_selection.active]


src_bar = make_dataset(init_cat) 
p, f = make_plot(src_bar)
layout = Column(cat_selection, p, f)
curdoc().add_root(layout)
