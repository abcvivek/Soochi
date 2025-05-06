"""
Gemini service implementation for Soochi.
Handles synchronous processing of content using Google's Gemini models.
"""

import json
from typing import List, Dict, Any
from google import genai
from openai import OpenAI

from soochi.services.ai_service import AIService
from soochi.utils.logger import logger
from soochi.utils.constants import EMBEDDING_MODEL, EMBEDDING_DIMENSION
from soochi.models.idea import Response
from soochi.utils.utils import hash_url

class GeminiService(AIService):
    """Gemini service implementation."""
    
    def __init__(self, google_api_key: str, openai_api_key: str, model: str):
        """
        Initialize the Gemini service.
        
        Args:
            google_api_key: Google AI API key
            openai_api_key: OpenAI API key (used for embeddings)
            model: Gemini model to use
        """
        self.google_api_key = google_api_key
        self.model = model
        self.gemini_client = genai.Client(api_key=google_api_key)
        self.openai_client = OpenAI(api_key=openai_api_key)
    
    def process_content(self, url: str, content: str, prompt: str) -> List[Dict[str, Any]]:
        """
        Process content using Gemini model and return structured ideas.
        This is a synchronous implementation that returns the results directly.
        
        Args:
            url: URL of the content
            content: The content to process
            prompt: The prompt to use for processing
            
        Returns:
            List of extracted ideas as dictionaries
        """
        try:
            logger.info(f"Processing content with Gemini: {url}")
            
            # Create the prompt
            full_prompt = f"""
            {prompt}
            
            Input: {content}
            Response (JSON):
            """
            
            # Configure the request
            config = {
                "temperature": 0.4,
                "response_mime_type": "application/json",
            }
            
            response = self.gemini_client.models.generate_content(
                model=self.model,
                contents=full_prompt,
                config=config
            )
            
            # Parse the response
            try:
                # Extract the text content
                text_content = response.text
                
                # Parse the JSON content
                parsed_response = json.loads(text_content)
                
                # Validate the response structure
                response_obj = Response(**parsed_response)
                
                # Convert to list of dictionaries
                ideas = []
                if response_obj.output:
                    for idea in response_obj.output:
                        idea.url_hash = hash_url(url)
                        ideas.append(idea.model_dump())
                
                return ideas
            except Exception as e:
                logger.error(f"Error parsing Gemini response: {e}")
                return []
        except Exception as e:
            logger.error(f"Error processing content with Gemini: {e}")
            return []
    
    def create_embedding(self, text: str) -> List[float]:
        """
        Create embeddings for the given text using OpenAI.
        Gemini service uses OpenAI for embeddings for consistency.
        
        Args:
            text: The text to create embeddings for
            
        Returns:
            List of floating point values representing the embedding
        """
        logger.debug(f"Creating embedding for text: {text[:50]}...")
        try:
            embedding = self.openai_client.embeddings.create(
                input=text,
                model=EMBEDDING_MODEL,
                dimensions=EMBEDDING_DIMENSION
            )
            if embedding.data:
                logger.debug("Successfully created embedding")
                return embedding.data[0].embedding
            logger.warning("No embedding data returned from API")
            return []
        except Exception as e:
            logger.error(f"Error creating embedding: {e}")
            return []
