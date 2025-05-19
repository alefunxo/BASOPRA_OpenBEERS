import os
import requests
import pandas as pd
from typing import Callable, Optional

def download_file_from_wap(
    server_address:str , 
    folder_name: str, 
    file_name: str, 
    save_path: str = "../temp"
) -> Optional[str]:
    """
    Downloads a file from a WAP-style HTTP server.

    Returns the full path to the downloaded file, or None on failure.
    """
    url = f"{server_address.rstrip('/')}/{folder_name.strip('/')}/{file_name}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        os.makedirs(save_path, exist_ok=True)
        local_file_path = os.path.join(save_path, file_name)
        with open(local_file_path, 'wb') as f:
            f.write(response.content)
        return local_file_path
    except requests.RequestException as e:
        print(f"Failed to download file: {e}")
        return None

def load_climate_file(filepath: str) -> pd.DataFrame:
    """
    Loads a whitespace-delimited climate data file into a pandas DataFrame.
    """
    return pd.read_csv(
        filepath,
        sep=r'\s+',
        skiprows=2,
        header=0,
    )

def load_and_cleanup(path: str, loader_func: Callable[[str], any]) -> any:
    """
    Uses the given loader_func to return the file contents and then takes care of removing the file
    """
    try:
        return loader_func(path)
    finally:
        if path and os.path.exists(path):
            os.remove(path)


if __name__ == "__main__":
    address = 'http://openbeers.hopto.org/simulations/'
    file_name = 'Val-de-Bagnes_Contemporary_2025.cli'
    simulation_name = 'val_de_bagnes_148_climate_contemporary_pv_roof_2025'
    path = '../temp'

    print("testing download_file_from_wap")
    file_path = download_file_from_wap(
        address,
        simulation_name,
        file_name,
        path,
    )

    print("testing load_climate_file")
    try:
        df = load_and_cleanup(file_path, load_climate_file)
        print(df.head())
    except Exception as e:
        print(f'Failed test: {e}')
