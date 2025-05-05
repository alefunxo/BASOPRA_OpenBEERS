# -*- coding: utf-8 -*-
## @namespace graphs
# Created on Wed Feb 28 09:47:22 2018
# Author
# Alejandro Pena-Bello
# alejandro.penabello@unige.ch
# Script used to plot the results of the SI in the paper Optimization of PV-coupled battery systems for combining applications: impact of battery technology and location (Pena-Bello et al 2018 to be published).
# The script works in Linux and Windows
# INPUTS
# ------
# OUTPUTS
# -------
# TODO
# ----
# User Interface, including path to save the results and choose countries, load curves, etc.
# Requirements
# ------------
# Pandas, numpy, itertools,sys,glob,multiprocessing, time, math.pi, itertools.group, matplotlib and seaborn

import sys,os
import numpy as np
import pandas as pd
import paper_classes_2 as pc
import matplotlib.pyplot as plt
import matplotlib.path as path1
from itertools import groupby
from matplotlib.patches import FancyBboxPatch
import matplotlib.patches as patches
import seaborn as sns
from math import pi
from itertools import groupby
import itertools
import graphs as g
Color_US='blue'
Color_CH='red'
width=1/1.5
figsize=(10,5)
title_size=20
large_size=18
normal_size=16
medium_size=14
small_size=12
project_life=15

def comparison_avg_season_month_demand(df_CH_season,df_CH_month,df_US_season,df_US_month):
    '''
    Description
    -----------
    This function plots side by side the comparison between the demand in the U.S. and the demand in Switzerland for every season and every month.

    Inputs
    ----------
    df_CH_season: DataFrame; Swiss DataFrame grouped by season
    df_CH_month: DataFrame; Swiss DataFrame grouped by month
    df_US_season: DataFrame; US DataFrame grouped by season
    df_US_month: DataFrame; US DataFrame grouped by month

    Returns
    ------

    '''
    N = 4
    ind = np.arange(N)  # the x locations for the groups
    width = 0.3       # the width of the bars
    font=20
    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(1,2,1)
    rects1 = ax.bar(ind, df_CH_season, width, color='r')
    rects2 = ax.bar(ind + width, df_US_season, width, color='b')

    # add some text for labels, title and axes ticks
    ax.set_ylabel('Total consumption [kWh]',fontsize=large_size)
    ax.set_xlabel('Season',fontsize=large_size)
    ax.set_title('a. Average consumption per \n household per season',fontsize=title_size)
    ax.set_xticks(ind + width / 2)
    ax.set_xticklabels(('Winter','Spring','Summer','Fall'))
    ax.legend((rects1[0], rects2[0]), ('Geneva', 'Austin'),fontsize=medium_size)
    width = 0.4
    plt.tick_params(axis='both', which='major', labelsize=medium_size)

    ax = fig.add_subplot(1,2,2)
    N = 12
    ind = np.arange(N)  # the x locations for the groups
    rects1 = ax.bar(ind, df_CH_month, width, color='r')
    rects2 = ax.bar(ind + width, df_US_month, width, color='b')

    # add some text for labels, title and axes ticks
    ax.set_ylabel('Total consumption [kWh]',fontsize=large_size)
    ax.set_xlabel('Month of the year',fontsize=large_size)

    ax.set_title('b. Average consumption per \n household per month',fontsize=title_size)
    ax.set_xticks(ind + width / 2)
    ax.set_xticklabels((df_CH_month.index))
    ax.legend((rects1[0], rects2[0]), ('Geneva', 'Austin'),fontsize=medium_size)
    plt.tick_params(axis='both', which='major', labelsize=medium_size)

    plt.tight_layout()



    plt.show()
    fig.savefig('Demand.pdf')
