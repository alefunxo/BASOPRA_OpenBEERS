import sys
import os
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
from pandas import DataFrame
from utils.utils import dataframe_load, is_type, list_files_recursive
import logging

from utils.logger import logger
logger.setLevel(logging.WARNING)


# TODO modify for timestamp based index when available and normalize outputs by dt
def assume_month_range() -> List[Tuple[int, int]]:
    month_hours = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    month_ranges = []
    start = 0
    for days in month_hours:
        end = start + days * 24
        month_ranges.append((start, end))
        start = end
    return month_ranges

def autoconsumption(df: DataFrame):
    e_pv = df["E_PV"].sum()
    if e_pv == 0:
        return 0
    return df["E_PV_load"].sum() / df["E_PV"].sum()

def autarky(df: DataFrame):
    e_demand = df["E_demand"].sum()
    if e_demand == 0:
        return 0
    return df["E_PV_load"].sum() / df["E_demand"].sum()

def peak_consumption(df: DataFrame):
    return df["E_demand"].max()

def peak_thermal_consumption(df: DataFrame):
    return (df["E_hp"] + df["E_hpdhw"]).max()

def cooling_hours(df: DataFrame):
    return (df["Cooling"] < 0.0).sum()

def cooling_energy(df: DataFrame):
    return df["Cooling"].sum()

kpi_fcts = {
    'autoconsumption': autoconsumption,
    'autarky': autarky,
    'peak_consumption': peak_consumption,
    # 'cooling_hours': cooling_hours,
    # 'cooling_energy': cooling_energy,
    # 'peak_thermal_consumption': peak_thermal_consumption,
}

def calc_kpis(df: DataFrame):
    kpis = {}
    for kpi, method in kpi_fcts.items():
        kpis[kpi] = method(df)
    return pd.Series(kpis)

def get_building_monthly_kpis(df: DataFrame):
    month_ranges = assume_month_range()
    monthly_kpis = []
    for i, (start, end) in enumerate(month_ranges, 1):
        month_df = df.iloc[start:end]
        kpis = calc_kpis(month_df)
        kpis['month'] = int(i)
        monthly_kpis.append(kpis)
    df_monthly_kpis = pd.DataFrame(monthly_kpis)
    df_monthly_kpis['month'] = df_monthly_kpis['month'].astype(int)
    return df_monthly_kpis

# def get_building_monthly_kpis(building_df) -> DataFrame:
#     simulation_kpis: List = []
#     for file in dir_content['files']:
#         if is_type(file, '.csv'):
#             df = dataframe_load(f'{dir_name}/{file}')
#             kpis = get_building_kpis(df)
#             simulation_kpis.append(kpis)
#     return simulation_kpis


def get_all_building_dfs(main_dir:str) -> Dict[str, Any]:
    # TODO, once we have date timestamped item. Add date sorting to the mix
    structure = list_files_recursive(main_dir)
    flattened_data = []
    for directory in structure:
        for file in structure[directory]['files']:
            if is_type(file, '.csv'):
                df = dataframe_load(f'{main_dir}/{directory}/{file}')
                split_file_name = file.split('.')[0].split('_')
                building = split_file_name[1]
                conf = split_file_name[2]
                df['simulation'] = directory
                df['building'] = building
                df['configuration'] = conf
                flattened_data.append(df)
    final_df = pd.concat(flattened_data, ignore_index=True)
    return final_df 

def main():
    main_dir = 'outputs_basopra'
    zone_dfs = get_all_building_dfs(main_dir)
    monthly_kpi_dfs = pd.DataFrame()
    yearly_kpi_dfs = []
    for sim_name, simulation in zone_dfs.groupby('simulation'):
        print(sim_name)
        print(simulation.shape)
        print(simulation['building'].unique().shape)
        for b_name, building in simulation.groupby('building'):
            for conf_name, conf in building.groupby('configuration'):
                month_kpis = get_building_monthly_kpis(conf)
                month_kpis['simulation'] = sim_name
                month_kpis['building'] = b_name
                month_kpis['configuration'] = conf_name
                monthly_kpi_dfs = pd.concat([monthly_kpi_dfs, month_kpis], ignore_index=True)

                yearly_kpis = calc_kpis(conf)
                yearly_kpis['simulation'] = sim_name
                yearly_kpis['building'] = b_name
                yearly_kpis['configuration'] = conf_name
                yearly_kpi_dfs.append(yearly_kpis)
    yearly_kpi_dfs = pd.DataFrame(yearly_kpi_dfs)

    pd.set_option("display.float_format", "{:.2f}".format)

    print(monthly_kpi_dfs)
    print(yearly_kpi_dfs)
    # print(df.describe())

if __name__ == "__main__":
    main()