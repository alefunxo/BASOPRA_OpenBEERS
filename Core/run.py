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
from elec_pricer.pricer import ElectricityPricer
from heat_pump.pump_sizer import calculate_heat_pump_size
from utils.utils import pickle_save, pickle_load
from Core.main_beers import run_basopra_simulation



async def run_pipeline(simulation_name: str) -> dict:
    api_wrapper = await ApiWrapper.from_config(config['openbeers_address'])

    async with api_wrapper as api:
        sim = await api.get_simulation(simulation_name)
        buildings = await api.get_buildings(sim.zone_id)
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
            s = await api.get_series(b.object_id, sim.id)
            api_series[b.id] = {
                t.name: next(
                    (
                        pt.data for pt in s if pt.time_series_type_id == t.id
                    ), []) for t in ser_types
            }
    
        climate = await api.get_climate(sim.climate_id)

        wap_address = config['openbeers_address'] + '/simulations/' + sim.name + '/'
        files = list_files_in_directory(wap_address, verify=False)
        for f in files:
            download_file_from_wap(
                config['openbeers_address'] + "/simulations/",
                sim.name,
                f, 
                config['dest_folder'],
            )
        
        xml_attributes, xml_series = get_xml_building_data(config['dest_folder'] + 'simulation.xml')
        climate_df = load_climate_file(config['dest_folder'] + climate.climate_file)

        cleanup(config['dest_folder'])

        result = build_basopra_input(api_attributes, api_series, xml_attributes, xml_series, climate_df)
        return result


async def main() -> None:
    logger.info('Entering main')
    save_file = f'{config['input_dir']}result.pkl'

    if not os.path.exists(save_file):
        logger.info('Results file does not exist. Extracting/Computing Basopra Inputs')
        result = await run_pipeline(config['simulation_name']) 

        # Add Electricity price for each building
        pricer = ElectricityPricer()
        for bid, data in result.items():
            attributes = data['attributes']
            price_category = pricer.get_consumption_category(attributes.iloc[0]['activity'])
            elec_price = pricer.get_electricity_price(attributes.iloc[0]['municipality_name'], price_category)
            attributes['elec_price'] = elec_price

        for bid, data in result.items():
            print(f"Building {bid} → Attributes:\n", data['attributes'].to_string(index=False))
            print(" → Series samples: \n", data['series'].head())

        calculate_heat_pump_size(f'{config['input_dir']}/HP_data.csv', result)

        print(type(result))
        print(result.keys())
        pickle_save(save_file, result)
    else:
        logger.info('Results file exists. Loading Basopra Inputs.')
        result = pickle_load(save_file)
    
    run_basopra_simulation(result)


if __name__ == "__main__":
    asyncio.run(main())