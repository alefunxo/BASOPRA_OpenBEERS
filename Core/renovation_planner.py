import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import asyncio
from typing import Any, Dict, List
import pandas as pd

from config.loader import config
from dateutil.relativedelta import relativedelta
from openbeers_api.api import ApiWrapper
from openbeers.models import AttributeType, Building, Simulation, Zone
import paper_classes as pc
from utils.utils import dataframe_load, dataframe_save

planner_config = config.renovation_planning
np.random.seed(planner_config.seed)

async def load_from_api(save_file: str) -> pd.DataFrame:
    api_wrapper = await ApiWrapper.from_config(config['openbeers_address'])
    zones: List[Zone] = []
    buildings: Dict[int, Building] = {} 
    async with api_wrapper as api:
        print("Retrieving zones")
        zones = await api.get_all_zones()
        print(f"Found {len(zones)} zones")

        print("Retrieving Buildings")
        tasks = [api.get_buildings(z.id) for z in zones]
        zone_buildings = await asyncio.gather(*tasks)
        for bldgs in zone_buildings:
            for bld in bldgs:
                buildings[bld.id] = bld
        buildings_list: List[Building] = list(buildings.values())
        print(f"Found {len(buildings_list)} buildings")

        if planner_config.testing:
            buildings_list = buildings_list[:planner_config.test_cases]

        print("Retrieving attribute types")
        attribute_types: List[AttributeType] = await api.get_attribute_types(planner_config.needed_attributes)
        attributes = await api.get_attributes_for_buildings(buildings_list, attribute_types)

        print("Converting attribute types")
        codification_heat_generator = planner_config.codification_heat_generator

        for attrs in attributes.values():
            for attr in ['gwaerzh1', 'gwaerzh2']:
                attrs[f'{attr}_lit'] = codification_heat_generator.get(attrs.get(attr))

        print("Saving attributes")
        df = pd.DataFrame(attributes).T
        print(df.head())
        dataframe_save(save_file, df, index=True)
    return df

def estimate_vehicles_per_building(df: pd.DataFrame) -> pd.DataFrame:
    people_per_houselhold = planner_config.people_per_household
    vehicles_per_household = planner_config.vehicles_per_household
    inhabitants_per_building = df['num_occupants']
    # CAUTION: assumption made that a one person building still counts as a household
    households_per_building = np.maximum(1, np.round(inhabitants_per_building / people_per_houselhold).astype(int))
    total_households = households_per_building.sum()
    total_vehicles = round(total_households * vehicles_per_household)
    building_indices_for_households = np.repeat(
        np.arange(len(households_per_building)), households_per_building
    )
    assigned_households = np.random.choice(
        building_indices_for_households,
        size=total_vehicles,
        replace=True
    )

    vehicle_counts = np.bincount(
        assigned_households, minlength=len(households_per_building)
    )

    df['total_vehicle_count'] = vehicle_counts
    print(df.head())
    return df

def add_evs(df: pd.DataFrame) -> pd.DataFrame:
    vehicle_counts = df['total_vehicle_count']
    ev_ratios = planner_config.ev_inclusion_rate
    building_ids = list(vehicle_counts.keys())

    flat_vehicle_building_ids = np.concatenate([
        [b_id] * vehicle_counts[b_id] for b_id in building_ids
    ])

    initial_year = min(ev_ratios.keys())
    initial_ratio = ev_ratios[initial_year]
    total_vehicles = sum(vehicle_counts)
    initial_evs = round(total_vehicles * initial_ratio)

    initial_assigned = np.random.choice(
        flat_vehicle_building_ids, size=initial_evs, replace=False
    )
    initial_ev_counts = {b_id: 0 for b_id in building_ids}
    for b_id in initial_assigned:
        initial_ev_counts[b_id] += 1

    ev_counts_by_year = {f'ev_count_{initial_year}': initial_ev_counts.copy()}
    current_ev_counts = initial_ev_counts.copy()

    print(initial_year, sum(current_ev_counts.values())/vehicle_counts.sum())

    for year in sorted(ev_ratios.keys()):
        if year == initial_year:
            continue

        target_total_evs = round(total_vehicles * ev_ratios[year])
        current_total_evs = sum(current_ev_counts.values())
        new_evs_needed = target_total_evs - current_total_evs

        if new_evs_needed <= 0:
            ev_counts_by_year[year] = current_ev_counts.copy()
            continue

        non_ev_vehicle_building_ids = np.concatenate([
            [b_id] * (vehicle_counts[b_id] - current_ev_counts[b_id])
            for b_id in building_ids
            if vehicle_counts[b_id] > current_ev_counts[b_id]
        ])

        assigned_new = np.random.choice(non_ev_vehicle_building_ids, size=new_evs_needed, replace=False)
        for b_id in assigned_new:
            current_ev_counts[b_id] += 1

        ev_counts_by_year[f'ev_count_{year}'] = current_ev_counts.copy()
        print(initial_year, sum(current_ev_counts.values())/vehicle_counts.sum())
    ev_df = pd.DataFrame(ev_counts_by_year).astype(int)
    buildings_df = df.merge(ev_df, left_index=True, right_index=True, how="left")

    return buildings_df

