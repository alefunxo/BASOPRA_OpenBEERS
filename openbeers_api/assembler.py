import pandas as pd
from typing import Dict, Any

surfaces = ['Roof', 'Wall', 'Ground']

def build_basopra_input(
    extracted_attributes: Dict[str, Dict[str, float]],
    attributes: Dict[str, Dict[str, Any]],
    series: dict[str, Dict[str, list]],
    climate: pd.DataFrame,
) -> Dict[str, Dict[str, pd.DataFrame]]:
    output = {}
    for bid in attributes:
        attr_df = pd.DataFrame([attributes[bid]])
        b_attributes = extracted_attributes.get(bid)
        if b_attributes:
            for attr_name in b_attributes.keys():
                attr_df[attr_name] = b_attributes.get(attr_name)
        else:
            continue

        ser_df = climate.copy()
        for key, values in series.get(bid, {}).items():
            if len(values) == len(ser_df):
                ser_df[key] = values
            else:
                print(f"⚠️ Skipping {key} for building {bid}: {len(values)} values (expected {len(ser_df)})")

        # for key, values in series.get(bid, {}).items():
        #     ser_df[key] = values

        output[bid] = {
            'attributes': attr_df,
            'series': ser_df,
        }
    return output
