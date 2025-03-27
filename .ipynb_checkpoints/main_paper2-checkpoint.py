# -*- coding: utf-8 -*-
## @namespace main_paper
# Created on Wed Feb 28 09:47:22 2018
# Author
# Alejandro Pena-Bello
# alejandro.penabello@unige.ch
# Modification of main script used for the paper Optimized PV-coupled battery systems for combining applications: Impact of battery technology and geography (Pena-Bello et al 2019).
# This enhancement includes the use of HP and thermal storage together with the previously assessed PV and battery system. We study the different applications which residential batteries can perform from a consumer perspective. Applications such as avoidance of PV curtailment, demand load-shifting and demand peak shaving are considered along  with the base application, PV self-consumption. It can be used with six different battery technologies currently available in the market are considered as well as three sizes (3 kWh, 7 kWh and 14 kWh). We analyze the impact of the type of demand profile and type of tariff structure by comparing results across dwellings in Switzerland.
# The HP, battery and TS schedule is optimized for every day (i.e. 24 h optimization framework), we assume perfect day-ahead forecast of the electricity and heat demand load and solar PV generation in order to determine the maximum economic potential regardless of the forecast strategy used. Battery aging was treated as an exogenous parameter, calculated on daily basis and was not subject of optimization. Data with 15-minute temporal resolution were used for simulations. The model objective function have two components, the energy-based and the power-based component, as the tariff structure depends on the applications considered, a boolean parameter activate the power-based factor of the bill when is necessary.

# The script has been tested in Linux and Windows
# This script works was tested with pyomo version 5.4.3
# INPUTS
# ------
# OUTPUTS
# -------
# TODO
# ----
# User Interface, including path to save the results and choose countries, load curves, etc.
# Simplify by merging select_data and load_data and probably load_param.
# Requirements
# ------------
#  Pandas, numpy, sys, glob, os, csv, pickle, functools, argparse, itertools, time, math, pyomo and multiprocessing


import sys
if sys.platform!='win32':
    import resource
import os
import pandas as pd
import argparse
import numpy as np
import itertools
import sys
import glob
import multiprocessing as mp
import time
import paper_classes as pc
from functools import wraps
from pathlib import Path
import traceback
import pickle
import csv
from Core_LP import single_opt2
import post_proc as pp

def fn_timer(function):
    @wraps(function)
    def function_timer(*args, **kwargs):
        t0 = time.time()
        result = function(*args, **kwargs)
        t1 = time.time()
        print ("Total time running %s: %s seconds" %
               (function.__name__, str(t1-t0))
               )
        return result
    return function_timer

def memory_limit():
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    resource.setrlimit(resource.RLIMIT_AS, (get_memory() * 1024 / 2, hard))
    print(get_memory() * 1024 / 2)

def get_memory():
    with open('/proc/meminfo', 'r') as mem:
        free_memory = 0
        for i in mem:
            sline = i.split()
            if str(sline[0]) in ('MemTotal:'):
                free_memory += int(sline[1])

    return free_memory
def expand_grid(dct):
    rows = itertools.product(*dct.values())
    return pd.DataFrame.from_records(rows, columns=dct.keys())

def str2bool(v):
    return v.lower() in ("yes", "true", "t", "1")

def load_obj(name ):
    with open(name + '.pkl', 'rb') as f:
        return pickle.load(f)

