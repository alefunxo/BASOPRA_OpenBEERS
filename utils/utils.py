from pathlib import Path
import pickle

import numpy as np
import pandas as pd
from pandas import DataFrame
from utils.logger import logger
from config.loader import config
from typing import Union

from typing import Any, Dict, List, Tuple
# TODO remove this import from here and move the logic that uses it elsewhere
from heat_pump.pump_sizer import HeatPumpDesign

def dataframe_save(path: str, df: DataFrame, index: bool = False) -> None:
    logger.info(f"Saving {type(df)} type object to: {path}.")
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists
    df.to_csv(path, index=index)

def dataframe_load(path: str, index_col: Union[int, str, None] = None) -> DataFrame:
    path_obj = Path(path)

    if not path_obj.is_file():
        raise FileNotFoundError(f"CSV file not found: {path}")

    df = pd.read_csv(path, index_col=index_col)
    logger.info(f"Loaded DataFrame with shape {df.shape} from: {path}")
    return df

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

agg_funcs = {
    'mean':     lambda row: np.mean(row),
    'sum':      lambda row: np.sum(row),
    'median':   lambda row: np.median(row),
    'random':   lambda row: np.random.choice(row),
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


def generate_aggregated_zone_data(buildings_data: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
    aggregation_methods = config.aggregation_methods.input_aggregations

    # attributes: 
    attribute_dfs = []
    for data in buildings_data.values():
        attribute_dfs.append(DataFrame([data['attributes']]))
    attributes_aggregation = apply_aggregations(attribute_dfs, aggregation_methods.attributes)
    attributes_dict = attributes_aggregation.iloc[0].to_dict()

    # series:
    series_dfs = []
    for data in buildings_data.values():
        series_dfs.append(data['series'])
    series_aggregation = apply_aggregations(series_dfs, aggregation_methods.series)

    # heat pump attributes:
    heat_pump_attribute_dfs = []
    for data in buildings_data.values():
        heat_pump_attribute_dfs.append(DataFrame([data['heat_pump'].attributes]))
    heat_pump_attributes_aggregation = apply_aggregations(heat_pump_attribute_dfs, aggregation_methods.heat_pump.attributes)
    heat_pump_attributes_dict = heat_pump_attributes_aggregation.iloc[0].to_dict()

    # heat pump series:
    heat_pump_series_dfs = []
    for data in buildings_data.values():
        heat_pump_series_dfs.append(data['heat_pump'].series)
    heat_pump_series_aggregation = apply_aggregations(heat_pump_series_dfs, aggregation_methods.heat_pump.series)

    pump = HeatPumpDesign(heat_pump_series_aggregation, heat_pump_attributes_dict)

    aggregated_building_data = {
        'attributes': attributes_dict,
        'series': series_aggregation,
        'heat_pump': pump,
    }

    return aggregated_building_data

def generate_aggregated_basopra_output_data(buildings_data: Dict[Tuple[int, int], DataFrame]) -> Dict[Tuple[int, int], DataFrame]:
    aggregated_buildings = {}
    scenarios_found = []
    for key in buildings_data.keys():
        if key[0] == 0:
            scenarios_found.append(key[1])
    for scenario in scenarios_found:
        aggregated_buildings[(0, scenario)] = buildings_data.pop((0, scenario))

    columns_to_aggregate = config.aggregation_methods.output_aggregations

    output_series: Dict[int, List[DataFrame]] = {scenario: [] for scenario in scenarios_found}
    for key, data in buildings_data.items():
        output_series[key[1]].append(data)
    for scenario in scenarios_found:
        aggregation = apply_aggregations(output_series[scenario], columns_to_aggregate)
        common_cols = aggregated_buildings[(0, scenario)].columns.intersection(aggregation.columns)
        aggregated_buildings[(0, scenario)][common_cols] = aggregation[common_cols]
    return aggregated_buildings


# if __name__ == "__main__":
#     import sys
#     import os
#     sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# 
#     df_1 = DataFrame({
#         'DD':                   [1, 2, 3],
#         'ElectricConsumption':  [1, 2, 3],
#         'FF':                   [1, 2, 3],
#         'N':                    [1, 2, 3],
#         'h':                    [1, 2, 3],
#         'dm':                   [1, 2, 3],
#     })
#     df_2 = DataFrame({
#         'DD':                   [4, 5, 6],
#         'ElectricConsumption':  [4, 5, 6],
#         'FF':                   [4, 5, 6],
#         'N':                    [4, 5, 6],
#         'h':                    [4, 5, 6],
#         'dm':                   [4, 5, 6],
#     })
#     df_3 = DataFrame({
#         'DD':                   [10, 11, 12],
#         'ElectricConsumption':  [10, 11, 12],
#         'FF':                   [10, 11, 12],
#         'N':                    [10, 11, 12],
#         'h':                    [10, 11, 12],
#         'dm':                   [10, 11, 12],
#     })
#     pds = [df_1, df_2, df_3]
#     pd = apply_aggregations(pds, config.aggregation_methods.series)
#     print(pd)