"""
Abstract base class for AI services used in Soochi.
This provides a common interface for different AI models.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any

class AIService(ABC):
    """Abstract base class for AI services."""
    
    @abstractmethod
    def process_content(self, url: str, content: str, prompt: str) -> List[Dict[str, Any]]:
        """
        Process content using AI model and return structured ideas.
        
        Args:
            url: URL of the content
            content: The content to process
            prompt: The prompt to use for processing
            
        Returns:
            List of extracted output
        """
        pass
    
    @abstractmethod
    def create_embedding(self, text: str) -> List[float]:
        """
        Create embeddings for the given text.
        
        Args:
            text: The text to create embeddings for
            
        Returns:
            List of floating point values representing the embedding
        """
        pass
