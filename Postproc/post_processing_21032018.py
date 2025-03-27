#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar 21 11:34:12 2018

@author: alejandro




"""
#os.chdir('C:/Users/alejandro/Dropbox/0. PhD/Python/Paper1_last')

import os
import pandas as pd
import numpy as np
import itertools
import paper_classes_2 as pc
def get_table_inputs():
    path='C:/Users/alejandro/Documents/Data/Output'
    os.listdir(path)
    household=[]
    country=[]
    for file in os.listdir(path):
        household.append(file.split('_')[1])
        country.append(file.split('_')[2])
    country=np.unique(np.array(country))
    hh=np.unique(np.array(household))
    hh_US=[i for i in hh if len(i)<5]
    hh_CH=[i for i in hh if len(i)>5]
    path='C:/Users/alejandro/Dropbox/Alejandro_David_Ed/FinalData'
    cluster_CH=pd.read_pickle(path+'/Clusters_CH.pickle')
    cluster_US=pd.read_pickle(path+'/Clusters_PS.pickle')
    dict_CH=[]
    dict_US=[]
    for j in range(12):
        for i in range (12):
            if hh_CH[j] in cluster_CH['data'].columns.values[np.where(cluster_CH['finalClusters']==i)[0]]:
                dict_CH.append({'hh':hh_CH[j],'cluster':i,'country':'CH'})
            if hh_US[j] in cluster_US['data'].columns.values[np.where(cluster_US['finalClusters']==i)[0]]:
                dict_US.append({'hh':hh_US[j],'cluster':i,'country':'US'})
    dict_CH=pd.DataFrame(sorted(dict_CH, key=lambda st: st['cluster']))
    dict_US=pd.DataFrame(sorted(dict_US, key=lambda st: st['cluster']))
    clusters=dict_CH.append(dict_US, ignore_index=True)
    clusters=clusters.apply(pd.to_numeric, errors='ignore')
    clusters.country=clusters.country.astype(str)
    PV=[{'PV':3.2,'quartile':25,'country':'US'},
        {'PV':5,'quartile':50,'country':'US'},
        {'PV':6.4,'quartile':75,'country':'US'},
        {'PV':3.2,'quartile':25,'country':'CH'},
        {'PV':4.8,'quartile':50,'country':'CH'},
        {'PV':6.9,'quartile':75,'country':'CH'}]
    PV=pd.DataFrame(PV)
    App_comb_scenarios=np.array([i for i in itertools.product([0, 1],
                        repeat=3)])
    App_comb_scenarios=np.insert(App_comb_scenarios,1,1,axis=1)
    App_comb=pd.DataFrame(App_comb_scenarios)
    App_comb=App_comb[0].map(str)+' '+App_comb[1].map(str)+' '+App_comb[2].map(
                    str)+' '+App_comb[3].map(str)
    App_comb=App_comb.reset_index()
    App_comb=App_comb.rename(columns={'index':'App_index',0:'App_comb'})

    return[clusters,PV,App_comb]

def get_base_prices(country,App_comb,PV_nom,df_base):
    curtailment=0.5
    dt=0.25
    if country=='US':
        Capacity_tariff=10.14*12/365
    else:
        Capacity_tariff=9.39*12/365
    df_base['rem_load']=(df_base.loc[:,'E_Demand']-df_base.loc[:,'E_PV'])
    df_base['surplus']=-df_base['rem_load']
    df_base.rem_load[df_base.rem_load<0]=0
    df_base.surplus[df_base.surplus<0]=0
    df_base['curt']=df_base.E_PV*0
    bill_power=0
    bill_power_PV=0

    if App_comb[0]:
        df_base.curt[df_base.surplus>PV_nom*curtailment*dt]=df_base.surplus[df_base.surplus>PV_nom*curtailment*dt]-PV_nom*curtailment*dt
        df_base.curt[df_base.curt<0]=0
    if App_comb[3]:
	#Using P_max_day:
        P_max_day_PV=df_base.groupby([df_base.index.month, df_base.index.day]).rem_load.max()*4
        bill_power_PV=P_max_day_PV*Capacity_tariff
        P_max_day=df_base.groupby([df_base.index.month, df_base.index.day]).E_Demand.max()*4
        bill_power=P_max_day*Capacity_tariff

    bill_energy_min_PV=df_base.rem_load*df_base.price
    bill_energy_day_PV=bill_energy_min_PV.groupby([df_base.index.month, df_base.index.day]).sum()

    bill_energy_min=df_base.E_Demand*df_base.price
    bill_energy_day=bill_energy_min.groupby([df_base.index.month, df_base.index.day]).sum()

    exported_energy=(df_base.surplus-df_base.curt)*df_base.Export_price
    exported_energy_day=exported_energy.groupby([df_base.index.month, df_base.index.day]).sum()
    bill_PV=bill_energy_day_PV+bill_power_PV-exported_energy_day
    bill=bill_energy_day+bill_power


    return [bill,bill_PV]

def get_main_results(dict_res,clusters,PV,App):
    """
    We are interested on some results such as
    %SC
    %DSC
    %BS
    EFC

    LCOES->E_dis and CF
    LVOES
    NPV

    We need to know the lifespan (this will be the tricky part)
    We want to know %PS,%LS,%CU,%PVSC ideally per month.
    we can do two different tables, one with the aggregated results
    (i.e. sums, max, min, means) and another one with monthly results
    """
    df=dict_res['df']
    App=App.App_index[App.App_comb==str(
                            dict_res['App_comb'])[1:-1]].values[0]
    df=df.apply(pd.to_numeric, errors='ignore')

    agg_results=df.sum()
    agg_results=agg_results.drop(['SOC','Inv_P','Conv_P','price',
                                  'Export_price'])
    agg_results['SOC_mean']=df['SOC'].mean()/dict_res['Capacity']*100
    agg_results['SOC_max']=df['SOC'].max()/dict_res['Capacity']*100
    agg_results['SOC_min']=df['SOC'].min()/dict_res['Capacity']*100
    agg_results['DoD_mean']=dict_res['DoD'].mean()*100
    agg_results['DoD_max']=dict_res['DoD'].max()*100
    agg_results['DoD_min']=dict_res['DoD'].min()*100
    agg_results['DoD_min']=dict_res['DoD'].min()*100
    agg_results['last_cap']=dict_res['Cap_arr'][-1]
    agg_results['cap_fading']=(1-dict_res['Cap_arr'][-1]/
               dict_res['Capacity'])*100

    agg_results['last_SOH']=dict_res['SOH'][-1]
    agg_results['P_max_year_batt']=dict_res['P_max'].max()
    agg_results['P_max_year_nbatt']=df['E_Demand'].max()*4

    agg_results['Capacity']=dict_res['Capacity']
    agg_results['App_comb']=App
    agg_results['Tech']=dict_res['Tech']
    agg_results['PV_nom']=dict_res['PV_nom']
    agg_results['cluster']=clusters[clusters.hh==int(
            dict_res['name'].split('_')[0])].cluster.values[0]
    agg_results['country']=dict_res['name'].split('_')[1]
    agg_results['quartile']=PV[(PV.PV==dict_res['PV_nom'])&
               (PV.country==dict_res['name'].split('_')[1])].quartile.values[0]
    df_base=df.loc[:,df.columns[16:20]]
    [base_bill,base_bill_PV]=get_base_prices(dict_res['name'].split('_')[1],
                              dict_res['App_comb'],dict_res['PV_nom'],df_base)

    agg_results['results_PVbatt']=sum(dict_res['results'])
    agg_results['results_PV']=base_bill_PV.sum()
    agg_results['results']=base_bill.sum()

    sum_results=df.groupby([df.index.month]).sum().reset_index(drop=True)
    month_results=sum_results.loc[:,['E_PV_grid', 'E_PV_load', 'E_PV_batt',
                                     'E_PV_curt', 'E_grid_load','E_grid_batt',
                                     'E_cons', 'E_char', 'E_dis','E_PV',
                                     'E_Demand']]
    if dict_res['name'].split('_')[1]=='CH':
        date=pd.DatetimeIndex(start='2015-01-01 00:00:00',
          end='2015-12-31 23:50:00',freq='1d',tz='Europe/Brussels')
    else:
        date=pd.DatetimeIndex(start='2015-01-01 00:00:00',
          end='2015-12-31 23:50:00',freq='1d',tz='US/Central')
    aux=pd.DataFrame(np.vstack((dict_res['results'],dict_res['P_max'],
                            dict_res['DoD'],dict_res['cycle_cal_arr'])).T,
                            columns=['results_PVbatt','P_max','DoD',
                            'cycle_cal_arr']).set_index(date)

    month_results['results_PVbatt']=aux.groupby(
            aux.index.month).sum().results_PVbatt.reset_index(drop=True)
    month_results['results_PV']=base_bill_PV.groupby(
            level=[0]).sum().reset_index(drop=True)
    month_results['results']=base_bill.groupby(
            level=[0]).sum().reset_index(drop=True)
    month_results['P_max_nobatt']=df.E_Demand.groupby(
            df.index.month).max().reset_index(drop=True)*4
    month_results['P_max']=aux.groupby(
            aux.index.month).max().P_max.reset_index(drop=True)
    month_results['DoD_mean']=aux.groupby(
            aux.index.month).mean().P_max.reset_index(drop=True)
    month_results['DoD_max']=aux.groupby(
            aux.index.month).max().DoD.reset_index(drop=True)
    month_results['DoD_min']=aux.groupby(
            aux.index.month).min().DoD.reset_index(drop=True)
    month_results['SOC_mean']=df.groupby(
            df.index.month).mean().SOC.reset_index(drop=True)/dict_res['Capacity']*100
    month_results['SOC_max']=df.groupby(
            df.index.month).max().SOC.reset_index(drop=True)/dict_res['Capacity']*100
    month_results['SOC_min']=df.groupby(
            df.index.month).min().SOC.reset_index(drop=True)/dict_res['Capacity']*100
    month_results['cycle_cal_arr']=aux.groupby(
            aux.index.month).sum().cycle_cal_arr.reset_index(drop=True)

    month_results['Capacity']=np.tile(dict_res['Capacity'],reps=12)
    month_results['App_comb']=np.tile(App,reps=12)
    month_results['Tech']=np.tile(dict_res['Tech'],reps=12)
    month_results['PV_nom']=np.tile(dict_res['PV_nom'],reps=12)
    month_results['cluster']=np.tile(clusters[clusters.hh==int(
            dict_res['name'].split('_')[0])].cluster.values[0],reps=12)
    month_results['country']=np.tile(dict_res['name'].split('_')[1],reps=12)
    month_results['quartile']=np.tile(PV[(PV.PV==dict_res['PV_nom'])&
               (PV.country==dict_res['name'].split('_')[1])].quartile.values[0],reps=12)
    month_results['month']=np.arange(12)
    month_results['TSC']=(month_results.E_PV_load+month_results.E_PV_batt)/month_results.E_PV*100#[%]
    month_results['DSC']=(month_results.E_PV_load)/month_results.E_PV*100#[%]
    month_results['ISC']=(month_results.E_PV_batt)/month_results.E_PV*100#[%]
    month_results['CU']=(month_results.E_PV_curt)/month_results.E_PV*100#[%]
    month_results['PS']=(month_results.P_max-month_results.P_max_nobatt)/month_results.P_max_nobatt*100#[%]
    month_results['BS']=(month_results.E_dis)/month_results.E_Demand*100#[%]
    month_results['EFC_nolifetime']=(month_results.E_dis)/dict_res['Capacity']
    agg_results['EFC_nolifetime']=(agg_results.E_dis)/dict_res['Capacity']
    if (App==0) or (App==1) or (App==4) or (App==5):
        month_results['LS']=np.tile(0,reps=12)
        agg_results['LS']=0
    else:

        if dict_res['name'].split('_')[1]=='US':
            cons=df.E_cons[df.price==df.price.max()].groupby(
                    df.E_cons[df.price==df.price.max()].index.month).sum()
            cons.index=cons.index-1
            rem=df.E_Demand[df.price==df.price.max()].groupby(
                    df.E_Demand[df.price==df.price.max()].index.month).sum()
            rem.index=rem.index-1
        else:
            cons=df.E_cons[df.price==df.price.max()].groupby(
                    df.E_cons[df.price==df.price.max()].index.month).sum().reset_index(drop=True)
            rem=df.E_Demand[df.price==df.price.max()].groupby(
                    df.E_Demand[df.price==df.price.max()].index.month).sum().reset_index(drop=True)
        month_results['LS']=(1-cons/rem)*100
        agg_results['LS']=(1-cons.sum()/rem.sum())*100
    agg_results['TSC']=(agg_results.E_PV_load+agg_results.E_PV_batt)/agg_results.E_PV*100#[%]
    agg_results['DSC']=(agg_results.E_PV_load)/agg_results.E_PV*100#[%]
    agg_results['ISC']=(agg_results.E_PV_batt)/agg_results.E_PV*100#[%]
    agg_results['CU']=(agg_results.E_PV_curt)/agg_results.E_PV*100#[%]
    if (App==0) or (App==2) or (App==4) or (App==6):
        agg_results['PS_mean']=0
        agg_results['PS_year']=0
    else:
        agg_results['PS_mean']=month_results['PS'].mean()
        agg_results['PS_year']=(agg_results['P_max_year_batt']-agg_results[
                    'P_max_year_nbatt'])/agg_results['P_max_year_nbatt']*100

    agg_results['BS']=(agg_results.E_dis)/agg_results.E_Demand*100#[%]


    return[agg_results,month_results]

def main():
    import time
    timezero=time.clock()

    [clusters,PV,App]=get_table_inputs()
    aggregated=pd.DataFrame()
    monthly=pd.DataFrame()
    path="C:/Users/alejandro/Documents/Data/Output/"
    j=0
    for file in os.listdir(path):
        dict_res=pd.read_pickle(path+file)
        [agg_results,month_results]=get_main_results(dict_res,clusters,PV,App)
        aggregated=aggregated.append(agg_results,ignore_index=True)
        monthly=monthly.append(month_results,ignore_index=True)
        print(j)
        j+=1
    stop=time.clock()-timezero
    print(stop)



    aggregated.to_pickle('aggregated_results_LS_4.pickle')
    monthly.to_pickle('monthly_results_LS_4.pickle')

if __name__== '__main__':
    main()
