from lxml import etree
import re
import pandas as pd
import numpy as np
from lxml.etree import _Element as Element
from typing import Any, Mapping, Dict
from Core import save_obj
from elec_pricer import get_consumption_category, ElectricityPricer

path_to_citysim_inputs = "C:/Users/alejandr.penabell/Downloads/simulations (1)/simulations/val_de_bagnes_41_climate_contemporary_pv_roof_2025/"
path_to_citysim_inputs = "/home/luciole/Documents/simulations/simulations/val_de_bagnes_41_climate_contemporary_pv_roof_2025/"
inputs_file_name = "simulation.xml"
cli_file_name = "Val-de-Bagnes_Contemporary_2025.cli"
citysim_output_file_name = "simulation_TH.out"
separator = "\t"

pv_pannel_types = {
    "JA Solar Deep Blue JAM54D41-455/LB": {
        "x": 1.762,
        "y": 1.1134,
        "capacity": 455,
    },
}

coord_points = ("V0", "V1", "V2")

def parse_point(coord_element: Element) -> np.array:
    x = float(coord_element.get("x"))
    y = float(coord_element.get("y"))
    z = float(coord_element.get("z"))
    return np.array([x,y,z])

def triangle_area_3d(p1:np.array, p2:np.array, p3:np.array) -> float:
    ab = p2 - p1
    ac = p3 - p1
    cross = np.cross(ab, ac)
    return 0.5 * np.linalg.norm(cross)

def get_surface(element:Element) -> float:
    coordinates = []
    for point_name in coord_points:
        point = element.xpath(f"./{point_name}")
        coordinates.append(point[0])
    p1, p2, p3 = map(parse_point, coordinates)
    area = triangle_area_3d(p1, p2, p3)
    return area

def has_pv_child(element:Element) -> bool:
    if len(element.xpath("./PV")) == 0:
        return False
    return True

def get_pv_info(element:Element) -> Mapping[str, str]:
    pv = element.xpath("./PV")[0]
    return pv.attrib

def get_pannel_specs(pannel_name: str) -> float:
    if (pannel_specs := pv_pannel_types.get(pannel_name)) is None:
        return None    
    if pannel_specs.get("m2_capacity") is None:
        x = pannel_specs.get('x')
        y = pannel_specs.get('y')
        capacity = pannel_specs.get('capacity')
        m2_capacity = capacity/x/y
        pannel_specs["m2_capacity"] = m2_capacity
    return pannel_specs.get("m2_capacity")

def calculate_pv_capacity(element: Element) -> float:
    if not has_pv_child(element):
        return 0
    surface = get_surface(element)
    pv_info = get_pv_info(element)
    pv_coverage = pv_info.get("pvRatio")
    pannel_type = pv_info.get("name")
    m2_capacity = get_pannel_specs(pannel_type)
    return surface * float(pv_coverage) * m2_capacity

def get_element_pv(building_zone: Element, element_name:str) -> float:
    total_pv_capacity = 0
    for element in building_zone.xpath(f"./{element_name}"):
        pv_capacity = calculate_pv_capacity(element)
        total_pv_capacity += pv_capacity
    # return {"pv_capacity": total_pv_capacity  / 1000, "unit": "kW"}
    return float(total_pv_capacity / 1000)

def get_zone_pv(zone: Element) -> Dict[str, float]:
    zone_pv_capacity = {'unit': 'kW'}
    for element_name in ["Roof", "Wall"]:
        zone_pv_capacity[element_name] = get_element_pv(zone, element_name)
    return zone_pv_capacity

def get_building_pv(building: Element) -> Dict[str, Any]:
    zone = building.xpath("./Zone")[0]
    zone_pv_capacity = get_zone_pv(zone)
    return zone_pv_capacity

def get_building_usage(building: Element) -> int:
    zone = building.xpath("./Zone")[0]
    zone_occupants = zone.xpath("./Occupants")[0]
    return zone_occupants.attrib['activityType']

def get_energy_consumption(building: Element) -> float:## APB: what is this for ???
    return 6500

