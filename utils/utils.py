from pathlib import Path
import pickle
from utils.logger import logger
from typing import Any

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