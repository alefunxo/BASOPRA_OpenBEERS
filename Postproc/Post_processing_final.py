# -*- coding: utf-8 -*-
## @namespace Post_processing_final
# Created on Wed Feb 28 09:47:22 2018
# Author
# Alejandro Pena-Bello
# alejandro.penabello@unige.ch
# Main script used to calculate the techno-indicators for the paper Optimization of PV-coupled battery systems for combining applications: impact of battery technology and location (Pena-Bello et al 2018 to be published).
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
# Pandas, numpy, itertools,sys,glob,multiprocessing, time
import sys,os
import numpy as np
import pandas as pd
import paper_classes_2 as pc
import matplotlib.pyplot as plt

title_size=20
large_size=18
normal_size=16
medium_size=14
small_size=12
project_life=15
def get_lifetime(row):
    '''
    Description
    -----------
    This function calculates the lifetime of every row of the dataframe

    Inputs
    ----------
    row : dataframe row; includes at least battery Capacity and Technology

    Returns
    ------
    lifetime in years: int

    '''
    Batt=pc.Battery(row.loc['Capacity'],row['Tech'])
    m=(row.Capacity-row.last_cap)/(0-365)
    x=(row.Capacity*0.7-row.Capacity)/m

    #investment=get_investment(row,Batt)
    return [min(int(x/365+1),Batt.Battery_cal_life)]

def get_replacements(investment,row,Batt,project_life,percentage_cost):
    '''
    Description
    -----------
    This function calculates if replacements are needed

    Inputs
    ----------
    investment: float; CAPEX
    row : dataframe row; includes at least battery Capacity and Technology
    Batt: Battery class; Class includes battery characteristics
    project_life: int; project lifetime
    percentage_cost: float; reduction on the installed cost of the system

    Returns
    ------
    investment: float; amount to be invested if replacements are needed
    rep: int; amount of times the battery need to be replaced

    '''
    rep=int(np.ceil(project_life/row.life))-1

    for i in range(rep):
        future_batt=Batt.Price_battery*percentage_cost/(1+.04)**(row.life*(i+1))
        investment=investment+future_batt

        if (i==rep-1)&(project_life>row.life*rep):
            investment=investment-((future_batt*percentage_cost)/(1+.04)**(row.life*(i+1))/row.life*(
                project_life-row.life*(rep+1)))

    return [investment,rep]

def get_investment(row,Batt,project_life,percentage_cost,PV):
    '''
    Description
    -----------
    This function calculates the investment (CAPEX) given the project lifetime and kind of battery. Takes into account installation cost (2000 USD), battery price, BoS (100 USD) and inverter discounting the required cost of PV inverter if it was installed alone (190 USD).

    Inputs
    ----------
    row : dataframe row; includes at least battery Capacity and Technology
    Batt: Battery class; Class includes battery characteristics
    project_life: int; project lifetime
    percentage_cost: float; reduction on the installed cost of the system
    PV: fload; PV size needed to calculate the inverter (1.2 ILR)
    Returns
    ------
    investment: float; amount to be invested, includes replacements if needed
    '''

    investment=percentage_cost*(2000+Batt.Price_battery+(
        100+(600-190)/1.2)*PV[
                (PV.country==row.country)&
                 (PV.quartile==row.quartile)].PV.values[0])

    [investment,batt_rep]=get_replacements(investment,row,Batt,
                                       project_life,percentage_cost)
    return [investment,batt_rep]
def get_future_dis(E_dis,life,project_life):
    '''
    Description
    -----------
    This function calculates projected energy discharged from the battery taking into account the life of the project. Takes a 2% reduction of the total energy discharged per year, this is the average for the first year for all batteries.

    Inputs
    ----------
    E_dis : float; Energy discharged in the first year
    life: Battery life; lifetime of the battery calculated in get_lifetime
    project_life: int; project lifetime

    Returns
    ------
    E_dis_array: array; Array with the energy discharged in the whole project
    '''

    E_dis_array=[]
    for i in range(int(life)):
        if i==0:
            E_dis_array.append(E_dis)
        else:
            E_dis_array.append(E_dis_array[i-1]*(1-0.002))
    if project_life>life:
        E_dis_array=np.tile(np.array(E_dis_array),int(np.ceil(project_life/life)))
    E_dis_array=E_dis_array[:project_life]

    return np.array(E_dis_array)

def get_future_diff(val,life,project_life):
    '''
    Description
    -----------
    This function calculates the projected revenue that steams from the battery only (difference between the revenue the user would made if had only a PV and the revenue the user makes when have a PV-coupled battery system).

    Inputs
    ----------
    val : float; Difference between the revenue the user would made if had only a PV and the revenue the user makes when have a PV-coupled battery system
    life: Battery life; lifetime of the battery calculated in get_lifetime
    project_life: int; project lifetime

    Returns
    ------
    val_array: array; Array with the projected revenue from the battery in the whole project lifetime
    '''
    val_array=[]
    for i in range(int(life)):
        if i==0:
            val_array.append(val)
        else:
            val_array.append(val_array[i-1]*(1-0.000))
    if project_life>life:
        val_array=np.tile(np.array(val_array),int(np.ceil(project_life/life)))
    val_array=val_array[:project_life]

    return np.array(val_array)

