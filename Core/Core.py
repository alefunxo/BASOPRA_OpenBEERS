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

import gc
from utils.logger import logger
from config.loader import config
import pandas as pd
import paper_classes as pc
from pyomo.opt import SolverFactory, SolverStatus, TerminationCondition

from pyomo.core import Var
import time
import numpy as np
import LP_mEV as optim
import math
import pickle
import sys
from functools import wraps
import csv
import os
import post_proc as pp
import threading
import ast

core_config = config.Core

def fn_timer(function):
    @wraps(function)
    def function_timer(*args, **kwargs):
        t0 = time.time()
        result = function(*args, **kwargs)
        t1 = time.time()
        logger.debug("Function '%s' executed in %s seconds", function.__name__, t1 - t0)
        return result
    return function_timer
def Get_output2(instance):
    import threading, numpy as np, csv, os, pandas as pd
    from pyomo.core.base.var import Var

    # 1) Dump raw rows
    lock = threading.Lock()
    while lock.locked(): pass
    lock.acquire()
    fname = 'out' + str(np.random.randint(1,1e9)) + '.csv'
    with open(fname, 'w', newline='') as f:
        writer = csv.writer(f, delimiter=';')
        for v in instance.component_objects(Var, active=True):
            varobj = getattr(instance, str(v))
            for idx in varobj:
                if str(v) == 'P_max_day':
                    P_max_ = varobj[idx].value
                else:
                    # split index into ev, time
                    if isinstance(idx, tuple) and len(idx)==2:
                        ev, t = idx
                    else:
                        ev, t = '', idx
                    writer.writerow([t, str(v), ev, varobj[idx].value])
    lock.release()

    # 2) Read back, preserving empty ev fields
    df = pd.read_csv(
        fname, sep=';', names=['time','var','ev','val'],
        dtype={'time':str,'var':str,'ev':str,'val':float},
        keep_default_na=False,  # ← do not convert empty to NaN
        na_filter=False         # ← also don’t do any NA filtering
    )
    os.remove(fname)

    # 3) … drop t=-1, convert time …
    df = df[df['time']!='-1']
    df['time'] = df['time'].astype(int)

    # 4) Now splitting will work:
    #    non-EV rows have ev=='', EV rows have ev in {'EV1','EV2',…}
    df_noev = df[df.ev == '']
    df_evs  = df[df.ev != '']

    # 5a) pivot non-EV
    pivot_noev = df_noev.pivot_table(
        index='time', columns='var', values='val', aggfunc='first'
    )

    # 5b) pivot EV
    pivot_evs = df_evs.pivot_table(
        index='time', columns=['var','ev'], values='val', aggfunc='first'
    )
    pivot_evs.columns = [f"{var}_{ev}" for var,ev in pivot_evs.columns]

    # 6) stitch them together
    result = pd.concat([pivot_noev, pivot_evs], axis=1).sort_index()

    # 7) collect P_max_day as before
    P_max_ = getattr(instance, 'P_max_day', None).value
    return result, P_max_



def _collect(instance):


    records = []
    P_max_ = None
    for v in instance.component_objects(Var, active=True):
        name = v.name
        varobj = getattr(instance, name)
        for idx in varobj:
            val = varobj[idx].value
            if name == 'P_max_day':
                P_max_ = val
                continue
            if isinstance(idx, tuple) and len(idx) == 2:
                ev, t = idx
            else:
                ev, t = '', idx
            if int(t) == -1:
                continue
            records.append({'time': int(t), 'var': name, 'ev': ev or None, 'val': val})
    df = pd.DataFrame.from_records(records)
    noev = df[df['ev'].isna()].pivot(index='time', columns='var', values='val')
    evs  = df[df['ev'].notna()].pivot(index='time', columns=['var','ev'], values='val')
    evs.columns = [f"{var}_{ev}" for var, ev in evs.columns]
    return pd.concat([noev, evs], axis=1).sort_index(), P_max_

