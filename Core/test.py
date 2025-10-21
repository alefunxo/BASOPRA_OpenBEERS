# Copyright © 2025 HES-SO Valais-Wallis <alejandro.penabello@hevs.ch>
# SPDX-FileContributor: Alejandro Penabello <alejandro.penabello@hevs.ch>
# SPDX-FileContributor: Lucien Troillet <lucien.troillet@hevs.ch>
#
# SPDX-License-Identifier: Apache-2.0

import sys
import os
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import asyncio
from config.loader import config
from utils.logger import logger
from openbeers_api.api import ApiWrapper
from openbeers_api.fileloader import cleanup, download_file_from_wap, list_files_in_directory, load_climate_file
from openbeers_api.extract import get_xml_building_data 
from openbeers_api.assembler import build_basopra_input
from openbeers.models import EnergyHeatPump, EnergyPhotovoltaicSystem, Simulation, TimeSeries
from elec_pricer.pricer import ElectricityPricer
from heat_pump.pump_sizer import calculate_heat_pump_size
from utils.utils import dataframe_save, generate_aggregated_basopra_output_data, generate_aggregated_zone_data, pickle_save, pickle_load
from Core.main_beers import run_basopra_simulation
from Core.renovation_planner import RenovationPlanning

async def main():
    simulation_names = config.simulation_names
    simulations = []
    api_wrapper = await ApiWrapper.from_config(config.openbeers_address)
    async with api_wrapper as api:
        # for name in simulation_names:
        #     simulations.append(await api.get_simulation(name))
        # for simulation in simulations:
        #     buildings = await api.get_buildings(simulation.zone_id)
        #     b_ids = [b.id for b in buildings]
        #     renovations = await api.get_renovations(b_ids, simulation.scenario_id, simulation.year)
        # for bid, renov in renovations.items():
        #     print(bid, renov)
        #     if renov is not None:
        #         heat_pumps = await api.get_heat_pumps_from_renovation(renov.id)
        #         print(heat_pumps)
        renovation = await api.get_renovation(14)
        print('Renovation')
        print(renovation)
        hp = await api.get_heat_pump(1)
        print("Heat Pump")
        print(hp)
        print("Heat Pumps")
        hps = await api.get_heat_pumps_from_renovation(14)
        print(hps)
        print()
        ren_id = 2030
        renovation = await api.get_renovation(ren_id)
        print('Renovation')
        print(renovation)
        hp = await api.get_heat_pump(1)
        print("Heat Pump")
        print(hp)
        print("Heat Pumps")
        hps = await api.get_heat_pumps_from_renovation(ren_id)
        print(hps)




    # print(simulations)
    # print(b_ids)
    # for ren, value in renovations.items():
    #     print(ren, value)
        # buildings = await api.get_buildings(simulation.zone_id)
        # b_ids = [b.id for b in buildings]

if __name__ == "__main__":
    asyncio.run(main())