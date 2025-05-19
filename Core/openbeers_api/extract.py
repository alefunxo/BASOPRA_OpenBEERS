import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element
import numpy as np
from typing import Dict

def parse_vertex(e: Element) -> np.ndarray:
    return np.array([float(e.attrib['x']), float(e.attrib['y']), float(e.attrib['z'])])

def triangle_area_3d(v0: np.ndarray, v1: np.ndarray, v2: np.ndarray) -> float:
    return 0.5 * np.linalg.norm(np.cross(v1 - v0, v2 - v0))

def get_surface_areas(building: Element, surface_type: str) -> float:
    bld_id = building.attrib.get("id")
    total_area = 0.0

    for zone in building.findall("Zone"):
        for surface in zone.findall(surface_type):
            try: 
                v0 = parse_vertex(surface.find("v0"))
                v1 = parse_vertex(surface.find("v1"))
                v2 = parse_vertex(surface.find("v2"))
                total_area += triangle_area_3d(v0, v1, v2)
            except Exception as e:
                print(f"Skipping malformed {surface_type} in building {bld_id}: {e}")
    
    return total_area

def get_all_building_areas(xml_path: str) -> Dict[str, float]:
    root = ET.parse(xml_path).getroot()
    result: Dict[str, Dict[str, float]] = {}
    for b in root.findall(".//Building"):
        b_surfaces: Dict[str, float]= {
            'Floor': get_surface_areas(b, 'Floor'),
            'Roof': get_surface_areas(b, 'Roof'),
        }
        result[b.attrib['id']] = b_surfaces
    return result
