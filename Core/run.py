import sys
import os
import traceback
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import asyncio
from config.loader import config
from utils.logger import logger, data_logger
from openbeers_api.api import ApiWrapper
from openbeers_api.fileloader import cleanup, download_file_from_wap, list_files_in_directory, load_climate_file
from openbeers_api.extract import get_xml_building_data 
from openbeers_api.assembler import build_basopra_input
from openbeers.models import EnergyHeatPump, EnergyPhotovoltaicSystem, Simulation, TimeSeries
from elec_pricer.pricer import ElectricityPricer
from heat_pump.pump_sizer import calculate_heat_pump_size, heat_pump_dimensioning_from_files
from utils.utils import dataframe_save, pickle_load, pickle_save
from utils.multiprocessing_utils import run_parallel
from utils.aggregator import generate_aggregated_basopra_output_data, generate_aggregated_zone_data
from Core.main_beers import run_basopra_simulation, run_basopra_simulation_from_file_names
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
            qs = api_series[b.id]['Qs'] if api_series[b.id].get('Qs') is not None else None
            pv_prod= api_series[b.id]['SolarPVProduction'] if api_series[b.id].get('SolarPVProduction') is not None else None
            if qs is not None:
                qs = [
                    val / 1000 
                    if val is not None
                    else (qs[i-1] + qs[(i+1) % len(qs)]) / 2 / 1000
                    for i, val in enumerate(qs) 
                ]
                api_series[b.id]['Qs'] = qs
            if pv_prod is not None:
                pv_prod = [
                    val / 1000  
                    if val is not None 
                    else (pv_prod[i-1] + pv_prod[(i+1) % len(pv_prod)]) / 2 / 1000 
                    for i, val in enumerate(pv_prod)
                ]
                api_series[b.id]['SolarPVProduction'] = pv_prod 

            # api_series[b.id]['Qs'] = [ val / 1000 for val in api_series[b.id]['Qs']] if api_series[b.id].get('Qs') is not None else None
            # api_series[b.id]['SolarPVProduction'] = [ val / 1000 for val in api_series[b.id]['SolarPVProduction']] if api_series[b.id].get('SolarPVProduction') is not None else None
    
        renovations = await api.get_renovations(b_ids, simulation.scenario_id, simulation.year)
        heat_pumps: Dict[int, List[EnergyHeatPump]] = {}
        pv_installations:Dict[int, List[EnergyPhotovoltaicSystem]] = {}
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
        
        xml_attributes, xml_series, heat_tanks, dhw_tanks = get_xml_building_data(config['dest_folder'] + 'simulation.xml')
        climate_df = load_climate_file(config['dest_folder'] + climate.climate_file)


        # Combining data from different sources
        result = build_basopra_input(
            simulation = simulation, 
            api_attributes = api_attributes, 
            api_series = api_series, 
            xml_attributes = xml_attributes, 
            xml_series = xml_series, 
            climate = climate_df, 
            heat_tanks = heat_tanks, 
            dhw_tanks = dhw_tanks, 
            renovations = renovations,
            heat_pumps = heat_pumps,
            pv_installations = pv_installations,
        )
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
    # if not has_renov:
    if True:
        renovation_planner.add_EVs(extraction, simulation)
        renovation_planner.add_batteries(extraction, simulation)
        renovation_planner.add_HP_flags(extraction, simulation)
    else:
        # TODO implement renovations from OpenBEERS part
        renovation_planner.add_EVs(extraction, simulation)
        renovation_planner.add_openbeers_batteries(extraction, simulation)
        renovation_planner.add_openbeers_HP_flags(extraction, simulation)

    get_elec_prices(extraction, elec_pricer)
        
    calculate_heat_pump_size(f"{config['input_dir']}/HP_data.csv", extraction, simulation)

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
    try:
        if sim is None and os.path.exists(save_file):
            logger.info(f"Simulation {sim_name} not found on OpenBeers.")
            logger.info(f'Falling back on found extraction file: {save_file}')
            extraction = pickle_load(save_file)
        elif sim is None and not os.path.exists(save_file):
            logger.info(f"Simulation {sim_name} not found on OpenBeers and no fallback extraction available.")
            logger.info(f"Interrupting simulation for {sim_name}")
            return
        else:
            logger.info(f"Processing {sim.name}")
            extraction = await extract_simulation_data(sim, pricer)
    except Exception as e:
        tb = traceback.format_exc()
        data_logger.error(f'Simulation data retrieval and preparation failed for: \n {sim.name} with error {e} and stacktrace: \n {tb}')
        return None

    try:
        basopra_input = input_aggregator(extraction)
        basopra_output_files = run_basopra_simulation(basopra_input)
        print(basopra_output_files)
    except Exception as e:
        tb = traceback.format_exc()
        data_logger.error(f'Simulation processing by Basopra failed for : \n {sim.name} with error {e} and stacktrace: \n {tb}')
        return None

    # basopra_output = output_aggregator(basopra_output)

    # conf_mapping = config.Core.conf_mapping

    # for bid, cid in basopra_output.keys():
    #     if basopra_output[(bid, cid)]['simulation_outputs'] is not None:
    #         building_output = basopra_output[(bid, cid)]
    #         inputs = building_output['simulation_inputs']['hh']['series']
    #         outputs = building_output['simulation_outputs']
    #         input_output_combination = pd.merge(inputs, outputs, left_index=True, right_index=True)
    #         egid = building_output['simulation_inputs']['hh']['attributes']['egid']
    #         conf_name = conf_mapping[cid]
    #         output_file_name = f'{config.basopra_output_dir}{sim.name}/df_{bid}_{egid}_{conf_name}'
    #         dataframe_save(f'{output_file_name}.csv', input_output_combination)

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
            try:
                logger.info(f'From config.yaml, simulation to process is: {name}')
                api_wrapper = await ApiWrapper.from_config(config['openbeers_address'])
                async with api_wrapper as api:
                    simulation = await api.get_simulation(name)
                
                if simulation is None:
                    logger.warning(f'Simulation "{name}" is None. Skipping.')
                    continue

                pricer = ElectricityPricer()

                try:
                    await process_simulation(name, simulation, pricer)
                except Exception as e:
                    logger.error(f'Processing failed for simulation "{name}": {e}')
                    continue

            except Exception as e:
                tb = traceback.format_exc()
                logger.error(f'Unexpected error while processing simulation "{name}": {e}')
                data_logger.error(f'Unexpected error while processing simulation "{name}": {e}\n {tb}')
                continue

