import os
import requests
import pandas as pd
from io import StringIO
from typing import Optional

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

if __name__ == "__main__":
    address = 'http://openbeers.hopto.org/simulations/'
    file_name = 'Val-de-Bagnes_Contemporary_2025.cli'
    simulation_name = 'val_de_bagnes_148_climate_contemporary_pv_roof_2025'
    path = '../temp'
    print("testing download_file_from_wap")
    download_file_from_wap(
        address,
        simulation_name,
        file_name,
        path,
    )
    print("testing load_climate_file")
    try:
        df = load_climate_file(
            f"{path}/{file_name}"
        )
        print(df.head())
    except Exception as e:
        print(f'Failed test: {e}')
