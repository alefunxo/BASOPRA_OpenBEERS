import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pathlib import Path
import pickle

import numpy as np
import pandas as pd
from pandas import DataFrame
from utils.logger import logger
from config.loader import config
from typing import Any, Dict, List
# TODO remove this import from here and move the logic that uses it elsewhere
from heat_pump.pump_sizer import HeatPumpDesign

def pickle_save(path: str, any_object: Any) -> None:
    logger.info(f"Saving {type(any_object)} type object to: {path}.")
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists

    with open(path, 'wb') as f:
        pickle.dump(any_object, f)
    logger.info(f"File successfully saved at {path}.")

def pickle_load(path: str) -> Any:
    logger.info(f"Loading file: '{path}' as python object.")
    my_object = None
    with open(path, 'rb') as f:
        my_object = pickle.load(f)
    logger.info(f"File '{path}' successfully loaded as {type(my_object)} type object.")
    return my_object


# def get_row_wise_mean(dfs: List[DataFrame]) -> DataFrame:
#     return pd.concat([df['value'] for df in dfs], axis=1).mean(axis=1)
# 
# def get_row_wise_sum(dfs: List[DataFrame]) -> DataFrame:
#     return pd.concat([df['value'] for df in dfs], axis=1).sum(axis=1)
# 
# def get_row_wise_median(dfs: List[DataFrame]) -> DataFrame:
#     return pd.concat([df['value'] for df in dfs], axis=1).median(axis=1)
#     
# def get_row_wise_random_value(dfs: List[DataFrame]) -> DataFrame:
#     return pd.concat([df['value'] for df in dfs], axis=1).apply(lambda row: np.random.choice(row), axis=1)
# 
# def get_row_wise_first_value(dfs: List[DataFrame]) -> DataFrame:
#     return dfs[0]
# 
# dataframe_combinations = {
#     'mean': get_row_wise_mean,
#     'sum': get_row_wise_sum,
#     'median': get_row_wise_median,
#     'random': get_row_wise_random_value,
#     'first': get_row_wise_first_value,
# }

agg_funcs = {
    'mean':     lambda row: np.mean(row),
    'sum':      lambda row: np.sum(row),
    'median':   lambda row: np.median(row),
    'random':   lambda row: np.median(row),
    'first':    lambda row: row.iloc[0]
}

def apply_aggregations(dfs: List[DataFrame], aggregation_methods: Dict[str, str]) -> DataFrame:
    # Retrieving aggregation functions
    per_column_aggregation = {}
    fallback_columns = {}
    for col, method in aggregation_methods.items():
        if method in agg_funcs:
            per_column_aggregation[col] = agg_funcs[method]
        else: 
            fallback_columns[col] = method

    aggregated_data = pd.DataFrame()
    # Columns with aggregation functions
    for col, agg_func in per_column_aggregation.items():
        if dfs[0].get(col) is None:
            continue
        stacked = pd.concat([df[col] for df in dfs], axis=1)
        aggregated_data[col] = stacked.apply(agg_func, axis=1)
    # Columns with default values
    for col, default_value in fallback_columns.items():
        num_rows = len(dfs[0])
        aggregated_data[col] = [default_value] * num_rows
    
    return aggregated_data 


def generate_aggregated_zone_data(buildings_data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    aggregation_methods = config.aggregation_methods

    # attributes: 
    attribute_dfs = []
    for data in buildings_data.values():
        attribute_dfs.append(DataFrame(data['attributes']))
    attributes_aggregation = apply_aggregations(attribute_dfs, aggregation_methods.attributes)

    # series:
    series_dfs = []
    for data in buildings_data.values():
        series_dfs.append(data['series'])
    series_aggregation = apply_aggregations(attribute_dfs, aggregation_methods.series)

    # heat pump attributes:
    heat_pump_attribute_dfs = []
    for data in buildings_data.values():
        heat_pump_attribute_dfs.append(DataFrame(data['heat_pump'].attributes))
    heat_pump_attributes_aggregation = apply_aggregations(heat_pump_attribute_dfs, aggregation_methods.heat_pump.attributes)

    # heat pump series:
    heat_pump_series_dfs = []
    for data in buildings_data.values():
        heat_pump_series_dfs.append(data['heat_pump'].series)
    heat_pump_series_aggregation = apply_aggregations(heat_pump_series_dfs, aggregation_methods.heat_pump.series)

    pump = HeatPumpDesign(heat_pump_series_aggregation, heat_pump_attributes_aggregation)

    aggregated_building_data = {
        'attributes': attributes_aggregation,
        'series': series_aggregation,
        'heat_pump': pump,
    }

    return aggregated_building_data

if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

    df_1 = DataFrame({
        'DD':                   [1, 2, 3],
        'ElectricConsumption':  [1, 2, 3],
        'FF':                   [1, 2, 3],
        'N':                    [1, 2, 3],
        'h':                    [1, 2, 3],
        'dm':                   [1, 2, 3],
    })
    df_2 = DataFrame({
        'DD':                   [4, 5, 6],
        'ElectricConsumption':  [4, 5, 6],
        'FF':                   [4, 5, 6],
        'N':                    [4, 5, 6],
        'h':                    [4, 5, 6],
        'dm':                   [4, 5, 6],
    })
    df_3 = DataFrame({
        'DD':                   [7, 8, 9],
        'ElectricConsumption':  [7, 8, 9],
        'FF':                   [7, 8, 9],
        'N':                    [7, 8, 9],
        'h':                    [7, 8, 9],
        'dm':                   [7, 8, 9],
    })
    pds = [df_1, df_2, df_3]
    pd = apply_aggregations(pds, config.aggregation_methods.series)
    print(pd)