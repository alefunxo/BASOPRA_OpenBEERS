import sys
import os
from typing import Any, Dict, List, Tuple, Union
from tqdm import tqdm
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import multiprocessing as mp
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

# def safe_get(df: DataFrame, col_name: str, default_value: Any=0) -> DataFrame:
#     df[col_name] = df.get(col_name, pd.Series(default_value, index=df.index))
#     return df[col_name]

def safe_get(df: pd.DataFrame, cols: Union[str, List[str]], default_value=0) -> pd.DataFrame:
    if isinstance(cols, str):
        return df[cols] if cols in df else pd.Series(default_value, index=df.index, name=cols)
    # list case
    if not cols:
        # no columns → empty DataFrame
        return pd.DataFrame(index=df.index)
    parts = []
    for col in cols:
        if col in df:
            parts.append(df[col])
        else:
            parts.append(pd.Series(default_value, index=df.index, name=col))
    return pd.concat(parts, axis=1)


def autoconsumption(df: DataFrame):
    pv_direct_cols = ['E_PV_bu', 'E_PV_budhw', 'E_PV_hp', 'E_PV_hpdhw', 'E_PV_load']
    ev_pv_cols = [col for col in df.columns if col.startswith('E_PV_batt_EV_')]
    pv_batt_col = 'E_PV_batt'  # PV to battery (base)

    # PV used locally includes direct use + PV to batteries (including EVs)
    pv_used_locally_cols = pv_direct_cols + [pv_batt_col] + ev_pv_cols

    # Aggregate totals
    # pv_used_locally = df[pv_used_locally_cols].sum().sum()
    pv_used_locally = safe_get(df, pv_used_locally_cols).sum().sum()
    pv_total = safe_get(df,'E_PV').sum()

    # Self-consumption [%]
    return (pv_used_locally / pv_total) * 100 if pv_total > 0 else 0

def autarky(df: DataFrame):
    # Direct PV usage
    pv_direct_cols = ['E_PV_bu', 'E_PV_budhw', 'E_PV_hp', 'E_PV_hpdhw', 'E_PV_load']

    # Battery discharges to local uses
    batt_discharge_cols = ['E_batt_bu', 'E_batt_budhw', 'E_batt_hp', 'E_batt_hpdhw', 'E_batt_load']
    ev_batt_discharge_cols = [col for col in df.columns if col.startswith('E_batt_EV_load_EV_')]

    # Local supply includes PV direct use and battery discharge
    local_supply_cols = pv_direct_cols + batt_discharge_cols + ev_batt_discharge_cols

    # Aggregate totals
    local_supply = safe_get(df, local_supply_cols).sum().sum()
    # referring only to the load served WITHIN the building, EV away is not part of it for instance
    ev_grid_cols = [col for col in df.columns if col.startswith('E_grid_batt_EV')]
    total_consumption = (
        safe_get(df,'E_demand').sum()
        + safe_get(df,'E_hp').sum()
        + safe_get(df,'E_hpdhw').sum()
        + safe_get(df,'E_bu').sum()
        + safe_get(df,'E_budhw').sum()
        + safe_get(df,'E_grid_batt').sum() 
        + safe_get(df,ev_grid_cols).sum().sum()
    )

    # Autarky [%]
    return (local_supply / total_consumption) * 100 if total_consumption > 0 else 0
def EV_consumption(df: DataFrame):
    ev_grid_cols = [col for col in df.columns if col.startswith('E_grid_batt_EV')]
    return safe_get(df,ev_grid_cols).sum().sum()
def peak_consumption(df: DataFrame):
    return safe_get(df,"E_cons").max()
def quantile99_consumption(df: DataFrame):
    return safe_get(df,"E_cons").quantile(0.99)
def peak_injection(df: DataFrame):
    return safe_get(df,"E_PV_grid").max()
def quantile99_injection(df: DataFrame):
    return safe_get(df,"E_PV_grid").quantile(0.99)
def peak_thermal_consumption(df: DataFrame):
    return (safe_get(df,"Req_kWh") + safe_get(df,"Req_kWh_DHW")).max()
def quantile99_thermal_consumption(df: DataFrame):
    return (safe_get(df,"Req_kWh") + safe_get(df,"Req_kWh_DHW")).quantile(0.99)
def cooling_hours(df: DataFrame):
    return (safe_get(df,"Cooling") < 0.0).sum()

def cooling_energy(df: DataFrame):
    return safe_get(df,"Cooling").sum()
def thermal_consumption(df: DataFrame):
    return (safe_get(df,"Req_kWh") + safe_get(df,"Req_kWh_DHW")).sum()

# Small KPI functions using safe_get
def total_pv_generation(df: pd.DataFrame):
    return safe_get(df, "E_PV").sum()

def total_grid_import(df: pd.DataFrame):
    return safe_get(df, "E_cons").sum()

def total_household_demand(df: pd.DataFrame):
    return safe_get(df, "E_demand").sum()

def peak_e_demand(df: pd.DataFrame):
    return safe_get(df, "E_demand").max()

def quantile99_e_demand(df: pd.DataFrame):
    return safe_get(df, "E_demand").quantile(0.99)

def change_peak_percent(df: pd.DataFrame):
    max_cons = peak_consumption(df)
    max_dem = peak_e_demand(df)
    return (max_cons / max_dem * 100) if max_dem else float('nan')

