# Copyright © 2025 HES-SO Valais-Wallis <alejandro.penabello@hevs.ch>
# SPDX-FileContributor: Alejandro Penabello <alejandro.penabello@hevs.ch>
# SPDX-FileContributor: Lucien Troillet <lucien.troillet@hevs.ch>
#
# SPDX-License-Identifier: Apache-2.0

import pandas as pd
from typing import Any, Dict, Optional
from utils.logger import logger, data_logger
from config.loader import config
from openbeers.models import Simulation

def is_valid_heat_demand(Qs: Optional[pd.Series]) -> bool: 
    if Qs is None:
        return False
    total_head_demand = Qs.sum()
    if total_head_demand <= 0:
        return False
    return True

def is_valid_SolarPVProduction(solarPVProduction: Optional[pd.Series]) -> bool:
    if solarPVProduction is None:
        return False
    return True

def is_blacklisted_building(b_data: Dict[str, Any]):
    egid = b_data['attributes'].get('egid')
    if config.building_blacklist is None:
        return False
    if int(egid) in config.building_blacklist:
        return True
    return False

def is_whitelisted_building(b_data: Dict[str, Any]):
    egid = b_data['attributes'].get('egid')
    if config.building_whitelist is None:
        return True
    if int(egid) in config.building_whitelist:
        return True
    return False

def conduct_building_sanity_check(
        buildings_data: Dict[str, Dict[str, pd.DataFrame]], 
        simulation: Simulation,
    ) -> None:
    removal_list: list = []
    for bid, build_data in buildings_data.items():
        Qs = build_data['series']['Qs']
        if not is_valid_heat_demand(Qs):
            data_logger.error(
                f"""
                Simulation: {simulation.name},
                Building: {bid}, 
                egid: {build_data['attributes']['egid']} 
                located in {build_data['attributes']['municipality_name']}
                does not have a valid heat demand.
                Qs_tot = {Qs.sum() if Qs is not None else "None"}
                """)
            removal_list.append(bid)

        solarPVProduction = build_data['series']['SolarPVProduction']
        if not is_valid_SolarPVProduction(solarPVProduction):
            data_logger.error(
                f"""
                Simulation: {simulation.name},
                Building: {bid}, 
                egid: {build_data['attributes']['egid']} 
                located in {build_data['attributes']['municipality_name']}
                Does not have a SolarPVProduction Series.
                """
            )

        if is_blacklisted_building(build_data):
            removal_list.append(bid)
            data_logger.info(
                f"""
                Simulation: {simulation.name},
                Removed
                Building: {bid}, 
                egid: {build_data['attributes']['egid']} 
                Egid matched in blacklist.
                """)

        if not is_whitelisted_building(build_data):
            removal_list.append(bid)
            data_logger.info(
                f"""
                Simulation: {simulation.name},
                Removed
                Building: {bid}, 
                egid: {build_data['attributes']['egid']} 
                Egid not found in whitelist.
                """)

    for bid in removal_list:
        logger.info(f"Removing building: {bid} due to invalid data content.")
        buildings_data.pop(bid, None)

