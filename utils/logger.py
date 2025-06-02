import os
import logging
import logging.config
from typing import Optional
from config.loader import config


def _setup_logger() -> logging.Logger:
    global _logger_instance
    
    log_config = config['logging']

    log_file = log_config.get("handlers", {}).get("file", {}).get("filename")
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

    logging.config.dictConfig(log_config)
    _logger_instance = logging.getLogger('openbeers')
    _logger_instance.info("Logger initialized")
    return _logger_instance

logger = _setup_logger()

