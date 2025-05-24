import pandas as pd
import numpy as np
import os
import csv
import matplotlib.pyplot as plt
import math
from main_beers import load_obj
from scipy import optimize
from Core import save_obj

'''We want to size the HP based on the demand and the outdoor temperature. 
The sizing is based on the Appendix A and C of The Reference Framework for 
System Simulations of the IEA SHC Task 44 / HPP Annex 38 Part B: Buildings 
and Space Heat Load. Once the heat pump size is known, the heating system' 
supply and return temperatures for the three types of houses are calculated 
for space heating and domestic hot water. Finally, the COP is calculated for 
the distribution temperature and the output temperature'''

def yearly_temps(times, avg, ampl, time_offset):
    return (avg
            + ampl * np.cos((times + time_offset) * 2 * np.pi / times.max()))


def get_design_temperature_hp(temperature_series,df_power,dict_design):
    """
    Estimate the design ambient temperature and corresponding heat load for heat pump sizing.

    Parameters
    ----------
    temperature_series : pandas.Series
        Hourly ambient temperature data (length 8760).
    df_power : pandas.DataFrame
        Power data indexed or grouped by ambient temperature ('Ts').

    Returns
    -------
    design_temp : float
        The estimated design ambient temperature (°C), based on the 1st percentile of deviations from a sine fit.
    heatload_dt_floor : float
        Estimated heat load (kW) at the design temperature using a linear fit for SFH_radiator.

    Notes
    -----
    The function fits a sinusoidal curve to the yearly temperature profile, calculates the deviation from this fit,
    and determines a conservative design temperature. It then regresses mean power data against temperature and
    estimates the heat load at the design temperature.
    The sizing is based on the Appendix A and C of The Reference Framework for System Simulations of the IEA SHC Task 44 / HPP Annex 38 Part B: Buildings and Space Heat Load. 
    """
    y_data=temperature_series.values
    x_data=np.linspace(0,math.pi,8760)

    opt_results, covariance = optimize.curve_fit(yearly_temps, x_data,
                                        y_data, [20, 10, 0])
    temp_deviation_from_sine_fit=yearly_temps(x_data,*opt_results)-y_data
    conf_int=0.99

    design_temp=np.quantile(temp_deviation_from_sine_fit,1-conf_int)
        
    heat_load_ix=np.arange(-20,20,0.1)
    heat_load=(df_power.groupby(temperature_series).mean())
    heat_load=heat_load.loc[heat_load.index<20]
    z100 = np.polyfit(heat_load.index, heat_load, 1)

    fitradiator=heat_load_ix*z100[0]+z100[1]


    heatload_dt=np.round(design_temp*z100[0]+z100[1],3)
    print('Design Temperature= {} °C'.format(design_temp))

    print('The heat load at design ambient temperature for SFH is:{}'.format(heatload_dt[0]))
    df_sr=pd.DataFrame([heat_load_ix,heat_load_ix*0+20]).T

    dict_design.update({'heatload_dt':heatload_dt[0],'design_temp':design_temp})
    #df_sr=supply_and_return_temps(df_sr,dict_design)


    return design_temp,heatload_dt[0]

def hp_sizing(dict_design,df_hp,flag_heating_floor):
    '''
    Get the HP rating according to the design temperature (in the interval of the input HP data) and the inlet temperature design.
    It returns the HP rating that provides the closest power to the required, if the HP cannot provide the required heat power, a backup 
    heater is required.
    '''
    desig_temp_hp_data=df_hp.T_outside.unique()[find_interval_hp(dict_design['design_temp'],df_hp.T_outside.unique())]
    if flag_heating_floor:
        hp=df_hp.loc[abs(df_hp.loc[(df_hp.T_outside==desig_temp_hp_data)&(df_hp.T_dist==dict_design['T_d_supply_floor'])].P_th-dict_design['heatload_dt']).idxmin(),'HP_rating']
        bu=np.ceil(max(0,dict_design['heatload_dt']-df_hp.loc[(df_hp.HP_rating==hp)&(df_hp.T_outside==desig_temp_hp_data)&(df_hp.T_dist==dict_design['T_d_supply_floor']),'P_th'].values[0]))
    else:
        hp=df_hp.loc[abs(df_hp.loc[(df_hp.T_outside==desig_temp_hp_data)&(df_hp.T_dist==dict_design['T_d_supply_radiator'])].P_th-dict_design['heatload_dt']).idxmin(),'HP_rating']
        bu=np.ceil(max(0,dict_design['heatload_dt']-df_hp.loc[(df_hp.HP_rating==hp)&(df_hp.T_outside==desig_temp_hp_data)&(df_hp.T_dist==dict_design['T_d_supply_radiator']),'P_th'].values[0]))
    dict_design.update({'hp':hp,'buradiator':bu})
    return