def load_param(combinations):
    '''
    Description
    -----------
    Load all parameters into a dictionary, if aging is present (True) or not
    (False), percentage of curtailment, Inverter and Converter efficiency, time
    resolution (0.25), number of years or days if only some days want to be
    optimized, applications, capacities and technologies to optimize.

    Applications are defined as a Boolean vector, where a True activates the
    corresponding application. PVSC is assumed to be always used. The order
    is as follows: [PVCT, PVSC, DLS, DPS]
	i.e PV avoidance of curtailment, PV self-consumption,
	Demand load shifting and demand peak shaving.
    [0,1,0,0]-0
    [0,1,0,1]-1
    [0,1,1,0]-2
    [0,1,1,1]-3
    [1,1,0,0]-4
    [1,1,0,1]-5
    [1,1,1,0]-6
    [1,1,1,1]-7


    Parameters
    ----------
    PV_nominal_power : int

    Returns
    ------
    param: dict
    Comments
    -----
    week 18 day 120 is transtion from cooling to heating
    week 40 day 274 is transtion from cooling to heating
    '''

    print('##############')
    print('loading data')
    print(int(combinations['App_comb']))
    print('****************')
    id_dwell=str(int(combinations['hh']))
    print(id_dwell)
    [clusters,PV,App_comb_df,conf,house_types,hp_types,rad_types]=pp.get_table_inputs()

    PV_nom=PV[PV.PV==combinations['PV_nom']].PV.values[0]
    quartile=PV[(PV.PV==combinations['PV_nom'])&(PV.country==combinations['country'])].quartile.values[0]
    App_comb=[str2bool(i) for i in App_comb_df[App_comb_df.index==int(combinations['App_comb'])].App_comb.values[0].split(' ')]

    #id_dwell=str(int(combinations['hh']))
    #id_dwell=str(int(clusters[(clusters.cluster==int(combinations['cluster'][1:-1]))&(clusters.country==combinations['country'])].hh.values[0]))
################################################
    design_param=load_obj('Input/dict_design')
    aging=True
    Inverter_power=round(PV_nom/1.2,1)
    Curtailment=0.5
    Inverter_Efficiency=0.95
    Converter_Efficiency_HP=0.98
    dt=0.25
    Capacity_tariff=9.39*12/365
    nyears=1
    days=365
    testing=False
    cooling=False
    week=47
