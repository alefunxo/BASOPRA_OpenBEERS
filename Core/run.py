import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import asyncio
from config.loader import config
from utils.logger import logger
from openbeers_api.api import ApiWrapper
from openbeers_api.fileloader import cleanup, download_file_from_wap, list_files_in_directory, load_climate_file
from openbeers_api.extract import get_xml_building_data 
from openbeers_api.assembler import build_basopra_input
from openbeers.models import Simulation
from elec_pricer.pricer import ElectricityPricer
from heat_pump.pump_sizer import calculate_heat_pump_size
from utils.utils import pickle_save, pickle_load
from Core.main_beers import run_basopra_simulation



async def run_pipeline(simulation: Simulation) -> dict:
    api_wrapper = await ApiWrapper.from_config(config['openbeers_address'])

    async with api_wrapper as api:
        # sim = await api.get_simulation(simulation_name)
        buildings = await api.get_buildings(simulation.zone_id)
        attr_types = await api.get_attribute_types(config['needed_attributes'])
        ser_types = await api.get_series_types(config['needed_series'])

        api_attributes = {}
        api_series = {}
        for b in buildings:
            attrs = await api.get_attributes(b.object_id)
            api_attributes[b.id] = {
                t.name: next((getattr(a, f"value_{t_}") for t_ in ["string", "integer", "float"] if getattr(a, f"value_{t_}", None) is not None),None)
                for t in attr_types for a in attrs if a.attribute_type_id == t.id
            }
            s = await api.get_series(b.object_id, simulation.id)
            api_series[b.id] = {
                t.name: next(
                    (
                        pt.data for pt in s if pt.time_series_type_id == t.id
                    ), []) for t in ser_types
            }
    
        climate = await api.get_climate(simulation.climate_id)

        wap_address = config['openbeers_address'] + '/simulations/' + simulation.name + '/'
        files = list_files_in_directory(wap_address, verify=False)
        for f in files:
            download_file_from_wap(
                config['openbeers_address'] + "/simulations/",
                simulation.name,
                f, 
                config['dest_folder'],
            )
        
        xml_attributes, xml_series = get_xml_building_data(config['dest_folder'] + 'simulation.xml')
        climate_df = load_climate_file(config['dest_folder'] + climate.climate_file)

        cleanup(config['dest_folder'])

        result = build_basopra_input(api_attributes, api_series, xml_attributes, xml_series, climate_df)
        return result

async def extract_simulation_data(
        simulation: Simulation,
        elec_pricer: ElectricityPricer,
    ) -> None:
    logger.info(f"Extracting all data from simulation: {simulation.id} - {simulation.name}")
    save_file = f'{config['simulation_extraction_dir']}/{simulation.name}.pkl'

    if os.path.exists(save_file):
        logger.info(f"Simulation extraction file already exists. {simulation.name}")
        return pickle_load(save_file)
    
    extraction = await run_pipeline(simulation)
    for bid, data in extraction.items():
        attributes = data['attributes']
        price_category = elec_pricer.get_consumption_category(attributes.iloc[0]['activity'])
        elec_price = elec_pricer.get_electricity_price(attributes.iloc[0]['municipality_name'], price_category)
        attributes['elec_price'] = elec_price

    calculate_heat_pump_size(f'{config['input_dir']}/HP_data.csv', extraction)

    pickle_save(save_file, extraction)
    return extraction

def basopra_optimization(extraction):
    return None
    # return run_basopra_simulation(extraction)

async def process_simulation(sim: Simulation, pricer: ElectricityPricer) -> None:
    logger.info(f"Processing {sim.name}")
    extraction = await extract_simulation_data(sim, pricer)
    basopra_output = basopra_optimization(extraction)
    dummy_name = f'{config['basopra_output_dir']}basopra_output.pkl'
    pickle_save(dummy_name, basopra_output)

async def basopra_loop():
    logger.info('Starting loop through simulations')
    api_wrapper = await ApiWrapper.from_config(config['openbeers_address'])
    async with api_wrapper as api:
        simulations = await api.get_all_simulations()

    pricer = ElectricityPricer()
    for sim in simulations:
        await process_simulation(sim, pricer)

async def main() -> None:
    logger.info('Entering main')
    if config['loop_mode']:
        logger.info('Entering loop_mode. All Simulations found will be processed')
        await basopra_loop()
    else:
        logger.info('Entering single simulation mode.')
        simulation_name = config['simulation_name']
        logger.info(f'From config.yaml, simulation to process is: {simulation_name}')
        api_wrapper = await ApiWrapper.from_config(config['openbeers_address'])
        async with api_wrapper as api:
            simulation = await api.get_simulation(simulation_name)
        pricer = ElectricityPricer()
        await process_simulation(simulation, pricer)

if __name__ == "__main__":
    asyncio.run(main())