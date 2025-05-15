"""
Integration tests for the Pinecone to Notion synchronization with the new architecture.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from soochi.services.vector_service import VectorService
from soochi.services.notion_service import NotionService


@pytest.fixture
def sample_ideas():
    """Fixture providing a list of sample ideas for testing."""
    return [
        {
            'title': 'New Idea 1',
            'type': 'SaaS',
            'problemStatement': 'Problem statement for new idea 1',
            'solution': 'Solution for new idea 1',
            'targetAudience': 'Developers',
            'innovationScore': 8.5,
            'potentialApplications': 'Various applications',
            'prerequisites': 'Python, AI knowledge',
            'additionalNotes': 'Additional notes for testing',
            'url_hash': 'test_hash_123',
            'embedding': [0.1] * 1536
        },
        {
            'title': 'Existing Idea',
            'type': 'Open-Source',
            'problemStatement': 'Problem statement for existing idea',
            'solution': 'Solution for existing idea',
            'targetAudience': 'Data Scientists',
            'innovationScore': 7.0,
            'potentialApplications': 'Data analysis',
            'prerequisites': 'Python, Statistics',
            'additionalNotes': 'This idea already exists in the system',
            'url_hash': 'test_hash_456',
            'embedding': [0.2] * 1536
        }
    ]


@pytest.fixture
def mock_pinecone_client():
    """Fixture providing a mocked Pinecone client."""
    mock_client = MagicMock()
    mock_index = MagicMock()
    mock_client.Index.return_value = mock_index
    return mock_client


@pytest.fixture
def mock_notion_client():
    """Fixture providing a mocked Notion client."""
    mock_client = MagicMock()
    mock_client.pages.create = MagicMock()
    mock_client.pages.update = MagicMock()
    mock_client.databases.query = MagicMock(return_value={'results': []})
    return mock_client


@pytest.fixture
def mock_mongodb_client():
    """Fixture providing a mocked MongoDB client."""
    mock_client = MagicMock()
    mock_client.fetch_url_metadata.return_value = {
        'url': 'https://example.com/test',
        'title': 'Test Article',
        'created_at': datetime.now()
    }
    return mock_client


@pytest.fixture
def notion_service(mock_notion_client):
    """Fixture providing a NotionService instance."""
    return NotionService(
        notion_client=mock_notion_client,
        database_id="test-database-id"
    )


@pytest.fixture
def vector_service(mock_pinecone_client, notion_service, mock_mongodb_client):
    """Fixture providing a VectorService instance with NotionService integration."""
    service = VectorService(
        pinecone_client=mock_pinecone_client,
        index_name="test-index",
        notion_service=notion_service,
        mongodb_client=mock_mongodb_client
    )
    # Patch the ensure_index_exists method to avoid actual calls
    service.ensure_index_exists = MagicMock()
    return service


class TestPineconeNotionIntegration:
    """Tests for the integration between Pinecone and Notion with the new architecture."""

    def test_end_to_end_new_idea_flow(self, vector_service, mock_pinecone_client, 
                                      mock_notion_client, sample_ideas):
        """
        Test the end-to-end flow for a new idea:
        1. Process idea vectors
        2. No similar ideas found in Pinecone
        3. Add new idea to Pinecone
        4. Create new idea in Notion
        """
        # Setup mocks for Pinecone
        mock_index = mock_pinecone_client.Index.return_value
        
        # No similar ideas found in query
        mock_index.query.return_value = {
            'matches': [
                {
                    'id': 'other_idea',
                    'score': 0.3,  # Low similarity score
                    'metadata': {
                        'count': 1,
                        'title': 'Other Idea'
                    }
                }
            ]
        }
        
        # Setup mocks for Notion
        mock_notion_client.databases.query.return_value = {"results": []}  # Idea not found in Notion
        
        # Setup mock AI service
        mock_ai_service = MagicMock()
        mock_ai_service.create_embedding.return_value = sample_ideas[0]['embedding']
        
        # Call the method to process the idea
        vector_service.process_idea_vectors([sample_ideas[0]], mock_ai_service)
        
        # Assertions
        # 1. Verify Pinecone interactions
        mock_index.query.assert_called_once()
        mock_index.upsert.assert_called_once()
        
        # 2. Verify Notion interactions
        mock_notion_client.databases.query.assert_not_called()  # NotionService handles this internally
        mock_notion_client.pages.create.assert_called_once()
        mock_notion_client.pages.update.assert_not_called()
        
        # 3. Verify the idea data in the Notion create call
        create_call_args = mock_notion_client.pages.create.call_args[1]
        assert create_call_args['properties']['Title']['title'][0]['text']['content'] == sample_ideas[0]['title']
        assert create_call_args['properties']['Count']['number'] == 1

    def test_end_to_end_existing_idea_flow(self, vector_service, mock_pinecone_client, 
                                          mock_notion_client, sample_ideas):
        """
        Test the end-to-end flow for an existing idea:
        1. Process idea vectors
        2. Similar idea found in Pinecone
        3. Update count in Pinecone
        4. Update existing idea in Notion with new count
        """
        # Setup mocks for Pinecone
        mock_index = mock_pinecone_client.Index.return_value
        existing_idea = sample_ideas[1]
        
        # Similar idea found in query
        mock_index.query.return_value = {
            'matches': [
                {
                    'id': existing_idea['title'],
                    'score': 0.9,  # High similarity score
                    'metadata': {
                        'count': 2,
                        'title': existing_idea['title'],
                        'type': existing_idea['type'],
                        'problemStatement': existing_idea['problemStatement'],
                        'solution': existing_idea['solution']
                    }
                }
            ]
        }
        
        # Setup mocks for Notion
        existing_page = {
            'id': 'page-id-456',
            'properties': {
                'Title': {
                    'title': [{'text': {'content': existing_idea['title']}}]
                },
                'Count': {'number': 2}
            }
        }
        mock_notion_client.databases.query.return_value = {"results": [existing_page]}
        
        # Setup mock AI service
        mock_ai_service = MagicMock()
        mock_ai_service.create_embedding.return_value = existing_idea['embedding']
        
        # Call the method to process the idea
        vector_service.process_idea_vectors([existing_idea], mock_ai_service)
        
        # Assertions
        # 1. Verify Pinecone interactions
        mock_index.query.assert_called_once()
        mock_index.update.assert_called_once()
        mock_index.upsert.assert_not_called()  # Should not create a new idea
        
        # 2. Verify Notion interactions
        mock_notion_client.pages.update.assert_called_once()
        mock_notion_client.pages.create.assert_not_called()
        
        # 3. Verify the count update in Notion
        update_call_args = mock_notion_client.pages.update.call_args[1]
        assert update_call_args['properties']['Count']['number'] == 3  # Incremented from 2 to 3

    def test_pinecone_as_source_of_truth(self, vector_service, mock_pinecone_client, 
                                         mock_notion_client, sample_ideas):
        """
        Test that Pinecone is used as the source of truth for idea data:
        1. When updating an existing idea in Notion, the count should come from Pinecone
        2. Verify that the count in Notion matches the count in Pinecone
        """
        # Setup mocks for Pinecone
        mock_index = mock_pinecone_client.Index.return_value
        existing_idea = sample_ideas[1]
        
        # Setup Pinecone data with a specific count
        mock_index.query.return_value = {
            'matches': [
                {
                    'id': existing_idea['title'],
                    'score': 0.9,  # High similarity score
                    'metadata': {
                        'count': 5,  # Count in Pinecone
                        'title': existing_idea['title'],
                        'type': existing_idea['type']
                    }
                }
            ]
        }
        
        # Setup mocks for Notion with a different count
        existing_page = {
            'id': 'page-id-456',
            'properties': {
                'Title': {
                    'title': [{'text': {'content': existing_idea['title']}}]
                },
                'Count': {'number': 3}  # Different count in Notion
            }
        }
        mock_notion_client.databases.query.return_value = {"results": [existing_page]}
        
        # Setup mock AI service
        mock_ai_service = MagicMock()
        mock_ai_service.create_embedding.return_value = existing_idea['embedding']
        
        # Call the method to process the idea
        vector_service.process_idea_vectors([existing_idea], mock_ai_service)
        
        # Assertions
        # 1. Verify Pinecone interactions
        mock_index.query.assert_called_once()
        mock_index.update.assert_called_once()
        
        # 2. Verify Notion interactions
        mock_notion_client.pages.update.assert_called_once()
        
        # 3. Verify the count update in Notion matches Pinecone's count + 1
        update_call_args = mock_notion_client.pages.update.call_args[1]
        assert update_call_args['properties']['Count']['number'] == 6  # Incremented from 5 to 6

    def test_error_handling_during_sync(self, vector_service, mock_pinecone_client, 
                                       mock_notion_client, sample_ideas):
        """
        Test error handling during the synchronization process:
        1. Simulate an error when adding an idea to the database
        2. Verify that the error is logged properly
        """
        # Setup mocks for Pinecone
        mock_index = mock_pinecone_client.Index.return_value
        
        # Setup mock AI service
        mock_ai_service = MagicMock()
        mock_ai_service.create_embedding.return_value = sample_ideas[0]['embedding']
        
        # We need to patch the actual method that's called in add_new_idea_to_db
        # Looking at the implementation, it's the index.upsert method that might fail
        mock_index.upsert.side_effect = Exception("Error adding idea")
        
        # Patch the logger to verify it's called
        with patch('soochi.services.vector_service.logger') as mock_logger:
            try:
                # Call the method
                vector_service.process_idea_vectors([sample_ideas[0]], mock_ai_service)
            except Exception:
                # The exception is expected to propagate up
                pass
            
            # Assertions
            # Verify error was logged
            mock_logger.error.assert_called_with("Error adding idea to database: Error adding idea")
        
        # 3. Verify that no Notion operations were attempted
        mock_notion_client.pages.create.assert_not_called()
        mock_notion_client.pages.update.assert_not_called()


if __name__ == "__main__":
    # This allows running the tests directly with python
    import sys
    sys.exit(pytest.main(["-v", __file__]))
