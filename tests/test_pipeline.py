"""
Tests for the ContentProcessingPipeline.
"""

import pytest
from unittest.mock import MagicMock, patch

from soochi.pipeline import ContentProcessingPipeline


@pytest.fixture
def mock_ai_service():
    """Fixture providing a mocked AI service."""
    mock_service = MagicMock()
    mock_service.process_content.return_value = [
        {
            'title': 'Test Idea',
            'type': 'SaaS',
            'problemStatement': 'Problem statement for test idea',
            'solution': 'Solution for test idea',
            'targetAudience': 'Developers',
            'innovationScore': 8.5,
            'potentialApplications': 'Various applications',
            'prerequisites': 'Python, AI knowledge',
            'additionalNotes': 'Additional notes for testing',
            'url_hash': 'test_hash_123'
        }
    ]
    return mock_service


@pytest.fixture
def mock_url_service():
    """Fixture providing a mocked URL service."""
    mock_service = MagicMock()
    mock_service.fetch_feeds.return_value = ['https://example.com/article1', 'https://example.com/article2']
    mock_service.deduplicate_urls.return_value = ['https://example.com/article1', 'https://example.com/article2']
    mock_service.deduplicate_urls_from_all_urls.return_value = ['https://example.com/article1', 'https://example.com/article2']
    mock_service.extract_url_metadata.return_value = [
        {'url': 'https://example.com/article1', 'title': 'Article 1', 'created_at': '2025-05-01'},
        {'url': 'https://example.com/article2', 'title': 'Article 2', 'created_at': '2025-05-02'}
    ]
    return mock_service


@pytest.fixture
def mock_vector_service():
    """Fixture providing a mocked vector service."""
    mock_service = MagicMock()
    return mock_service


@pytest.fixture
def mock_notion_service():
    """Fixture providing a mocked notion service."""
    mock_service = MagicMock()
    return mock_service


@pytest.fixture
def mock_mongodb_client():
    """Fixture providing a mocked MongoDB client."""
    mock_client = MagicMock()
    mock_client.fetch_seen_urls_hash.return_value = []
    return mock_client


@pytest.fixture
def pipeline(mock_ai_service, mock_url_service, mock_vector_service, mock_notion_service):
    """Fixture providing a ContentProcessingPipeline instance with mocked dependencies."""
    return ContentProcessingPipeline(
        ai_service=mock_ai_service,
        url_service=mock_url_service,
        vector_service=mock_vector_service,
        notion_service=mock_notion_service,
        batch_mode=False  # Use synchronous processing (Gemini)
    )


