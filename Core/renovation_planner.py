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

def add_HP(df: pd.DataFrame) -> pd.DataFrame:
    years_of_interest = planner_config.years_of_interest

    # existing hp and district heating
    hp_presence = df["gwaerzh1"].isin([7410, 7411])
    district_heating_presence = df["gwaerzh1"].isin([7460, 7461])

    # calculating all dates where a renovation of heating system should be done
    # CAUTION: Assumption made that any absent renovation date is due to the renovation being exceedingly old
    renovation_dates = pd.to_datetime(df['gwaerdath1'], format = "%d.%m.%Y", errors='coerce')
    dummy_date = pd.Timestamp("1900-01-01")
    renovation_dates = renovation_dates.fillna(dummy_date)
    renovation_dates_plus_20 = renovation_dates.apply(lambda d: d + relativedelta(years=20))

    # Determining what buildings should have been equipped with a HP at each year of interest
    hp_installed_per_year = {}
    for year in years_of_interest:
        cutoff = pd.Timestamp(f"{year}-01-01")
        renovated = renovation_dates_plus_20 < cutoff
        hp_installed_per_year[f'hp_installed_{year}'] = (hp_presence | renovated) & ~district_heating_presence
    
    hp_per_year = pd.DataFrame(hp_installed_per_year)
    buildings_df = df.merge(hp_per_year, left_index=True, right_index=True, how="left")

    # Adding HP pumps up to projected HP ratio
    hp_inclusion_rates = dataframe_load(planner_config.hp_inclusion_rates)
    hp_inclusion_rates = hp_inclusion_rates[
        (hp_inclusion_rates['Canton'] == planner_config.canton) &
        (hp_inclusion_rates['quantile'] == planner_config.quantile)
    ]

    municipalities = buildings_df["commune"].str.replace(r"\s*\(.*?\)", "", regex=True).unique()
    municipalities_hp_inclusion_rates = hp_inclusion_rates[hp_inclusion_rates['MunicipalityName'].isin(municipalities)]

    print(municipalities_hp_inclusion_rates.head())

    return buildings_df 

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
        print(self.renovation_plan.head())
        print(len(self.renovation_plan))
        for b, values in buildings.items():
            ev_count = 0
            if b in self.renovation_plan.index:
                ev_count = self.renovation_plan.loc[b, f'ev_count_{sim_year}']

            values['attributes']['ev_count'] = ev_count



async def main() -> None:
    save_file = planner_config.save_file

    df = None
    if os.path.exists(save_file) and not planner_config.no_cache:
        df = dataframe_load(save_file)
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

