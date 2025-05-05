#!/usr/bin/python3
# -*- coding: utf-8 -*-
## @namespace Core_LP
# Created on Tue Oct 31 11:11:33 2017
# Author
# Alejandro Pena-Bello
# alejandro.penabello@unige.ch
# This script prepares the input for the LP algorithm and get the output in a dataframe, finally it saves the output.
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
# Pandas, numpy, pyomo, pickle, math, sys,glob, time

import pandas as pd
import paper_classes_2 as pc
from pyomo.opt import SolverFactory
from pyomo.core import Var
import time
import numpy as np
import LP as optim
import math
import pickle
import sys
import glob
from functools import wraps


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

@fn_timer
def Get_output(instance):
    '''
    Gets the model output and transforms it into a pandas dataframe
	with the desired names.
    Parameters
    ----------
    instance : instance of pyomo

    Returns
    -------
    df : DataFrame
    P_max_ : vector of daily maximum power
    '''

    df=pd.DataFrame(columns=[str(v) for v in instance.component_objects(Var,
                             active=True) if str(v)!='P_max_day'])

    for v in instance.component_objects(Var, active=True):
        for index in v:
            if str(v) =='P_max_day':
                P_max_=(v[index].value)
            else:
                df.loc[index,str(v)]=(v[index].value)

    #due to the set that begins at -1 we have an additional row
    df=df.drop(-1)
    return [df,P_max_]
