import pandas as pd
from typing import Dict, Any
from Core.paper_classes import heat_storage_tank
from openbeers_api.integrity_checker import conduct_building_sanity_check
from openbeers.models import Simulation
from utils.logger import data_logger

surfaces = ['Roof', 'Wall', 'Ground']

def build_basopra_input(
    simulation: Simulation,
    api_attributes: Dict[str, Dict[str, Any]],
    api_series: dict[str, Dict[str, list]],
    xml_attributes: Dict[str, Dict[str, float]],
    xml_series: Dict[str, Dict[str, list]],
    climate: pd.DataFrame,
    heat_tank: heat_storage_tank,
    dhw_tank: heat_storage_tank,
) -> Dict[str, Dict[str, pd.DataFrame]]:
    output = {}
    for bid in api_attributes:
        valid_building = True
        attributes = api_attributes[bid]
        building_xml_attributes = xml_attributes.get(bid)
        if building_xml_attributes:
            for attr_name in building_xml_attributes.keys():
                attributes[attr_name] = building_xml_attributes.get(attr_name)
        else:
            continue

        ser_df = climate.copy()
        for key, values in api_series.get(bid, {}).items():
            if len(values) == len(ser_df):
                ser_df[key] = values
            else:
                print(f"⚠️ Skipping building{bid} due to {key}: {len(values)} values (expected {len(ser_df)})")
                data_logger.error(f"Error with {simulation.name}: mismatch in dimensions {key} for building {bid}: {len(values)} values (expected {len(ser_df)} from climate data)")
                valid_building = False

        for key, values in xml_series.get(bid, {}).items():
            if len(values) == len(ser_df):
                ser_df[key] = values
            else:
                data_logger.error(f"Error with {simulation.name}: mismatch in dimensions {key} for building {bid}: {len(values)} values (expected {len(ser_df)} from climate data)")
                print(f"⚠️ Skipping building {bid} due to {key}: {len(values)} values (expected {len(ser_df)})")
                valid_building = False

        # ser_df.index = pd.date_range(f"{simulation.year}-01-01 00:00", periods=8760, freq="H")

        datetime_index = pd.date_range(start=f'{simulation.year}-01-01 00:00', end=f'{simulation.year}-12-31 23:00', freq='h')
        ser_df.index = datetime_index
        if valid_building:
            output[bid] = {
                'attributes': attributes,
                'series': ser_df,
                'heat_tank': heat_tank,
                'dhw_tank': dhw_tank,
            }

    conduct_building_sanity_check(output)

    return output
