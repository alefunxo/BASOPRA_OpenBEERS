import sys
import os
from typing import List, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
from pandas import DataFrame
from utils.utils import dataframe_load, is_type, list_files_recursive

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
    return df["E_PV_load"].sum() / df["E_PV"].sum()

def autarky(df: DataFrame):
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

def get_building_kpis(df: DataFrame):
    month_ranges = assume_month_range()
    monthly_kpis = []
    for i, (start, end) in enumerate(month_ranges, 1):
        month_df = df.iloc[start:end]
        kpis = calc_kpis(month_df)
        kpis['month'] = i
        monthly_kpis.append(kpis)
    return monthly_kpis

def main():
    main_dir = 'outputs_basopra'
    structure = list_files_recursive(main_dir)
    for directory in structure:
        print(directory)
        for file in structure[directory]['files']:
            if is_type(file, '.csv'):
                print(file)
                df = dataframe_load(f'{main_dir}/{directory}/{file}')
                kpis = get_building_kpis(df)
                

    file_name = 'outputs_basopra/val_de_bagnes_41_climate_contemporary_pv_roof_2025/df_902138_only Battery.csv'
    df = dataframe_load(file_name)
    month_ranges = assume_month_range()
    monthly_kpis = []
    for i, (start, end) in enumerate(month_ranges, 1):
        month_df = df.iloc[start:end]
        kpis = calc_kpis(month_df)
        kpis['month'] = i
        monthly_kpis.append(kpis)
    monthly_kpis_df = pd.DataFrame(monthly_kpis)
    monthly_kpis_df['month'] = monthly_kpis_df['month'].astype(int)
    monthly_kpis_df = monthly_kpis_df.set_index('month')
    yearly_kpis = calc_kpis(df)

    pd.set_option("display.float_format", "{:.2f}".format)

    print(monthly_kpis_df)
    print(yearly_kpis)
    print(df.describe())

if __name__ == "__main__":
    main()