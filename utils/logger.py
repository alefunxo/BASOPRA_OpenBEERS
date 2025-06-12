import os
import logging
import logging.config
from config.loader import config

def _setup_logger(name: str) -> logging.Logger:
    log_config = config['logging']

    for handler in log_config.get("handlers", {}).values():
        if "filename" in handler:
            log_dir = os.path.dirname(handler["filename"])
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)

    logging.config.dictConfig(log_config)

    logger = logging.getLogger(name)
    if not logger.handlers or not logger.hasHandlers():
        logger.info(f"Logger '{name}' initialized")
    return logger 

_main_logger = None
_data_logger = None

if _main_logger is None:
    _main_logger = _setup_logger('openbeers.default')
if _data_logger is None:
    _data_logger = _setup_logger('openbeers.data')

logger = _main_logger
data_logger = _data_logger

