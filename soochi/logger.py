import logging
from soochi.config import config

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(config.log_level)

# Clear any existing handlers to avoid duplicate logs
if root_logger.handlers:
    for handler in root_logger.handlers:
        root_logger.removeHandler(handler)

# Add a new handler with our format
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(config.log_format))
root_logger.addHandler(handler)

# Set levels for third-party loggers that might be too verbose
logging.getLogger('pinecone').setLevel(config.log_level)
logging.getLogger('pinecone_plugin_interface').setLevel(config.log_level)
logging.getLogger('pymongo').setLevel(config.log_level)
logging.getLogger('httpcore').setLevel(config.log_level)
logging.getLogger('httpx').setLevel(config.log_level)

# Get our application logger
logger = logging.getLogger(__name__)