def get_LCOES(row,project_life,percentage_cost,PV):
    '''
    Description
    -----------
    This function calculates the LCOES with a 4% discount rate

    Inputs
    ----------
    row : dataframe row; includes at least battery Capacity and Technology
    project_life: int; project lifetime
    percentage_cost: float; reduction on the installed cost of the system
    PV: fload; PV size needed to calculate the inverter (1.2 ILR)

    Returns
    ------
    LCOES: float; Levelized cost of energy storage
    investment: float; amount to be invested, includes replacements if needed

    '''
    Batt=pc.Battery(row.Capacity,row.Tech)
    [investment,na]=get_investment(row,Batt,project_life,percentage_cost,PV)
    E_dis_pres=np.npv(0.04,get_future_dis(row.E_dis,row.life,project_life))
    return [investment/E_dis_pres,investment]

def get_LVOES(row,project_life):
    '''
    Description
    -----------
    This function calculates the LVOES with a 4% discount rate

    Inputs
    ----------
    row : dataframe row; includes at least battery Capacity and Technology
    project_life: int; project lifetime

    Returns
    ------
    LVOES: float; Levelized value of energy storage

    '''
    CF_pres=np.npv(0.04,get_future_diff(row.results_PV-row.results_PVbatt,
                                        row.life,project_life))

    E_dis_pres=np.npv(0.04,get_future_dis(row.E_dis,row.life,project_life))

    return CF_pres/E_dis_pres

def get_NPV(row,project_life):
    '''
    Description
    -----------
    This function calculates the NPV with a 4% discount rate

    Inputs
    ----------
    row : dataframe row; includes at least battery Capacity and Technology
    project_life: int; project lifetime

    Returns
    ------
    NPV: float; Net present value

    '''
    aux=get_future_diff(row.results_PV-row.results_PVbatt,row.life,project_life)
    aux=np.insert(aux,0,-row.investment)
    appr=np.npv(0.04,aux)
    return appr

def func(row):
    '''
    Description
    -----------
    This function assigns a qualitative cluster depending on the number of cluster

    Inputs
    ----------
    row : dataframe row; includes at least battery Capacity and Technology

    Returns
    ------
    string: string; either high, medium or low

    '''
    if row.cluster<=3:
        return 'clow'
    elif row.cluster>=8:
        return 'ahigh'
    else:
        return 'bmedium'
def calculate_indicators(dfa,PV):
    '''
    Description
    -----------
    This function calculates the techno-economic indicators

    Inputs
    ----------
    dfa : dataframe; Aggregated results
    PV: float; PV size

    Returns
    ------
    dfa: dataframe; Aggregated results with indicators

    '''
    dfa['life']=dfa.apply(lambda x: get_lifetime(x)[0],axis=1)
    percentage_cost=1
    dfa['investment']=dfa.apply(lambda x: get_LCOES(x,project_life,percentage_cost,PV)[1],axis=1)
    dfa['LCOES']=dfa.apply(lambda x: get_LCOES(x,project_life,percentage_cost,PV)[0],axis=1)
    dfa['LVOES']=dfa.apply(lambda x: get_LVOES(x,project_life),axis=1)
    dfa['NPV']=dfa.apply(lambda x: get_NPV(x,project_life),axis=1)
    dfa['cons']=dfa.apply(lambda x: func(x),axis=1)
    dfa=dfa.round(2)
    return(dfa)


def main():
    '''
    Description
    -----------
    This function calculates the techno-economic indicators based on aggregated results for the paper Optimization of PV-coupled battery systems for combining applications: impact of battery technology and location. Pena-Bello et al. (2019)

    '''
    print("########################################################")
    print("Post processing Paper Optimization of PV-coupled battery systems for combining applications: impact of battery technology and location. Pena-Bello et al. (2019)")
    print("########################################################")
    dfa=pd.read_pickle('aggregated_results_LS_6 (copy).pkl')#aggregated

    dfa.cluster=dfa.cluster.astype(int)

    PV=[{'PV':3.2,'quartile':25,'country':'US'},
            {'PV':5,'quartile':50,'country':'US'},
            {'PV':6.4,'quartile':75,'country':'US'},
            {'PV':3.2,'quartile':25,'country':'CH'},
            {'PV':4.8,'quartile':50,'country':'CH'},
            {'PV':6.9,'quartile':75,'country':'CH'}]
    PV=pd.DataFrame(PV)
    print("########################################################")
    print("Calculating the techno-economic indicators")
    print("########################################################")
    dfa=calculate_indicators(dfa,PV)
    dfa.to_pickle('dfa_V2.pickle')
    print("End calculation")
    print("########################################################")
    print(dfa)
if __name__== '__main__':
    main()
