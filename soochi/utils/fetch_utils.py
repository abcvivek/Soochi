"""
Utilities for fetching and caching web content.
"""

import time
from typing import Dict, Optional, Tuple
import trafilatura
from trafilatura.settings import DEFAULT_CONFIG
from copy import deepcopy

from soochi.utils.logger import logger

# In-memory cache for URL content
# Structure: {url: (content, timestamp)}
_url_content_cache: Dict[str, Tuple[str, float]] = {}

# Cache expiration time in seconds (1 hour)
CACHE_EXPIRY = 3600


def fetch_url_with_cache(url: str, max_redirects: int = -1, timeout: int = 2) -> Optional[str]:
    """
    Fetch URL content with caching to avoid redundant downloads.
    
    Args:
        url: The URL to fetch
        max_redirects: Maximum number of redirects to follow (-1 for unlimited)
        timeout: Timeout in seconds for the request
        
    Returns:
        The fetched content or None if the fetch failed
    """
    # Check if URL is in cache and not expired
    current_time = time.time()
    if url in _url_content_cache:
        content, timestamp = _url_content_cache[url]
        if current_time - timestamp < CACHE_EXPIRY:
            logger.debug(f"Using cached content for {url}")
            return content
    
    # Configure trafilatura
    my_config = deepcopy(DEFAULT_CONFIG)
    my_config['DEFAULT']['MAX_REDIRECTS'] = str(max_redirects)
    my_config['DEFAULT']['DOWNLOAD_TIMEOUT'] = str(timeout)
    
    # Fetch the content
    try:
        content = trafilatura.fetch_url(url, config=my_config)
        if content:
            # Cache the content
            _url_content_cache[url] = (content, current_time)
        return content
    except Exception as e:
        logger.error(f"Error fetching URL {url}: {e}")
        return None
