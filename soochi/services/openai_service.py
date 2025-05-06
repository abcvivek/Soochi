"""
OpenAI service implementation for Soochi.
Handles batch processing of content using OpenAI models.
"""

import json
import os
from typing import List, Dict, Any
from openai import OpenAI

from soochi.services.ai_service import AIService
from soochi.utils.logger import logger
from soochi.utils.constants import EMBEDDING_MODEL, EMBEDDING_DIMENSION, BATCH_RESULTS_FILE
from soochi.utils.utils import hash_url

class OpenAIService(AIService):
    """OpenAI service implementation."""
    
    def __init__(self, api_key: str, model: str):
        """
        Initialize the OpenAI service.
        
        Args:
            api_key: OpenAI API key
            model: OpenAI model to use
        """
        self.api_key = api_key
        self.model = model
        self.client = OpenAI(api_key=api_key)
    
    def process_content(self, url: str, content: str, prompt: str) -> List[Dict[str, Any]]:
        """
        Process content using OpenAI model and return structured ideas.
        For OpenAI, this creates a batch job and returns the task information.
        The actual processing happens asynchronously.
        
        Args:
            url: URL of the content
            content: The content to process
            prompt: The prompt to use for processing
            
        Returns:
            List containing the batch task information
        """
        task = {
            "custom_id": f"task-{hash_url(url)}",
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": self.model,
                "temperature": 0.4,
                "response_format": {
                    "type": "json_object"
                },
                "messages": [
                    {
                        "role": "system",
                        "content": prompt
                    },
                    {
                        "role": "user",
                        "content": f"""
                            Input: {content}
                            Response (JSON):
                        """
                    }
                ],
            }
        }
        return [task]
    
    def create_embedding(self, text: str) -> List[float]:
        """
        Create embeddings for the given text using OpenAI.
        
        Args:
            text: The text to create embeddings for
            
        Returns:
            List of floating point values representing the embedding
        """
        logger.debug(f"Creating embedding for text: {text[:50]}...")
        try:
            embedding = self.client.embeddings.create(
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
    
    def create_batch_file(self, tasks: List[Dict[str, Any]]) -> str:
        """
        Create a JSONL file for batch processing.
        
        Args:
            tasks: List of tasks to include in the batch
            
        Returns:
            Path to the created file
        """
        # create data folder if it doesn't exist
        if not os.path.exists("data"):
            os.makedirs("data")

        file_name = BATCH_RESULTS_FILE
        with open(file_name, 'w') as file:
            for obj in tasks:
                file.write(json.dumps(obj) + '\n')
        logger.info(f"File created at {file_name}")
        return file_name
    
    def submit_batch_job(self, file_name: str) -> str:
        """
        Submit a batch job to OpenAI.
        
        Args:
            file_name: Path to the JSONL file containing tasks
            
        Returns:
            ID of the created batch job
        """
        try:
            # Ensure the file has the correct extension and format
            if not file_name.endswith('.jsonl'):
                logger.warning(f"File {file_name} doesn't have .jsonl extension. Ensuring it's properly formatted.")
                
            # Verify file content is valid JSONL
            with open(file_name, 'r') as f:
                lines = f.readlines()
                for i, line in enumerate(lines):
                    try:
                        json.loads(line.strip())
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON on line {i+1}: {e}")
                        raise ValueError(f"File contains invalid JSON on line {i+1}")
            
            # Open file in binary mode for the API
            with open(file_name, "rb") as file_object:
                batch_file = self.client.files.create(
                    file=file_object,
                    purpose="batch"
                )

            logger.info(f"Batch file created: {batch_file.id}")

            batch_job = self.client.batches.create(
                input_file_id=batch_file.id,
                endpoint="/v1/chat/completions",
                completion_window="24h"
            )

            logger.info(f"Batch job created: {batch_job.id}")
            
            # Delete the local file
            os.remove(file_name)
            logger.info("Local file deleted")
            
            return batch_job.id
            
        except Exception as e:
            logger.error(f"Error in processing pipeline: {e}")
            raise
    
    def check_batch_status(self, batch_id: str) -> str:
        """
        Check the status of a batch job.
        
        Args:
            batch_id: ID of the batch job to check
            
        Returns:
            ID of the result file if the batch is complete, empty string otherwise
        """
        batch_status = self.client.batches.retrieve(batch_id)
        if batch_status.status == "completed":
            return batch_status.output_file_id
        elif batch_status.status == "failed":
            logger.error(f"Batch {batch_id} failed. Please check the logs in platform.openai.com.")
        return ""
    
    def save_and_parse_results(self, result_file_id: str) -> List[Dict[str, Any]]:
        """
        Save and parse the results from an OpenAI batch job.
        
        Args:
            result_file_id: ID of the result file
            
        Returns:
            List of parsed ideas
        """
        result = self.client.files.content(result_file_id).content
        result_str = result.decode('utf-8')
        
        # Parse the JSONL content
        ideas = []
        for line in result_str.strip().split('\n'):
            try:
                resp = json.loads(line)
                data = resp['response']['body']
                
                # Extract the response content
                if 'choices' in data and data['choices']:
                    content = data['choices'][0]['message']['content']
                    
                    # Parse the JSON content
                    idea_data = json.loads(content)
                    
                    # Extract ideas from the response
                    if 'output' in idea_data and idea_data['output']:
                        for idea in idea_data['output']:
                            idea['url_hash'] = resp['custom_id'].split("-")[1]
                            ideas.append(idea)
            except Exception as e:
                logger.error(f"Error parsing result line: {e}")
        
        return ideas