def get_COP(df,df_hp,dict_design):
    '''
    Calculates the COP for the three house types as well as the hp consumption (electricity, in kW) according to the HP rating, inlet temperature 
    and ambient temperature
   
    '''
    df['COP_DHW']=df.apply(lambda x: df_hp.loc[(df_hp.HP_rating==dict_design['hp'])&(df_hp.T_dist==55)&(df_hp.T_outside==x.Temp_amb_interval),'COP'].values[0],axis=1)
    df['hp_dhw_cons']=df.apply(lambda x: df_hp.loc[(df_hp.HP_rating==dict_design['hp'])&(df_hp.T_dist==55)&(df_hp.T_outside==x.Temp_amb_interval),'P_el'].values[0],axis=1)


    df['COP_SH']=df.apply(lambda x: df_hp.loc[(df_hp.HP_rating==dict_design['hp'])&(df_hp.T_dist==x.HP_T_SFH_to_use)&(df_hp.T_outside==x.Temp_amb_interval),'COP'].values[0],axis=1)
    
    df['COP_tank']=df.apply(lambda x: df_hp.loc[(df_hp.HP_rating==dict_design['hp'])&(df_hp.T_dist==x.HP_T_SFH_tank_to_use)&(df_hp.T_outside==x.Temp_amb_interval),'COP'].values[0],axis=1)
    
    df['hp_sh_cons']=df.apply(lambda x: df_hp.loc[(df_hp.HP_rating==dict_design['hp'])&(df_hp.T_dist==x.HP_T_SFH_to_use)&(df_hp.T_outside==x.Temp_amb_interval),'P_el'].values[0],axis=1)
    
    df['hp_tank_cons']=df.apply(lambda x: df_hp.loc[(df_hp.HP_rating==dict_design['hp'])&(df_hp.T_dist==x.HP_T_SFH_tank_to_use)&(df_hp.T_outside==x.Temp_amb_interval),'P_el'].values[0],axis=1)
    
    
    return
def find_interval_hp(x, partition):
    '''
    Description
    -----------
    find_interval at which x belongs inside partition. Returns the index i.

    Parameters
    ------
    x: float; numerical value
    partition: array; sequence of numerical values
    Returns
    ------
    i: index; index for which applies
    partition[i] < x < partition[i+1], if such an index exists.
    -1 otherwise
    TODO
    ------
    '''

    for i in range(0, len(partition)):
        if x <= partition[i]:
            return i
    if x >partition[i]:
        return i
    
def supply_temp(df,heatload,design_temp,T_supply,T_return,rad_exp):
    '''
    Description
    ---------
    Determines the inlet temperature according to the The Reference Framework for System Simulations of the IEA SHC Task 44 / HPP Annex 38
Part B: Buildings and Space Heat Load eq 11 pg 13 of 35. For this the ambient temperature, the set temperature and the design temperatures are needed
    Temperatures in Celsius or Kelvin
    Parameters
    ---------
    df: dataframe; includes ambient and set Temp as well as the heat demand for the SFH
    heatload:
    T_supply:
    T_return:
    rad_exp:
    Returns
    ---------
    Temperature of supply (pd.Series)
    '''
    df_sup=df.copy()
    
    df_sup['Q_herf']=np.heaviside(15-df_sup.Temp_mean,0)*heatload*(df_sup.Set_T-df_sup.Temp_mean)/(df_sup.Set_T-design_temp)

    df_sup['delta_t']=0.5*(T_supply+T_return)-df_sup.Set_T

    df_sup['second']=(df_sup.Q_herf/heatload)**(1/rad_exp)*df_sup.delta_t

    df_sup['third']=df_sup.Q_herf/(2*heatload)*(T_supply-T_return)
    return df_sup.Set_T+df_sup.second+df_sup.third

def return_temp(df,heatload,design_temp,T_supply,T_return,rad_exp):
    '''
    Description
    ---------
    Determines the inlet temperature according to the The Reference Framework for System Simulations of the IEA SHC Task 44 / HPP Annex 38
Part B: Buildings and Space Heat Load eq 11 pg 13 of 35. For this the ambient temperature, the set temperature and the design temperatures are needed
    Temperatures in Celsius or Kelvin
    Parameters
    ---------
    df: dataframe; includes ambient and set Temp as well as the heat demand for the SFH
    heatload:
    T_supply:
    T_return:
    rad_exp:
    Returns
    ---------
    Temperature of return (pd.Series)
    '''
    df_sup=df.copy()
    df_sup['second']=(T_supply-T_return)/2*(df_sup.Set_T-df_sup.Temp_mean)/(df.Set_T-design_temp)
    df_sup['third']=((T_supply+T_return)/2-df_sup.Set_T)*((df_sup.Set_T-df_sup.Temp_mean)/(df.Set_T-design_temp))**(1/rad_exp)
    return df_sup.Set_T-df_sup.second+(df_sup.third)*np.heaviside(15-df_sup.Temp_mean,0)


