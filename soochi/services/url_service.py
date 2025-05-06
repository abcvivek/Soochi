"""
URL Service for handling feed fetching, URL processing, and metadata extraction.
"""

import feedparser
from urllib.parse import urlparse, parse_qs
import trafilatura
from typing import List, Dict, Any

from soochi.utils.logger import logger
from soochi.utils.utils import hash_url

class URLService:
    """Service for URL-related operations."""
    
    def fetch_feeds(self, feeds_config: Dict[str, str]) -> List[str]:
        """
        Fetch feeds from the configured sources.
        
        Args:
            feeds_config: Dictionary mapping feed names to feed URLs
            
        Returns:
            List of URLs extracted from feeds
        """
        feed_links = []
        for feed_name, feed_url in feeds_config.items():
            logger.info("*****************")
            logger.info(f"Fetching feed: {feed_name}")
            try:
                feed = feedparser.parse(feed_url)
                logger.info(f"Found total entries: {len(feed.entries)}")
                logger.info("*****************")
                feed_links.extend(self.process_feed_entries(feed.entries))
            except Exception as e:
                logger.error(f"Error fetching feed {feed_name}: {e}")
        return feed_links
    
    def process_feed_entries(self, entries: List[Any]) -> List[str]:
        """
        Process feed entries and extract URLs.
        
        Args:
            entries: List of feed entries
            
        Returns:
            List of extracted URLs
        """
        feed_links = []
        for entry in entries:
            parsed_url = urlparse(entry.link)
            actual_url = parse_qs(parsed_url.query).get('url', [None])[0]
            if actual_url:
                feed_links.append(actual_url)
            else:
                logger.error(f"Invalid URL: {entry.link}")
        return feed_links
    
    def deduplicate_urls(self, feed_links: List[str]) -> List[str]:
        """
        Remove duplicate URLs based on their hash.
        
        Args:
            feed_links: List of URLs to deduplicate
            
        Returns:
            List of deduplicated URLs
        """
        seen_hashes = set()
        new_urls = []
        for url in feed_links:
            url_hash = hash_url(url)
            if url_hash not in seen_hashes:
                seen_hashes.add(url_hash)
                new_urls.append(url)
        return new_urls
    
    def deduplicate_urls_from_all_urls(self, new_urls: List[str], seen_urls_hash: List[str]) -> List[str]:
        """
        Remove URLs that have already been processed.
        
        Args:
            new_urls: List of new URLs
            seen_urls_hash: List of hashes of already processed URLs
            
        Returns:
            List of URLs that haven't been processed yet
        """
        deduped_urls = [url for url in new_urls if hash_url(url) not in seen_urls_hash]
        logger.info(f"Deduped URLs after removing seen URLs from DB: {len(deduped_urls)}")
        return deduped_urls
    
    def extract_url_metadata(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Extract metadata from URLs.
        
        Args:
            urls: List of URLs to extract metadata from
            
        Returns:
            List of dictionaries containing URL metadata
        """
        url_data_list = []
        
        for url in urls:
            try:
                raw_content = trafilatura.fetch_url(url)
                if not raw_content:
                    continue
                    
                # Extract title and content
                metadata = trafilatura.extract_metadata(raw_content)
                    
                title = metadata.title if metadata and metadata.title else "No title"
                
                url_data = {
                    "url_hash": hash_url(url),
                    "url": url,
                    "title": title,
                }
                
                url_data_list.append(url_data)
                
            except Exception as e:
                logger.error(f"Error extracting metadata from {url}: {e}")
        
        return url_data_list
