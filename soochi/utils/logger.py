import logging
import sys
from soochi.utils.config import config

# Configure root logger - set to ERROR by default to suppress all non-Soochi logs
logging.basicConfig(level=logging.ERROR, format=config.log_format, stream=sys.stdout)

# Configure only the Soochi logger to show logs at the configured level
soochi_logger = logging.getLogger('soochi')
soochi_logger.setLevel(config.log_level)

# Create a dedicated handler for Soochi logs
soochi_handler = logging.StreamHandler(sys.stdout)
soochi_handler.setFormatter(logging.Formatter(config.log_format))

# Remove any existing handlers to avoid duplicate logs
if soochi_logger.handlers:
    for handler in soochi_logger.handlers:
        soochi_logger.removeHandler(handler)

soochi_logger.addHandler(soochi_handler)

# Prevent Soochi logs from propagating to the root logger to avoid duplication
soochi_logger.propagate = False

# Get our specific module logger
logger = logging.getLogger(__name__)