################################################

    filename_el=Path('Input/Electricity_demand_supply_2017.csv')
    filename_heat=Path('Input/preprocessed_heat_demand_2017.csv')
    filename_prices=Path('Input/Prices_2017.csv')

    fields_el=['index',id_dwell,'E_PV']
    new_cols=['E_demand', 'E_PV']

    df_el = pd.read_csv(filename_el,engine='python',sep=',|;',index_col=0,
                        parse_dates=[0],infer_datetime_format=True, usecols=fields_el)

    if np.issubdtype(df_el.index.dtype, np.datetime64):
        df_el.index=df_el.index.tz_localize('UTC').tz_convert('Europe/Brussels')
    else:
        df_el.index=pd.to_datetime(df_el.index,utc=True)
        df_el.index=df_el.index.tz_convert('Europe/Brussels')

    df_el.columns=new_cols

    if (combinations['house_type']=='SFH15')| (combinations['house_type']=='SFH45'):
        aux_name='SFH15_45'
    else:
        aux_name='SFH100'

    fields_heat=['index','Set_T','Temp', combinations['house_type']+'_kWh','DHW_kWh', 'Temp_supply_'+aux_name,'Temp_supply_'+aux_name+'_tank',
                'COP_'+combinations['house_type'],'hp_'+combinations['house_type']+'_el_cons','COP_'+combinations['house_type']+'_DHW',
                 'hp_'+combinations['house_type']+'_el_cons_DHW','COP_'+combinations['house_type']+'_tank',
                 'hp_'+combinations['house_type']+'_tank_el_cons']
    new_cols=['Set_T','Temp', 'Req_kWh','Req_kWh_DHW','Temp_supply','Temp_supply_tank','COP_SH','COP_tank','COP_DHW',
              'hp_sh_cons','hp_tank_cons','hp_dhw_cons']
    df_heat=pd.read_csv(filename_heat,engine='python',sep=';',index_col=[0],
                        parse_dates=[0],infer_datetime_format=True, usecols=fields_heat)
    df_heat.columns=new_cols


    if np.issubdtype(df_heat.index.dtype, np.datetime64):
        df_heat.index=df_heat.index.tz_localize('UTC').tz_convert('Europe/Brussels')
    else:
        df_heat.index=pd.to_datetime(df_heat.index,utc=True)
        df_heat.index=df_heat.index.tz_convert('Europe/Brussels')

    fields_prices=['index', 'Price_flat', 'Price_DT', 'Export_price', 'Price_flat_mod',
   'Price_DT_mod']
    df_prices=pd.read_csv(filename_prices,engine='python',sep=',|;',index_col=[0],
                        parse_dates=[0],infer_datetime_format=True ,usecols=fields_prices)

    if np.issubdtype(df_prices.index.dtype, np.datetime64):
        df_prices.index=df_prices.index.tz_localize('UTC').tz_convert('Europe/Brussels')
    else:
        df_prices.index=pd.to_datetime(df_prices.index,utc=True)
        df_prices.index=df_prices.index.tz_convert('Europe/Brussels')

    data_input=pd.concat([df_el,df_heat,df_prices],axis=1,copy=True,sort=False)
    #skip the first DHW data since cannot be produced simultaneously with SH
    data_input.loc[(data_input.index.hour<1),'Req_kWh_DHW']=0
    T_var=data_input.Temp.resample('1d').mean()
    data_input.loc[:,'E_PV']=data_input.loc[:,'E_PV']*PV_nom
    data_input['T_var']=T_var
    data_input.T_var=data_input.T_var.fillna(method='ffill')
    data_input['Cooling']=0
    data_input.loc[((data_input.index.month<=4)|(data_input.index.month>=10))&(data_input.Req_kWh<0),'Req_kWh']=0
    if cooling:
        data_input.loc[(data_input.index.month>4)&(data_input.index.month<10)&(data_input.T_var>20),'Cooling']=1#is T_var>20 then we need to cool only
        data_input.loc[(data_input.Cooling==1)&(data_input.Req_kWh>0),'Req_kWh']=0#if we should cool then ignore the heating requirements
        data_input.loc[(data_input.Cooling==1),'Req_kWh']=abs(data_input.loc[(data_input.Cooling==1),'Req_kWh'])

    data_input.loc[(data_input.index.month>4)&(data_input.index.month<10)&(data_input.Cooling==0),'Req_kWh']=0#if we should heat then ignore the cooling requirements
    data_input['Temp']=data_input['Temp']+273.15
    data_input['Set_T']=data_input['Set_T']+273.15
    data_input['Temp_supply']=data_input['Temp_supply']+273.15
    data_input['Temp_supply_tank']=data_input['Temp_supply_tank']+273.15
    data_input.loc[data_input.index.dayofyear==120,'Req_kWh']=0
    data_input.loc[data_input.index.dayofyear==274,'Req_kWh']=0
    data_input.loc[(data_input.index.dayofyear<120)|(data_input.index.dayofyear>274),'season']=0#'heating'
    data_input.loc[data_input.index.dayofyear==120,'season']=1#'transition_heating_cooling'
    data_input.loc[(data_input.index.dayofyear>120)&(data_input.index.dayofyear<274),'season']=2#'cooling'
    data_input.loc[data_input.index.dayofyear==274,'season']=3#'transition_cooling_heating'
    if data_input[((data_input.index.dayofyear<120)|(data_input.index.dayofyear>274))&(data_input.Temp_supply==data_input.Temp_supply_tank)].empty==False:
        data_input.loc[((data_input.index.dayofyear<120)|(data_input.index.dayofyear>274))&(data_input.Temp_supply==data_input.Temp_supply_tank),'Temp_supply_tank']+=1.5

    if testing:
        data_input=data_input[data_input.index.week==week]
        nyears=1
        days=7
        ndays=7

    print('##############')
    print('load parameters')
    conf=combinations['conf']
    print('conf')
    print(conf)

    #configuration=[Batt,HP,TS,DHW]
    #if all false, only PV
    conf_aux=[False,True,False,False]#[Batt,HP,TS,DHW]

    if conf<4:#No battery
        #print('inside batt')
        Converter_Efficiency_Batt=1
    else:
        conf_aux[0]=True
        Converter_Efficiency_Batt=0.98

    if (conf!=0)&(conf!=1)&(conf!=4)&(conf!=5):#TS present
        #print('inside TS')
        conf_aux[2]=True

        tank_sh=pc.heat_storage_tank(mass=1500,surface=5.6) # For a 1500 liter tank with 1.426 m height and 1.25 diameter
        T_min_cooling=285.15#12°C
    else:#No TS
        tank_sh=pc.heat_storage_tank(mass=0, surface=0.41)# For a 50 liter tank with .26 m height and .25 diameter
        T_min_cooling=0

    if (conf==1)|(conf==3)|(conf==5)|(conf==7):#DHW present
        #print('inside DHW')
        conf_aux[3]=True
        tank_dhw=pc.heat_storage_tank(mass=200, t_max=60+273.15, t_min=40+273.15,surface=1.6564) # For a 200 liter tank with 0.95 m height and .555 diameter
        if (conf==1)|(conf==5):
            tank_sh=pc.heat_storage_tank(mass=200, surface=1.6564)# For a 50 liter tank with .26 m height and .25 diameter
    else:#No DHW
        tank_dhw=pc.heat_storage_tank(mass=1, t_max=0, t_min=0,specific_heat_dhw=0,U_value_dhw=0,surface_dhw=0)#null

    ndays=days*nyears

    if combinations['HP']=='AS':
        if combinations['house_type']=='SFH15':
            Backup_heater=design_param['bu_15']
            hp=pc.HP_tech(technology='ASHP',power=design_param['hp_15'])
        elif combinations['house_type']=='SFH45':
            Backup_heater=design_param['bu_45']
            hp=pc.HP_tech(technology='ASHP',power=design_param['hp_45'])
        else:
            Backup_heater=design_param['bu_100']
            hp=pc.HP_tech(technology='ASHP',power=design_param['hp_100'])
    elif combinations['HP']=='GSHP':
        #TODO
        pass
    param={'conf':conf_aux,
    'aging':aging,'Inv_power':Inverter_power,
    'Curtailment':Curtailment,'Inverter_eff':Inverter_Efficiency,
    'Converter_Efficiency_HP':Converter_Efficiency_HP,
    'Converter_Efficiency_Batt':Converter_Efficiency_Batt,
    'delta_t':dt,'nyears':nyears,'T_min_cooling':T_min_cooling,
    'days':days,'ndays':ndays,'hp':hp,'tank_dhw':tank_dhw,'tank_sh':tank_sh,
    'Backup_heater':Backup_heater,'Capacity':combinations['Capacity'],'Tech':combinations['Tech'],
    'App_comb':App_comb,'cases':combinations['cases'],'ht':combinations['house_type'],
    'HP_type':combinations['HP'],'testing':testing, 'Cooling_ind':cooling,'name':str(id_dwell)+'_'+combinations['country']+'_PV'+str(quartile),
    'PV_nom':PV_nom,'Capacity_tariff':Capacity_tariff}
    return param,data_input

