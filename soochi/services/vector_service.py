"""
Vector Service for handling operations related to vector databases (Pinecone).
"""

from typing import List, Dict, Any, Optional
from pinecone import Pinecone

from soochi.utils.logger import logger
from soochi.utils.constants import (
    EMBEDDING_DIMENSION,
    EMBEDDING_METRIC,
    SIMILARITY_THRESHOLD,
    AWS_REGION,
    AWS_CLOUD
)
from soochi.services.notion_service import NotionService

class VectorService:
    """Service for vector database operations."""
    
    def __init__(self, pinecone_client: Pinecone, index_name: str, notion_service: Optional[NotionService] = None, mongodb_client = None):
        """
        Initialize the vector service.
        
        Args:
            pinecone_client: Initialized Pinecone client
            index_name: Name of the Pinecone index to use
            notion_service: Optional NotionService for updating Notion
            mongodb_client: Optional MongoDB client for URL metadata
        """
        self.pinecone_client = pinecone_client
        self.index_name = index_name
        self.notion_service = notion_service
        self.mongodb_client = mongodb_client
        self.ensure_index_exists()
    
    def ensure_index_exists(self):
        """Ensure that the Pinecone index exists, creating it if necessary."""
        try:
            self.pinecone_client.describe_index(self.index_name)
            logger.info(f"Index '{self.index_name}' already exists.")
        except Exception as e:
            if "not found" in str(e):
                # Index does not exist, so create it
                self.pinecone_client.create_index(
                    name=self.index_name,
                    dimension=EMBEDDING_DIMENSION,
                    metric=EMBEDDING_METRIC,
                    spec=ServerlessSpec(
                        cloud=AWS_CLOUD,
                        region=AWS_REGION
                    )
                )
                logger.info(f"Index '{self.index_name}' created.")
            else:
                logger.error(f"Error checking index: {e}")
    
    def process_idea_vectors(self, ideas: List[Dict[str, Any]], ai_service):
        """
        Process ideas and handle vector similarity checks.
        
        Args:
            ideas: List of ideas to process
            ai_service: AI service to use for creating embeddings
        """
        logger.info(f"Processing vectors for {len(ideas)} ideas")
        index = self.pinecone_client.Index(self.index_name)
        
        for i, idea in enumerate(ideas, 1):
            logger.debug(f"Processing idea {i}/{len(ideas)}: {idea['title']}")
            embedding = ai_service.create_embedding(f"{idea['problemStatement']}_{idea['solution']}")
            if not embedding:
                logger.warning(f"Skipping idea {idea['title']} due to embedding failure")
                continue
                
            idea['embedding'] = embedding  # Use 'embedding' instead of 'embeddings' for consistency
            query_result = index.query(
                vector=idea['embedding'],
                top_k=5,
                include_metadata=True
            )

            if self.handle_similar_ideas(index, query_result, idea):
                logger.debug(f"Found similar idea for {idea['title']}")
                continue

            logger.debug(f"Adding new idea to DB: {idea['title']}")
            self.add_new_idea_to_db(index, idea)
    
    def handle_similar_ideas(self, index, query_result: Dict[str, Any], idea: Dict[str, Any]) -> bool:
        """
        Handle similar ideas found in the database.
        
        Args:
            index: Pinecone index
            query_result: Result of the similarity query
            idea: The idea being processed
            
        Returns:
            True if a similar idea was found and handled, False otherwise
        """
        for match_ in query_result['matches']:
            if match_['score'] > SIMILARITY_THRESHOLD:
                logger.info(f"Found similar idea with score {match_['score']} for {idea['title']}")
                # Update count in metadata
                new_count = match_['metadata']['count'] + 1
                match_['metadata']['count'] = new_count
                
                # Update Pinecone
                index.update(
                    id=match_['id'],
                    set_metadata=match_['metadata']
                )

                # Update Notion page if NotionService is available
                if self.notion_service:
                    # Use the dedicated method in NotionService to update the idea count
                    self.notion_service.update_idea_count(match_['metadata']['title'], new_count)

                return True
        return False
    
    def add_new_idea_to_db(self, index, idea: Dict[str, Any]):
        """
        Add a new idea to the vector database.
        
        Args:
            index: Pinecone index
            idea: The idea to add
        """
        try:
            # Add to Pinecone
            index.upsert(
                vectors=[{
                    "id": idea['title'],
                    "metadata": {
                        "title": idea['title'],
                        "type": idea['type'],
                        "problemStatement": idea['problemStatement'],
                        "solution": idea['solution'],
                        "targetAudience": idea['targetAudience'],
                        "innovationScore": idea['innovationScore'],
                        "potentialApplications": idea['potentialApplications'],
                        "prerequisites": idea['prerequisites'],
                        "additionalNotes": idea['additionalNotes'],
                        "count": 1
                    },
                    "values": idea['embedding']
                }]
            )
            logger.info(f"Successfully added new idea to Pinecone: {idea['title']}")
            
            # Add to Notion if NotionService is available
            if self.notion_service:
                # Use the dedicated method in NotionService to create the idea
                self.notion_service.create_idea(idea, self.mongodb_client)
        except Exception as e:
            logger.error(f"Error adding idea to database: {e}")
            raise
