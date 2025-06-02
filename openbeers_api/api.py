from openbeers import ApiClient, Configuration, DefaultApi
from config.loader import config
from openbeers.rest import ApiException
from typing import Any, List, Optional
from openbeers.models import (
    Simulation, Building, TimeSeriesType, TimeSeries, AttributeType, Attribute, Climate
)

class ApiWrapper:
    def __init__(self, api_client: ApiClient, api_instance: DefaultApi) -> None:
        self.api_client = api_client
        self.api = api_instance

    async def __aenter__(self) -> "ApiWrapper":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.api_client.__aexit__(exc_type, exc_val, exc_tb)

    @classmethod
    async def from_config(cls, verify: bool = True) -> "ApiWrapper":
        configuration = Configuration(host=config['openbeers_address'])
        configuration.verify_ssl = verify
        api_client = ApiClient(configuration)
        api_instance = DefaultApi(api_client)
        return cls(api_client, api_instance)
    
    async def fetch (self, func: Any, *args: Any) -> Any:
        try:
            return await func(*args)
        except ApiException as e:
            print(f"API Error: {e}")
            return None
    
    async def get_all_simulations(self) -> List[Simulation]:
        return await self.fetch(self.api.get_simulations_api_simulations_get)

    async def get_simulation(self, name: str) -> Optional[Simulation]:
        simulations = await self.get_all_simulations()
        return next((s for s in simulations if s.name == name), None)
    
    async def get_series_types(self, needed: List[str]) -> List[TimeSeriesType]:
        all_types = await self.fetch(self.api.get_time_series_types_api_time_series_types_get)
        return [t for t in all_types if t.name in needed]

    async def get_attribute_types(self, needed: List[str]) -> List[AttributeType]:
        all_types = await self.fetch(self.api.get_attribute_types_api_attribute_types_get)
        return [a for a in all_types if a.name in needed]
    
    async def get_buildings(self, zone_id: int) -> List[Building]:
        return await self.fetch(self.api.get_buildings_zone_id_api_buildings_zone_zone_id_get, zone_id)

    async def get_climate(self, climate_id: int) -> Optional[Climate]:
        return await self.fetch(self.api.get_climate_api_climate_climate_id_get, climate_id)

    async def get_attributes(self, object_id: int) -> List[Attribute]:
        return await self.fetch(self.api.get_attributes_object_id_api_attributes_object_object_id_get, object_id)

    async def get_series(self, object_id: int, sim_id: int) -> List[TimeSeries]:
        return await self.fetch(self.api.get_time_series_object_id_simulation_id_api_time_series_s_object_object_id_simulation_simulation_id_get, object_id, sim_id)