@fn_timer
def Optimize(Capacity,Tech,App_comb,Capacity_tariff,data_input,
            param,PV_nom):

    """
    This function calls the LP and controls the aging. The aging is then
    calculated in daily basis and the capacity updated. When the battery
    reaches the EoL the loop breaks. 'days' allows to optimize multiple days at once.

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
    print(App_comb)
    print(Tech)
    print(Capacity)

    days=365
    dt=param['delta_t']
    end_d=int(param['ndays']*24/dt)
    window=int(24*days/dt)

    print('%%%%%%%%% Optimizing %%%%%%%%%%%%%%%')
    Batt=pc.Battery(Capacity,Tech)
    aux_Cap_arr=np.zeros(param['ndays'])
    SOC_max_arr=np.zeros(param['ndays'])
    SOH_arr=np.zeros(param['ndays'])
    P_max_arr=np.zeros(param['ndays'])
    cycle_cal_arr=np.zeros(param['ndays'])
    results_arr=[]
    DoD_arr=np.zeros(param['ndays'])
    aux_Cap=Batt.Capacity
    SOC_max_=Batt.SOC_max
    SOH_aux=1
    for i in range(int(param['ndays']/days)):
        print(i)
        if i==0:
            aux_Cap_aged=Batt.Capacity
            aux_SOC_max=Batt.SOC_max
            SOH=1
        else:
            aux_Cap_aged=aux_Cap
            aux_SOC_max=SOC_max_
            SOH=SOH_aux
        ini=i*int(24*days/dt)
        endi=i*int(24*days/dt)+96*days

        data_input_=data_input[ini:endi]
        if App_comb[2]==1:
            retail_price_dict=dict(enumerate(data_input_.Price_DT))
        else:
            retail_price_dict=dict(enumerate(data_input_.Price_flat))
        Export_price_dict=dict(enumerate(data_input_.Export_price))
        E_demand_dict=dict(enumerate(data_input_.E_demand))
        E_PV_dict=dict(enumerate(data_input_.E_PV))
        Set_T_dict=dict(enumerate(data_input_.Set_T))
        Req_W_dict=dict(enumerate(data_input_.Req_W))
        Temp_dict=dict(enumerate(data_input_.Temp))
        COP_dict=dict(enumerate(data_input_.COP))
        param.update({'PV_nominal_power':PV_nom,
    		'SOC_max':aux_SOC_max,
    		'Batt':Batt,
    		'Export_price':Export_price_dict,
    		'Set_declare':np.arange(-1,window),
            'Set_T':Set_T_dict,
            'Req_W':Req_W_dict,
            'Temp':Temp_dict,
            'COP':COP_dict,
    		'Capacity_tariff':Capacity_tariff,
    		'E_demand':E_demand_dict,'E_PV':E_PV_dict,
    		'retail_price':retail_price_dict,'Capacity':Capacity,
    		'technology':Tech,'App_comb':dict(enumerate(App_comb))})
            #Max_inj is in kW
        param['Max_inj']=param['Curtailment']*param['PV_nominal_power']
        instance = optim.Concrete_model(param)
        if sys.platform=='win32':
            opt = SolverFactory('cplex')
        else:
            opt = SolverFactory('cplex',executable='/opt/ibm/ILOG/'
                            'CPLEX_Studio1271/cplex/bin/x86-64_linux/cplex')
        results = opt.solve(instance)
        #results.write(num=1)
        instance.pprint()


        if param['aging']:
            [SOC_max_,aux_Cap,SOH_aux,Cycle_aging_factor,cycle_cal,DoD]=aging_day(
            df_1.E_char,SOH,Batt.SOC_min,Batt,aux_Cap_aged)
            DoD_arr[i]=DoD
            cycle_cal_arr[i]=cycle_cal
            P_max_arr[i]=P_max
            aux_Cap_arr[i]=aux_Cap
            SOC_max_arr[i]=SOC_max_
            SOH_arr[i]=SOH_aux
        else:
            DoD_arr[i]=df_1.E_dis.sum()/Batt.Capacity
            cycle_cal_arr[i]=0
            P_max_arr[i]=P_max
            aux_Cap_arr[i]=aux_Cap
            SOC_max_arr[i]=SOC_max_
            SOH_arr[i]=SOH_aux
            Cycle_aging_factor=0
        results_arr.append(instance.total_cost())
        #if i==0:#initialize
            #df=pd.DataFrame(df_1)
        if i==param['ndays']-1:#if we go until the end of the days
            #df=df.append(df_1,ignore_index=True)
            if SOH<=0:
                break
            if param['ndays']/365>Batt.Battery_cal_life:
                break
        else:#if SOH or ndays are greater than the limit
            df=df.append(df_1,ignore_index=True)
            if SOH<=0:
                #df=df.append(df_1,ignore_index=True)
                end_d=df.shape[0]
                break
            if i/365>Batt.Battery_cal_life:
                #df=df.append(df_1,ignore_index=True)
                break
    [df_1,P_max]=Get_output(instance)
    end_d=df.shape[0]
    df=pd.concat([df,data_input.loc[data_input.index[:end_d],data_input.columns[[0,1,4]]].reset_index()],axis=1)
    if App_comb[2]==1:
        df['price']=data_input.Price_DT.reset_index(drop=True)[:end_d].values
    else:
        df['price']=data_input.Price_flat.reset_index(drop=True)[:end_d].values
    df['Inv_P']=((df.E_PV_load+df.E_dis+df.E_PV_grid+df.E_loss_inv)/dt)
    df['Conv_P']=((df.E_PV_load+df.E_PV_batt+df.E_PV_grid
                  +df.E_loss_conv)/dt)
    df['Req_W']=data_input.Req_W.reset_index(drop=True)[:end_d].values
    df.set_index('index',inplace=True)
    #totaltime=time.clock()-timezero
    return (df,aux_Cap_arr,SOH_arr,Cycle_aging_factor,P_max_arr,results_arr,
            cycle_cal_arr,DoD_arr)

def get_cycle_aging(DoD,Technology):
    '''
    The cycle aging factors are defined for each technology according
	to the DoD using an exponential function close to the Woehler curve.
    Parameters
    ----------
    DoD : float
    Technology : string

    Returns
    -------
    Cycle_aging_factor : float
    '''
    if Technology=='LTO':#Xalt 60Ah LTO Model F920-0006
        Cycle_aging_factor=1/(math.exp((math.log(DoD)-math.log(771.51))/-0.604)-45300)#R2=.9977
    elif Technology=='LFP':#https://doi.org/10.1016/j.apenergy.2013.09.003
        Cycle_aging_factor=1/(math.exp((math.log(DoD)-math.log(70.869))/-0.54)+1961.37135)#R2=.917
    elif Technology=='NCA':#Saft Evolion
        #Cycle_aging_factor=1/(math.exp((math.log(DoD)-math.log(1216.7))/-0.869)-289.736058)#R2=.9675 SAFT
        Cycle_aging_factor=1/(math.exp((math.log(DoD)-math.log(1216.7))/-0.869)+4449.67011)#TRINA BESS
    elif Technology=='NMC':#Tesla Truong et al. 2016
        Cycle_aging_factor=1/(math.exp((math.log(DoD)-math.log(1E8))/-2.168))
    elif Technology=='ALA':#Sacred sun FCP-1000 lead carbon
        Cycle_aging_factor=1/(math.exp((math.log(DoD)-math.log(37403))/-1.306)+330.656417)#R2=.9983
    elif Technology=='VRLA':#Sonnenschein
        Cycle_aging_factor=1/(math.exp((math.log(DoD)-math.log(667.61))/-.988))#R2=0.99995
    elif Technology=='test':
        Cycle_aging_factor=1/(math.exp((math.log(DoD)-math.log(238.86))/-0.875)+4482.74484)#R2=.961
    return Cycle_aging_factor

def aging_day(daily_ESB,SOH,SOC_min,Batt,aux_Cap):
    """"
    A linear relationship between the capacity loss with the maximum battery
    life (years) was chosen. The values of calendric lifetime provide a
    reference value for storage degradation to 70% SOH at 20 °C temperature,
    when no charge throughput is applied [1].

    The temperature is assumed to be controlled and its effect on the battery
    aging minimized. As for the cyclic aging, we use a similar approach as the
    presented by Magnor et al. assuming different Woehler curves for different
    battery technologies [2]. The Woehler curves are provided in the
    specifications for some technologies (e.g. NCA), when the curve is not
    provided, we use other manufacturer curve, which use the same technology
    and adapt it to the referenced number of cycles of the real manufacturer.
    The cyclic agingis then the number of cycles per day at the given DoD,
    divided by the maximum number of cycles at a given DoD.

    [1] H. C. Hesse, R. Martins, P. Musilek, M. Naumann, C. N. Truong, and A.
    Jossen, “Economic Optimization of Component Sizing for Residential
    Battery Storage Systems,” Energies, vol. 10, no. 7, p. 835, Jun. 2017.

    [2]D. U. Sauer, P. Merk, M. Ecker, J. B. Gerschler, and D. Magnor, “Concept
    of a Battery Aging Model for Lithium-Ion Batteries Considering the Lifetime
    Dependency on the Operation Strategy,” 24th Eur. Photovolt. Sol. Energy
    Conf. 21-25 Sept. 2009 Hambg. Ger., pp. 3128–3134, Nov. 2009.

    cycle_cal indicates which aging dominates in the day if 1 cycle is dominating.
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
    #aging is daily
    Cal_aging_factor=1/(Batt.Battery_cal_life*24*365)
    aux_DOD=(Batt.SOC_max-Batt.SOC_min)/Batt.Capacity
    DoD=daily_ESB.sum()/Batt.Capacity
    if DoD==0:
        Cycle_aging_factor=get_cycle_aging(DoD+0.00001,Batt.Technology)
    elif DoD<=1:
        Cycle_aging_factor=get_cycle_aging(DoD,Batt.Technology)
    else:
        aux_DoD=DoD-int(DoD)
        Cycle_aging_factor=get_cycle_aging(aux_DoD,Batt.Technology)
        for i in range(int(DoD)):
            Cycle_aging_factor+=get_cycle_aging(1,Batt.Technology)
    #Linearize SOH in [0,1]
    #SOH=0 if EoL (70% CNom)
    SOH=1/.3*aux_Cap/Batt.Capacity-7/3
    aging=max(Cycle_aging_factor,Cal_aging_factor*24)
    aux_Cap=Batt.Capacity*(1-0.3*(1-SOH+aging))
    if Cycle_aging_factor>(Cal_aging_factor*24):
        cycle_cal=1
    else:
        cycle_cal=0
    SOC_max=Batt.SOC_min+aux_Cap*(aux_DOD)
    return [SOC_max,aux_Cap,SOH,Cycle_aging_factor,cycle_cal,DoD]
