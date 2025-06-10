import pandas as pd
from typing import Dict
from utils.logger import logger, data_logger

def is_valid_heat_demand(Qs: pd.Series) -> bool: 
    total_head_demand = Qs.sum()
    if total_head_demand <= 0:
        return False
    return True

def conduct_building_sanity_check(buildings_data: Dict[str, Dict[str, pd.DataFrame]]) -> None:
    removal_list: list = []
    for bid, build_data in buildings_data.items():
        Qs = build_data['series']['Qs']
        if not is_valid_heat_demand(Qs):
            data_logger.error(
                f"""
                Building: {bid}, 
                egid: {build_data['attributes']['egid']} 
                located in {build_data['attributes']['municipality_name']}
                does not have a valid heat demand.
                Qs_tot = {Qs.sum()}
                """)
            removal_list.append(bid)
    for bid in removal_list:
        logger.info(f"Removing building: {bid} due to invalid data content.")
        buildings_data.pop(bid)

