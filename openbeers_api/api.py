import asyncio
from openbeers import ApiClient, Configuration, DefaultApi
from config.loader import config
from openbeers.rest import ApiException
from typing import Any, Dict, List, Optional
from openbeers.models import (
    Simulation, 
    Building, 
    EnergyHeatPump, 
    EnergyPhotovoltaicSystem, 
    EnergyRenovation, 
    TimeSeriesType, 
    TimeSeries, 
    AttributeType, 
    Attribute, 
    Climate, 
    Zone
)

from utils.multiprocessing_utils import run_parallel

class ApiWrapper:
    def __init__(self, api_client: ApiClient, api_instance: DefaultApi) -> None:
        self.semaphore = asyncio.Semaphore(10)
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
            async with self.semaphore:
                return await func(*args)
        except ApiException as e:
            print(f"API Error: {e}")
            return None
        except asyncio.TimeoutError:
            print("Request timed out")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None
    
    async def get_all_simulations(self) -> List[Simulation]:
        return await self.fetch(
            self.api.get_simulations_api_simulations_get
        )

    async def get_simulation(self, name: str) -> Optional[Simulation]:
        simulations = await self.get_all_simulations()
        return next((s for s in simulations if s.name == name), None)
    
    async def get_series_types(self, needed: List[str]) -> List[TimeSeriesType]:
        all_types = await self.fetch(
            self.api.get_time_series_types_api_time_series_types_get
        )
        return [t for t in all_types if t.name in needed]

    async def get_attribute_types(self, needed: List[str]) -> List[AttributeType]:
        all_types = await self.fetch(
            self.api.get_attribute_types_api_attribute_types_get
        )
        return [a for a in all_types if a.name in needed]
    
    async def get_buildings(self, zone_id: int) -> List[Building]:
        return await self.fetch(
            self.api.get_buildings_zone_id_api_buildings_zone_zone_id_get, 
            zone_id
        )

    async def get_climate(self, climate_id: int) -> Optional[Climate]:
        return await self.fetch(
            self.api.get_climate_api_climate_climate_id_get, 
            climate_id
        )

    async def get_attributes(self, object_id: int) -> List[Attribute]:
        return await self.fetch(
            self.api.get_attributes_object_id_api_attributes_object_object_id_get, 
            object_id
        )

    async def get_series(self, object_id: int, sim_id: int) -> List[TimeSeries]:
        return await self.fetch(
            self.api.get_time_series_object_id_simulation_id_api_time_series_s_object_object_id_simulation_simulation_id_get, 
            object_id, 
            sim_id
        )
    
    async def get_all_zones(self) -> List[Zone]:
        return await self.fetch(
            self.api.get_all_zones_api_zones_all_get
        )
    
    async def get_renovation(self, object_id: int) -> EnergyRenovation:
        return await self.fetch(
            self.api.get_energy_renovation_energy_renovation_id_get, 
            object_id
        )

    async def get_renovation_building_scenario_year(self, building_id: int, scenario_id: int, year: int) -> EnergyRenovation:
        return await self.fetch(
            self.api.get_energy_renovation_building_scenario_year_api_energy_renovation_building_building_id_scenario_scenario_id_year_scenario_year_get, 
            building_id, 
            scenario_id, 
            year
        )
    
    async def get_renovations(self, building_ids: List[int], scenario_id: int, year: int) -> Dict[int, EnergyRenovation]:
        renovations: Dict[int, EnergyRenovation] = {}
        for bid in building_ids:
            renovations[bid] = await self.get_renovation_building_scenario_year(bid, scenario_id, year)
        return renovations

    async def get_heat_pump(self, object_id: int) -> EnergyHeatPump:
        return await self.fetch(
            self.api.get_energy_heat_pump_api_energy_heat_pump_energy_heat_pump_id_get, 
            object_id
        )

    async def get_heat_pumps_from_renovation(self, renovation_id: int) -> List[EnergyHeatPump]:
        return await self.fetch(
            self.api.get_energy_heat_pump_energy_renovation_api_energy_heat_pumps_energy_renovation_energy_renovation_id_get, 
            renovation_id
        )
    
    async def get_PV(self, object_id: int) -> EnergyPhotovoltaicSystem:
        return await self.fetch(
            self.api.get_energy_renovation_api_energy_photovoltaic_system_energy_photovoltaic_system_id_get, 
            object_id
        )

    async def get_PV_from_renovation(self, renovation_id: int) -> List[EnergyPhotovoltaicSystem]:
        return await self.fetch(
            self.api.get_energy_photovoltaic_system_energy_renovation_api_energy_photovoltaic_systems_energy_renovation_energy_renovation_id_get, 
            renovation_id
        )

    async def get_attributes_for_buildings(self, buildings: List[Building], attribute_types: List[AttributeType]) ->Dict[Optional[int], Dict[str, Optional[Any]]]:
        tasks = {
            b.id: self.get_attributes(b.object_id)
            for b in buildings
        }
        keys = list(tasks.keys())
        values = list(tasks.values())

        # awaited_attributes = await asyncio.gather(*values)
        awaited_attributes = await gather_in_batches(values, batch_size=10)
        b_attributes = dict(zip(keys, awaited_attributes))

        attributes = {}
        for b in buildings:
            attrs = b_attributes[b.id]
            attributes[b.id] = {
                t.name: next((
                    getattr(a, f"value_{t_}") 
                    for t_ in ["string", "integer", "float"] 
                    if getattr(a, f"value_{t_}", None) is not None
                ),None)
                for t in attribute_types for a in attrs if a.attribute_type_id == t.id
            }
        return attributes

async def gather_in_batches(coros: list, batch_size: int = 10):
    results = []
    for i in range(0, len(coros), batch_size):
        batch = coros[i:i + batch_size]
        batch_result = await asyncio.gather(*batch)
        results.extend(batch_result)
        print(f"Retrieved batch {i}")
    return results
