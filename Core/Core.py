#!/usr/bin/python3
# -*- coding: utf-8 -*-
## @namespace Core_LP
# Created on Tue Oct 31 11:11:33 2017
# Author
# Alejandro Pena-Bello
# alejandro.penabello@hevs.ch
# This script prepares the input for the LP algorithm and gets the output in a dataframe, then saves the output.
# Description
# -----------
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
# Pandas, numpy, pyomo, pickle, math, sys, glob, time

import logging
import pandas as pd
import paper_classes as pc
from pyomo.opt import SolverFactory, SolverStatus, TerminationCondition
from pyomo.core import Var
import time
import numpy as np
import LP_EV as optim
import math
import pickle
import sys
from functools import wraps
import csv
import os
import post_proc as pp
import threading

# Configure logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fn_timer(function):
    @wraps(function)
    def function_timer(*args, **kwargs):
        t0 = time.time()
        result = function(*args, **kwargs)
        t1 = time.time()
        logger.debug("Function '%s' executed in %s seconds", function.__name__, t1 - t0)
        return result
    return function_timer

def Get_output(instance):
    '''
    Gets the model output and transforms it into a pandas dataframe with the desired names.
    Parameters
    ----------
    instance : instance of pyomo
    Returns
    -------
    df : DataFrame
    P_max_ : vector of daily maximum power
    '''
    logger.debug("Entering Get_output function.")
    # to write in a csv goes faster than actualizing a df
    global_lock = threading.Lock()
    while global_lock.locked():
        continue
    global_lock.acquire()
    np.random.seed()
    filename = 'out' + str(np.random.randint(1, 10, 10))[1:-1].replace(" ", "") + '.csv'
    logger.debug("Temporary output filename: %s", filename)
    with open(filename, 'a') as f:
        writer = csv.writer(f, delimiter=';')
        for v in instance.component_objects(Var, active=True):
            varobject = getattr(instance, str(v))
            for index in varobject:
                if str(v) == 'P_max_day':
                    P_max_ = (v[index].value)
                else:
                    writer.writerow([index, varobject[index].value, v])
    df = pd.read_csv(filename, sep=';', names=['val', 'var'])
    os.remove(filename)
    global_lock.release()
    df = df.pivot_table(values='val', columns='var', index=df.index)
    df = df.drop(-1)
    logger.debug("Output dataframe and P_max retrieved successfully.")
    return [df, P_max_]