def single_opt(param, data_input, Capacity_tariff,PV_nom,name):
    """"
    Iterates over capacities, technologies and applications and calls the module to save the results.
    Parameters
    ----------
    param: dict
    data_input: DataFrame
    Capacity_tariff: float
    PV_nom: float
    name: string

    Returns
    -------
    df : DataFrame
    Cap_arr : array
    SOH : float
    Cycle_aging_factor : float
    P_max : float
    results : float
    cycle_cal_arr :array
    """
    l=0
#    totaltime_tech=np.zeros(len(param['Technologies']))
#    totaltime_app=np.zeros(len(param['App_comb_scenarios']))
#    totaltime_cap=np.zeros(len(param['Capacities']))
#    timezero=time.clock()


    for Tech in param['Technologies']:
        timetech=time.clock()
        k=0
        for App_comb in param['App_comb_scenarios']:
            timeapp=time.clock()
            j=0
            for Capacity in param['Capacities']:
                timecap=time.clock()
                timezeroz=time.clock()

                [df,Cap_arr,SOH,Cycle_aging_factor,P_max,results,
                 cycle_cal_arr,DoD_arr]=Optimize(Capacity,
                                Tech,App_comb,Capacity_tariff,
                                data_input,param,PV_nom)

                save_results(name,df,Tech, App_comb, Capacity,Cap_arr,SOH,
                             Cycle_aging_factor,P_max,results,cycle_cal_arr,
                             PV_nom,DoD_arr)
        #        totaltime=time.clock()-timezeroz
        #        totaltime_cap[j]=time.clock()-timecap
                j+=1
        #    totaltime_app[k]=time.clock()-timeapp
            k+=1
        #totaltime_tech[l]=time.clock()-timetech
        l+=1

    return  [df,Cap_arr,SOH,Cycle_aging_factor,P_max,results,cycle_cal_arr]