def comparison_avg_season_month_PV(PV_CH_season,PV_CH_month,PV_US_season,PV_US_month):
    '''
    Description
    -----------
    This function plots side by side the comparison between the PV generation of a 1 kW PV panel in the U.S. and in Switzerland for every season and every month.

    Inputs
    ----------
    PV_CH_season: DataFrame; Swiss DataFrame grouped by season
    PV_CH_month: DataFrame; Swiss DataFrame grouped by month
    PV_US_season: DataFrame; US DataFrame grouped by season
    PV_US_month: DataFrame; US DataFrame grouped by month

    Returns
    ------

    '''
    N = 4
    ind = np.arange(N)  # the x locations for the groups
    width = 0.3       # the width of the bars
    font=20
    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(1,2,1)
    rects1 = ax.bar(ind, PV_CH_season.values.flatten(), width, color=Color_CH)
    #rects2 = ax.bar(ind + width, PV_US_season.values.flatten(), width, color='white',edgecolor='black', hatch='//')
    rects2 = ax.bar(ind + width, PV_US_season.values.flatten(), width, color=Color_US)

    # add some text for labels, title and axes ticks
    ax.set_ylabel('Total PV production [kWh]',fontsize=large_size)
    ax.set_xlabel('Season',fontsize=large_size)
    ax.set_title('a. PV production of a 1 kWp \n installation per season',fontsize=large_size)
    ax.set_xticks(ind + width / 2)
    ax.set_xticklabels(('Winter','Spring','Summer','Fall'))
    ax.legend((rects1[0], rects2[0]), ('Geneva', 'Austin'),fontsize=small_size,loc=2)
    width = 0.3
    plt.tick_params(axis='both', which='major', labelsize=medium_size)

    ax = fig.add_subplot(1,2,2)
    N = 12
    ind = np.arange(N)  # the x locations for the groups
    rects1 = ax.bar(ind, PV_CH_month.values.flatten(), width, color=Color_CH)
    rects2 = ax.bar(ind + width, PV_US_month.values.flatten(), width, color=Color_US)

    # add some text for labels, title and axes ticks
    ax.set_ylabel('Total PV production [kWh]',fontsize=large_size)
    ax.set_xlabel('Month of the year',fontsize=large_size)

    ax.set_title('b. PV production of a 1 kWp \n installation per month',fontsize=large_size)
    ax.set_xticks(ind + width / 2)
    ax.set_xticklabels((PV_CH_month.index))
    ax.legend((rects1[0], rects2[0]), ('Geneva', 'Austin'),fontsize=small_size,loc=2)
    plt.tick_params(axis='both', which='major', labelsize=medium_size)

    plt.tight_layout()

    fig.savefig('Generation.pdf')


    plt.show()

def PV_size_distribution():
    '''
    Description
    -----------
    This function plots side by side the comparison between the PV size distribution in the U.S. and in Switzerland.

    Inputs
    ----------


    Returns
    ------

    '''
    if sys.platform=='win32':
        init_path='C:/Users/alejandro/'
    else :
        init_path='/home/alefunxo/'
    max_PV=10
    path=init_path+'/Dropbox/0. PhD/2017/Paper 1/PV/'
    df_pv_ch=pd.read_excel(path+'PV_beneficiaires_Swiss.xlsx')
    df_nat=df_pv_ch[(df_pv_ch['Anlage_Projekt-Bezeichnung']=='natürliche Person')]
    df_nat_pv=df_nat[(df_nat['Anlage_Energieträger']=='Photovoltaik')]

    df_nat_pv_15=df_nat_pv[df_nat_pv['Leistung [kW]']<max_PV]['Leistung [kW]'].reset_index(drop=True)
    bins_CH=np.linspace(.3,max_PV,(max_PV-.3)*5+1)
    n_CH=pd.cut(df_nat_pv_15,bins_CH).value_counts().sort_index()
    path=init_path+'Dropbox/0. PhD/2017/Paper 1/PV/'
    df_pv_us=pd.read_excel(path+'PV texas.xlsx')
    df_nat=df_pv_us[(df_pv_us['install_type']=='Residential')|
            (df_pv_us['install_type']=='residential')]
    df_nat_pv=df_nat[(df_nat['city']=='Austin')|(df_nat['city']=='AUSTIN')]
    df_nat_pv_10=df_nat_pv[df_nat_pv['size_kw']<max_PV].size_kw.reset_index(drop=True)
    bins_US=np.linspace(.3,max_PV,(max_PV-.3)*5+1)
    n_US=pd.cut(df_nat_pv_10,bins_US).value_counts().sort_index()
    Color_lines_CH=Color_US
    Color_lines_US=Color_CH
    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(1,2,1)
    # get the corners of the rectangles for the histogram
    left = np.array(bins_CH[:-1])
    right = np.array(bins_CH[1:])
    bottom = np.zeros(len(left))
    top = bottom + n_CH
    # we need a (numrects x numsides x 2) numpy array for the path helper
    # function to build a compound path
    XY = np.array([[left, left, right, right], [bottom, top, top, bottom]]).T

    # get the Path object
    barpath = path1.Path.make_compound_path_from_polys(XY)

    # make a patch out of it
    patch = patches.PathPatch(barpath,color=Color_CH)
    ax.add_patch(patch)

    # update the view limits
    ax.set_xlim(left[0], right[-1])
    ax.set_ylim(bottom.min(), top.max())
    ax.axvline(x=df_nat_pv_15.quantile(0.25),color=Color_lines_CH, linestyle='--')
    ax.axvline(x=df_nat_pv_15.quantile(0.75),color=Color_lines_CH, linestyle='--')
    ax.axvline(x=df_nat_pv_15.quantile(0.5),color=Color_lines_CH, linestyle='--')
    ax.set_xlabel('PV size [kW]',fontsize=large_size)
    ax.set_ylabel('Frequency',fontsize=large_size)
    ax.set_title('a. PV system size distribution \n for Switzerland',fontsize=large_size)
    plt.tick_params(axis='both', which='major', labelsize=medium_size)


    ax = fig.add_subplot(1,2,2)
    # get the corners of the rectangles for the histogram
    left = np.array(bins_US[:-1])
    right = np.array(bins_US[1:])
    bottom = np.zeros(len(left))
    top = bottom + n_US
    # we need a (numrects x numsides x 2) numpy array for the path helper
    # function to build a compound path
    XY = np.array([[left, left, right, right], [bottom, top, top, bottom]]).T

    # get the Path object
    barpath = path1.Path.make_compound_path_from_polys(XY)

    # make a patch out of it
    patch = patches.PathPatch(barpath,color=Color_US)
    ax.add_patch(patch)

    # update the view limits
    ax.set_xlim(left[0], right[-1])
    ax.set_ylim(bottom.min(), top.max())
    ax.axvline(x=df_nat_pv_10.quantile(0.25),color=Color_lines_US, linestyle='--')
    ax.axvline(x=df_nat_pv_10.quantile(0.75),color=Color_lines_US, linestyle='--')
    ax.axvline(x=df_nat_pv_10.quantile(0.5),color=Color_lines_US, linestyle='--')
    ax.set_xlabel('PV size [kW]',fontsize=large_size)
    ax.set_ylabel('Frequency',fontsize=large_size)
    ax.set_title('b. PV system size distribution \n for Austin',fontsize=large_size)
    #plt.suptitle('Size of PV installations', fontsize=font+4)
    plt.tick_params(axis='both', which='major', labelsize=medium_size)

    plt.tight_layout()

    fig.savefig('Size.pdf')
    plt.show()

