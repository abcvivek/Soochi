"""
Unified processing pipeline for content processing in Soochi.
"""

import time
from typing import List, Dict
import trafilatura

from soochi.services.ai_service import AIService
from soochi.services.url_service import URLService
from soochi.services.vector_service import VectorService
from soochi.services.notion_service import NotionService
from soochi.utils.mongodb_client import MongoDBClient
from soochi.utils.logger import logger


class ContentProcessingPipeline:
    """Unified pipeline for content processing."""
    
    def __init__(
        self, 
        ai_service: AIService, 
        url_service: URLService, 
        vector_service: VectorService, 
        notion_service: NotionService,
        batch_mode: bool = False
    ):
        """
        Initialize the content processing pipeline.
        
        Args:
            ai_service: AI service to use for processing
            url_service: URL service for handling URLs
            vector_service: Vector service for vector operations
            notion_service: Notion service for Notion integration
            batch_mode: Whether to use batch processing (OpenAI) or synchronous processing (Gemini)
        """
        self.ai_service = ai_service
        self.url_service = url_service
        self.vector_service = vector_service
        self.notion_service = notion_service
        self.batch_mode = batch_mode
    
    def process(self, feeds_config: Dict[str, str]):
        """
        Process content from feeds.
        
        Args:
            feeds_config: Dictionary mapping feed names to feed URLs
        """
        logger.info("Starting content processing pipeline")
        try:
            # Fetch and deduplicate URLs
            feed_links = self.url_service.fetch_feeds(feeds_config)
            new_urls = self.url_service.deduplicate_urls(feed_links)
            logger.info(f"Total feed count: {len(feeds_config)}")
            logger.info(f"Total URLs: {len(feed_links)}")
            logger.info(f"Deduped URLs: {len(new_urls)}")

            # Get already seen URLs from database
            with MongoDBClient() as mongodb_client:
                seen_urls_hash = mongodb_client.fetch_seen_urls_hash()
            
            deduped_urls = self.url_service.deduplicate_urls_from_all_urls(new_urls, seen_urls_hash)

            if not deduped_urls:
                logger.info("No new URLs to process")
                return

            # Extract metadata from URLs
            url_data_list = self.url_service.extract_url_metadata(deduped_urls)
            
            # Insert URLs with metadata into database
            with MongoDBClient() as mongodb_client:
                mongodb_client.bulk_insert_seen_urls(url_data_list)

            # Process content with AI service
            if self.batch_mode:
                # Batch processing (OpenAI)
                self._process_batch(deduped_urls)
            else:
                # Synchronous processing (Gemini)
                self._process_synchronous(deduped_urls)
                
            logger.info("Processing complete")
        except Exception as e:
            logger.error(f"Error in processing pipeline: {e}")
            raise
    
    def _process_batch(self, deduped_urls: List[str]):
        """
        Process content using batch processing (OpenAI).
        
        Args:
            deduped_urls: List of URLs to process
        """
        # Read the prompt
        with open('soochi/prompts/idea_extractor.txt', 'r') as prompt_file:
            prompt_content = prompt_file.read()
        
        # Create tasks for batch processing
        tasks = []
        for url in deduped_urls:
            raw_content = trafilatura.fetch_url(url)
            content = trafilatura.extract(raw_content)
            if not content:
                continue
            
            # Process content with AI service
            task = self.ai_service.process_content(url, content, prompt_content)[0]
            tasks.append(task)
        
        # Create batch file and submit job
        openai_service = self.ai_service  # Type: OpenAIService
        file_name = openai_service.create_batch_file(tasks)
        batch_id = openai_service.submit_batch_job(file_name)
        
        # Store the batch job ID in the database
        with MongoDBClient() as mongodb_client:
            mongodb_client.create_batch_job(batch_id)
        
    
    def _process_synchronous(self, deduped_urls: List[str]):
        """
        Process content synchronously (Gemini).
        
        Args:
            deduped_urls: List of URLs to process
        """
        # Read the prompt
        with open('soochi/prompts/idea_extractor.txt', 'r') as prompt_file:
            prompt_content = prompt_file.read()
        
        # Process each URL
        all_ideas = []
        for url in deduped_urls:
            raw_content = trafilatura.fetch_url(url)
            content = trafilatura.extract(raw_content)
            if not content:
                continue
            
            # Process content with AI service
            ideas = self.ai_service.process_content(url, content, prompt_content)
            
            all_ideas.extend(ideas)
        
        # Store a reference to the results in MongoDB
        batch_id = f"gemini-{int(time.time())}"
        with MongoDBClient() as mongodb_client:
            mongodb_client.create_batch_job(batch_id)
            
            # Update VectorService with NotionService and MongoDBClient
            self.vector_service.notion_service = self.notion_service
            self.vector_service.mongodb_client = mongodb_client
            
            # Process the ideas - VectorService will handle both Pinecone and Notion updates
            self.vector_service.process_idea_vectors(all_ideas, self.ai_service)

        logger.info(f"Processed {len(all_ideas)} ideas")
    
    def process_batch_results(self, batch_id: str):
        """
        Process the results of a batch job.
        
        Args:
            batch_id: ID of the batch job to process
        """
        logger.info(f"Processing batch results for job {batch_id}")
        try:
            # Check batch status
            openai_service = self.ai_service  # Type: OpenAIService
            result_file_id = openai_service.check_batch_status(batch_id)
            
            if not result_file_id:
                logger.warning("No result file ID found")
                return
            
            # Parse the results
            ideas = openai_service.save_and_parse_results(result_file_id)
            
            # Update VectorService with NotionService and MongoDBClient
            with MongoDBClient() as mongodb_client:
                self.vector_service.notion_service = self.notion_service
                self.vector_service.mongodb_client = mongodb_client
                
                # Process the ideas - VectorService will handle both Pinecone and Notion updates
                self.vector_service.process_idea_vectors(ideas, self.ai_service)
        except Exception as e:
            logger.error(f"Error processing batch results: {e}")
            raise