@fn_timer
def Optimize(data_input, param):
    """
    This function calls the LP and controls the aging. The aging is then calculated on a daily basis and the capacity updated.
    When the battery reaches the EoL the loop breaks. 'days' allows to optimize multiple days at once.
    Parameters
    ----------
    Capacity : float
    Tech : string
    App_comb : array
    Capacity_tariff : float
    data_input: DataFrame
    param: dict
    PV_nom: float
    Returns
    -------
    df : DataFrame
    aux_Cap_arr : array
    SOH_arr : array
    Cycle_aging_factor : array
    P_max_arr : array
    results_arr : array
    cycle_cal_arr : array
    DoD_arr : array
    """
    logger.info("Starting optimization process.")
    days = 1
    dt = param['delta_t']
    end_d = int(param['ndays'] * 24 / dt)
    window = int(24 * days / dt)

    logger.info("Optimizing for %s day(s) with a window of %s timesteps.", days, window)
    logger.info("%%%%%%%%% Optimizing %%%%%%%%%%%%%%%")

    Batt = pc.Battery_tech(Capacity=param['Capacity'], Technology=param['Tech'])
    logger.debug("Initialized Battery_tech: %s", Batt.Technology)

    aux_Cap_arr = np.zeros(param['ndays'])
    SOC_max_arr = np.zeros(param['ndays'])
    SOH_arr = np.zeros(param['ndays'])
    P_max_arr = np.zeros(param['ndays'])
    cycle_cal_arr = np.zeros(param['ndays'])
    results_arr = []
    DoD_arr = np.zeros(param['ndays'])
    aux_Cap = Batt.Capacity
    SOC_max_ = Batt.SOC_max
    SOH_aux = 1

    #width = 200
    #data_input.loc[:, 'Temp_supply'] = data_input['Temp_supply'].rolling(window=width).mean().bfill()
    #data_input.loc[:, 'Temp_supply_tank'] = data_input['Temp_supply_tank'].copy().rolling(window=width).mean().bfill()
    data_input['T_aux_supply'] = data_input.apply(lambda row: row.Temp_supply + 10, axis=1)
    for i in range(int(param['ndays'] / days)):
        logger.debug("Processing day index: %s", i)
        toy = 0
        data_input_ = data_input[data_input.index.dayofyear == data_input.index.dayofyear[0] + i]
        #print(data_input_)
        if i == 0:
            aux_Cap_aged = Batt.Capacity
            aux_SOC_max = Batt.SOC_max
            SOH = 1
            T_init = data_input[data_input.index.dayofyear == data_input.index.dayofyear[0] + i].Temp_supply.iloc[0]
        else:
            aux_Cap_aged = aux_Cap
            aux_SOC_max = SOC_max_
            SOH = SOH_aux
            T_init = T_init_

        if data_input.index.dayofyear[0] + i == 120:
            toy = 1
        elif data_input.index.dayofyear[0] + i == 274:
            toy = 3
        elif (data_input.index.dayofyear[0] + i < 274) & (data_input.index.dayofyear[0] + i > 120):
            toy = 2
        
        if param['App_comb'][2] == True:
            if param['App_comb'][3] == True:
                retail_price_dict = dict(enumerate(data_input_.Price_DT_mod))
            else:
                retail_price_dict = dict(enumerate(data_input_.Price_DT))
        else:
            if param['App_comb'][3] == True:
                retail_price_dict = dict(enumerate(data_input_.Price_flat_mod))
            else:
                retail_price_dict = dict(enumerate(data_input_.Price_flat))
        for col in data_input_.keys():
            param.update({col: dict(enumerate(data_input_[col]))})
        Set_declare = np.arange(-1, data_input_.shape[0])
        if i == 0:
            logger.debug("Retail price dictionary (first day): %s", retail_price_dict)
        param.update({'dayofyear': data_input.index.dayofyear[0] + i,
                      'SOC_max': aux_SOC_max,
                      'toy': toy,
                      #'subset_tank_day': (np.arange(1, 97 / 3) * 3).astype(int), #not used
                      'Batt': Batt,
                      'Set_declare': Set_declare,
                      'T_init': T_init,
                      'retail_price': retail_price_dict,
                      'App_comb_mod': dict(enumerate(param['App_comb']))})
        param['Max_inj'] = param['Curtailment'] * param['PV_nom']
        instance = optim.Concrete_model(param)
        global_lock = threading.Lock()
        while global_lock.locked():
            continue
        global_lock.acquire()
        if sys.platform == 'win32':
            opt = SolverFactory('gurobi')
            opt.options["threads"] = 1
            opt.options["mipgap"] = 0.001
        else:
            opt = SolverFactory('cplex', executable='/opt/ibm/ILOG/CPLEX_Studio1271/cplex/bin/x86-64_linux/cplex')
            opt.options["threads"] = 1
            opt.options["mipgap"] = 0.001
        logger.debug("Solver initialized, starting solve for day index %s", i)
        results = opt.solve(instance)#, tee=True)
        global_lock.release()
        #results.write(num=1)

        if (results.solver.status == SolverStatus.ok) and (results.solver.termination_condition == TerminationCondition.optimal):
            logger.debug("Optimal solution found for day index %s", i)
            [df_1, P_max] = Get_output(instance)
            T_init_ = df_1.loc[df_1.index[-1], 'T_ts']
            if param['aging']:
                [SOC_max_, aux_Cap, SOH_aux, Cycle_aging_factor, cycle_cal, DoD] = aging_day(
                    df_1.E_char, SOH, Batt.SOC_min, Batt, aux_Cap_aged)
                DoD_arr[i] = DoD
                cycle_cal_arr[i] = cycle_cal
                P_max_arr[i] = P_max
                aux_Cap_arr[i] = aux_Cap
                SOC_max_arr[i] = SOC_max_
                SOH_arr[i] = SOH_aux
            else:
                DoD_arr[i] = df_1.E_dis.sum() / Batt.Capacity
                cycle_cal_arr[i] = 0
                P_max_arr[i] = P_max
                aux_Cap_arr[i] = aux_Cap
                SOC_max_arr[i] = SOC_max_
                SOH_arr[i] = SOH_aux
                Cycle_aging_factor = 0
            results_arr.append(instance.total_cost())
            if i == 0:  # initialize
                df = pd.DataFrame(df_1)
            elif i == param['ndays'] - 1:  # if we go until the end of the days
                df = pd.concat([df, df_1], ignore_index=True)
                if SOH <= 0:
                    logger.info("SOH <= 0, breaking loop.")
                    break
                if param['ndays'] / 365 > Batt.Battery_cal_life:
                    logger.info("Exceeded battery lifetime, breaking loop.")
                    break
            else:  # if SOH or ndays are greater than the limit
                df = pd.concat([df, df_1], ignore_index=True)
                if SOH <= 0:
                    logger.info("SOH <= 0, ending optimization early.")
                    df = pd.concat([df, df_1], ignore_index=True)
                    end_d = df.shape[0]
                    break
                if i / 365 > Batt.Battery_cal_life:
                    logger.info("Day index exceeds battery lifetime, breaking loop.")
                    df = pd.concat([df, df_1], ignore_index=True)
                    break
        elif (results.solver.termination_condition == TerminationCondition.infeasible):
            logger.error("Model infeasible for day index %s", i)
            return (None, None, None, None, None, None, None, None, results)
        else:
            logger.error("Solver error: status %s for day index %s", results.solver.status, i)
            return (None, None, None, None, None, None, None, None, results)
    end_d = df.shape[0]
    df = pd.concat([df, data_input.loc[data_input.index[:end_d], ['E_demand', 'E_PV', 'Export_price']].reset_index()], axis=1)
    if param['App_comb'][2] == True:
        if param['App_comb'][3] == True:
            logger.info("App2 and App 3 selected.")
            df['price'] = data_input.Price_DT_mod.reset_index(drop=True)[:end_d].values
        else:
            logger.info("App2 selected.")
            df['price'] = data_input.Price_DT.reset_index(drop=True)[:end_d].values
    else:
        if param['App_comb'][3] == True:
            logger.info("App3 selected.")
            df['price'] = data_input.Price_flat_mod.reset_index(drop=True)[:end_d].values
        else:
            logger.info("No App2 nor App3 selected.")
            df['price'] = data_input.Price_flat.reset_index(drop=True)[:end_d].values
    #logger.debug("First five price values: %s", df['price'].head())
    
    # Compute inverter and converter power
    df['Inv_P'] = (df[['E_PV_load', 'E_batt_load', 'E_PV_grid', 'E_loss_inv']].sum(axis=1)) / dt
    df['Conv_P'] = (df[['E_PV_load', 'E_PV_batt', 'E_PV_grid', 'E_loss_conv']].sum(axis=1)) / dt
    columns_to_map = [
    'Req_kWh', 'Req_kWh_DHW', 'Set_T', 'Temp', 'Temp_supply',
    'Temp_supply_tank', 'T_aux_supply', 'COP_tank', 'COP_SH', 'COP_DHW', 'E_EV_trip'
]
    # Define the list of columns to map from data_input
    new_cols = {col: data_input[col].reset_index(drop=True).iloc[:end_d].values 
                for col in columns_to_map}
    df = df.assign(**new_cols)
    df.set_index('index', inplace=True)

    aux_dict = {'aux_Cap_arr': aux_Cap_arr, 'SOH_arr': SOH_arr, 'Cycle_aging_factor': Cycle_aging_factor, 'P_max_arr': P_max_arr,
                'results_arr': results_arr, 'cycle_cal_arr': cycle_cal_arr, 'DoD_arr': DoD_arr, 'results': results}
    logger.info("Optimization process completed.")
    return df, aux_dict

