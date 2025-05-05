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
    
import re
import os
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
from Core import single_opt2
import post_proc as pp
import logging

INPUT_PATH = "../Input/"
OUTPUT_PATH = "../Output/"


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
        print ("Total time running %s: %s seconds" %
               (function.__name__, str(t1-t0))
               )
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

def load_EV_data(combinations, param):
    
    ########## LOAD EV DATA
    Batt_EV = pc.Battery_tech(Capacity=combinations['EV_batt_cap'], Technology='NMC')
    logger.info("Extract the id numbers")
    if combinations['EV_use'] == 'Low':
            EV_IDs = pd.read_csv(f'{INPUT_PATH}hhnrEVLow.csv')
    
    if combinations['EV_use'] == 'Medium':
            EV_IDs = pd.read_csv(f'{INPUT_PATH}hhnrEVMedium.csv')
    
    if combinations['EV_use'] == 'High':
            EV_IDs = pd.read_csv(f'{INPUT_PATH}hhnrEVHigh.csv')
            
    if combinations['EV_use'] == 'None': #It will select a number for the model to work, but it is not used later
            EV_IDs = pd.read_csv(f'{INPUT_PATH}hhnrEVHigh.csv')
    
    EV_ID = EV_IDs.iloc[combinations['profile_row_number']]['HHNR_WEEKDAY_WEEKENDAY']
    
    logger.info("EV_ID: s"  + str(EV_ID))
    
    if ( combinations['EV_P_max_home'] != '3_6' and combinations['EV_P_max_home'] != '7' and combinations['EV_P_max_home'] != '11' ): 
        print('Invalid charging power, choose 3_6, 7, or 11')
    
    filename_EV = Path(f'{INPUT_PATH}dfEVBasopra.csv')
    fields_EV=['index','energyRequired'+combinations['EV_P_max_home']+'kW'+ combinations['EV_use'],'maxPower'+ combinations['EV_use'],'energyTrip'+ combinations['EV_use']]
    
   
    df_EV = pd.read_csv(filename_EV,engine='python',sep=',|;',index_col=0,
                         parse_dates=[0],usecols=fields_EV)

    
    df_EV.columns=['E_EV_req','EV_home','E_EV_trip']
    
    logger.info("separate EV files per profile")
    if combinations['EV_use'] == 'Low':
            filename_EV2 = Path(f'{INPUT_PATH}dfEVLow.csv')
    elif combinations['EV_use'] == 'Medium':
            filename_EV2 = Path(f'{INPUT_PATH}dfEVMedium.csv')
    
    elif combinations['EV_use'] == 'High':
            filename_EV2 = Path(f'{INPUT_PATH}dfEVHigh.csv')
            
    else:
            filename_EV2 = Path(f'{INPUT_PATH}dfEVNone.csv')
    
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
    param['EV_batt_cap'] = combinations['EV_batt_cap']
    if combinations['EV_P_max_home'] == '3_6':
        param['EV_P_max_home'] = 3.6
    elif combinations['EV_P_max_home'] == '7':
        param['EV_P_max_home'] = 7
    elif combinations['EV_P_max_home'] == '11':
        param['EV_P_max_home'] = 11
    param['EV_P_max_away'] = 22
    param['EV_use'] = combinations['EV_use']
    Batt_EV.SOC_max =  1.0*Batt_EV.Capacity
    Batt_EV.SOC_min =  0.2*Batt_EV.Capacity
    param['Batt_EV']=Batt_EV
    param['E_EV_start']=Batt_EV.SOC_min
    df_EV['EV_away']=abs(df_EV.EV_home-1)
    param['public_charging_price']=0.48
    return param, df_EV, EV_ID

