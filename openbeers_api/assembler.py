import pandas as pd
from typing import Dict, Any, List
from Core.paper_classes import heat_storage_tank
from openbeers_api.integrity_checker import conduct_building_sanity_check
from openbeers.models import Simulation, EnergyHeatPump, EnergyPhotovoltaicSystem
from utils.logger import data_logger

surfaces = ['Roof', 'Wall', 'Ground']

def build_basopra_input(
    simulation: Simulation,
    api_attributes: Dict[str, Dict[str, Any]],
    api_series: dict[str, Dict[str, list]],
    xml_attributes: Dict[str, Dict[str, float]],
    xml_series: Dict[str, Dict[str, list]],
    climate: pd.DataFrame,
    heat_tanks: Dict[int, heat_storage_tank],
    dhw_tanks: Dict[int, heat_storage_tank],
    heat_pumps: Dict[int, List[EnergyHeatPump]],
    pv_installations: Dict[int, List[EnergyPhotovoltaicSystem]],
) -> Dict[str, Dict[str, pd.DataFrame]]:
    output = {}
    for bid in api_attributes:
        valid_building = True

        # Building attributes
        attributes = api_attributes[bid]
        attributes['sim_name'] = simulation.name
        building_xml_attributes = xml_attributes.get(bid)
        if building_xml_attributes:
            for attr_name in building_xml_attributes.keys():
                attributes[attr_name] = building_xml_attributes.get(attr_name)
        else:
            continue

        # Building series 
        ser_df = climate.copy()
        for key, values in api_series.get(bid, {}).items():
            if len(values) == len(ser_df):
                ser_df[key] = values
            else:
                data_logger.error(f"Error with {simulation.name}: mismatch in dimensions {key} for building {bid}: {len(values)} values (expected {len(ser_df)} from climate data)")
                valid_building = False

        for key, values in xml_series.get(bid, {}).items():
            if len(values) == len(ser_df):
                ser_df[key] = values
            else:
                data_logger.error(f"Error with {simulation.name}: mismatch in dimensions {key} for building {bid}: {len(values)} values (expected {len(ser_df)} from climate data)")
                valid_building = False

        # Creating a proper date time index
        datetime_index = pd.date_range(start=f'{simulation.year}-01-01 00:00', end=f'{simulation.year}-12-31 23:00', freq='h')
        ser_df.index = datetime_index

        # Creating final output
        if valid_building:
            output[bid] = {
                'attributes': attributes,
                'series': ser_df,
                'heat_tank': heat_tanks[int(bid)],
                'dhw_tank': dhw_tanks[int(bid)],
                'heat_pump': heat_pumps.get(int(bid)),
                'PV': pv_installations.get(int(bid)),
            }

    conduct_building_sanity_check(output)

    return output