def add_current_HP(df: pd.DataFrame) -> pd.DataFrame:
    df['hp_installed_2025'] = df["gwaerzh1"].isin([7410, 7411])
    return df

def add_HP_when_renovated(df: pd.DataFrame, years_of_interest: List[int]) -> pd.DataFrame:
    # CAUTION: Assumption made that any absent renovation date is due to the renovation being exceedingly old
    district_heating_presence = df["gwaerzh1"].isin([7460, 7461])
    renovation_dates = pd.to_datetime(df['gwaerdath1'], format = "%d.%m.%Y", errors='coerce')
    dummy_date = pd.Timestamp("1900-01-01")
    renovation_dates = renovation_dates.fillna(dummy_date)
    renovation_dates_plus_20 = renovation_dates.apply(lambda d: d + relativedelta(years=20))

    # Determining what buildings should have been equipped with a HP at each year of interest
    hp_presence = df['hp_installed_2025']
    hp_installed_per_year = {}
    for year in years_of_interest:
        cutoff = pd.Timestamp(f"{year}-01-01")
        renovated = renovation_dates_plus_20 < cutoff
        hp_installed_per_year[f'hp_installed_{year}'] = (hp_presence | renovated) & ~district_heating_presence
        print(year, hp_installed_per_year[f'hp_installed_{year}'].sum()/len(hp_installed_per_year[f'hp_installed_{year}']))

    hp_per_year = pd.DataFrame(hp_installed_per_year, index=df.index)
    df = df.drop(columns=['hp_installed_2025'])
    buildings_df = df.merge(hp_per_year, left_index=True, right_index=True, how="left")
    return buildings_df

def add_HP_to_projected_ratio(df: pd.DataFrame, years_of_interest: List[int]) -> pd.DataFrame:
    hp_inclusion_rates = dataframe_load(planner_config.hp_inclusion_rates)
    hp_inclusion_rates = hp_inclusion_rates[
        (hp_inclusion_rates['Canton'] == planner_config.canton) &
        (hp_inclusion_rates['quantile'] == planner_config.quantile)
    ]

    municipalities = df["commune"].unique()
    municipalities_hp_inclusion_rates = hp_inclusion_rates[hp_inclusion_rates['MunicipalityName'].isin(municipalities)]

    municipality_dfs = {
        municipality: group.copy()
        for municipality, group in df.groupby('commune')
    }
    for year in years_of_interest:
        for municipality, buildings in municipality_dfs.items():
            column = f'hp_installed_{year}'
            actual_rate = buildings[column].sum()/len(buildings[column])
            hp_rate = municipalities_hp_inclusion_rates[municipalities_hp_inclusion_rates['MunicipalityName'] == municipality][str(year)].iloc[0]/100
            print(year, municipality, actual_rate, hp_rate)
            if hp_rate < actual_rate:
                continue
            total_hp_needed = round(hp_rate * len(buildings[column]))
            hp_to_add = total_hp_needed - buildings[column].sum()
            false_indices = buildings[buildings[column] is False].index
            flip_indices = np.random.choice(false_indices, size=hp_to_add, replace=False)
            df.loc[flip_indices, column] = True
    full_df = pd.concat(municipality_dfs.values())
    return full_df

def add_HP(df: pd.DataFrame) -> pd.DataFrame:
    years_of_interest = planner_config.years_of_interest
    df['commune'] = df["commune"].str.replace(r"\s*\(.*?\)", "", regex=True)

    hp_inclusion_rates = dataframe_load(planner_config.hp_inclusion_rates)
    hp_inclusion_rates = hp_inclusion_rates[
        (hp_inclusion_rates['Canton'] == planner_config.canton) &
        (hp_inclusion_rates['quantile'] == planner_config.quantile)
    ]

    municipalities = df["commune"].unique()
    municipalities_hp_inclusion_rates = hp_inclusion_rates[hp_inclusion_rates['MunicipalityName'].isin(municipalities)]

    # existing hp and district heating
    df = add_current_HP(df)
    for year in [2025]:
        for municipality, group in df.groupby('commune'):
            column = f'hp_installed_{year}'
            actual_rate = group[column].sum()/len(group[column])
            hp_rate = municipalities_hp_inclusion_rates[municipalities_hp_inclusion_rates['MunicipalityName'] == municipality][str(year)].iloc[0]/100
            print(year, municipality, actual_rate, hp_rate)

    # calculating all dates where a renovation of heating system should be done
    df = add_HP_when_renovated(df, years_of_interest)
    for year in years_of_interest:
        for municipality, group in df.groupby('commune'):
            column = f'hp_installed_{year}'
            actual_rate = group[column].sum()/len(group[column])
            hp_rate = municipalities_hp_inclusion_rates[municipalities_hp_inclusion_rates['MunicipalityName'] == municipality][str(year)].iloc[0]/100
            print(year, municipality, actual_rate, hp_rate)

    # Adding HP pumps up to projected HP ratio
    df = add_HP_to_projected_ratio(df, years_of_interest)

    return df 