def Electricity_prices(ep_CH_season,ep_CH_month,ep_US_season,ep_US_month):
    '''
    Description
    -----------
    This function plots side by side the comparison between the electricity prices in Austin, TX, U.S. and in Switzerland for every season and every month of 2015.

    Inputs
    ----------
    ep_CH_season: DataFrame; Swiss DataFrame grouped by season
    ep_CH_month: DataFrame; Swiss DataFrame grouped by month
    ep_US_season: DataFrame; US DataFrame grouped by season
    ep_US_month: DataFrame; US DataFrame grouped by month

    Returns
    ------

    '''
    N = 4
    ind = np.arange(N)  # the x locations for the groups
    width = 0.3       # the width of the bars
    font=20
    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(1,2,1)
    rects1 = ax.bar(ind, ep_CH_season.values.flatten(), width, color='r')
    rects2 = ax.bar(ind + width, ep_US_season.values.flatten(), width, color='b')
    ax.set_ylim(0, 0.06)

    # add some text for labels, title and axes ticks
    ax.set_ylabel('Electricity price [USD/kWh]',fontsize=large_size)
    ax.set_xlabel('Season',fontsize=large_size)
    ax.set_title('a. Average electricity prices \n per season',fontsize=large_size)
    ax.set_xticks(ind + width / 2)
    ax.set_xticklabels(('Winter','Spring','Summer','Fall'))
    ax.legend((rects1[0], rects2[0]), ('Geneva', 'Austin'),fontsize=small_size,loc=9)
    width = 0.3
    plt.tick_params(axis='both', which='major', labelsize=medium_size)

    ax = fig.add_subplot(1,2,2)
    N = 12
    ind = np.arange(N)  # the x locations for the groups
    rects1 = ax.bar(ind, ep_CH_month, width, color='r')
    rects2 = ax.bar(ind + width, ep_US_month, width, color='b')
    ax.set_ylim(0, 0.06)

    # add some text for labels, title and axes ticks
    ax.set_ylabel('Electricity price [USD/kWh]',fontsize=large_size)
    ax.set_xlabel('Month of the year',fontsize=large_size)

    ax.set_title('b.  Average electricity prices \n per month',fontsize=large_size)
    ax.set_xticks(ind + width / 2)
    ax.set_xticklabels((ep_CH_month.index))
    plt.tick_params(axis='both', which='major', labelsize=medium_size)

    ax.legend((rects1[0], rects2[0]), ('Geneva', 'Austin'),fontsize=small_size,loc=9)
    plt.tight_layout()

    fig.savefig('Prices.pdf')


    plt.show()
