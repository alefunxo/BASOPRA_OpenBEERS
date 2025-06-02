# config/loader.py
import os
import yaml
from typing import Any
class GlobalConfig:
    _instance: dict[str, Any] | None = None

    def __new__(cls, path: str ='config/config.yaml') -> dict[str, Any]:
        if cls._instance is None:
            with open(path, 'r') as f:
                config = yaml.safe_load(f)
                config['dest_folder'] = os.path.expanduser(config['dest_folder'])
                cls._instance = config
        return cls._instance

# Usage: from config.loader import config
config: dict[str, Any] = GlobalConfig()