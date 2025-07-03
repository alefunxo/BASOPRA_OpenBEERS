# -*- coding: utf-8 -*-## @namespace main_beers
# Author
# Alejandro Pena-Bello
# alejandro.penabello@hevs.ch; marten.vanderkam@unibas.ch
# Modification of main script used for the papers Optimized PV-coupled battery systems for combining applications: Impact of battery technology and geography (Pena-Bello et al 2019) and Decarbonizing heat with PV-coupled heat pumps supported by electricity and heat storage: Impacts and trade-offs for prosumers and the grid (Pena-Bello et al 2021)
# This enhancement includes the use electric vehicles together with the previously assessed PV, battery system and HP and thermal storage. We study the different applications which residential batteries can perform from a consumer perspective. Applications such as avoidance of PV curtailment, demand load-shifting and demand peak shaving are considered along  with the base application, PV self-consumption. It can be used with six different battery technologies currently available in the market are considered as well as three sizes (3 kWh, 7 kWh and 14 kWh). We analyze the impact of the type of demand profile and type of tariff structure by comparing results across dwellings in Switzerland. The electric vehicles chargers that can be chosen are 3.6, 7, or 11 kW.
# The HP, battery and TS schedule is optimized for every day (i.e. 24 h optimization framework), we assume perfect day-ahead forecast of the electric vehicle use, the electricity and heat demand load and solar PV generation in order to determine the maximum economic potential regardless of the forecast strategy used. Battery aging was treated as an exogenous parameter, calculated on daily basis and was not subject of optimization. Data with 15-minute temporal resolution were used for simulations. The model objective function have two components, the energy-based and the power-based component, as the tariff structure depends on the applications considered, a boolean parameter activate the power-based factor of the bill when is necessary.

# The script works on Linux and Windows
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
import os
from typing import Any, Dict
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from box import Box
import re
import pandas as pd
import argparse
import numpy as np
import itertools

from dateutil import parser
import glob
import multiprocessing as mp
import time
import paper_classes as pc
from functools import wraps
from pathlib import Path
import traceback
import pickle
import csv
import post_proc as pp
import logging


from config.loader import config
from Core.Core import single_opt2
from utils.multiprocessing_utils import run_parallel

core_config = config['Core']
#INPUT_PATH = "../Input/"
#OUTPUT_PATH = "../Output/"
INPUT_PATH = config['input_dir']
OUTPUT_PATH = config['output_dir']