def main():
    '''
    Description
    -----------
    Calls all the functions to plot the graphs in the SI of the paper
    '''
    if sys.platform=='win32':
        init_path='C:/Users/alejandro/'
    else :
        init_path='/home/alefunxo/'
    print("########################################################")
    print("SI graphics from the paper Optimization of PV-coupled battery systems for combining applications: impact of battery technology and location. Pena-Bello et al. (2019)")
    print("########################################################")
    print("Loading data")
    #Demand
    path=(init_path+'Documents/Data/CREM_755_Loadprofiles_15_min_2015')
    date=pd.DatetimeIndex(start='2015-01-01 00:00:00',
          end='2015-12-31 23:50:00',freq='15min',tz='Europe/Brussels')
    df_CH=pd.read_csv(path+'/df_CH_Use_final.csv',index_col=[0],
        parse_dates=[0],infer_datetime_format=True)
    df_CH=df_CH.set_index(date)
    path=(init_path+'Documents/Data/Pecan_Street')
    date=pd.DatetimeIndex(start='2015-01-01 00:00:00',
          end='2015-12-31 23:50:00',freq='15min',tz='US/Central')
    df_US=pd.read_csv(path+'/df_barbour_use_final.csv',index_col=[0],
        parse_dates=[0],infer_datetime_format=True)
    df_US=df_US.set_index(date)
    #PV generation
    filename=(init_path+'Documents/Data/PV/GVA/'
       'GVA_Generated_15_min.pickle')
    PV_CH=(pd.read_pickle(filename)*0.25/230).set_index(df_CH.index)
    filename=(init_path+'Documents/Data/PV/DataAustin/'
                      'Austin_Generated_15_min.pickle')
    PV_US=(pd.read_pickle(filename)*0.25/230).set_index(df_US.index)
    #Electricity prices
    ep_CH=pd.read_csv(init_path+'Dropbox/0. PhD/Python/Paper1/'
                                 'Paper1_v5/Day_ahead_Prices_2015_CH'
                                 '.csv')['Day-ahead Price [EUR/MWh]']/1000
    date=pd.DatetimeIndex(start='2015-01-01 00:00:00',
      end='2016-01-01 00:00:00',freq='1h',tz='Europe/Brussels')
    ep_CH.index=pd.to_datetime(date)
    ep_CH=ep_CH.resample('15min').ffill()
    ep_CH=ep_CH[:-1]
    ep_US=pd.read_csv(init_path+'Dropbox/0. PhD/Python/Paper1/'
                                     'Paper1_v5/Day_ahead_Prices_2015_ERCOT'
                                     '.csv',sep=',')
    ep_US=(ep_US[ep_US.zone=='LZ_SOUTH']['price']/1000).reset_index(drop=True)
    ep_US.loc[ep_US.index[-1]+1]=ep_US[ep_US.index[-1]]
    date=pd.DatetimeIndex(start='2015-01-01 00:00:00',
      end='2016-01-01 00:00:00',freq='1h',tz='US/Central')
    ep_US.index=date
    ep_US=ep_US.resample('15min').ffill()
    ep_US=ep_US[:-1]
    #Processing DataFrames
    spring = range(80, 172)#march 20
    summer = range(172, 264)#june 21
    fall = range(264, 355)#september 22
    # winter = everything else#december 21
    df_CH['season']='winter'
    df_CH.loc[(df_CH.index.dayofyear>80) &(df_CH.index.dayofyear < 172),'season']='spring'
    df_CH.loc[(df_CH.index.dayofyear>=172) &(df_CH.index.dayofyear < 264),'season']='summer'
    df_CH.loc[(df_CH.index.dayofyear>=264) &(df_CH.index.dayofyear < 355),'season']='fall'

    df_US['season']='winter'
    df_US.loc[(df_US.index.dayofyear>80) &(df_US.index.dayofyear < 172),'season']='spring'
    df_US.loc[(df_US.index.dayofyear>=172) &(df_US.index.dayofyear < 264),'season']='summer'
    df_US.loc[(df_US.index.dayofyear>=264) &(df_US.index.dayofyear < 355),'season']='fall'
    df_CH_season=df_CH.groupby(df_CH.season,sort=False).sum().mean(axis=1)
    df_US_season=df_US.groupby(df_US.season,sort=False).sum().mean(axis=1)
    df_CH_month=df_CH.groupby(df_CH.index.month).sum().mean(axis=1)
    df_US_month=df_US.groupby(df_US.index.month).sum().mean(axis=1)
    PV_CH['season']='winter'
    PV_CH.loc[(PV_CH.index.dayofyear>80) &(PV_CH.index.dayofyear < 172),'season']='spring'
    PV_CH.loc[(PV_CH.index.dayofyear>=172) &(PV_CH.index.dayofyear < 264),'season']='summer'
    PV_CH.loc[(PV_CH.index.dayofyear>=264) &(PV_CH.index.dayofyear < 355),'season']='fall'

    PV_US['season']='winter'
    PV_US.loc[(PV_US.index.dayofyear>80) &(PV_US.index.dayofyear < 172),'season']='spring'
    PV_US.loc[(PV_US.index.dayofyear>=172) &(PV_US.index.dayofyear < 264),'season']='summer'
    PV_US.loc[(PV_US.index.dayofyear>=264) &(PV_US.index.dayofyear < 355),'season']='fall'
    PV_CH_season=PV_CH.groupby(PV_CH.season,sort=False).sum()
    PV_US_season=PV_US.groupby(PV_US.season,sort=False).sum()
    max_PV=10
    PV_CH_month=PV_CH.groupby(PV_CH.index.month).sum().mean(axis=1)
    PV_US_month=PV_US.groupby(PV_US.index.month).sum().mean(axis=1)
    ep_CH_month=ep_CH.groupby(ep_CH.index.month).mean()
    ep_US_month=ep_US.groupby(ep_US.index.month).mean()
    ep_CH=pd.DataFrame(ep_CH)
    ep_US=pd.DataFrame(ep_US)
    ep_CH['season']='winter'
    ep_CH.loc[(ep_CH.index.dayofyear>80) &(ep_CH.index.dayofyear < 172),'season']='spring'
    ep_CH.loc[(ep_CH.index.dayofyear>=172) &(ep_CH.index.dayofyear < 264),'season']='summer'
    ep_CH.loc[(ep_CH.index.dayofyear>=264) &(ep_CH.index.dayofyear < 355),'season']='fall'

    ep_US['season']='winter'
    ep_US.loc[(ep_US.index.dayofyear>80) &(ep_US.index.dayofyear < 172),'season']='spring'
    ep_US.loc[(ep_US.index.dayofyear>=172) &(ep_US.index.dayofyear < 264),'season']='summer'
    ep_US.loc[(ep_US.index.dayofyear>=264) &(ep_US.index.dayofyear < 355),'season']='fall'

    ep_CH_season=ep_CH.groupby(ep_CH.season,sort=False).mean()
    ep_US_season=ep_US.groupby(ep_US.season,sort=False).mean()
    # Post_processed Data
    dfa=pd.read_pickle('dfa_V2.pickle')#aggregated

    print("########################################################")
    print("Plotting")
    #Fig 1
    #Schematic
    #Fig 2
    comparison_avg_season_month_demand(df_CH_season,df_CH_month,df_US_season,df_US_month)
    #Fig 3
    #Distributions consumption MISSING
    #Fig 4
    # Variance clusters MISSING
    #Fig 5
    comparison_avg_season_month_PV(PV_CH_season,PV_CH_month,PV_US_season,PV_US_month)
    #Fig 6
    PV_size_distribution()
    #Fig 7
    Electricity_prices(ep_CH_season,ep_CH_month,ep_US_season,ep_US_month)
    #Fig 8
    #DC-coupled figure
    #Fig 9
    #Woehler curves
    #Model validation
    #Fig 10
    #Single off-peak
    #Fig 11
    #Square wave test
    #Fig 12
    #Sinus wave test
    #Fig 13
    g.plot_col2(dfa,'LCOES',7,50,1,App=[1,3,5,6,7])
    #Fig 14
    g.plot_col2(dfa,'LVOES',7,50,1,App=[1,3,5,6,7])
    #Fig 15
    g.plot_col2(dfa,'NPV',7,50,1,App=[1,3,5,6,7])

    #Fig 16
    g.plot_PV2(dfa,'CH',7,1)
    #Fig 17
    g.plot_PV2(dfa,'US',7,1)


    print("End plotting SI paper")
    print("########################################################")

if __name__== '__main__':
    main()
