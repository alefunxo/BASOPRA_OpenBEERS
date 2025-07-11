import pickle
import sys
import os
from config.loader import config
from dataclasses import dataclass
from utils.logger import logger
from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np
import math
from scipy import optimize
from utils.multiprocessing_utils import run_parallel

hp_config = config.heat_pump

'''We want to size the HP based on the demand and the outdoor temperature. 
The sizing is based on the Appendix A and C of The Reference Framework for 
System Simulations of the IEA SHC Task 44 / HPP Annex 38 Part B: Buildings 
and Space Heat Load. Once the heat pump size is known, the heating system' 
supply and return temperatures for the three types of houses are calculated 
for space heating and domestic hot water. Finally, the COP is calculated for 
the distribution temperature and the output temperature'''

@dataclass
class HeatPumpDesign:
    series: pd.DataFrame
    attributes: Dict

def save_obj(obj, name):
    output_dir = 'Output/'
    os.makedirs(output_dir, exist_ok=True)
    with open(f'{output_dir}{name}.pkl', 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)
    logger.info("Object saved as %s.pkl", name)

def yearly_temps(times, avg, ampl, time_offset):
    return (avg
            + ampl * np.cos((times + time_offset) * 2 * np.pi / times.max()))


def get_design_temperature_hp(df_temperature, df_power, dict_design):
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
    temperature_series = df_temperature['Ts']
    y_data=temperature_series.values
    x_data=np.linspace(0,math.pi,8760)

    opt_results, covariance = optimize.curve_fit(
        yearly_temps, 
        x_data,
        y_data, 
        [20, 10, 0],
    )
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

    return df_sup.Set_T + df_sup.second + df_sup.third


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

def calculate_one_heat_pump_size(
    building_id: int,
    building_data: Dict[str, Any],
    heat_pumps_df: pd.DataFrame,
) -> Optional[HeatPumpDesign]:
    logger.info(f"Starting dimensioning of heat pump for building: {building_id}")
    # TODO Allow no heat pump to exist as a case
    # if  not building_data['attributes']['has_HP']:
    #     return None
    dict_design = hp_config.dict_design
    b_Ts = building_data['series']['Ts']
    b_Qs = building_data['series']['Qs']
    design_temp, heatload_dt=get_design_temperature_hp(
        pd.DataFrame(b_Ts),
        pd.DataFrame(b_Qs),
        dict_design,
    )  # Qs resolution is 1 hour power and energy are then interchangeable here
    df_heat=pd.DataFrame([b_Qs,b_Ts]).T
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
    surface = building_data['attributes']['habitable_surface']
    ############
    if df_heat.Req_kWh.sum()/surface < 50: 
        flag_heating_floor=True 
    else: 
        flag_heating_floor=False

    if flag_heating_floor:
        df_heat['Temp_supply'] = df_heat.apply(
            lambda x: supply_temp(
                x,
                dict_design['heatload_dt'],
                dict_design['design_temp'],
                dict_design['T_d_supply_floor'],
                dict_design['T_d_return_floor'],
                dict_design['rad_exp_floor']
            ),
            axis=1,
        )

        df_heat['Temp_supply_tank'] = df_heat.apply(
            lambda x: supply_temp(
                x,
                dict_design['heatload_dt'],
                dict_design['design_temp'],
                dict_design['T_d_supply_floor_tank'],
                dict_design['T_d_return_floor_tank'],
                dict_design['rad_exp_floor'],
            ),
            axis=1,
        )
    else:
        df_heat['Temp_supply'] = df_heat.apply(
            lambda x: supply_temp(
                x,
                dict_design['heatload_dt'],
                dict_design['design_temp'],
                dict_design['T_d_supply_radiator'],
                dict_design['T_d_return_radiator'],
                dict_design['rad_exp_radiator'],
            ),
            axis=1,
        )

        df_heat['Temp_supply_tank'] = df_heat.apply(
            lambda x: supply_temp(
                x,
                dict_design['heatload_dt'],
                dict_design['design_temp'],
                dict_design['T_d_supply_radiator_tank'],
                dict_design['T_d_return_radiator_tank'],
                dict_design['rad_exp_radiator'],
            ),
            axis=1,
        )
        
    df_heat['HP_T_SFH_to_use'] = df_heat.apply(lambda x: heat_pumps_df.T_dist.unique()[find_interval_hp(x.Temp_supply,heat_pumps_df.T_dist.unique())],axis=1)
    df_heat['HP_T_SFH_tank_to_use'] = df_heat.apply(lambda x: heat_pumps_df.T_dist.unique()[find_interval_hp(x.Temp_supply_tank,heat_pumps_df.T_dist.unique())],axis=1)
    df_heat['Temp_amb_interval'] = df_heat.apply(lambda x: heat_pumps_df.T_outside.unique()[find_interval_hp(x.Temp,heat_pumps_df.T_outside.unique())],axis=1)
    # here we need to select the T supply and return depending on the kWh/m2
    hp_sizing(dict_design,heat_pumps_df,flag_heating_floor)

    get_COP(df_heat,heat_pumps_df,dict_design)
    
    
    df_heat = df_heat[['Set_T', 'Temp', 'Req_kWh', 'Temp_supply',
                    'Temp_supply_tank', 'COP_SH', 'COP_tank', 'COP_DHW',
                    'hp_sh_cons', 'hp_tank_cons', 'hp_dhw_cons']]
    heat_pump = HeatPumpDesign(
        series=df_heat,
        attributes=dict_design,
    )
    return heat_pump
    building_data['heat_pump']=heat_pump