def get_cycle_aging(DoD, Technology):
    '''
    The cycle aging factors are defined for each technology according to the DoD using an exponential function.
    Parameters
    ----------
    DoD : float
    Technology : string
    Returns
    -------
    Cycle_aging_factor : float
    '''
    logger.debug("Calculating cycle aging for Technology: %s, DoD: %s", Technology, DoD)
    if Technology == 'LTO':  # Xalt 60Ah LTO Model F920-0006
        Cycle_aging_factor = 1 / (math.exp((math.log(DoD) - math.log(771.51)) / -0.604) - 45300)
    elif Technology == 'LFP':  # https://doi.org/10.1016/j.apenergy.2013.09.003
        Cycle_aging_factor = 1 / (math.exp((math.log(DoD) - math.log(70.869)) / -0.54) + 1961.37135)
    elif Technology == 'NCA':  # Saft Evolion
        Cycle_aging_factor = 1 / (math.exp((math.log(DoD) - math.log(1216.7)) / -0.869) + 4449.67011)
    elif Technology == 'NMC':  # Tesla Truong et al. 2016
        Cycle_aging_factor = 1 / (math.exp((math.log(DoD) - math.log(1E8)) / -2.168))
    elif Technology == 'ALA':  # Sacred sun FCP-1000 lead carbon
        Cycle_aging_factor = 1 / (math.exp((math.log(DoD) - math.log(37403)) / -1.306) + 330.656417)
    elif Technology == 'VRLA':  # Sonnenschein
        Cycle_aging_factor = 1 / (math.exp((math.log(DoD) - math.log(667.61)) / -0.988))
    elif Technology == 'test':
        Cycle_aging_factor = 1 / (math.exp((math.log(DoD) - math.log(238.86)) / -0.875) + 4482.74484)
    logger.debug("Cycle aging factor: %s", Cycle_aging_factor)
    return Cycle_aging_factor