class TestContentProcessingPipeline:
    """Tests for the ContentProcessingPipeline."""

    @patch('soochi.pipeline.MongoDBClient')
    @patch('soochi.pipeline.trafilatura')
    def test_process_synchronous(self, mock_trafilatura, MockMongoDBClient, 
                                pipeline, mock_ai_service, mock_url_service, mock_vector_service):
        """Test the synchronous processing flow (Gemini)."""
        # Setup mocks
        mock_trafilatura.fetch_url.return_value = "Raw content"
        mock_trafilatura.extract.return_value = "Extracted content"
        
        mock_mongodb_instance = MagicMock()
        MockMongoDBClient.return_value.__enter__.return_value = mock_mongodb_instance
        
        # Setup feeds config
        feeds_config = {
            'feed1': 'https://example.com/feed1',
            'feed2': 'https://example.com/feed2'
        }
        
        # Call the method
        pipeline.process(feeds_config)
        
        # Assertions
        # 1. Verify URL service interactions
        mock_url_service.fetch_feeds.assert_called_once_with(feeds_config)
        mock_url_service.deduplicate_urls.assert_called_once()
        mock_url_service.deduplicate_urls_from_all_urls.assert_called_once()
        mock_url_service.extract_url_metadata.assert_called_once()
        
        # 2. Verify MongoDB interactions
        mock_mongodb_instance.bulk_insert_seen_urls.assert_called_once()
        mock_mongodb_instance.create_batch_job.assert_called_once()
        
        # 3. Verify content processing
        assert mock_trafilatura.fetch_url.call_count == 2  # Called for each URL
        assert mock_trafilatura.extract.call_count == 2  # Called for each URL
        assert mock_ai_service.process_content.call_count == 2  # Called for each URL
        
        # 4. Verify vector service interactions
        mock_vector_service.process_idea_vectors.assert_called_once()
        
        # 5. Verify the vector service was properly configured
        assert mock_vector_service.notion_service == pipeline.notion_service
        assert mock_vector_service.mongodb_client == mock_mongodb_instance

    @patch('soochi.pipeline.MongoDBClient')
    @patch('soochi.pipeline.trafilatura')
    def test_process_batch(self, mock_trafilatura, MockMongoDBClient, 
                          mock_ai_service, mock_url_service, mock_vector_service, mock_notion_service):
        """Test the batch processing flow (OpenAI)."""
        # Setup mocks
        mock_trafilatura.fetch_url.return_value = "Raw content"
        mock_trafilatura.extract.return_value = "Extracted content"
        
        mock_mongodb_instance = MagicMock()
        MockMongoDBClient.return_value.__enter__.return_value = mock_mongodb_instance
        
        # Create a pipeline with batch mode
        pipeline = ContentProcessingPipeline(
            ai_service=mock_ai_service,
            url_service=mock_url_service,
            vector_service=mock_vector_service,
            notion_service=mock_notion_service,
            batch_mode=True  # Use batch processing (OpenAI)
        )
        
        # Setup OpenAI-specific mocks
        mock_ai_service.create_batch_file.return_value = "batch_file.jsonl"
        mock_ai_service.submit_batch_job.return_value = "batch-123"
        
        # Setup feeds config
        feeds_config = {
            'feed1': 'https://example.com/feed1',
            'feed2': 'https://example.com/feed2'
        }
        
        # Call the method
        pipeline.process(feeds_config)
        
        # Assertions
        # 1. Verify URL service interactions
        mock_url_service.fetch_feeds.assert_called_once_with(feeds_config)
        
        # 2. Verify MongoDB interactions
        mock_mongodb_instance.bulk_insert_seen_urls.assert_called_once()
        mock_mongodb_instance.create_batch_job.assert_called_once_with("batch-123")
        
        # 3. Verify content processing
        assert mock_trafilatura.fetch_url.call_count == 2  # Called for each URL
        assert mock_trafilatura.extract.call_count == 2  # Called for each URL
        assert mock_ai_service.process_content.call_count == 2  # Called for each URL
        
        # 4. Verify batch processing
        mock_ai_service.create_batch_file.assert_called_once()
        mock_ai_service.submit_batch_job.assert_called_once_with("batch_file.jsonl")

    @patch('soochi.pipeline.MongoDBClient')
    def test_process_batch_results(self, MockMongoDBClient, 
                                  mock_ai_service, mock_url_service, mock_vector_service, mock_notion_service):
        """Test processing batch results."""
        # Setup mocks
        mock_mongodb_instance = MagicMock()
        MockMongoDBClient.return_value.__enter__.return_value = mock_mongodb_instance
        
        # Create a pipeline with batch mode
        pipeline = ContentProcessingPipeline(
            ai_service=mock_ai_service,
            url_service=mock_url_service,
            vector_service=mock_vector_service,
            notion_service=mock_notion_service,
            batch_mode=True  # Use batch processing (OpenAI)
        )
        
        # Setup OpenAI-specific mocks
        mock_ai_service.check_batch_status.return_value = "result_file_id"
        mock_ai_service.save_and_parse_results.return_value = [
            {
                'title': 'Batch Idea',
                'type': 'SaaS',
                'problemStatement': 'Problem statement for batch idea',
                'solution': 'Solution for batch idea',
                'targetAudience': 'Developers',
                'innovationScore': 8.5,
                'potentialApplications': 'Various applications',
                'prerequisites': 'Python, AI knowledge',
                'additionalNotes': 'Additional notes for testing',
                'url_hash': 'test_hash_batch'
            }
        ]
        
        # Call the method
        pipeline.process_batch_results("batch-123")
        
        # Assertions
        # 1. Verify batch status check
        mock_ai_service.check_batch_status.assert_called_once_with("batch-123")
        
        # 2. Verify result parsing
        mock_ai_service.save_and_parse_results.assert_called_once_with("result_file_id")
        
        # 3. Verify vector service interactions
        mock_vector_service.process_idea_vectors.assert_called_once()
        
        # 4. Verify the vector service was properly configured
        assert mock_vector_service.notion_service == pipeline.notion_service
        assert mock_vector_service.mongodb_client == mock_mongodb_instance

    @patch('soochi.pipeline.MongoDBClient')
    @patch('soochi.pipeline.logger')
    def test_error_handling(self, mock_logger, MockMongoDBClient, 
                           pipeline, mock_url_service):
        """Test error handling in the pipeline."""
        # Setup mocks
        mock_url_service.fetch_feeds.side_effect = Exception("Test error")
        
        # Setup feeds config
        feeds_config = {
            'feed1': 'https://example.com/feed1',
            'feed2': 'https://example.com/feed2'
        }
        
        # Call the method and verify it raises an exception
        with pytest.raises(Exception):
            pipeline.process(feeds_config)
        
        # Verify error was logged
        mock_logger.error.assert_called_once()


if __name__ == "__main__":
    # This allows running the tests directly with python
    import sys
    sys.exit(pytest.main(["-v", __file__]))