def pooling2(combinations):
    '''
    Description
    -----------
    Calls other functions, load the data and Core_LP.
    This function includes the variables for the tests (testing and data_input.index.week)
    Parameters
    ----------
    selected_dwellings : dict

    Returns
    ------
    bool
        True if successful, False otherwise.


    '''

    print('##########################################')
    print('pooling')
    print(combinations)
    print('##########################################')
    param,data_input=load_param(combinations)
    try:
        if param['nyears']>1:
            data_input=pd.DataFrame(pd.np.tile(pd.np.array(data_input).T,
                                   param['nyears']).T,columns=data_input.columns)
        print('#############pool################')
        [df_out,aux_dict]=single_opt2(param, data_input)
        print('out of optimization')
        #print(df_out.sum())
    except IOError as e:
        print ("I/O error({0}): {1}".format(e.errno, e.strerror))
        print(e)
        raise

    except ValueError:
        print ("Could not convert data to an integer.")
        raise
    except:
        print ("Unexpected error:", sys.exc_info()[0])
        print ("Unexpected error2:", sys.stderr)
        raise

    return


@fn_timer
def main():
    '''
    Main function of the main script. Allows the user to select the country
	(CH or US). For the moment is done automatically if working in windows
	the country is US. It opens a pool of 4 processes to process in parallel, if several dwellings are assessed.
    '''
    print(os.getcwd())
    print('&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&')
    print('Welcome to basopra')
    print('Here you will able to optimize the schedule of PV-coupled HP systems with electric and/or thermal storage for a given electricity demand')

    try:
        filename=Path('Output/aggregated_resultsx.csv')
        df_done=pd.read_csv(filename,sep=';|,',engine='python',index_col=False).drop_duplicates()
        #df_done.drop(df_done.tail(2).index,inplace=True)
        aux=df_done.groupby([df_done.Capacity,df_done.App_comb,df_done.Tech,df_done.PV_nom,df_done.cluster,df_done.hh,df_done.country,df_done.cases,df_done.conf,df_done.HP,df_done.house_type]).size().reset_index()
    except IOError:
        #There is not such a file, then create it
        cols=['E_PV_batt','E_PV_bu','E_PV_budhw','E_PV_curt','E_PV_grid','E_PV_hp','E_PV_hpdhw','E_PV_load','E_batt_bu','E_batt_budhw','E_batt_hp','E_batt_hpdhw','E_batt_load','E_bu','E_budhw','E_char','E_cons','E_dis','E_grid_batt','E_grid_bu','E_grid_budhw','E_grid_hp','E_grid_hpdhw','E_grid_load','E_hp','E_hpdhw','E_loss_Batt','E_loss_conv','E_loss_inv','E_loss_inv_PV','E_loss_inv_batt','E_loss_inv_grid','Q_dhwst_hd','Q_hp_sh','Q_hp_ts','Q_loss_dhwst','Q_loss_ts','Q_ts','Q_ts_delta','Q_ts_sh','T_dhwst','T_ts','E_demand','E_PV','Req_kWh','Req_kWh_DHW','Set_T','Temp','Temp_supply','Temp_supply_tank','T_aux_supply','COP_tank','COP_SH','COP_DHW','E_demand_hp_pv_dhw','E_demand_hp_pv','E_demand_pv','TSC','DSC','ISC','CU','EFC_nolifetime','BS','LS1','LS2','LS3','LS4','LS5','PS1','PS2','PS3','PS4','PS5','App_comb','conf','Capacity','Tech','PV_nom','cluster','hh','country','quartile','cases','house_type','HP','SOC_mean','P_drained_max','P_injected_max','last_cap','cap_fading','last_SOH','cycle_to_total','Bill']
        with open(filename, "w+") as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(cols)

        aux=pd.DataFrame()
    finally:
        #Define the different combinations of inputs to be run
        #dct={'Capacity':[7.],'App_comb':[3],'Tech':['NMC',],'PV_nom':[4.8],'cluster':['[11]'],'country':['CH'],'cases':[False],'conf':[5.],'house_type':['SFH15'],'HP':['AS']}
        dct={'Capacity':[7.],'App_comb':[2],'Tech':['NMC',],'PV_nom':[4.8],'country':['CH'],'cases':['mean'],'conf':[1,3,5,7],'house_type':['SFH15'],'HP':['AS'],'hh':[ 110143956137,  110699130150, 1127351129756,  110697129369,
        110699430243,  110697129372,  110145456531,  110143956140,
        110143956143, 1127349127592,  110141755842,  110697129375,
        110697929733, 1127345129700,  110696529007, 1127342129672,
        110696929206,  110697929737,  110696929258,  110696729103,
        110141755863,  110143956145,  110696629051,  110697029312,
        110697129381,  110141955877,  110696128864,  110697929745,
        110696428966,  110697129383, 1127347129714,  110143956148,
        110145256495,  110141955878, 1127341129658,  110698029749,
        110696729154,  110697229396,  110699230221,  110143956150,
       1127344129686,  110698029755,  110699430245,  110697229401,
       1127351129757,  110143956153, 1127345129701,  110141955880,
        110696529011,  110698029760,  110697229406,  110145556534,
        110144156205, 1127342129673,  110141955882,  110696929209,
       1127349129734,  110144156209,  110697229408,  110141755843,
        110145856588,  110696629055,  110144156211,  110697229411,
        110697029314,  110696929262,  110698029768,  110141955885,
        110696428969,  110144156214,  110697229419, 1127347129715,
        110698029770,  110141955887,  110696729157, 1127341129659,
        110144156217,  110141755829,  110699230224,  110698029774,
       1127345129702,  110144156221,  110697229425,  110699430246,
        110698029777, 1127351129758,  110141955890,  110696529013,
        110141955891, 1127349129735,  110698129789,  110145556537,
        110697229429,  110696629058,  110144156229,  110146056594,
        110698129793,  110696929265,  110144356264,  110696729111,
        110141955895,  110696428972,  110698129799,  110697029318,
        110697329441,  110145356503,  110144356267,  110696328876,
        110141955897,  110696829161,  110698129801, 1127347129716,
        110697329444,  110144356269, 1127341129660,  110141955898,
       1127345129703,  110698129805,  110699230227,  110697329446,
        110699130162,  110144356270, 1127344129688,  110697329450,
        110698129812,  110699430248, 1127351129760,  110144356271,
       1127349129736,  110696529016,  110697329454,  110698229816,
        110696629062,  110696929216,  110144356272,  110146056597,
        110141955902,  110141755845,  110698229819,  110696929268,
        110697329456, 1127347129717,  110698229823,  110696428975,
        110696729115,  110144356274,  110145356505,  110697329461,
        110697029321,  110698229825,  110696829164,  110141955906,
       1127341129661,  110144556313,  110141755831,  110696328879,
        110697329465,  110144556314, 1127345129704,  110699230230,
        110141955907,  110144556315,  110699130166, 1127344129689,
        110697329468,  110698229830, 1127352129767,  110144556316,
       1127349129739,  110145556543,  110697329472,  110698229835,
        110696629065,  110696929220,  110144556317,  110141755846,
        110697329474,  110698229838,  110696929272, 1127347129719,
        110141955910,  110696428978, 1127341129662,  110697329477,
        110698329851,  110145356508,  110699230232,  110141955911,
        110696729119,  110697329480,  110698329854,  110697029326,
        110144556322,  110699430252, 1127344129690,  110697329483,
        110698329858, 1127345129705,  110696328882,  110142355939,
        110144756372,  110699130169, 1127353129781,  110142355940,
        110698329861, 1127343129676,  110145556546,  110697329486,
        110144756374,  110696529022,  110142355941,  110698329867,
        110696629067,  110697329488,  110144756376,  110696128835,
        110141755847,  110142355942,  110698329871,  110696929276,
       1127347129720,  110697429491,  110144756379,  110696428981,
        110699330235,  110142355943,  110145356511, 1127341129663,
        110142355944,  110144756381,  110696829176, 1127344129691,
        110697429498,  110698329880,  110141755833,  110142355945,
        110699430254,  110696729124, 1127346127589,  110696328884,
        110142355946, 1127354129797,  110697429509,  110698429896,
       1127343129677,  110145556549,  110142355947,  110144756389,
       1127350127593,  110696529024,  110697429513,  110698429899,
        110696629071,  110696929228,  110142556012,  110144856395,
        110696929280,  110141755848,  110697429516,  110698429902,
        110696128837, 1127348127591,  110142556013,  110144856397,
        110696428984,  110699330237,  110697529529,  110144856399,
        110145356514, 1127341129664,  110142556015,  110698429906,
        110696829179, 1127344129692,  110697529533,  110144856401,
       1127354129799,  110142556016,  110698429909, 1127346129706,
        110697129333,  110142556017,  110144856404,  110699430256,
        110696729126,  110697529546,  110698429912,  110699130179,
        110696328886,  110142556018,  110144856407, 1127343129678,
        110696529027,  110697529550,  110698429916, 1127350129746,
        110141755849,  110142756041,  110144856411,  110696929283,
        110696929232,  110697529557,  110698529920,  110696629073,
       1127348129725,  110142756042,  110145056430,  110696128842,
        110699330238,  110142756043,  110698529926,  110696428987,
       1127342129667,  110697529561,  110145056432,  110145356516,
       1127344129693,  110142756044,  110698529930,  110696829183,
        110697129336,  110697529565,  110145056435,  110141755835,
        110696729128,  110698529934, 1127346129707,  110697529569,
        110145056438,  110699430258,  110141755850,  110142756046,
        110698529936,  110699130183,  110145556555,  110697529571,
       1127343129679,  110696529030,  110142756047,  110698529939,
       1127350129747,  110696929236,  110697529574,  110145056447,
        110696128845, 1127348129726,  110142956052,  110698529942,
        110696929286,  110699330239,  110142956053,  110145056453,
        110696528990, 1127342129668,  110697629584,  110698529945,
        110145456520, 1127345127588,  110142956055,  110145156456,
        110696829190, 1127355129783,  110697629587,  110698529950,
        110141755836,  110697129340,  110142956056,  110145156459,
       1127346129708,  110696729133,  110697629595,  110698529953,
        110699430260,  110696328892,  110142956057,  110145156462,
        110699130188,  110698629959, 1127343129680,  110696529033,
        110142956058,  110145156465,  110696929241,  110145156468,
        110696629081, 1127348129729,  110142956059,  110698629962,
        110696128849,  110699330240,  110697629607,  110696929290,
       1127342129669,  110698629965,  110696528993, 1127345129695,
        110142956061,  110145256477,  110145456522, 1127355129784,
        110697629613,  110145256480,  110696829194,  110697129344,
        110142956062,  110698629973, 1127346129709,  110696729137,
        110697729616,  110145256483,  110699430262,  110141755852,
        110142956063,  110698629977,  110699130193,  110145656567,
        110142956064,  110698629981, 1127343129681, 1127348129730,
        110697729619,  110145256489,  110696629086,  110696529037,
        110142956065,  110698629985,  110697029296,  110696929245,
        110142956066,  110145256492,  110696128853,  110699330241,
        110697729630,  110698629989,  110141755838, 1127342129670,
        110143156073,  110698629992,  110696528996, 1127345129697,
        110697729634,  110698730003,  110145456524, 1127355129786,
        110143156074,  110698730006,  110696829197,  110697129348,
        110697729637,  110698730009, 1127346129710,  110143156075,
        110143156076,  110698730016,  110699130197,  110141755853,
        110697729644, 1127343129682,  110143156077,  110698730039,
       1127351129752,  110697729648,  110698730043,  110696729091,
        110696529040,  110698830051,  110143156078,  110697029301,
        110699430242,  110698830053,  110143356092,  110696128856,
       1127342129671,  110698830056,  110697729654, 1127345129698,
        110698830059,  110696529000,  110145456526,  110697129350,
        110698830063,  110143556102, 1127346129712,  110696428960,
        110698830065,  110143556103, 1127341129655,  110696729145,
        110698830067,  110696829200,  110141755854,  110698830069,
        110143556104,  110699230205,  110145656576,  110698830071,
        110697829674, 1127343129683,  110696529044,  110698830073,
        110143556105, 1127351129753,  110697129353,  110698830079,
        110697829679,  110696729096,  110696428963,  110698930092,
        110697029304,  110696729150,  110698930096,  110143556107,
        110696128859,  110141755855,  110698930100,  110697829690,
        110141755840,  110145656579,  110143556108, 1127341129656,
        110696529047,  110698930108,  110143756116,  110696529004,
        110696929256,  110698930113,  110145456529,  110697829698,
        110697129356,  110698930117, 1127344127587,  110143756118,
        110141755856,  110699030125, 1127351129754,  110143756120,
        110699030128,  110697129359,  110696929203,  110697929712,
        110699030131,  110141755857,  110696729099,  110143756122,
        110699030135,  110697029308,  110697929717,  110699030138,
        110697129362,  110696128862,  110699030142,  110141755841,
        110697929723,  110699030146,  110697129366, 1127341129657,
        110143756126,  110141755860,  110699230217,  110697929727,
       1127344129685]}
        Total_combs=expand_grid(dct)
        print(Total_combs.dtypes)
        print(aux)
        if aux.empty:
            Combs_todo=Total_combs.copy()
        else:

            Combs_todo=aux.merge(Total_combs,how='outer',indicator=True)#Warning

            Combs_todo=Combs_todo[Combs_todo['_merge']=='right_only']
            Combs_todo=Combs_todo.loc[:,Combs_todo.columns[:-1]]

        print(Combs_todo.head())
        Combs_todo=[dict(Combs_todo.loc[i,:]) for i in Combs_todo.index]
        print(len(Combs_todo))
        mp.freeze_support()
        print('&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&')
        pool=mp.Pool(processes=1, maxtasksperchild=1000)
        #selected_dwellings=select_data(Combs_todo)
        #print(selected_dwellings)
        #print(Combs_todo)
        pool.map(pooling2,Combs_todo)
        pool.close()
        pool.join()
        print('&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&')


if __name__ == '__main__':
    if sys.platform!='win32':
        memory_limit() # Limitates maximun memory usage to half
        try:
            main()
        except MemoryError:
            sys.stderr.write('MAXIMUM MEMORY EXCEEDED')
            sys.exit(-1)
    else:
        main()