def wrapper(args):
    return calculate_one_heat_pump_size(*args)

def calculate_heat_pump_size(
    heat_pump_data_file: str,
    building_data: List[int],
):
    logger.info('Started Heat Pump Sizing Procedure')
    # test_dict=load_obj(f'{input_dir}/test')
    # dict_design = config['dict_design']

    df_hp=pd.read_csv(heat_pump_data_file,sep=';')  # Temperature in celcius
    df_hp.loc[:,'P_el']=df_hp.loc[:,'P_el'].str.replace(',','.').astype(float)
    df_hp.loc[:,'COP']=df_hp.loc[:,'COP'].str.replace(',','.').astype(float)
    df_hp['P_th']=df_hp.P_el*df_hp.COP

    sizing_inputs = [
        {
            'building_id': bid, 
            'building_data': building_data[bid], 
            'heat_pumps_df': df_hp,
        } 
        for bid in building_data.keys()
    ]

    results = run_parallel(
        calculate_one_heat_pump_size,
        sizing_inputs,
        config.multiprocessing,
        processes=config.max_processes,
        mode='kwargs',
    )
    # if hp_config.multiprocessing:
    #     mp.freeze_support()
    #     mp.set_start_method("spawn")
    #     with mp.Pool(processes=hp_config.max_processes) as pool:
    #         results = pool.map(wrapper, sizing_inputs)
    # else:
    #     results = [wrapper(hp_input) for hp_input in sizing_inputs]
    
    for i in range(len(sizing_inputs)):
        bid = sizing_inputs[i]['building_id']
        building_data[bid]['heat_pump'] = results[i]

    # for building in building_data.keys():
    #     b_Ts = building_data[building]['series']['Ts']
    #     b_Qs = building_data[building]['series']['Qs']
    #     design_temp, heatload_dt=get_design_temperature_hp(
    #         pd.DataFrame(b_Ts),
    #         pd.DataFrame(b_Qs),
    #         dict_design,
    #     )  # Qs resolution is 1 hour power and energy are then interchangeable here
    #     df_heat=pd.DataFrame([b_Qs,b_Ts]).T
    #     df_heat.columns=['Req_kWh','Temp']
    #     # Create datetime index for every hour of 2017
    #     datetime_index = pd.date_range(start='2017-01-01 00:00', end='2017-12-31 23:00', freq='h')

    #     # Assign to DataFrame
    #     df_heat.index = datetime_index
    #     aux=df_heat.groupby(df_heat.index.dayofyear).mean().Temp
    #     df_heat.loc[(df_heat.index.hour==0)&(df_heat.index.minute==0),'Temp_mean']=aux.values
    #     df_heat.Temp_mean=df_heat.Temp_mean.ffill().round(1)
    #     
    #     width=200
    #     df_heat.loc[:,'Temp_mean']=df_heat.loc[:,'Temp_mean'].rolling(window=width).mean().bfill()
    #     df_heat['Set_T']=20
    #     # here we need to select the T supply and return depending on the kWh/m2
    #     ############
    #     surface = building_data[building]['attributes']['habitable_surface']
    #     ############
    #     if df_heat.Req_kWh.sum()/surface < 50: 
    #         flag_heating_floor=True 
    #     else: 
    #         flag_heating_floor=False

    #     if flag_heating_floor:
    #         df_heat['Temp_supply'] = df_heat.apply(
    #             lambda x: supply_temp(
    #                 x,
    #                 dict_design['heatload_dt'],
    #                 dict_design['design_temp'],
    #                 dict_design['T_d_supply_floor'],
    #                 dict_design['T_d_return_floor'],
    #                 dict_design['rad_exp_floor']
    #             ),
    #             axis=1,
    #         )

    #         df_heat['Temp_supply_tank'] = df_heat.apply(
    #             lambda x: supply_temp(
    #                 x,
    #                 dict_design['heatload_dt'],
    #                 dict_design['design_temp'],
    #                 dict_design['T_d_supply_floor_tank'],
    #                 dict_design['T_d_return_floor_tank'],
    #                 dict_design['rad_exp_floor'],
    #             ),
    #             axis=1,
    #         )
    #     else:
    #         df_heat['Temp_supply'] = df_heat.apply(
    #             lambda x: supply_temp(
    #                 x,
    #                 dict_design['heatload_dt'],
    #                 dict_design['design_temp'],
    #                 dict_design['T_d_supply_radiator'],
    #                 dict_design['T_d_return_radiator'],
    #                 dict_design['rad_exp_radiator'],
    #             ),
    #             axis=1,
    #         )

    #         df_heat['Temp_supply_tank'] = df_heat.apply(
    #             lambda x: supply_temp(
    #                 x,
    #                 dict_design['heatload_dt'],
    #                 dict_design['design_temp'],
    #                 dict_design['T_d_supply_radiator_tank'],
    #                 dict_design['T_d_return_radiator_tank'],
    #                 dict_design['rad_exp_radiator'],
    #             ),
    #             axis=1,
    #         )
    #         
    #     df_heat['HP_T_SFH_to_use'] = df_heat.apply(lambda x: df_hp.T_dist.unique()[find_interval_hp(x.Temp_supply,df_hp.T_dist.unique())],axis=1)
    #     df_heat['HP_T_SFH_tank_to_use'] = df_heat.apply(lambda x: df_hp.T_dist.unique()[find_interval_hp(x.Temp_supply_tank,df_hp.T_dist.unique())],axis=1)
    #     df_heat['Temp_amb_interval'] = df_heat.apply(lambda x: df_hp.T_outside.unique()[find_interval_hp(x.Temp,df_hp.T_outside.unique())],axis=1)
    #     # here we need to select the T supply and return depending on the kWh/m2
    #     hp_sizing(dict_design,df_hp,flag_heating_floor)

    #     get_COP(df_heat,df_hp,dict_design)
    #     
    #     
    #     df_heat = df_heat[['Set_T', 'Temp', 'Req_kWh', 'Temp_supply',
    #                     'Temp_supply_tank', 'COP_SH', 'COP_tank', 'COP_DHW',
    #                     'hp_sh_cons', 'hp_tank_cons', 'hp_dhw_cons']]
    #     heat_pump = HeatPumpDesign(
    #         series=df_heat,
    #         attributes=dict_design,
    #     )
    #     building_data[building]['heat_pump']=heat_pump

    # save_obj(building_data,'Test_floor')#it is saving in Output/Test