# Configure logger
logging.basicConfig(filename='main.log', 
                    level=logging.DEBUG,
                    filemode='w',
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.info("Test message")

def expand_grid(dct): #MAIN PARAMETERS MULTIPLICATION TO CONSTRUCT SCENARIOS
    rows = itertools.product(*dct.values())
    return pd.DataFrame.from_records(rows, columns=dct.keys())

def fn_timer(function):
    @wraps(function)
    def function_timer(*args, **kwargs):
        t0 = time.time()
        result = function(*args, **kwargs)
        t1 = time.time()
        
        return result
    return function_timer

def str2bool(v):
    return v.lower() in ("yes", "true", "t", "1")

def load_obj(name ):
    with open(name + '.pkl', 'rb') as f:
        return pickle.load(f)

def celsius_to_kelvin(celsius):
    return celsius + 273.15

def create_app_combinations(index):
    # Generate combinations of three booleans and insert True as the second element in each list
    combinations = [list((a, True, b, c)) for a, b, c in itertools.product([False, True], repeat=3)]
    df = pd.DataFrame({'App_comb': combinations})
    return df.loc[index,'App_comb']

def create_app_configurations(index):
    # Generate combinations of three booleans and insert True as the second element in each list
    configurations = [list((a, b, c, d)) for a, b, c,d in itertools.product([False, True], repeat=4)]
    df = pd.DataFrame({'conf': configurations})
    return df.loc[index,'conf']

def load_prices():
    filename_prices=Path(f'{INPUT_PATH}Prices_2017.csv')
    
    fields_prices=['index', 'Price_flat', 'Price_DT', 'Export_price', 'Price_flat_mod',
   'Price_DT_mod']
    df_prices=pd.read_csv(filename_prices,engine='python',sep=',|;',index_col=[0],
                        parse_dates=[0],usecols=fields_prices)

    if np.issubdtype(df_prices.index.dtype, np.datetime64):
        df_prices.index=df_prices.index.tz_localize('UTC').tz_convert('Europe/Brussels')
    else:
        df_prices.index=pd.to_datetime(df_prices.index,utc=True)
        df_prices.index=df_prices.index.tz_convert('Europe/Brussels')
    return df_prices
        



def load_heat_demand(combinations):
    filename_heat=Path(f'{INPUT_PATH}preprocessed_heat_demand_2_new_Oct.csv')
    
    if (combinations['house_type']=='SFH15')| (combinations['house_type']=='SFH45'):
        aux_name1='SFH15_45'
        aux_name2=combinations['house_type']
    else:
        aux_name1='SFH100'
        aux_name2='SFH100'

    fields_heat=['index','Set_T','Temp', aux_name2+'_kWh','DHW_kWh', 'Temp_supply_'+aux_name1,'Temp_supply_'+aux_name1+'_tank',
                'COP_'+aux_name2,'hp_'+aux_name2+'_el_cons','COP_'+aux_name2+'_DHW',
                 'hp_'+aux_name2+'_el_cons_DHW','COP_'+aux_name2+'_tank',
                 'hp_'+aux_name2+'_tank_el_cons']
    new_cols=['Set_T','Temp', 'Req_kWh','Req_kWh_DHW','Temp_supply','Temp_supply_tank','COP_SH','COP_tank','COP_DHW',
              'hp_sh_cons','hp_tank_cons','hp_dhw_cons']
    df_heat=pd.read_csv(filename_heat,engine='python',sep=';',index_col=[0],
                        parse_dates=[0], usecols=fields_heat)
    df_heat.columns=new_cols


    if np.issubdtype(df_heat.index.dtype, np.datetime64):
        df_heat.index=df_heat.index.tz_localize('UTC').tz_convert('Europe/Brussels')
    else:
        df_heat.index=pd.to_datetime(df_heat.index,utc=True)
        df_heat.index=df_heat.index.tz_convert('Europe/Brussels')
    return df_heat

def load_electricity_demand(id_dwell):
    filename_el=Path(f'{INPUT_PATH}Electricity_demand_supply_2017.csv')
    fields_el=['index',str(id_dwell.values[0]),'E_PV']
    new_cols=['E_demand', 'E_PV']

    df_el = pd.read_csv(filename_el,engine='python',sep=',|;',index_col=0,
                        parse_dates=[0], usecols=fields_el)
    
    if np.issubdtype(df_el.index.dtype, np.datetime64):
        df_el.index=df_el.index.tz_localize('UTC').tz_convert('Europe/Brussels')
    else:
        df_el.index=pd.to_datetime(df_el.index,utc=True)
        df_el.index=df_el.index.tz_convert('Europe/Brussels')

    df_el.columns=new_cols
    return df_el

def load_EV_data(combinations, single_param):
    
    ########## LOAD EV DATA
    Batt_EV = pc.Battery_tech(Capacity=combinations['EV_batt_cap'], Technology='NMC')
    logger.info("Extract the id numbers")
    if combinations['EV_use'] == 'Low':
            EV_IDs = pd.read_csv(f'{INPUT_PATH}hhnrEVLow.csv')
            filename_EV2 = Path(f'{INPUT_PATH}dfEVLow.csv')
    
    if combinations['EV_use'] == 'Medium':
            EV_IDs = pd.read_csv(f'{INPUT_PATH}hhnrEVMedium.csv')
            filename_EV2 = Path(f'{INPUT_PATH}dfEVMedium.csv')

    
    if combinations['EV_use'] == 'High':
            EV_IDs = pd.read_csv(f'{INPUT_PATH}hhnrEVHigh.csv')
            filename_EV2 = Path(f'{INPUT_PATH}dfEVHigh.csv')            
    if combinations['EV_use'] == 'None': #It will select a number for the model to work, but it is not used later
            EV_IDs = pd.read_csv(f'{INPUT_PATH}hhnrEVHigh.csv')
            filename_EV2 = Path(f'{INPUT_PATH}dfEVNone.csv')    
    EV_ID = EV_IDs.iloc[combinations['profile_row_number']]['HHNR_WEEKDAY_WEEKENDAY']
    
    logger.info("EV_ID: s"  + str(EV_ID))
    
    #if ( combinations['EV_P_max_home'] != '3_6' and combinations['EV_P_max_home'] != '7' and combinations['EV_P_max_home'] != '11' ): 
        #print('Invalid charging power, choose 3_6, 7, or 11')
    
    filename_EV = Path(f'{INPUT_PATH}dfEVBasopra.csv')
    fields_EV=['index','energyRequired'+combinations['EV_P_max_home']+'kW'+ combinations['EV_use'],'maxPower'+ combinations['EV_use'],'energyTrip'+ combinations['EV_use']]
    
   
    df_EV = pd.read_csv(filename_EV,engine='python',sep=',|;',index_col=0,
                         parse_dates=[0],usecols=fields_EV)

    
    df_EV.columns=['E_EV_req','EV_home','E_EV_trip']
    
    if combinations['EV_use'] == 'None':
        aux_nameEV='1'
    else:
        aux_nameEV=str(combinations['profile_row_number']+1)

    fields_EV2=['energyRequired'+combinations['EV_P_max_home']+'kW_'+ aux_nameEV,'energyTrip_'+ aux_nameEV,'maxPower_'+ aux_nameEV]
    df_EV2 = pd.read_csv(filename_EV2, usecols=lambda x: x.strip().strip('"') in fields_EV2)
    df_EV2.columns=['E_EV_req','E_EV_trip','EV_home']
    
    df_EV['E_EV_req'] = df_EV2['E_EV_req'].values
    df_EV['EV_home']=df_EV2['EV_home'].values
    df_EV['E_EV_trip']=df_EV2['E_EV_trip'].values

    if np.issubdtype(df_EV.index.dtype, np.datetime64):
        df_EV.index=df_EV.index.tz_localize('UTC').tz_convert('Europe/Brussels')
    else:
        df_EV.index=pd.to_datetime(df_EV.index,utc=True)
        df_EV.index=df_EV.index.tz_convert('Europe/Brussels')
            
    ####### EV variables
    single_param['EV_batt_cap'] = combinations['EV_batt_cap']
    if combinations['EV_P_max_home'] == '3_6':
        single_param['EV_P_max_home'] = 3.6
    elif combinations['EV_P_max_home'] == '7':
        single_param['EV_P_max_home'] = 7
    elif combinations['EV_P_max_home'] == '11':
        single_param['EV_P_max_home'] = 11
    single_param['EV_P_max_away'] = 22
    single_param['EV_use'] = combinations['EV_use']
    Batt_EV.SOC_max =  1.0*Batt_EV.Capacity
    Batt_EV.SOC_min =  0.2*Batt_EV.Capacity
    single_param['Batt_EV']=Batt_EV
    single_param['E_EV_start']=Batt_EV.SOC_max
    df_EV['EV_away']=abs(df_EV.EV_home-1)
    single_param['public_charging_price']=0.48
    return single_param, df_EV

def load_multi_EV_data(ev_profiles,param):
    """
    ev_profiles: dict mapping ev_name -> combinations dict (exactly as you pass into load_EV_data)
    Returns:
      param: dict ready for LP.Data (with EV_list, Batt_EV, E_EV_start, EV_home, EV_away, E_EV_trip, …)
      dfs:    dict of pandas.DataFrame for each EV (if you still need per‐EV dfs)
    """
    # containers for the LP Data
    EV_list        = list(ev_profiles.keys())
    Batt_EV        = {}
    E_EV_start     = {}
    EV_P_max_home  = {}
    EV_P_max_away  = {}
    EV_V2G         = {}
    EV_home        = {}
    EV_away        = {}
    E_EV_trip      = {}
    dfs            = {}

    # call your original loader once per EV
    for ev in EV_list:
        combos = ev_profiles[ev]
        # this is your existing function, unchanged:
        single_param, df_ev = load_EV_data(combos, {})  

        # stash the class instance and scalars
        Batt_EV[ev]       = single_param['Batt_EV']
        E_EV_start[ev]    = single_param['E_EV_start']
        EV_P_max_home[ev] = single_param['EV_P_max_home']
        EV_P_max_away[ev] = single_param['EV_P_max_away']
        EV_V2G[ev]        = single_param.get('EV_V2G', 1)

        # pull the time‐series out of the df
        EV_home[ev]       = df_ev['EV_home'].to_dict()
        EV_away[ev]       = df_ev['EV_away'].to_dict()
        E_EV_trip[ev]     = df_ev['E_EV_trip'].to_dict()

        dfs[ev] = df_ev

    # now assemble the final param dict for the LP
    param.update({
        'EV_list':             EV_list,
        'Batt_EV':             Batt_EV,
        'E_EV_start':          E_EV_start,
        'EV_P_max_home':       EV_P_max_home,
        'EV_P_max_away':       EV_P_max_away,
        'EV_V2G':              EV_V2G,
        'EV_home':             EV_home,
        'EV_away':             EV_away,
        'E_EV_trip':           E_EV_trip,
        'public_charging_price': single_param['public_charging_price'],
    })

    return param, dfs


def configure_system_parameters(combinations, heat_pump, param):
    """
    Configure system parameters based on the input 'combinations' dictionary.
    
    Parameters:
        combinations (dict): Contains configuration flags (e.g. 'conf' and 'house_type').
        param (dict): Dictionary to store various system parameters.
        
        
    Returns:
        tuple: Updated 'param' dictionary and a configuration auxiliary list (conf_aux).
    """
    #print('##############')
    #print('load parameters')
    conf = combinations['conf']
    #print('conf')
    #print(conf)

    # configuration = [Batt, HP, TS, DHW]
    # if all false, only PV is used
    conf_aux = [False, True, False, False]  # [Batt, HP, TS, DHW]
    dhw_tank = combinations['hh']['dhw_tank']
    heat_tank = combinations['hh']['heat_tank']
    # For some settings the heat pump is removed
    if combinations['house_type'] == 'NoHeatPump':
        conf_aux[1] = False

    if conf < 4:  # No battery
        logger.debug('No battery')
        param['Batt'] = pc.Battery_tech(Capacity=0, Technology=combinations['Tech'])

    else:
        logger.debug('Battery present')
        conf_aux[0] = True
        # The Batt will come defined by the citysim preprocessing
        # I added it here for completeness in the meanwhile
        param['Batt'] = pc.Battery_tech(Capacity=param['Capacity'], Technology=combinations['Tech'])

        

    if (conf != 0) & (conf != 1) & (conf != 4) & (conf != 5) & (conf != 8) & (conf != 9):  # TS present
        logger.debug('TS present')
        conf_aux[2] = True
        if (combinations['house_type'] == 'SFH15') | (combinations['house_type'] == 'SFH45'):
            logger.debug('SHF 15 or 45')
            param['tank_sh'] = pc.heat_storage_tank(volume=20*heat_pump.attributes['hp'])
        else:
            logger.debug('SHF 100')
            param['tank_sh'] = pc.heat_storage_tank(volume=20*heat_pump.attributes['hp'])
    else:  # No TS
        logger.debug('SHF 100')
        param['tank_sh'] = pc.heat_storage_tank(volume=20*heat_pump.attributes['hp'])

    if (conf == 1) | (conf == 3) | (conf == 5) | (conf == 7):  # DHW present
        logger.debug('DHW present')
        conf_aux[3] = True
        dhw_tank.volume=dhw_tank.volume*1000
        param['tank_dhw'] = dhw_tank
    else:  # No DHW
        logger.debug('No DHW')
        param['tank_dhw'] = pc.heat_storage_tank(volume=0,  specific_heat_dhw=0, U_value_dhw=0, surface_dhw=0)
    '''
    design_param = load_obj(f'{INPUT_PATH}dict_design_oct')
    if combinations['house_type'] == 'SFH15':
        param['Backup_heater'] = 10000000 # Big number to run all design_param['bu_15']
        param['hp'] = pc.HP_tech(technology='ASHP', power=design_param['hp_15'])
    elif combinations['house_type'] == 'SFH45':
        param['Backup_heater'] = 10000000 #design_param['bu_45']
        param['hp'] = pc.HP_tech(technology='ASHP', power=design_param['hp_45'])
    else:
        param['Backup_heater'] = 10000000 #design_param['bu_100']
        param['hp'] = pc.HP_tech(technology='ASHP', power=design_param['hp_100'])
    '''
    param['Backup_heater'] = 10000000 #design_param['bu_100']
    return param, conf_aux

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
    '''
    logger.info('Loading data for Basopra Optimization')

    series = combinations['hh']['series']
    attributes = combinations['hh']['attributes']
    heat_pump = combinations['hh']['heat_pump']
    df_el = series[['ElectricConsumption', 'SolarPVProduction','dhw']]
    pv_roof_capacity = attributes['roof_pv_capacity']
    pv_wall_capacity = attributes['wall_pv_capacity']
    pv_capacity = pv_roof_capacity + pv_wall_capacity
    elec_price = attributes['elec_price']/100
    ev_profiles = combinations['hh']['ev_profiles']
    
    Export_price = 0.06
    
    logger.info("Choose the corresponding profile for electricity")

    if combinations['electricity_profile'] == 'Low':
            logger.info("Electricity profile Low")
            electricity_profiles = pd.read_csv(f'{INPUT_PATH}HHLow.csv')
    elif combinations['electricity_profile'] == 'Medium':
            logger.info("Electricity profile Medium")
            electricity_profiles = pd.read_csv(f'{INPUT_PATH}HHMedium.csv')
    else :
            logger.info("Electricity profile High")
            electricity_profiles = pd.read_csv(f'{INPUT_PATH}HHHigh.csv')
    
    combinations['electricity_profiles'] = electricity_profiles.iloc[combinations['profile_row_number']]
    param = core_config['param_load_fixed_parameters']
    # param=dict()
    param['name']=combinations['name']

    
    param['App_comb']=combinations['App_comb']
    param['id_dwell']=electricity_profiles.iloc[combinations['profile_row_number']]#combinations['building_name'] # To be added for citysim

    week = 1


    df_el.columns=['E_demand','E_PV','dhw']
    
    # PV_nom = df_el.E_PV.sum()/1000 # Estimated kW
    PV_nom = np.round(pv_capacity,1)
    logger.info('PV_nom : {PV_nom}')
    # Let-s try with the demand instead of the PV due to the high PV nom in the facade
    param["Capacity"] = np.round(df_el.E_demand.sum()/1000,0) # pv_capacity['Roof'] + pv_capacity['Wall']# Capacity is for the battery, PV_nom is for PV
    logger.info('Battery Capacity : {Capacity}')
    param['Inverter_power'] = round(pv_capacity/ 1.2, 1)


    df_heat_new = heat_pump.series[[
        'Set_T', 
        'Temp', 
        'Req_kWh', 
        'Temp_supply', 
        'Temp_supply_tank',
        'COP_SH',
        'COP_tank',
        'COP_DHW',
        'hp_sh_cons',
        'hp_tank_cons',
        'hp_dhw_cons',
    ]]
    #df_heat_new = df_heat_new.reset_index(drop=True)         # Remove the datetime index

    
    ev_param, df_EVs = load_multi_EV_data(ev_profiles,param)

    #[param, df_EV, EV_ID] = load_EV_data(combinations,param)
    

    for ev, df in df_EVs.items():
        df_hourly = df.resample('1h').agg({
            'E_EV_req':  'sum',
            'E_EV_trip': 'sum',
            'EV_home':   'max',
        })
        # recompute EV_away
        df_hourly['EV_away'] = 1 - df_hourly['EV_home']

        # store it back
        df_EVs[ev] = df_hourly
        '''
        param['EV_home'][ev]   = df_hourly['EV_home'].reset_index(drop=True).to_dict()
        param['EV_away'][ev]   = df_hourly['EV_away'].reset_index(drop=True).to_dict()
        param['E_EV_trip'][ev] = df_hourly['E_EV_trip'].reset_index(drop=True).to_dict()
        '''
    df_el.index=df_heat_new.index
    df_el['Price_flat']=elec_price
    df_el['Export_price']=Export_price
    df_el.rename(columns={'dhw': 'Req_kWh_DHW'}, inplace=True)
    df_el['Req_kWh_DHW']/=10
    df_el['Req_kWh_DHW']=5
    ############ data profiles through time
    # 1) Concatenate all EV frames into one, with top‐level EV names
    df_EVs = pd.concat(df_EVs, axis=1)
    # This yields a MultiIndex for columns: ('EV1','EV_home'), ('EV1','E_EV_trip'), ('EV2','EV_home'), …

    # 2) Flatten the MultiIndex into single strings, e.g. "EV1_E_EV_trip"
    df_EVs.columns = [
        f"{ev}_{col}"
        for ev, col in df_EVs.columns
    ]
    df_EVs.index=df_heat_new.index
    data_input=pd.concat([df_el,df_heat_new,df_EVs],axis=1,copy=True,sort=False)

    #skip the first DHW data since cannot be produced simultaneously with SH    data_input.loc[(data_input.index.hour<2),'Req_kWh_DHW']=0
    #data_input.loc[:,'E_PV']=data_input.loc[:,'E_PV']*PV_nom

    data_input['Temp']=data_input['Temp'].apply(celsius_to_kelvin)
    data_input['Set_T']=data_input['Set_T'].apply(celsius_to_kelvin)
    data_input['Temp_supply']=data_input['Temp_supply'].apply(celsius_to_kelvin)
    data_input['Temp_supply_tank']=data_input['Temp_supply_tank'].apply(celsius_to_kelvin)
    
    if param['testing']:
        data_input=data_input[data_input.index.isocalendar().week==week]
        nyears=1
        days=7
        ndays=7
    else:
        nyears=1
        days=365
        ndays=365
    param['ndays']=days*nyears
    param, conf_aux=configure_system_parameters(combinations, heat_pump, param)
    
    param.update({
        'Tech': combinations['Tech'],
        'conf': conf_aux,
        'ht': combinations['house_type'],
        'electricity_profile': combinations['electricity_profile'],
        'EV_V2G': combinations['EV_V2G'],
        'PV_nom': PV_nom,
        'App_comb': create_app_combinations(combinations['App_comb']),
    })

    return param, data_input


def pooling2(combinations):
    try:
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

        ##print('##########################################')
        ##print('pooling')
        ##print(combinations)
        ##print('##########################################')
        param, data_input=load_param(combinations)
        try:
            if param['nyears']>1:
                data_input=pd.DataFrame(pd.np.tile(pd.np.array(data_input).T,
                                       param['nyears']).T,columns=data_input.columns)
            ##print('#############pool################')


            [df,aux_dict]=single_opt2(param, data_input)
        except OSError as e:
            ##print(f"OSError: {e}")
            raise
        except Exception as e:
            ##print(f"Unexpected error: {e}")
            raise
        return df, aux_dict
    except Exception:
         traceback.print_exc()
         raise

def get_conf_for_building(b_data: Dict[str, Any]) -> int:
    has_heat_pump = True if b_data.get('heat_pump') is not None else False
    has_DHW = True if b_data['series'].get('dhw') is not None else False

    return 0
    


@fn_timer
def run_basopra_simulation(big_data_object):
    # #print('Loading things the old fashioned way')
    # files_directory = INPUT_PATH
    # buildings_file = "test"
    # buildings_path = f"{files_directory}{buildings_file}"
    # buildings=load_obj(buildings_path)
    # keys = list(buildings.keys())
    # #print(keys)
    # Define the different combinations of inputs to be run
    dct = core_config['basopra_run_combinations']
    # b_items = buildings.items()
    # b_items_list = list(b_items)
    # b_items_list_cut = list(b_items)[2:]
    # dct['hh'] = b_items_list_cut
    #print('Loading things the cool new way')
    #print(big_data_object.keys())

    # TODO move the file finding logic from here to the run.py logic
    output_folder = OUTPUT_PATH
    logger.info(f"Searching for all done basopra simulations in {output_folder}")
    pattern = os.path.join(output_folder, 'df_*(Building-*)_NMC_0100_*_*_SFH100.csv')
    existing_files = glob.glob(pattern)

    logger.info("Determining remaining simulations to run")
    existing_simulations = set()
    for file in existing_files:
        filename = os.path.basename(file)
        match = re.search(r'df_((?:\d+\(Building-[\d\-]+-[\dA-Z]+\)))_NMC_0100_([0-9]+)_([0-9]+)_SFH100', filename)
        try:
            if match:
                building_id = match.group(1)
                configuration = match.group(3)
                existing_simulations.add((building_id, configuration))
        except (IndexError, ValueError):
            raise
            #print(f"Skipping file with unexpected format: {file}")

    # if core_config['oldschool']:
    #     buildings_data = buildings
    #     for building in buildings_data:
    #         match = re.search(r'\d+\(Building-([\d\-]+)-[\dA-Z]+\)', building)
    #         egid = match.group(1)
    #         for build in big_data_object:
    #             if egid == big_data_object[build]['attributes']['egid'].iloc[0]:
    #                 buildings_data[building]['heat_pump'] = big_data_object[build]['heat_pump']
    # else:
    buildings_data = big_data_object
    for bld_id, bld_data in buildings_data.items():
        bld_data['ev_profiles'] = dct['ev_profiles']
    
    mapping = core_config['mapping']
    mapping_str_to_num = core_config['reverse_mapping']
    expected_combinations = {(building_id, mapping[configuration]) for building_id in buildings_data.keys() for configuration in dct['conf']}
                  
    missing_simulations = expected_combinations - existing_simulations
    logger.info(f"Following simulations to be run: {missing_simulations}")
    Combs_todo_list = []
    for bld_id, config in missing_simulations:
        building_data = buildings_data.get(bld_id, None)
        Combs_todo_list.append({'hh': building_data, 'name': bld_id, 'conf': mapping_str_to_num[config]})
    Combs_todo = pd.DataFrame(Combs_todo_list)
    logger.info(f'{len(Combs_todo)} simulations to be run')

    static_cfg = core_config['basopra_fixed_parameters']
    Combs_todo_dicts = [
        {'combinations':{**row, **static_cfg}}
        for row in Combs_todo.to_dict(orient='records')
    ]

    results = run_parallel(
        pooling2,
        Combs_todo_dicts,
        core_config.multiprocessing,
        processes=core_config.basopra_processes,
        mode='kwargs',
    )
    results = [
        res[0].loc[:, ~res[0].columns.str.startswith("Bool_")] 
        if res[0] is not None else None
        for res in results
    ]
    basopra_results = {}
    for i in range(len(results)):
        building_id = Combs_todo_dicts[i]['combinations']['name']
        conf_id = Combs_todo_dicts[i]['combinations']['conf']
        basopra_results[(building_id, conf_id)] = {
            'simulation_inputs': Combs_todo_dicts[i]['combinations'],
            'simulation_outputs': results[i],
        }

    return basopra_results
    

# @fn_timer
# def main():
#     '''
#     Main function of the main script. Allows the user to select the country
# 	(CH or US). For the moment is done automatically if working in windows
# 	the country is US. It opens a pool of 4 processes to process in parallel, if several dwellings are assessed.
#     '''
#     #print(os.getcwd())
#     #print('&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&')
#     #print('Welcome to basopra')
#     #print('Here you will able to optimize the schedule of PV-coupled HP systems and an electric vehicle with electric and/or thermal storage for a given electricity demand')
# 
#     files_directory = INPUT_PATH
#     buildings_file = "test"
#     buildings_path = f"{files_directory}{buildings_file}"
#     buildings=load_obj('Input/test')
#     keys = list(buildings.keys())
#     #Define the different combinations of inputs to be run
#     dct = core_config['basopra_run_combinations']
#     for bld_id, bld_data in buildings.items(): # to be changed to appropriately include the EVs
#         bld_data['ev_profiles'] = dct['ev_profiles']
#     dct['hh'] = list(buildings.items())[2:] # why is there a [2:] here?
# 
# 
# 
#     # Define the folder containing the files
#     output_folder = Path(OUTPUT_PATH)
#     pattern = os.path.join(output_folder, 'df_*(Building-*)_NMC_0100_*_*_SFH100.csv')
# 
#     # List of matched files
#     existing_files = glob.glob(pattern)
# 
#     # Extract Respondent_id and EV_V2G_buffer from filenames
#     existing_simulations = set()
#     for file in existing_files:
#         filename = os.path.basename(file)
#         match = re.search(r'df_((?:\d+\(Building-[\d\-]+-[\dA-Z]+\)))_NMC_0100_([0-9]+)_([0-9]+)_SFH100', filename)
#         try:
#             if match:
#                 building_id = match.group(1)
#                 configuration = match.group(3)
#                 existing_simulations.add((building_id, configuration))    
#         except (IndexError, ValueError):
#             #print(f"Skipping file with unexpected format: {file}")
# 
#     mapping = core_config['mapping']
#     mapping_str_to_num = core_config['reverse_mapping']
# 
#     expected_combinations = {(building_id, mapping[configuration]) for building_id in keys for configuration in dct['conf']}
#     missing_simulations = expected_combinations - existing_simulations
#     Combs_todo_list = []
#     for bld_id, config in missing_simulations:
#         # Retrieve the full building information using the building id as key
#         building_info = buildings.get(bld_id, None)
#         Combs_todo_list.append({'hh': building_info,'name': bld_id, 'conf': mapping_str_to_num[config]})
# 
#     Combs_todo = pd.DataFrame(Combs_todo_list)
#     #print(len(Combs_todo))
#     static_cfg = core_config['basopra_fixed_parameters']
#     Combs_todo_dicts = [
#         {**row, **static_cfg}
#         for row in Combs_todo.to_dict(orient='records')
#     ]
# 
#     mp.freeze_support()
#     #print('&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&')
#     mp.set_start_method("spawn")
#     pool=mp.Pool(processes=1)
#     #selected_dwellings=select_data(Combs_todo)
#     ##print(selected_dwellings)
#     ##print(Combs_todo)
#     pool.map(pooling2,Combs_todo_dicts)
#     pool.close()
#     pool.join()
#     #print('&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&')
# 
# if __name__ == '__main__':
#     main()