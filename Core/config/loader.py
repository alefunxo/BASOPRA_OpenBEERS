# config/loader.py
import os
import yaml

class GlobalConfig:
    _instance = None

    def __new__(cls, path='config/config.yaml'):
        if cls._instance is None:
            with open(path, 'r') as f:
                config = yaml.safe_load(f)
                config['dest_folder'] = os.path.expanduser(config['dest_folder'])
                cls._instance = config
        return cls._instance

# Usage: from config.loader import config
config = GlobalConfig()