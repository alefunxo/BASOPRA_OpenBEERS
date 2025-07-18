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

async def get_attributes_for_building(api, buildings, attribute_types):
    attributes = {}
    for b in buildings:
        attrs = await api.get_attributes(b.object_id)
        attributes[b.id] = {
            t.name: next((
                getattr(a, f"value_{t_}") 
                for t_ in ["string", "integer", "float"] 
                if getattr(a, f"value_{t_}", None) is not None
            ),None)
            for t in attribute_types for a in attrs if a.attribute_type_id == t.id
        }

async def run_pipeline(simulation: Simulation) -> Tuple[Dict[int, Any], bool]:
    api_wrapper = await ApiWrapper.from_config(config['openbeers_address'])

    async with api_wrapper as api:
        buildings = await api.get_buildings(simulation.zone_id)
        b_ids = [b.id for b in buildings]
        attr_types = await api.get_attribute_types(config['needed_attributes'])
        ser_types = await api.get_series_types(config['needed_series'])

        # Data retrieval through Openbeers API
        api_attributes = await api.get_attributes_for_buildings(buildings, attr_types)

        api_series: Dict[int, Dict[str, TimeSeries]]= {}
        for b in buildings:
            series = await api.get_series(b.object_id, simulation.id)
            api_series[b.id] = {
                t.name: next(
                    (
                        pt.data for pt in series if pt.time_series_type_id == t.id
                    ), []) for t in ser_types
            }
            api_series[b.id]['Qs'] = [ val / 1000 for val in api_series[b.id]['Qs']]
            api_series[b.id]['SolarPVProduction'] = [ val / 1000 for val in api_series[b.id]['SolarPVProduction']]
    
        renovations = await api.get_renovations(b_ids, simulation.scenario_id, simulation.year)
        heat_pumps: Dict[int, List[EnergyHeatPump]] = {}
        pv_installations: Dict[int, List[EnergyPhotovoltaicSystem]] = {}
        has_renov: bool = False
        for bid, renov in renovations.items():
            if renov is None:
                continue
            heat_pumps[bid] = await api.get_heat_pumps_from_renovation(renov.id)
            pv_installations[bid] = await api.get_PV_from_renovation(renov.id)
            has_renov = True

        climate = await api.get_climate(simulation.climate_id)

        # Data retrieval through web server directory
        wap_address = config['openbeers_address'] + '/simulations/' + simulation.name + '/'
        files = list_files_in_directory(wap_address, verify=False)
        for f in files:
            download_file_from_wap(
                config['openbeers_address'] + "/simulations/",
                simulation.name,
                f, 
                config['dest_folder'],
            )
        
        xml_attributes, xml_series, heat_tank, dhw_tank = get_xml_building_data(config['dest_folder'] + 'simulation.xml')
        climate_df = load_climate_file(config['dest_folder'] + climate.climate_file)

        cleanup(config['dest_folder'])

        # Combining data from different sources
        result = build_basopra_input(simulation, api_attributes, api_series, xml_attributes, xml_series, climate_df, heat_tank, dhw_tank)
        return result, has_renov

def get_elec_prices(buildings_data:Dict[str, Any], elec_pricer: ElectricityPricer) -> None:
    for data in buildings_data.values():
        attributes = data['attributes']
        price_category = elec_pricer.get_consumption_category(attributes.get('activity'))
        elec_price = elec_pricer.get_electricity_price(attributes.get('municipality_name'), price_category)
        attributes['elec_price'] = elec_price