def configure_system_parameters(combinations, param, data_input):
    """
    Configure system parameters based on the input 'combinations' dictionary.
    
    Parameters:
        combinations (dict): Contains configuration flags (e.g. 'conf' and 'house_type').
        param (dict): Dictionary to store various system parameters.
        data_input (pd.DataFrame): Data used for logging or further configuration.
        
        
    Returns:
        tuple: Updated 'param' dictionary and a configuration auxiliary list (conf_aux).
    """
    print('##############')
    print('load parameters')
    conf = combinations['conf']
    print('conf')
    print(conf)

    # configuration = [Batt, HP, TS, DHW]
    # if all false, only PV is used
    conf_aux = [False, True, False, False]  # [Batt, HP, TS, DHW]
    
    # For some settings the heat pump is removed
    if combinations['house_type'] == 'NoHeatPump':
        conf_aux[1] = False

    if conf < 4:  # No battery
        logger.debug('No battery')
        param['Converter_efficiency_batt'] = 1
    else:
        logger.debug('Battery present')
        conf_aux[0] = True
        param['Converter_efficiency_batt'] = 0.98

    if (conf != 0) & (conf != 1) & (conf != 4) & (conf != 5) & (conf != 8) & (conf != 9):  # TS present
        logger.debug('TS present')
        conf_aux[2] = True
        if (combinations['house_type'] == 'SFH15') | (combinations['house_type'] == 'SFH45'):
            logger.debug('SHF 15 or 45')
            param['tank_sh'] = pc.heat_storage_tank(mass=1500, surface=6)
        else:
            logger.debug('SHF 100')
            param['tank_sh'] = pc.heat_storage_tank(mass=1500, surface=6)
    else:  # No TS
        logger.debug('SHF 100')
        param['tank_sh'] = pc.heat_storage_tank(mass=0, surface=0.41)

    if (conf == 1) | (conf == 3) | (conf == 5) | (conf == 7):  # DHW present
        logger.debug('DHW present')
        conf_aux[3] = True
        param['tank_dhw'] = pc.heat_storage_tank(mass=200, t_max=60 + 273.15, t_min=40 + 273.15, surface=1.6564)
    else:  # No DHW
        logger.debug('No DHW')
        param['tank_dhw'] = pc.heat_storage_tank(mass=0, t_max=0, t_min=0, specific_heat_dhw=0, U_value_dhw=0, surface_dhw=0)

    logger.debug(data_input.head())
    design_param = load_obj(f'{INPUT_PATH}dict_design_oct')
    if combinations['house_type'] == 'SFH15':
        param['Backup_heater'] = design_param['bu_15']
        param['hp'] = pc.HP_tech(technology='ASHP', power=design_param['hp_15'])
    elif combinations['house_type'] == 'SFH45':
        param['Backup_heater'] = design_param['bu_45']
        param['hp'] = pc.HP_tech(technology='ASHP', power=design_param['hp_45'])
    else:
        param['Backup_heater'] = design_param['bu_100']
        param['hp'] = pc.HP_tech(technology='ASHP', power=design_param['hp_100'])
    
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
    print('##############')
    print('load data')
    print(combinations['hh'])
    pv_capacity = combinations['hh']['pv_capacity']
    consumption_category = combinations['hh']['consumption_category']
    elec_price = combinations['hh']['elec_price']
    combinations['hh'].pop('pv_capacity')
    combinations['hh'].pop('consumption_category')
    combinations['hh'].pop('elec_price')

    df_el = pd.DataFrame(combinations['hh'])
    
    logger.info("Choose the correspongind profile for electricity")

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
    param=dict()
    param['name']=combinations['name']

    
    param['App_comb']=combinations['App_comb']
    param['id_dwell']=electricity_profiles.iloc[combinations['profile_row_number']]#combinations['building_name'] # To be added for citysim
#####################################################
    param['aging'] = True
    param['Curtailment'] = 0
    param['Inverter_efficiency'] = 0.95
    param['Converter_efficiency_HP'] = 0.98
    param['delta_t'] = 1
    param['Capacity_tariff'] = 0
    param['nyears'] = 1
    param['days'] = 365
    param['testing'] = False
    week = 1