# Define a function to generate extrapolated heat pump data
def cop_model(delta_T):
    return 68.455 * delta_T ** -0.76 #from Arpagaus, Bless, Bertsch & Schiffmann. Wärmepumpen für die Industrie: Eine aktuelle Übersicht. 2019 
# https://www.ost.ch/fileadmin/dateiliste/3_forschung_dienstleistung/institute/ies/projekte/projekte_tes/91_sccer-eip/arpagaus_et_al._2019_wp-tagung_burgdorf_-_waermepumpen_fuer_die_industrie_-_eine_aktuelle_uebersicht.pdf

def generate_extrapolated_hp_data(hp_ratings, T_dists, T_outsides):
    """
    Generates extrapolated COP and electrical power input (P_el) data
    for a range of heat pump nominal capacities based on the empirical COP model:
    COP_H = 68.455 * ΔT^-0.76, where ΔT = T_dist - T_outside.

    Parameters:
        hp_ratings (list): List of nominal heat pump ratings in kW.
        T_dists (list): List of distribution temperatures in °C.
        T_outsides (list or array): List or array of outside temperatures in °C.

    Returns:
        pd.DataFrame: A DataFrame with columns [HP_rating, T_dist, T_outside, P_el, COP].
    """
    rows = []
    for hp in hp_ratings:
        for T_dist in T_dists:
            for T_out in T_outsides:
                delta_T = T_dist - T_out
                cop = cop_model(delta_T)
                P_el = hp / cop
                rows.append({
                    "HP_rating": hp,
                    "T_dist": T_dist,
                    "T_outside": T_out,
                    "P_el": round(P_el, 2),
                    "COP": round(cop, 2)
                })
    return pd.DataFrame(rows)