def main():
    '''
    TODO: change the surface by the real surface
    '''
    # input_dir = '../Input'
    input_dir = 'Input'
    print('in sizing')
    test_dict=load_obj(f'{input_dir}/test')
    dict_design={'T_d_supply_floor':35,'T_d_return_floor':30,'T_d_supply_radiator':50,'T_d_return_radiator':40,'T_d_supply_floor_tank':40,
                'T_d_return_floor_tank':35,'T_d_supply_radiator_tank':55,'T_d_return_radiator_tank':45,'rad_exp_floor':1.1,'rad_exp_radiator':1.3}
    df_hp=pd.read_csv(f'{input_dir}/HP_data.csv',sep=';')# Temperature in celcius
    df_hp.loc[:,'P_el']=df_hp.loc[:,'P_el'].str.replace(',','.').astype(float)
    df_hp.loc[:,'COP']=df_hp.loc[:,'COP'].str.replace(',','.').astype(float)
    df_hp['P_th']=df_hp.P_el*df_hp.COP
    for building in test_dict.keys():
        print(building)
        design_temp,heatload_dt=get_design_temperature_hp(pd.DataFrame(test_dict[building]['temperature']).Ts,
                                                                 pd.DataFrame(test_dict[building]['Qs']),
                                                                 dict_design)# Qs resolution is 1 hour power and energy are then interchangeable here
        df_heat=pd.DataFrame([test_dict[building]['Qs'],test_dict[building]['temperature']]).T
        df_heat.columns=['Req_kWh','Temp']
        # Create datetime index for every hour of 2017
        datetime_index = pd.date_range(start='2017-01-01 00:00', end='2017-12-31 23:00', freq='h')

        # Assign to DataFrame
        df_heat.index = datetime_index
        aux=df_heat.groupby(df_heat.index.dayofyear).mean().Temp
        df_heat.loc[(df_heat.index.hour==0)&(df_heat.index.minute==0),'Temp_mean']=aux.values
        df_heat.Temp_mean=df_heat.Temp_mean.ffill().round(1)
        
        width=200
        df_heat.loc[:,'Temp_mean']=df_heat.loc[:,'Temp_mean'].rolling(window=width).mean().bfill()
        df_heat['Set_T']=20
        # here we need to select the T supply and return depending on the kWh/m2
        ############
        surface=350
        ############
        if df_heat.Req_kWh.sum()/surface < 50: 
            flag_heating_floor=True 
        else: 
            flag_heating_floor=False

        if flag_heating_floor:
            df_heat['Temp_supply']=df_heat.apply(lambda x: supply_temp(x,dict_design['heatload_dt'],dict_design['design_temp'],dict_design['T_d_supply_floor'],
                                                            dict_design['T_d_return_floor'],dict_design['rad_exp_floor']),axis=1)

            df_heat['Temp_supply_tank']=df_heat.apply(lambda x: supply_temp(x,dict_design['heatload_dt'],dict_design['design_temp'],dict_design['T_d_supply_floor_tank'],
                                                            dict_design['T_d_return_floor_tank'],dict_design['rad_exp_floor']),axis=1)
        else:
            df_heat['Temp_supply']=df_heat.apply(lambda x: supply_temp(x,dict_design['heatload_dt'],dict_design['design_temp'],dict_design['T_d_supply_radiator'],
                                                            dict_design['T_d_return_radiator'],dict_design['rad_exp_radiator']),axis=1)

            df_heat['Temp_supply_tank']=df_heat.apply(lambda x: supply_temp(x,dict_design['heatload_dt'],dict_design['design_temp'],dict_design['T_d_supply_radiator_tank'],
                                                            dict_design['T_d_return_radiator_tank'],dict_design['rad_exp_radiator']),axis=1)
            
        df_heat['HP_T_SFH_to_use']=df_heat.apply(lambda x: df_hp.T_dist.unique()[find_interval_hp(x.Temp_supply,df_hp.T_dist.unique())],axis=1)
        df_heat['HP_T_SFH_tank_to_use']=df_heat.apply(lambda x: df_hp.T_dist.unique()[find_interval_hp(x.Temp_supply_tank,df_hp.T_dist.unique())],axis=1)
        df_heat['Temp_amb_interval']=df_heat.apply(lambda x: df_hp.T_outside.unique()[find_interval_hp(x.Temp,df_hp.T_outside.unique())],axis=1)
        # here we need to select the T supply and return depending on the kWh/m2
        hp_sizing(dict_design,df_hp,flag_heating_floor)

        get_COP(df_heat,df_hp,dict_design)
        
        
        df_heat = df_heat[['Set_T', 'Temp', 'Req_kWh', 'Temp_supply',
                        'Temp_supply_tank', 'COP_SH', 'COP_tank', 'COP_DHW',
                        'hp_sh_cons', 'hp_tank_cons', 'hp_dhw_cons']]
        test_dict[building]['df_heat']=df_heat
        test_dict[building]['dict_design']=dict_design

        print(df_heat.head())

    save_obj(test_dict,'Test_floor')#it is saving in Output/Test


if __name__ == '__main__':
    main()
        