import pandas as pd
from typing import Any, Dict
from utils.logger import logger, data_logger
from config.loader import config

def is_valid_heat_demand(Qs: pd.Series) -> bool: 
    total_head_demand = Qs.sum()
    if total_head_demand <= 0:
        return False
    return True

def is_blacklisted_building(b_data: Dict[str, Any]):
    egid = b_data['attributes'].get('egid')
    if int(egid) in config.building_blacklist:
        return True
    return False

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

        if is_blacklisted_building(build_data):
            removal_list.append(bid)
            data_logger.info(
                f"""
                Removed
                Building: {bid}, 
                egid: {build_data['attributes']['egid']} 
                Egid matched in blacklist.
                """)

    for bid in removal_list:
        logger.info(f"Removing building: {bid} due to invalid data content.")
        buildings_data.pop(bid)

