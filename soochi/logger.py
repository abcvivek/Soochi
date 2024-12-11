import logging
from soochi.config import config

# Configure logging
logging.basicConfig(
    level=config.log_level,
    format=config.log_format,
)

logger = logging.getLogger(__name__)