def change_q99_peak_percent(df: pd.DataFrame):
    q99_cons = quantile99_consumption(df)
    q99_dem = quantile99_e_demand(df)
    return (q99_cons / q99_dem * 100) if q99_dem else float('nan')

def peak_pv_injection(df: pd.DataFrame):
    return safe_get(df, "E_PV_grid").max()

def quantile99_pv_injection(df: pd.DataFrame):
    return safe_get(df, "E_PV_grid").quantile(0.99)

def total_hp_space_heat(df: pd.DataFrame):
    return safe_get(df, "E_hp").sum()

def total_hp_dhw(df: pd.DataFrame):
    return safe_get(df, "E_hpdhw").sum()

def total_req_space_kwh(df: pd.DataFrame):
    return safe_get(df, "Req_kWh").sum()

def total_req_dhw_kwh(df: pd.DataFrame):
    return safe_get(df, "Req_kWh_DHW").sum()

def dhw_share(df: pd.DataFrame):
    space = total_req_space_kwh(df)
    dhw = total_req_dhw_kwh(df)
    total = space + dhw
    return (dhw / total) if total else 0.0

# Updated KPI functions dictionary
kpi_fcts = {
    'self-consumption': autoconsumption,
    'autarky': autarky,
    'total_pv_generation': total_pv_generation,
    'total_grid_import':    total_grid_import,
    'total_household_demand': total_household_demand,
    'peak_e_cons':         peak_consumption,
    'quantile99_e_cons':   quantile99_consumption,
    'peak_e_demand':       peak_e_demand,
    'quantile99_e_demand': quantile99_e_demand,
    'change_peak_percent': change_peak_percent,
    'change_q99_peak_percent': change_q99_peak_percent,
    'peak_pv_injection':       peak_pv_injection,
    'quantile99_pv_injection': quantile99_pv_injection,
    'total_hp_space_heat': total_hp_space_heat,
    'total_hp_dhw':        total_hp_dhw,
    'total_req_space_kwh': total_req_space_kwh,
    'total_req_dhw_kwh':   total_req_dhw_kwh,
    'thermal_consumption': thermal_consumption,
    'dhw_share': dhw_share,
    'peak_thermal_consumption': peak_thermal_consumption,
    'quantile99_thermal_consumption':quantile99_thermal_consumption,
    'EV_consumption':EV_consumption
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

def discover_tasks(root_dir: str) -> List[Tuple[str, str, str, str]]:
    structure = list_files_recursive(root_dir)
    tasks = []
    for sim, info in structure.items():
        for fname in info['files']:
            if is_type(fname, '.csv'):
                parts = fname.rsplit('.', 1)[0].split('_')
                building, config = parts[1], parts[2]
                full_path = os.path.join(root_dir, sim, fname)
                tasks.append((full_path, sim, building, config))
    return tasks

def worker(args: Tuple[str, str, str, str]):
    path, sim, building, config = args
    df = dataframe_load(path)
    m = get_building_monthly_kpis(df)
    m['simulation'], m['building'], m['configuration'] = sim, building, config
    y = calc_kpis(df).to_frame().T
    y['simulation'], y['building'], y['configuration'] = sim, building, config
    return path, m, y

def safe_worker(args):
    try:
        return (*worker(args), None)
    except Exception as e:
        return (args[0], None, None, e)

def main():
    root = 'outputs_basopra'
    monthly_csv = 'monthlykpi.csv'
    yearly_csv  = 'yearlykpi.csv'

    for f in (monthly_csv, yearly_csv):
        if os.path.exists(f):
            os.remove(f)

    tasks = discover_tasks(root)
    first_month, first_year = True, True

    failed_monthly = []  # list of (path, df)
    failed_yearly  = []  # list of (path, df)

    with mp.Pool(mp.cpu_count()) as pool:
        for path, m_df, y_df, error in tqdm(
            pool.imap_unordered(safe_worker, tasks),
            total=len(tasks),
            desc="Processing KPIs"
        ):
            if error:
                print(f"[ERROR] loading {path}: {error}", file=sys.stderr)
                continue

            try:
                m_df.to_csv(monthly_csv, mode='a', index=False, header=first_month)
            except Exception as e:
                print(f"[ERROR] writing monthly for {path}: {e}", file=sys.stderr)
                failed_monthly.append((path, m_df))
            else:
                first_month = False

            try:
                y_df.to_csv(yearly_csv, mode='a', index=False, header=first_year)
            except Exception as e:
                print(f"[ERROR] writing yearly for {path}: {e}", file=sys.stderr)
                failed_yearly.append((path, y_df))
            else:
                first_year = False

    # Retry any failed writes once more
    if failed_monthly or failed_yearly:
        print("Retrying failed writes...", file=sys.stderr)
    for path, m_df in failed_monthly:
        try:
            m_df.to_csv(monthly_csv, mode='a', index=False, header=first_month)
        except Exception as e:
            print(f"[RETRY ERROR] monthly for {path}: {e}", file=sys.stderr)
        else:
            first_month = False

    for path, y_df in failed_yearly:
        try:
            y_df.to_csv(yearly_csv, mode='a', index=False, header=first_year)
        except Exception as e:
            print(f"[RETRY ERROR] yearly for {path}: {e}", file=sys.stderr)
        else:
            first_year = False

if __name__ == "__main__":
    main()