def get_temperature(path_to_cli_file: str) -> Dict[str, float]:
    
    # Read all lines to locate the header
    with open(path_to_cli_file, 'r') as f:
        for i, line in enumerate(f):
            if line.strip().startswith('dm'):
                header_row = i
                break

    # Load the data into a DataFrame, using whitespace delimitation
    df = pd.read_csv(
        path_to_cli_file,
        sep=r'\s+',
        header=header_row-1,
        comment=None
    )

    # Extract the Ts column
    Ts_series = df['Ts']
    return Ts_series
    
def extract_building_output(col):
    pattern = r'^(?P<building>\d+\([^)]*\))(?::\d+)?\:(?P<output>\w+)\((?P<unit>[^)]+)\)$'
    match = re.match(pattern, col)
    if match:
        return match.group('building'), match.group('output'), match.group('unit')
    return None, None, None

def process_citysim_output(df: pd.DataFrame):
    # Extract unique building names
    building_names = set()
    pattern_name = re.compile(r'^(\d+\([^)]*\))')
    for col in df.columns:
        if col.startswith('#') or col.startswith('Unnamed'):
            continue
        match = pattern_name.match(col)
        if match:
            building_names.add(match.group(1))
    
    outputs_of_interest = ['SolarPVProduction', 'ElectricConsumption', 'Qs']
    building_outputs = {}
    for col in df.columns:
        if col.startswith('#timeStep') or col.startswith('Unnamed'):
            continue
        building, output, unit = extract_building_output(col)
        if building and output in outputs_of_interest:
            if building not in building_outputs:
                building_outputs[building] = {}
            # Convert from Wh to kWh for SolarPVProduction and Qs
            if output in ['SolarPVProduction', 'Qs','Heating'] and unit == 'Wh':
                building_outputs[building][output] = df[col] / 1000.0
            else:
                building_outputs[building][output] = df[col] 
    
    # Create annual summary (summing each output).
    annual_summary = {}
    for building in building_names:
        annual_summary[building] = {}
        for output in outputs_of_interest:
            if building in building_outputs and output in building_outputs[building]:
                annual_summary[building][output] = building_outputs[building][output].sum()
            else:
                annual_summary[building][output] = None
        
    summary_df = pd.DataFrame.from_dict(annual_summary, orient = 'index')

    return building_names, building_outputs, annual_summary, summary_df


def main():
    # retrieve input information
    electricity_pricer = ElectricityPricer()
    tree = etree.parse(path_to_citysim_inputs + inputs_file_name)
    root = tree.getroot()

    pv_capacities = {}
    consumption_categories = {}
    electricity_prices = {}
    temperature={}

    municipality_info = root.xpath('/CitySim/Climate')
    municipality_location_file_name = municipality_info[0].get('location')

    before_first_underscore = municipality_location_file_name.split('_')[0]

    municipality_name = before_first_underscore.replace('-', ' ')

    for building in root.xpath('//Building'):
        building_id = building.get('id')
        building_name = building.get('Name')
        building_concat_name = f"{building_id}({building_name})"
        temperature[building_concat_name]=get_temperature(path_to_citysim_inputs+cli_file_name)
        pv_capacities[building_concat_name] = get_building_pv(building)

        building_activity = get_building_usage(building)
        consumption = get_energy_consumption(building)
        consumption_category = get_consumption_category(building_activity, consumption)
        consumption_categories[building_concat_name] = consumption_category
        electricity_prices[building_concat_name] = electricity_pricer.get_electricity_price(municipality_name, consumption_category)


    # retrieve output information
    df = pd.read_csv(path_to_citysim_inputs+citysim_output_file_name, sep=separator)
    # print(df.head())
    building_names, building_outputs, annual_summary, summary_df = process_citysim_output(df)
    for key in building_outputs.keys():
        building_outputs[key]['pv_capacity'] = pv_capacities[key]
        building_outputs[key]['consumption_category'] = consumption_categories[key]
        building_outputs[key]['elec_price'] = electricity_prices[key]
        building_outputs[key]['temperature'] = temperature[key]
    for key, value in building_outputs.items():
        print(key)
        print(value.keys())
        print(value['pv_capacity'])
        print(value['consumption_category'])
        print(value['elec_price'])
    save_obj(building_outputs, 'test')


if __name__ == "__main__":
    main()