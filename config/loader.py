import os
import yaml
from box import Box
from functools import lru_cache
from typing import Any

@lru_cache(maxsize=1)
def _load_config(path: str = 'config/config.yaml') -> Box:
    with open(path, 'r') as f:
        config_dict = yaml.safe_load(f)
    config_dict['dest_folder'] = os.path.expanduser(config_dict['dest_folder'])
    return Box(config_dict)

# Lazy singleton-style config object
# Usage: from config.loader import config
config: Box = _load_config()