def save_results(name,df,Tech, App_comb, Capacity,Cap_arr,SOH,
                 Cycle_aging_factor,P_max,results,cycle_cal_arr,
                 PV_nominal_power,DoD_arr):
    '''
    Save the results in pickle format using the corresponding timezone.
	The file is saved in the same directory the program is saved.
	The name is structured as follows: df_name_tech_App_Cap.pickle
    Parameters
    ----------
    name : string
    df : DataFrame
    Tech : string
    App_comb : array
    Capacity : float
    Cap_arr : array
    SOH : float
    Cycle_aging_factor : float
    P_max :float
    results : array
    cycle_cal_arr : array
    PV_nominal_power : float
    DoD_arr : array

    Returns
    -------
    bool
        True if successful, False otherwise.

    '''

    Capacity_aux=Capacity
    if Capacity%1>0:
        Capacity_aux=str(Capacity).replace('.','_')

    dict_save={'df':df,'Tech':Tech, 'App_comb': App_comb, 'Capacity':Capacity_aux,
    'Cap_arr':Cap_arr,'SOH':SOH,'DoD':DoD_arr,
    'Cycle1_aging0_factor':Cycle_aging_factor,'P_max':P_max,'name':name,
    'results':results,'cycle_cal_arr':cycle_cal_arr,'PV_nom':PV_nominal_power}
    col = ["%i" % x for x in App_comb]
    name_comb=col[0]+col[1]+col[2]+col[3]
    if 'test'in name:
        filename_save=(list(glob.glob('./'))[0]
                        +'df_%(name)s_%(Tech)s_%(App_comb)s_%(Cap)s.pickle'
                        %{'name':name,'Tech':Tech,'App_comb':name_comb,
                        'Cap':Capacity})
        pickle.dump(dict_save,open(filename_save,"wb"),protocol=2)
    else:
        if sys.platform=='win32':
            filename_save=('df_%(name)s_%(Tech)s_%(App_comb)s_%(Cap)s.pickle'
                            %{'name':name,'Tech':Tech,'App_comb':name_comb,
                            'Cap':Capacity})
            df.to_csv('test_out.csv',sep=';')
            print(P_max)
        else:
        		filename_save=('df_%(name)s_%(Tech)s_%(App_comb)s_%(Cap)s.pickle'
                            %{'name':name,'Tech':Tech,'App_comb':name_comb,
                            'Cap':Capacity})
        pickle.dump(dict_save,open(filename_save,"wb"))

    print ('%%%%%%%%%%%% File Saved as %%%%%%%%%%%%%%%%%')
    print(filename_save)
    return()