async def list_simulations() -> List[str]:
    logger.info('Starting loop through simulations')
    api_wrapper = await ApiWrapper.from_config(config['openbeers_address'])
    async with api_wrapper as api:
        simulations = await api.get_all_simulations()
    sim_names = [sim.name for sim in simulations]
    sim_names.sort()
    return sim_names

async def extract_openbeers_data(
        simulation: Simulation,
        planner: RenovationPlanning,
        pricer: ElectricityPricer,
) -> List[str]:
    logger.info(f"Extracting all data from simulation: {simulation.id} - {simulation.name}")
    save_dir = f"{config['simulation_extraction_dir']}/{simulation.name}_noHP"

    if os.path.exists(save_dir) and config.cache:
        logger.info(f"Simulation extraction file already exists. {simulation.name}")
        files = [os.path.join(save_dir, f) for f in os.listdir(save_dir) if os.path.isfile(os.path.join(save_dir, f))]
        return files

    extraction, has_renov = await run_pipeline(simulation)

    if True:
        planner.add_EVs(extraction, simulation)
        planner.add_batteries(extraction, simulation)
        planner.add_HP_flags(extraction, simulation)
    else:
        # TODO implement renovations from OpenBEERS part
        planner.add_EVs(extraction, simulation)
        planner.add_openbeers_batteries(extraction, simulation)
        planner.add_openbeers_HP_flags(extraction, simulation)
    
    get_elec_prices(extraction, pricer)

    extracted_files = []
    for bid, b_data in extraction.items():
        save_file = f"{save_dir}/{bid}_{b_data['attributes']['egid']}.pkl"
        pickle_save(save_file, {bid: b_data})
        extracted_files.append(save_file)

    return extracted_files