######################################################

    #df_el = load_electricity_demand(param['id_dwell'])
    df_el.columns=['Req_kWh','E_demand','E_PV']
    
    # PV_nom = df_el.E_PV.sum()/1000 # Estimated kW
    # param['Capacity']=(df_el.E_PV.sum()/1000).round()  # Estimated kW ratio 1:1 with PV
    PV_nom = pv_capacity['Roof'] + pv_capacity['Wall']
    param["Capacity"] = pv_capacity['Roof'] + pv_capacity['Wall']
    print(param['Capacity'])
    param['Inverter_power'] = round(PV_nom / 1.2, 1)

    df_prices = load_prices()
    
    df_heat = load_heat_demand(combinations)
    [param, df_EV, EV_ID] = load_EV_data(combinations,param)
    

    df_prices=df_prices.resample('1h').mean()
    #######################################################
    # df_prices.Price_flat=31.76 # pour val de bagnes   TO BE CHANGED ACCORDINGLY
    df_prices.Price_flat= elec_price
    #######################################################

    df_EV=df_EV.resample('1h').agg({'E_EV_req': 'sum', 'E_EV_trip': 'sum', 
                                     'EV_home': 'max','EV_away':'max'})
    df_EV.EV_away=np.abs(df_EV.EV_home-1)
    df_heat=df_heat.resample('1h').agg({'Set_T': 'mean', 'Temp': 'mean', 
                                     'Req_kWh': 'sum', 'Req_kWh_DHW':'sum',
                                       'Temp_supply':'mean', 'Temp_supply_tank':'mean',
                                        'COP_SH':'mean', 'COP_tank':'mean',
                                        'COP_DHW':'mean',
                                        'hp_sh_cons':'max','hp_tank_cons':'max',
                                        'hp_dhw_cons':'max'})
    df_el.index=df_heat.index
    df_heat.Req_kWh = df_el.Req_kWh
    df_el=df_el.drop('Req_kWh',axis=1)

    ############ data profiles through time
    
    data_input=pd.concat([df_el,df_heat,df_prices,df_EV],axis=1,copy=True,sort=False)

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
    param, conf_aux=configure_system_parameters(combinations, param, data_input)
    
    logger.debug("Initialized EV battery with capacity %s", param['EV_batt_cap'])

    
    param.update({'Tech':combinations['Tech'],'conf':conf_aux,'ht':combinations['house_type'],
                  'EV_ID':EV_ID, 'electricity_profile':combinations['electricity_profile'],'EV_V2G':combinations['EV_V2G'],
                  'PV_nom':PV_nom,'App_comb':create_app_combinations(combinations['App_comb'])})


    return param, data_input


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
        

        [df,aux_dict]=single_opt2(param,data_input)
        print('out of optimization')
    except OSError as e:
        #print(f"OSError: {e}")
        raise
    except Exception as e:
        #print(f"Unexpected error: {e}")
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
    print('Here you will able to optimize the schedule of PV-coupled HP systems and an electric vehicle with electric and/or thermal storage for a given electricity demand')

    # files_directory = "../Input/"
    # buildings_file = "PVroof_valdebagnes"
    files_directory = INPUT_PATH
    buildings_file = "test"
    buildings_path = f"{files_directory}{buildings_file}"
    buildings=load_obj(buildings_path)
    keys = list(buildings.keys())
    #Define the different combinations of inputs to be run
    dct={
        'Capacity':[7],
        'App_comb':[0],
        'Tech':['NMC'],
        'PV_nom':[1],
        'country':['CH'],
        'cases':['mean'],
        'house_type':['SFH100'],
        'hh':list(buildings.items())[2:],
        'HP':['AS'],
        'conf':[0,4],
        'EV_V2G':[0],
        'electricity_profile':['High'],
        'EV_batt_cap':[60],
        'EV_P_max_home':['11'],
        'EV_use':['Low'],
        'profile_row_number':[99],
    }
    # TODO Understand why most of the entries of the dct object, outside of 'conf', don't seem to be used at all
    ''''
    conf 
    0 only HP
    1 HP+DHW
    2 HP+SH
    3 HP+SH+DHW
    4 only Battery
    5 HP+DHW+BATT
    6 HP+SH+BATT
    7 HP+SH+DHW+BATT
    '''

    # Define the folder containing the files
    output_folder = Path('../Output/')
    pattern = os.path.join(output_folder, 'df_*(Building-*)_NMC_0100_*_*_SFH100.csv')

    # List of matched files
    existing_files = glob.glob(pattern)


    # Extract Respondent_id and EV_V2G_buffer from filenames
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
            print(f"Skipping file with unexpected format: {file}")

    mapping = {
        0: '0100',
        1: '0101',
        2: '0110',
        3: '0111',
        4: '1100',
        5: '1101',
        6: '1110',
        7: '1111',
    }
    mapping_str_to_num = {
    '0100': 0,
    '0101': 1,
    '0110': 2,
    '0111': 3,
    '1100': 4,
    '1101': 5,
    '1110': 6,
    '1111': 7,
}

    expected_combinations = {(building_id, mapping[configuration]) for building_id in keys for configuration in dct['conf']}
    missing_simulations = expected_combinations - existing_simulations
    Combs_todo_list = []
    for bld_id, config in missing_simulations:
        # Retrieve the full building information using the building id as key
        building_info = buildings.get(bld_id, None)
        Combs_todo_list.append({'hh': building_info,'name': bld_id, 'conf': mapping_str_to_num[config]})

    Combs_todo = pd.DataFrame(Combs_todo_list)
    print(len(Combs_todo))
    Combs_todo_dicts = [
        {
            **row,  # Existing respondent and EV_V2G_buffer values
            #capacity is defined in input data
            'App_comb':0,
            'Tech':'NMC',
            'PV_nom':1,
            'country':'CH',
            'cases':'mean',
            'house_type':'SFH100',
            'HP':'AS',
            'EV_V2G':0,
            'electricity_profile':'High',
            'EV_batt_cap':60,
            'EV_P_max_home':'11',
            'EV_use':'High',
            'profile_row_number':99
        }
        for row in Combs_todo.to_dict(orient='records')
    ]

    mp.freeze_support()
    print('&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&')
    mp.set_start_method("spawn")
    pool=mp.Pool(processes=1)
    #selected_dwellings=select_data(Combs_todo)
    #print(selected_dwellings)
    #print(Combs_todo)
    pool.map(pooling2,Combs_todo_dicts)
    pool.close()
    pool.join()
    print('&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&')

if __name__ == '__main__':
    main()