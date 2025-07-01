import os
import yaml
from box import Box
from functools import lru_cache
from typing import Dict

def load_yaml_file(path: str) -> Dict:
    with open(path, 'r') as f:
        return yaml.safe_load(f) or {}

@lru_cache(maxsize=1)  # CAUTION: only *maxsize* configs can exist at most
def _load_configs(config_dir: str = 'config') -> Box:
    """
    Load and merge YAML configuration files from a directory into a single config object.

    - All `.yaml` or `.yml` files in the specified directory are loaded.
    - The file named `config.yaml` is merged directly into the top-level of the config.
    - All other YAML files are nested under a key named after the file (without extension).

    Args:
        config_dir (str): Path to the directory containing YAML configuration files.

    Returns:
        Box: A dictionary-like object with attribute-style access to configuration values.
    """
    merged = {}

    for filename in os.listdir(config_dir):
        if not filename.endswith((".yaml", ".yml")):
            continue
        full_path = os.path.join(config_dir, filename)
        key = os.path.splitext(filename)[0]

        config = load_yaml_file(full_path)

        if filename == "config.yaml":
            merged.update(config)
        else:
            merged[key] = config

    return Box(merged)

# Lazy singleton-style config object
# Usage: from config.loader import config
config: Box = _load_configs()