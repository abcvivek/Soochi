"""
Notion Service for handling operations related to Notion integration.
"""

from typing import Dict, Any, Optional
from notion_client import Client as NotionClient

from soochi.utils.logger import logger

class NotionService:
    """Service for Notion-related operations."""
    
    def __init__(self, notion_client: NotionClient, database_id: str):
        """
        Initialize the Notion service.
        
        Args:
            notion_client: Initialized Notion client
            database_id: ID of the Notion database to use
        """
        self.notion_client = notion_client
        self.database_id = database_id
    
    def update_idea_count(self, title: str, count: int) -> bool:
        """
        Update the count of an existing idea in Notion.
        
        Args:
            title: Title of the idea to update
            count: New count value
            
        Returns:
            True if update was successful, False otherwise
        """
        try:
            # Find the existing page in Notion
            existing_page = self.find_idea_in_notion(title)
            
            if existing_page:
                # Update the count in Notion
                logger.info(f"Updating existing idea in Notion: {title}")
                self.notion_client.pages.update(
                    page_id=existing_page['id'],
                    properties={
                        "Count": {"number": count}
                    }
                )
                return True
            else:
                logger.warning(f"Idea not found in Notion for update: {title}")
                return False
        except Exception as e:
            logger.error(f"Error updating idea count in Notion: {e}")
            return False
    
    def create_idea(self, idea: Dict[str, Any], mongodb_client=None) -> bool:
        """
        Create a new idea in Notion.
        
        Args:
            idea: Idea data to create in Notion
            mongodb_client: Optional MongoDB client for fetching URL metadata
            
        Returns:
            True if creation was successful, False otherwise
        """
        try:
            # Fetch URL metadata if url_hash is available
            url_metadata = {"url": "", "title": "", "created_at": ""}
            if idea.get('url_hash') and mongodb_client:
                url_metadata = self.fetch_url_metadata(mongodb_client, idea['url_hash'])
            
            # Format date for Notion if available
            notion_date = None
            if url_metadata["created_at"]:
                notion_date = {
                    "date": {
                        "start": url_metadata["created_at"]
                    }
                }
            
            # Create properties for Notion
            properties = {
                "Title": {"title": [{"text": {"content": idea['title']}}]},
                "Count": {"number": 1},
                "Type": {"rich_text": [{"text": {"content": idea['type']}}]},
                "Problem Statement": {"rich_text": [{"text": {"content": idea['problemStatement']}}]},
                "Solution": {"rich_text": [{"text": {"content": idea['solution']}}]},
                "Target Audience": {"rich_text": [{"text": {"content": idea['targetAudience']}}]},
                "Innovation Score": {"number": idea['innovationScore']},
                "Potential Applications": {"rich_text": [{"text": {"content": idea['potentialApplications']}}]},
                "Prerequisites": {"rich_text": [{"text": {"content": idea['prerequisites']}}]},
                "Additional Notes": {"rich_text": [{"text": {"content": idea['additionalNotes']}}]},
            }
            
            # Add URL if available
            if url_metadata["url"]:
                properties["Source URL"] = {"url": url_metadata["url"]}
            
            # Add Source Title if available
            if url_metadata["title"]:
                properties["Source Title"] = {"rich_text": [{"text": {"content": url_metadata["title"]}}]}
            
            # Add Date if available
            if notion_date:
                properties["Processed Date"] = notion_date
            
            # Create the page in Notion
            logger.info(f"Creating new idea in Notion: {idea['title']}")
            self.notion_client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )
            return True
        except Exception as e:
            logger.error(f"Error creating idea in Notion: {e}")
            return False
    
    def find_idea_in_notion(self, title: str) -> Optional[Dict[str, Any]]:
        """
        Find an idea in Notion by its title using Notion's filter API.
        
        Args:
            title: Title of the idea to find
            
        Returns:
            Notion page object if found, None otherwise
        """
        try:
            response = self.notion_client.databases.query(
                database_id=self.database_id,
                filter={
                    "property": "Title",
                    "title": {
                        "equals": title
                    }
                }
            )
            
            if response["results"]:
                return response["results"][0]
            return None
        except Exception as e:
            logger.error(f"Error finding idea in Notion: {e}")
            return None
    
    def fetch_url_metadata(self, mongodb_client, url_hash: str) -> Dict[str, Any]:
        """
        Fetch URL metadata from the seen_urls collection.
        
        Args:
            mongodb_client: MongoDB client
            url_hash: Hash of the URL to fetch metadata for
            
        Returns:
            Dictionary containing URL metadata
        """
        try:
            url_data = mongodb_client.fetch_url_metadata(url_hash)
            if url_data:
                created_at = url_data.get("created_at", "")
                if created_at:
                    # Convert to string format if it's a datetime
                    if hasattr(created_at, "strftime"):
                        created_at = created_at.strftime("%Y-%m-%d")
                
                return {
                    "url": url_data.get("url", ""),
                    "title": url_data.get("title", ""),
                    "created_at": created_at
                }
            return {"url": "", "title": "", "created_at": ""}
        except Exception as e:
            logger.error(f"Error fetching URL metadata: {e}")
            return {"url": "", "title": "", "created_at": ""}
