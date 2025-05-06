"""
Factory for creating service instances and pipelines.
"""

from pinecone import Pinecone
from notion_client import Client as NotionClient

from soochi.services.url_service import URLService
from soochi.services.vector_service import VectorService
from soochi.services.notion_service import NotionService
from soochi.services.openai_service import OpenAIService
from soochi.services.gemini_service import GeminiService
from soochi.pipeline import ContentProcessingPipeline
from soochi.utils.config import config
from soochi.utils.utils import hash_url

def create_pipeline(model_type):
    """
    Factory to create the appropriate pipeline based on model type.
    
    Args:
        model_type: Type of model to use ("openai" or "gemini")
        
    Returns:
        ContentProcessingPipeline instance
    """
    # Initialize URL service
    url_service = URLService()
    url_service.hash_url = hash_url
    
    # Initialize Vector service
    pinecone_client = Pinecone(api_key=config.pinecone_api_key)
    vector_service = VectorService(pinecone_client, config.pinecone_index_name)
    
    # Initialize Notion service
    notion_client = NotionClient(auth=config.notion_api_key)
    notion_service = NotionService(notion_client, config.notion_database_id)
    
    # Initialize AI service based on model type
    if model_type == "openai":
        ai_service = OpenAIService(config.openai_api_key, config.openai_model)
        batch_mode = True
    elif model_type == "gemini":
        ai_service = GeminiService(config.google_ai_api_key, config.openai_api_key, config.google_ai_model)
        batch_mode = False
    else:
        raise ValueError(f"Unsupported model type: {model_type}")
    
    # Create and return the pipeline
    return ContentProcessingPipeline(
        ai_service=ai_service,
        url_service=url_service,
        vector_service=vector_service,
        notion_service=notion_service,
        batch_mode=batch_mode
    )