async def extract_simulation_data(
        simulation: Simulation,
        elec_pricer: ElectricityPricer,
    ) -> Dict[int, Dict[str, Any]]:
    logger.info(f"Extracting all data from simulation: {simulation.id} - {simulation.name}")
    save_file = f"{config['simulation_extraction_dir']}/{simulation.name}.pkl"

    if os.path.exists(save_file) and config.cache:
        logger.info(f"Simulation extraction file already exists. {simulation.name}")
        return pickle_load(save_file)
    
    extraction, has_renov = await run_pipeline(simulation)

    # Add tags allowing to know if building is equipped with EV, Battery, and a HP
    renovation_planner = RenovationPlanning(config.renovation_planning.save_file)
    if not has_renov:
        renovation_planner.add_EVs(extraction, simulation)
        renovation_planner.add_batteries(extraction)
        renovation_planner.add_HP_flags(extraction, simulation)
    else:
        # TODO implement renovations from OpenBEERS part
        # Current code is the same as above condition because we don't have data to use.
        renovation_planner.add_EVs(extraction, simulation)
        renovation_planner.add_batteries(extraction)
        renovation_planner.add_HP_flags(extraction, simulation)

    get_elec_prices(extraction, elec_pricer)
        
    calculate_heat_pump_size(f"{config['input_dir']}/HP_data.csv", extraction)

    pickle_save(save_file, extraction)
    return extraction

def input_aggregator(extraction: Dict[int, Any])-> Dict[int, Any]:
    basopra_input = {}
    if config.building_aggregation:
        basopra_input[0] = generate_aggregated_zone_data(extraction)

    for key, value in extraction.items():
        basopra_input[key] = value

    return basopra_input

def output_aggregator(basopra_output: Dict[Tuple[int,int], Any])->Any:
    if config.building_aggregation:
        to_concatenate = {key: value['simulation_outputs'] for key, value in basopra_output.items()}
        aggregated_output = generate_aggregated_basopra_output_data(to_concatenate)
        for key, value in aggregated_output.items():
            basopra_output[key]['simulation_outputs'] = value
        return basopra_output
    return basopra_output
    
async def process_simulation(sim_name: str, sim: Simulation, pricer: ElectricityPricer) -> None:
    save_file = f'{config.simulation_extraction_dir}/{sim_name}.pkl'
    extraction = None
    if sim is None and os.path.exists(save_file):
        logger.info(f"Simulation {sim_name} not found on OpenBeers.")
        logger.info(f'Falling back on found extraction file: {save_file}')
        extraction = pickle_load(save_file)
    elif sim is None and not os.path.exists(save_file):
        logger.info(f"Simulation {sim_name} not found on OpenBeers and no fallback extraction available.")
        logger.info(f"Interrupting simulation for {sim.name}")
        return
    else:
        logger.info(f"Processing {sim.name}")
        extraction = await extract_simulation_data(sim, pricer)

    basopra_input = input_aggregator(extraction)
    basopra_output = run_basopra_simulation(basopra_input)
    basopra_output = output_aggregator(basopra_output)

    conf_mapping = config.Core.conf_mapping
    for bid, cid in basopra_output.keys():
        if basopra_output[(bid, cid)]['simulation_outputs'] is not None:
            egid = basopra_output[(bid, cid)]['simulation_inputs']['hh']['attributes']['egid']
            conf_name = conf_mapping[cid]
            output_file_name = f'{config.basopra_output_dir}{sim.name}/df_{egid}_{conf_name}'
            dataframe_save(f'{output_file_name}.csv', basopra_output[(bid, cid)]['simulation_outputs'])

async def basopra_loop():
    logger.info('Starting loop through simulations')
    api_wrapper = await ApiWrapper.from_config(config['openbeers_address'])
    async with api_wrapper as api:
        simulations = await api.get_all_simulations()

    pricer = ElectricityPricer()
    for sim in simulations:
        await process_simulation(sim.name, sim, pricer)

async def main() -> None:
    logger.info('Entering main')
    if config.loop_mode:
        logger.info('Entering loop_mode. All Simulations found will be processed')
        await basopra_loop()
    else:
        logger.info('Entering list mode. Only given simulation names will be processed')
        simulation_names = config.simulation_names
        for name in simulation_names:
            logger.info(f'From config.yaml, simulation to process is: {name}')
            api_wrapper = await ApiWrapper.from_config(config['openbeers_address'])
            async with api_wrapper as api:
                simulation = await api.get_simulation(name)
            if simulation is None:
                logger.info(f'Simulation is None')
            pricer = ElectricityPricer()
            await process_simulation(name, simulation, pricer)

if __name__ == "__main__":
    asyncio.run(main())