def prep_battery_prob(df: pd.DataFrame) -> pd.DataFrame:
    will_have_battery_if_PV = np.random.rand(len(df)) <= planner_config.battery_install_ratio
    df["install_battery"] = will_have_battery_if_PV
    return df

    
class RenovationPlanning:
    def __init__(self, renovation_plan_path: str) -> None:
        self.renovation_plan: pd.DataFrame = dataframe_load(renovation_plan_path, 0)
    
    def add_EV_counts(self, buildings: Dict[int, Any], simulation: Simulation) -> None:
        sim_year = simulation.year
        # ev_counts_year = self.renovation_plan[f'ev_count_{sim_year}']
        for b, values in buildings.items():
            ev_count = 0
            if b in self.renovation_plan.index:
                ev_count = self.renovation_plan.loc[b, f'ev_count_{sim_year}']

            values['attributes']['ev_count'] = ev_count

    def add_batteries(self, buildings: Dict[int, Any]) -> None:
        surfaces = ['roof', 'wall', 'floor']
        battery_type = planner_config.battery_type
        for b, values in buildings.items():
            pv = sum(
                [values['attributes'][f'{surface}_pv_capacity']
                for surface in surfaces]
            )
            print(values['series'].head())
            if pv>0 and self.renovation_plan.loc[b, 'install_battery']:
                values['attributes']['has_battery'] = True
                battery_capacity = values['series']['ElectricConsumption'].sum()/1000
                battery = pc.Battery_tech(Capacity=battery_capacity, Technology=battery_type)
                values['battery'] = battery
    
    def add_HP_flags(self, buildings: Dict[int, Any], simulation: Simulation) -> None:
        sim_year = simulation.year
        citysim_hp_flag_name = planner_config.citysim_hp_flag
        citysim_hp = {}
        for b, values in buildings.items():
            citysim_hp[b] = {
                'municipality': values['attributes']['commune'],
                citysim_hp_flag_name: values['attributes'].get(citysim_hp_flag_name, False),
            }
        citysim_hp = pd.DataFrame(citysim_hp).T
        precomputed_has_hp = self.renovation_plan.loc[citysim_hp.index.intersection(self.renovation_plan.index)]

        aligned = precomputed_has_hp[[f'hp_installed_{sim_year}']].join(citysim_hp[['citysim_hp']],how='inner')
        flags_to_turn_True = aligned[
            (~aligned[f"hp_installed_{sim_year}"]) 
            & (aligned["citysim_hp"])
        ].index.to_list()
        ok_but_different = aligned[
            (aligned[f"hp_installed_{sim_year}"]) 
            & (~aligned["citysim_hp"])
        ].index.to_list()

        number_of_flags_to_change = len(flags_to_turn_True)
        number_of_ok_differences = len(ok_but_different)
        print(number_of_flags_to_change, number_of_ok_differences)
        flags_to_turn_False = np.random.choice(ok_but_different, size=number_of_flags_to_change, replace=False)

        for b, values in buildings.items():
            has_HP = self.renovation_plan.loc[b, f'hp_installed_{sim_year}']
            if b in flags_to_turn_False:
                has_HP = False
            if b in flags_to_turn_True:
                has_HP = True
            values['attributes']['has_HP'] = has_HP

async def main() -> None:
    save_file = planner_config.save_file

    df = None
    if os.path.exists(save_file) and not planner_config.no_cache:
        df = dataframe_load(save_file, index_col=0)
    else: 
        df = await load_from_api(save_file)
        
    df = estimate_vehicles_per_building(df)
    df = add_evs(df)
    df = add_HP(df)
    df = prep_battery_prob(df)
    print(df.head)
    dataframe_save(save_file, df, index=True)
            
if __name__ == "__main__":
    asyncio.run(main())