def get_output(instance, lock=None):
    if lock is not None:
        with lock:
            return _collect(instance)
    else:
        return _collect(instance)

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
    Batt = param['Batt']
    end_d = int(param['ndays'] * 24 / dt)
    window = int(24 * days / dt)

    logger.info("Optimizing for %s day(s) with a window of %s timesteps.", days, window)
    logger.info("%%%%%%%%% Optimizing %%%%%%%%%%%%%%%")

    # Pre-allocated_arrays
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

    data_input['T_aux_supply'] = data_input['Temp_supply'] + 10

    df_list = []
    for i in range(int(param['ndays'] / days)):
        logger.info("Processing day index: %s", i)

        dayofyear_i = data_input.index.dayofyear[0] + i
        data_input_ = data_input[data_input.index.dayofyear == dayofyear_i]

        if i == 0:
            aux_Cap_aged = Batt.Capacity
            aux_SOC_max = Batt.SOC_max
            SOH = 1
            T_init = data_input_.Temp_supply.iloc[0]
            T_init_dhw = 50 + 273.15
        else:
            aux_Cap_aged = aux_Cap
            aux_SOC_max = SOC_max_
            SOH = SOH_aux
            T_init = T_init_
            T_init_dhw = T_init_dhw_

        # Time of year
        if dayofyear_i == 120:
            toy = 1
        elif dayofyear_i == 274:
            toy = 3
        elif 120 < dayofyear_i < 274:
            toy = 2
        else:
            toy = 0
       
        # Retail price logic
        app2, app3 = param['App_comb'][2], param['App_comb'][3]
        if app2:
            retail_price_dict = dict(enumerate(data_input_.Price_DT_mod if app3 else data_input_.Price_DT))
        else:
            retail_price_dict = dict(enumerate(data_input_.Price_flat_mod if app3 else data_input_.Price_flat))

        param_day = param.copy()
        param_day.update({
            col: dict(enumerate(data_input_[col])) for col in data_input_.columns
        })

        for col in data_input_.keys():
            param.update({col: dict(enumerate(data_input_[col]))})
        param_day.update({
            'dayofyear': dayofyear_i,
            'SOC_max': aux_SOC_max,
            'toy': toy,
            'Batt': Batt,
            'Set_declare': np.arange(-1, data_input_.shape[0]),
            'T_init': T_init,
            'T_init_dhw': T_init_dhw,
            'retail_price': retail_price_dict,
            'App_comb_mod': dict(enumerate(param['App_comb'])),
            'Max_inj': param['Curtailment'] * param['PV_nom'],
            'EV_home': {ev: data_input[f"{ev}_EV_home"].reset_index(drop=True).to_dict() for ev in param['EV_list']},
            'EV_away': {ev: data_input[f"{ev}_EV_away"].reset_index(drop=True).to_dict() for ev in param['EV_list']},
            'E_EV_trip': {ev: data_input[f"{ev}_E_EV_trip"].reset_index(drop=True).to_dict() for ev in param['EV_list']},
            'E_EV_req': {ev: data_input[f"{ev}_E_EV_req"].reset_index(drop=True).to_dict() for ev in param['EV_list']},
            'Batt_EV': dict(param['Batt_EV']),
        })
        
        # Build and solve model
        instance = optim.Concrete_model(param_day)
        opt = SolverFactory('gurobi')
        opt.options.update({
            "threads": 1,
            "mipgap": 0.02,
            "TimeLimit": 180,
        })

        results = opt.solve(instance)
        
        if core_config.Optimizer.solver_results_write:
            results.write(num=1)

        if (results.solver.status == SolverStatus.ok) and (results.solver.termination_condition == TerminationCondition.optimal):
            logger.debug("Optimal solution found for day index %s", i)
            df_1, P_max = get_output(instance)

            T_init_ = df_1.loc[df_1.index[-1], 'T_ts']
            T_init_dhw_ = df_1.loc[df_1.index[-1], 'T_dhwst']
            if param['aging']:
                SOC_max_, aux_Cap, SOH_aux, Cycle_aging_factor, cycle_cal, DoD = aging_day(
                    df_1.E_char, SOH, Batt.SOC_min, Batt, aux_Cap_aged
                )
                DoD_arr[i] = DoD
                cycle_cal_arr[i] = cycle_cal
                P_max_arr[i] = P_max
                aux_Cap_arr[i] = aux_Cap
                SOC_max_arr[i] = SOC_max_
                SOH_arr[i] = SOH_aux
            else:
                DoD_arr[i] = df_1.E_dis.sum() / Batt.Capacity if Batt.Capacity else 0
                cycle_cal_arr[i] = 0
                P_max_arr[i] = P_max
                aux_Cap_arr[i] = aux_Cap
                SOC_max_arr[i] = SOC_max_
                SOH_arr[i] = SOH_aux
                Cycle_aging_factor = 0

            results_arr.append(instance.total_cost())
            df_list.append(df_1)
            del df_1
            gc.collect()
            # df = pd.concat([df, df_1])

            if SOH <= 0 or i / 365 > Batt.Battery_cal_life:
                logger.info("Battery life or SOH limit reached. Breaking.")
                break

        else:
            logger.error("Solver issue (status: %s, condition: %s)", results.solver.status, results.solver.termination_condition)
            return None, results
        
        # Clean up model
        del instance, opt, data_input_, retail_price_dict, param_day
        gc.collect()

    df = pd.concat(df_list, ignore_index=True)
    del df_list

    end_d = df.shape[0]
    df = pd.concat([
        df, 
        data_input.loc[data_input.index[:end_d], ['E_demand', 'E_PV', 'Export_price']].reset_index()
    ], axis=1)

    if param['App_comb'][2]:
        df['price'] = (data_input.Price_DT_mod if param['App_comb'][3] else data_input.Price_DT).reset_index(drop=True)[:end_d].values
    else:
        df['price'] = (data_input.Price_flat_mod if param['App_comb'][3] else data_input.Price_flat).reset_index(drop=True)[:end_d].values
   
    # Compute inverter and converter power
    df['Inv_P'] = (df[['E_PV_load', 'E_batt_load', 'E_PV_grid', 'E_loss_inv']].sum(axis=1)) / dt
    df['Conv_P'] = (df[['E_PV_load', 'E_PV_batt', 'E_PV_grid', 'E_loss_conv']].sum(axis=1)) / dt

    # Add mapped columns
    columns_to_map = [
        'Req_kWh', 'Req_kWh_DHW', 'Set_T', 'Temp', 'Temp_supply',
        'Temp_supply_tank', 'T_aux_supply', 'COP_tank', 'COP_SH', 'COP_DHW'
    ]

    # Define the list of columns to map from data_input
    new_cols = {
        col: data_input[col].reset_index(drop=True).iloc[:end_d].values 
        for col in columns_to_map
    }

    for ev in param['EV_list']:
        new_cols[f"{ev}_EV_home"]   = data_input[f"{ev}_EV_home"].reset_index(drop=True).iloc[:end_d].values
        new_cols[f"{ev}_EV_away"]   = data_input[f"{ev}_EV_away"].reset_index(drop=True).iloc[:end_d].values
        new_cols[f"{ev}_E_EV_trip"] = data_input[f"{ev}_E_EV_trip"].reset_index(drop=True).iloc[:end_d].values

    df = pd.concat([df, pd.DataFrame(new_cols, index=df.index)], axis=1)
    df.set_index('index', inplace=True)
    df = df.copy()

    aux_dict = {
        'aux_Cap_arr': aux_Cap_arr, 
        'SOH_arr': SOH_arr, 
        'Cycle_aging_factor': Cycle_aging_factor, 
        'P_max_arr': P_max_arr,
        'results_arr': results_arr, 
        'cycle_cal_arr': cycle_cal_arr, 
        'DoD_arr': DoD_arr, 
        # 'results': results,
        'results_summary': {
            'status': str(results.solver.status),
            'termination_condition': str(results.solver.termination_condition)
        }
    }

    del data_input, param, new_cols, results
    gc.collect()

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
    output_dir = 'Output/'
    os.makedirs(output_dir, exist_ok=True)
    with open(f'{output_dir}{name}.pkl', 'wb') as f:
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
        filename_save = ('Output/df_%(name)s_%(Tech)s_%(App_comb)s_%(Cap)s_%(conf)s_%(house_type)s.csv' %
                         {'name': param['name'], 'Tech': param['Tech'], 'App_comb': name_comb, 'Cap': int(param['Capacity']),
                          'conf': name_conf, 'house_type': param['ht']})
        df.to_csv(filename_save)
        logger.info("Results for egid number %s", param['id_dwell']['x'])
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
    original_app_comb = param['App_comb'].copy()  # afterwards is modified to send to LP

    df, aux_dict = Optimize(data_input, param)

    param['App_comb'] = original_app_comb
    del original_app_comb

    logger.info("Optimization complete; proceeding with saving results.")

    if not param['testing']:
        logger.info("Non-testing mode: aggregating results.")
    else:
        logger.debug("Testing mode active; skipping aggregation. Data input head: %s", data_input.head())

    result = [df, aux_dict]
    del data_input, param, df, aux_dict
    gc.collect()

    logger.info("single_opt2 process completed.")
    return result
