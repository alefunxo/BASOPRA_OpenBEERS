# Copyright © 2025 HES-SO Valais-Wallis <alejandro.penabello@hevs.ch>
# SPDX-FileContributor: Alejandro Penabello <alejandro.penabello@hevs.ch>
# SPDX-FileContributor: Lucien Troillet <lucien.troillet@hevs.ch>
#
# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path
import pickle

import numpy as np
import pandas as pd
from pandas import DataFrame
from utils.logger import logger
from config.loader import config
from typing import Union

from typing import Any, Dict, List, Tuple

def is_type(file_path, extension):
    path = os.path.splitext(file_path)[1].lower()
    return path == extension.lower()

def list_files_recursive(directory: str):
    def build_structure(path):
        structure = {}
        for file in path.iterdir():
            if file.is_dir():
                structure[file.name] = build_structure(file)
            else:
                structure.setdefault('files', []).append(file.name)
        return structure
    path = Path(directory)
    return build_structure(path)

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
