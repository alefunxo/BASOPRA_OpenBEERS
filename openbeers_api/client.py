import pandas as pd
import openbeers
from openbeers import ApiClient, Configuration
from openbeers.rest import ApiException
from openbeers.models import (
    Simulation, Building, TimeSeriesType, AttributeType, Climate
)
from typing import Optional, Any
from config.loader import config
from openbeers_api.utils import download_file_from_wap, load_and_cleanup, load_climate_file

class OpenBeersClient:
    def __init__(self, api_client: ApiClient, api_instance: openbeers.DefaultApi) -> None:
        self.api_client = api_client
        self.api_instance = api_instance
        self.simulation: Optional[Simulation] = None
        self.series_types: list[TimeSeriesType] = []
        self.attribute_types: list[AttributeType] = []
        self.buildings: list[Building] = []
        self.building_attributes: dict[int, dict[str, dict[str, Any]]] = {}
        self.building_series: dict[int, dict[str, list[float]]] = {}
        self.climate: Optional[Climate] = None
        self.climate_data: Optional[pd.DataFrame] = None
        self.basopra_input: dict[int, dict[str, pd.DataFrame]] = {}

    @classmethod
    async def from_config(cls) -> "OpenBeersClient":
        configuration = Configuration(host=config['openbeers_address'])
        configuration.verify_ssl = False
        api_client = ApiClient(configuration)
        api_instance = openbeers.DefaultApi(api_client)
        return cls(api_client, api_instance)

    async def close(self) -> None:
        await self.api_client.__aexit__(None, None, None)

    async def prepare_basopra_input(self) -> None:
        sim_name = config['simulation_name']
        needed_series = config['needed_series']
        needed_attrs = config['needed_attributes']
        dest_folder = config['dest_folder']
        base_url = config['openbeers_address']

        self.series_types = [s for s in await self.get_series_types() if s.name in needed_series]
        self.attribute_types = [a for a in await self.get_attribute_types() if a.name in needed_attrs]
        self.simulation = await self.get_simulation(sim_name)
        self.buildings = await self.get_simulation_buildings(self.simulation)

        for building in self.buildings:
            self.building_attributes[building.id] = await self.get_building_attributes(building, self.attribute_types)
            self.building_series[building.id] = await self.get_building_series(self.simulation, building, self.series_types)

        self.climate = await self.get_simulation_climate(self.simulation)
        path = download_file_from_wap(base_url + '/simulations', self.simulation.name, self.climate.climate_file, dest_folder)
        self.climate_data = load_and_cleanup(path, load_climate_file)

        self.build_basopra_input()

    def build_basopra_input(self) -> None:
        if self.climate_data is None:
            raise ValueError("climate_data is not loaded")
        
        ta_column = self.climate_data['Ta']
        basopra_input: dict[int, dict[str, pd.DataFrame]] = {}
        for building in self.buildings:
            building_dfs: dict[str, pd.DataFrame] = {}

            df = ta_column.to_frame()
            for key, values in self.building_series[building.id].items():
                df[key] = values
                building_dfs['series'] = df
            
            attr_df = pd.DataFrame()
            for key, val in self.building_attributes[building.id].items():
                selected_val = next((v for v in val.values() if v is not None), None)
                attr_df[key] = [selected_val]
            building_dfs['attributes'] = attr_df

            basopra_input[building.id] = building_dfs
        
        self.basopra_input = basopra_input


    async def get_series_types(self) -> list[TimeSeriesType]:
        return await self._call(self.api_instance.get_time_series_types_api_time_series_types_get)

    async def get_attribute_types(self) -> list[AttributeType]:
        return await self._call(self.api_instance.get_attribute_types_api_attribute_types_get)
    
    async def get_simulation(self, simulation_name: str) -> Optional[Simulation]:
        simulations = await self._call(self.api_instance.get_simulations_api_simulations_get)
        return next((s for s in simulations if s.name == simulation_name), None)

    async def get_simulation_buildings(self, simulation: Simulation) -> list[Building]:
        return await self._call(self.api_instance.get_buildings_zone_id_api_buildings_zone_zone_id_get, simulation.zone_id)

    async def get_building_attributes(self, building: Building, attribute_types: list[AttributeType]) -> dict[str, dict[str, Any]]:
        all_attrs = await self._call(self.api_instance.get_attributes_object_id_api_attributes_object_object_id_get, building.object_id)
        data: dict[str, dict[str, Any]] = {}
        for attr_type in attribute_types:
            for a in all_attrs:
                if a.attribute_type_id == attr_type.id:
                    data[attr_type.name] = {
                        'value_string': a.value_string,
                        'value_integer': a.value_integer,
                        'value_float': a.value_float,
                    }
        return data
    
    async def get_building_series(self, simulation: Simulation, building: Building, series_types: list[TimeSeriesType]) -> dict[str, list[float]]:
        all_series = await self._call(
            self.api_instance.get_time_series_object_id_simulation_id_api_time_series_s_object_object_id_simulation_simulation_id_get,
            building.object_id,
            simulation.id,
        )
        data: dict[str, list[float]] = {}
        for s_type in series_types:
            for series in all_series:
                if series.time_series_type_id == s_type.id:
                    data[s_type.name] = series.data
        return data
    
    async def get_simulation_climate(self, simulation: Simulation) -> Optional[Climate]:
        return await self._call(self.api_instance.get_climate_api_climate_climate_id_get, simulation.climate_id)
    
    async def _call(self, func: Any, *args: Any) -> Any:
        try:
            return await(func(*args))
        except ApiException as e:
            print(f"API call failed: {e}")
            return None

if __name__ == "__main__":
    import asyncio

    async def test():
        client = await OpenBeersClient.from_config()
        await client.prepare_basopra_input()
        await client.close()
        print(client.basopra_input)
    
    asyncio.run(test())