import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element
import numpy as np
from typing import Dict

pv_pannel_types = {
    "JA Solar Deep Blue JAM54D41-455/LB": {
        "x": 1.762,
        "y": 1.1134,
        "capacity": 455,
    },
}

def parse_vertex(e: Element) -> np.ndarray:
    return np.array([float(e.attrib['x']), float(e.attrib['y']), float(e.attrib['z'])])

def triangle_area_3d(v0: np.ndarray, v1: np.ndarray, v2: np.ndarray) -> float:
    return 0.5 * np.linalg.norm(np.cross(v1 - v0, v2 - v0))

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

def get_municipality_name(xml_path: str):
    root = ET.parse(xml_path).getroot()
    climate = root.find("Climate")
    climate_file_name = climate.attrib.get('location')
    municipality_name = climate_file_name.split('_')[0].replace('-', ' ')
    return municipality_name

def get_building_attributes(building: Element):
    bid = building.attrib.get('id')
    name = building.attrib.get('Name')
    occupants = building.find("Zone/Occupants")
    activity = occupants.attrib.get('activityType')
    return bid, name, activity


def get_surface_n_PV(building: Element, surface_type: str) -> float:
    bld_id = building.attrib.get("id")
    total_area = 0.0
    pv_area = 0.0
    total_capacity = 0.0

    for zone in building.findall("Zone"):
        for surface in zone.findall(surface_type):
            try: 
                v0 = parse_vertex(surface.find("V0"))
                v1 = parse_vertex(surface.find("V1"))
                v2 = parse_vertex(surface.find("V2"))
                area = triangle_area_3d(v0, v1, v2)
                total_area += area 
            except Exception as e:
                print(f"Skipping malformed {surface_type} in building {bld_id}: {e}")
            
            # pv = surface.find("PV")
            if (pv := surface.find("PV")) is not None: 
                pv_ratio = pv.attrib.get('pvRatio')
                pannel_capacity = get_pannel_specs(pv.attrib.get('name'))
                total_capacity += area * float(pv_ratio) * pannel_capacity
                pv_area += area * float(pv_ratio)
    
    return total_area, pv_area, total_capacity

def get_all_building_attributes(xml_path: str) -> Dict[str, float]:
    root = ET.parse(xml_path).getroot()
    result: Dict[str, Dict[str, float]] = {}
    municipality_name = get_municipality_name(xml_path)

    for b in root.findall(".//Building"):
        bid, name, activity =  get_building_attributes(b)
        b_surfaces: Dict[str, float]= {
            'municipality_name': municipality_name,
            'bid': bid,
            'name': name,
            'activity': activity,
        }
        for surface_type in ['Roof', 'Wall', 'Floor']:
            surface, pv_surface, pv_capacity = get_surface_n_PV(b, surface_type)
            b_surfaces[f"{surface_type.lower()}_surface"] = surface
            b_surfaces[f"{surface_type.lower()}_pv_surface"] = pv_surface 
            b_surfaces[f"{surface_type.lower()}_pv_capacity"] = pv_capacity

        result[int(b.attrib['id'])] = b_surfaces

    return result



