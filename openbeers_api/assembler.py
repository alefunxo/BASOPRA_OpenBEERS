import pandas as pd
from typing import Dict, Any
from openbeers_api.integrity_checker import conduct_building_sanity_check

surfaces = ['Roof', 'Wall', 'Ground']

def build_basopra_input(
    api_attributes: Dict[str, Dict[str, Any]],
    api_series: dict[str, Dict[str, list]],
    xml_attributes: Dict[str, Dict[str, float]],
    xml_series: Dict[str, Dict[str, list]],
    climate: pd.DataFrame,
) -> Dict[str, Dict[str, pd.DataFrame]]:
    output = {}
    for bid in api_attributes:
        attributes = api_attributes[bid]
        building_xml_attributes = xml_attributes.get(bid)
        if building_xml_attributes:
            for attr_name in building_xml_attributes.keys():
                attributes[attr_name] = building_xml_attributes.get(attr_name)
        else:
            continue

        ser_df = climate.copy()
        for key, values in api_series.get(bid, {}).items():
            if len(values) == len(ser_df):
                ser_df[key] = values
            else:
                print(f"⚠️ Skipping {key} for building {bid}: {len(values)} values (expected {len(ser_df)})")

        for key, values in xml_series.get(bid, {}).items():
            if len(values) == len(ser_df):
                ser_df[key] = values
            else:
                print(f"⚠️ Skipping {key} for building {bid}: {len(values)} values (expected {len(ser_df)})")

        output[bid] = {
            'attributes': attributes,
            'series': ser_df,
        }

    conduct_building_sanity_check(output)

    return output
