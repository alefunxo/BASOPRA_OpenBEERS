import shutil
import os
import pandas as pd
import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import Any, Dict, List, Callable, Optional


def download_file_from_wap(
    server_address: str,
    folder: str,
    filename: str,
    dest: str,
) -> Optional[str]:
    url = f"{server_address.rstrip('/')}/{folder.strip('/')}/{filename}"
    os.makedirs(dest, exist_ok=True)
    path = os.path.join(dest, filename)
    try:
        r = requests.get(url)
        r.raise_for_status()
        with open(path, 'wb') as f:
            f.write(r.content)
        return path
    except Exception as e:
        print(f"Failed to download {filename}: {e}")
        return None

def list_files_in_directory(directory_url: str, verify: bool = True) -> List[str]:
    response = requests.get(directory_url, verify=verify)
    soup = BeautifulSoup(response.text, 'html.parser')
    return [a['href'] for a in soup.find_all('a') if not a['href'].endswith('/')]
    
def load_climate_file(path: str) -> pd.DataFrame:
    return pd.read_csv(path, sep=r'\s+', skiprows=2, header=0)

def load_and_cleanup(path: str, loader: Callable[[str], Any]) -> Any:
    try:
        return loader(path)
    finally:
        if os.path.exists(path):
            os.remove(path)

def cleanup(path: str,) -> None:
    if os.path.exists(path):
        shutil.rmtree(path)

def parse_simulation_metadata(path: str) -> Dict[str, Any]:
    root = ET.parse(path).getroot()
    return {
        'name': root.attrib.get('name'),
        'climate_file': root.find("Climate").attrib.get("location"),
    }