def aging_day(daily_ESB, SOH, SOC_min, Batt, aux_Cap):
    """
    Calculates daily aging based on cyclic and calendric factors.
    Parameters
    ----------
    daily_ESB : array
    SOH : float
    SOC_min : float
    Batt : class
    aux_Cap : float
    Returns
    -------
    SOC_max : float
    aux_Cap : float
    SOH : float
    Cycle_aging_factor : float
    cycle_cal : int
    DoD : float
    """
    logger.debug("Starting aging_day computation.")
    Cal_aging_factor = 1 / (Batt.Battery_cal_life * 24 * 365)
    aux_DOD = (Batt.SOC_max - Batt.SOC_min) / Batt.Capacity
    DoD = daily_ESB.sum() / Batt.Capacity
    if DoD == 0:
        Cycle_aging_factor = get_cycle_aging(DoD + 0.00001, Batt.Technology)
    elif DoD <= 1:
        Cycle_aging_factor = get_cycle_aging(DoD, Batt.Technology)
    else:
        aux_DoD = DoD - int(DoD)
        Cycle_aging_factor = get_cycle_aging(aux_DoD, Batt.Technology)
        for i in range(int(DoD)):
            Cycle_aging_factor += get_cycle_aging(1, Batt.Technology)
    SOH = 1 / .3 * aux_Cap / Batt.Capacity - 7 / 3
    aging = max(Cycle_aging_factor, Cal_aging_factor * 24)
    aux_Cap = Batt.Capacity * (1 - 0.3 * (1 - SOH + aging))
    if Cycle_aging_factor > (Cal_aging_factor * 24):
        cycle_cal = 1
    else:
        cycle_cal = 0
    SOC_max = Batt.SOC_min + aux_Cap * (aux_DOD)
    logger.debug("Completed aging_day: SOC_max=%s, aux_Cap=%s, SOH=%s", SOC_max, aux_Cap, SOH)
    return [SOC_max, aux_Cap, SOH, Cycle_aging_factor, cycle_cal, DoD]