async def get_one_simulation_data(
        sim_name: str,
        sim: Simulation,
):
    extracted_sims = []
    save_dir = f'{config.simulation_extraction_dir}/{sim.name}_noHP'
    planner = RenovationPlanning(config.renovation_planning.save_file)
    pricer = ElectricityPricer()
    try:
        if sim is None and os.path.exists(save_dir):
            logger.info(f"Simulation {sim_name} not found on OpenBeers.")
            logger.info(f"Falling back on found extraction dir: {save_dir}")
            files = [os.path.join(save_dir, f) for f in os.listdir(save_dir) if os.path.isfile(os.path.join(save_dir, f))]
            extracted_sims.extend(files)
        elif sim is None and not os.path.exists(save_dir):
            logger.info(f"Simulation {sim_name} not found on OpenBeers and no fallback extraction available.")
            logger.info(f"Interrupting simulation for {sim_name}")
        else:
            logger.info(f"Processing {sim.name}")
            save_files = await extract_openbeers_data(sim, planner, pricer)
            extracted_sims.extend(save_files)
    except Exception as e:
        tb = traceback.format_exc()
        data_logger.error(f"Simulation data retrieval and preparation failed for: \n{sim.name} with error {e} and stacktrace: \n{tb}")
    return extracted_sims

def get_one_simulation_data_sync(sim_name: str, sim: Simulation):
    return asyncio.run(get_one_simulation_data(sim_name, sim))


def get_openbeers_data(
        sim_names: List[str],
        simulations: List[Simulation],
) -> List[str]:
    simulation_retrieving_inputs = (
        {
            'sim_name': name,
            'sim': sim,
        } for name, sim in zip(sim_names, simulations)
    )
    results = run_parallel(
        get_one_simulation_data_sync,
        simulation_retrieving_inputs,
        # config.multiprocessing,
        False,
        processes=config.max_processes,
        mode='kwargs',
    )
    results = [item for sublist in results for item in sublist]
    return results

def alternate(simulations: List[Simulation]) -> None:
    simulation_names = config.simulation_names
   
    # Retrieving and saving Simulation data
    try:
        simulation_save_files = get_openbeers_data(simulation_names, simulations)
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f'Unexpected error while retrieving OpenBeers data: {e}')
        data_logger.error(f'Unexpected error while retrieving OpenBeers data: {e}\n {tb}')

    cleanup(config['dest_folder'])

    # Creating and saving Heat Pumps
    try:
        files_for_basopra = heat_pump_dimensioning_from_files(simulation_save_files, f"{config['input_dir']}/HP_data.csv")
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Unexpected error while dimensionning Heat Pumps: {e}")
        data_logger.error(f"Unexpected error while dimensionning Heat Pumps: {e}\n{tb}")

    # Initiating Basopra simulations
    try:
        output_file_names = run_basopra_simulation_from_file_names(files_for_basopra)
        logger.info("Finished all Basopra runs")
        for file in output_file_names:
            print(file)
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Unexpected error while running Basopra simulations: {e}\n{tb}")

async def get_simulations() -> List[Simulation]:
    logger.info("Starting loop through simulations")
    logger.info("Entering list mode. Only given simulation names will be processed")
    if config.loop_mode:
        simulation_names = await list_simulations()
    else:
        simulation_names = config.simulation_names

    simulations = []
    for name in simulation_names:
        try:
            logger.info(f"From config.yaml, simulation to process is: {name}")
            api_wrapper = await ApiWrapper.from_config(config['openbeers_address'])
            async with api_wrapper as api:
                simulation = await api.get_simulation(name)
            
            if simulation is None:
                logger.warning(f'Simulation "{name}" is None. Skipping.')
                continue

            simulations.append(simulation)
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f'Unexpected error while processing simulation "{name}": {e}')
            data_logger.error(f'Unexpected error while processing simulation "{name}": {e}\n {tb}')
            continue
    return simulations

if __name__ == "__main__":
    # asyncio.run(list_simulations())
    # asyncio.run(main())
    simulations = asyncio.run(get_simulations())
    alternate(simulations)