def aggregate_results(df, aux_dict, param):
    '''
    Aggregates results from the whole year optimization.
    Parameters
    ----------
    df : DataFrame
    param: dict
    aux_dict: dict
    Returns
    -------
    bool
        True if successful, False otherwise.
    '''
    logger.info("Aggregating results.")
    try:
        App_comb = param['App_comb']
        if param['testing']:
            [agg_results, El_out, Power_out] = pp.get_main_results(param, aux_dict, df)
            El_out.to_csv('../Output/test_el_out.csv')
            Power_out.to_csv('../Output/test_power_out.csv')
        else:
            agg_results = pp.get_main_results(param, aux_dict, df)
        global_lock = threading.Lock()
        while global_lock.locked():
            continue
        global_lock.acquire()
        filename = '../Output/aggregated_results.csv'
        with open(filename, 'a', newline='') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(agg_results.values)
        global_lock.release()
        logger.info("Aggregated results saved to %s", filename)
    except IOError as e:
        logger.error("I/O error during aggregation: %s", e)
        logger.error("I/O error({0}): {1}".format(e.errno, e.strerror))
    except ValueError:
        logger.error("Value error during aggregation: Could not convert data to an integer.")
    except:
        logger.error("Unexpected error during aggregation: %s", sys.exc_info()[0])
        logger.error("Unexpected error details: %s", sys.stderr)
    return

def save_obj(obj, name):
    with open('Output/' + name + '.pkl', 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)
    logger.debug("Object saved as %s.pkl", name)

def save_results(df, aux_dict, param):
    '''
    Save the results in pickle format using the corresponding timezone.
    Parameters
    ----------
    df : DataFrame
    param: dict
    aux_dict: dict
    Returns
    -------
    bool
        True if successful, False otherwise.
    '''
    try:
        App_comb = param['App_comb']
        col = ["%i" % x for x in App_comb]
        name_comb = col[0] + col[1] + col[2] + col[3]
        col2 = ["%i" % x for x in param['conf']]
        name_conf = col2[0] + col2[1] + col2[2] + col2[3]
        filename_save = ('../Output/df_%(name)s_%(Tech)s_%(App_comb)s_%(Cap)s_%(conf)s_%(house_type)s.csv' %
                         {'name': param['name'], 'Tech': param['Tech'], 'App_comb': name_comb, 'Cap': int(param['Capacity']),
                          'conf': name_conf, 'house_type': param['ht']})
        df.to_csv(filename_save)
        logger.info("Results saved to %s", filename_save)
        return
    except:
        logger.error("Save Failed.")
        return

def single_opt2(param, data_input):
    """
    Iterates over capacities, technologies and applications and calls the module to save the results.
    Parameters
    ----------
    param: dict
    data_input: DataFrame
    Returns
    -------
    df : DataFrame
    aux_dict : dict
    """
    logger.info("Starting single_opt2 process.")
    logger.info("Begin single_opt2: Starting optimization sequence.")
    aux_app_comb = param['App_comb']  # afterwards is modified to send to LP
    logger.info("App_comb stored.")
    df, aux_dict = Optimize(data_input, param)
    param.update({'App_comb': aux_app_comb})
    logger.info("Optimization complete; proceeding with saving results.")
    if param['testing'] == False:
        logger.info("Non-testing mode: aggregating results.")
        save_results(df, aux_dict, param)

        #aggregate_results(df, aux_dict, param)
    else:
        save_results(df, aux_dict, param)
        logger.debug("Testing mode active; skipping aggregation. Data input head: %s", data_input.head())
    logger.info("single_opt2 process completed.")
    return [df, aux_dict]
