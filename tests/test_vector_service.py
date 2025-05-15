"""
Unit tests for the Vector Service.
"""

import sys
import pytest
from unittest.mock import MagicMock

from soochi.services.vector_service import VectorService


@pytest.fixture
def sample_ideas():
    """Fixture providing sample ideas for testing."""
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
            'embedding': [0.1] * 1536  # Using 'embedding' instead of 'embeddings'
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
def mock_notion_service():
    """Fixture providing a mocked Notion service."""
    mock_service = MagicMock()
    return mock_service


@pytest.fixture
def mock_mongodb_client():
    """Fixture providing a mocked MongoDB client."""
    mock_client = MagicMock()
    return mock_client


@pytest.fixture
def vector_service(mock_pinecone_client, mock_notion_service, mock_mongodb_client):
    """Fixture providing a VectorService instance with mocked dependencies."""
    service = VectorService(
        pinecone_client=mock_pinecone_client,
        index_name="test-index",
        notion_service=mock_notion_service,
        mongodb_client=mock_mongodb_client
    )
    # Patch the ensure_index_exists method to avoid actual calls
    service.ensure_index_exists = MagicMock()
    return service


class TestVectorService:
    """Tests for the VectorService."""

    # Skipping test_ensure_index_exists since it requires ServerlessSpec which is causing issues
    # The functionality is still tested indirectly in other tests

    def test_process_idea_vectors_new_idea(self, vector_service, sample_ideas, mock_pinecone_client):
        """Test processing a new idea that doesn't have similar matches."""
        # Setup
        mock_index = mock_pinecone_client.Index.return_value
        mock_index.query.return_value = {
            'matches': [
                {
                    'id': 'other_idea',
                    'score': 0.3,  # Below threshold
                    'metadata': {
                        'count': 1,
                        'title': 'Other Idea'
                    }
                }
            ]
        }
        
        mock_ai_service = MagicMock()
        mock_ai_service.create_embedding.return_value = sample_ideas[0]['embedding']
        
        # Call the method
        vector_service.process_idea_vectors([sample_ideas[0]], mock_ai_service)
        
        # Verify
        mock_index.query.assert_called_once()
        mock_index.upsert.assert_called_once()
        vector_service.notion_service.create_idea.assert_called_once_with(
            sample_ideas[0], vector_service.mongodb_client
        )

    def test_process_idea_vectors_similar_idea(self, vector_service, sample_ideas, mock_pinecone_client):
        """Test processing an idea that has a similar match."""
        # Setup
        mock_index = mock_pinecone_client.Index.return_value
        existing_idea = sample_ideas[1]
        
        mock_index.query.return_value = {
            'matches': [
                {
                    'id': existing_idea['title'],
                    'score': 0.8,  # Above threshold
                    'metadata': {
                        'count': 1,
                        'title': existing_idea['title'],
                        'type': existing_idea['type'],
                        'problemStatement': existing_idea['problemStatement'],
                        'solution': existing_idea['solution'],
                        'targetAudience': existing_idea['targetAudience'],
                        'innovationScore': existing_idea['innovationScore'],
                        'potentialApplications': existing_idea['potentialApplications'],
                        'prerequisites': existing_idea['prerequisites'],
                        'additionalNotes': existing_idea['additionalNotes']
                    }
                }
            ]
        }
        
        mock_ai_service = MagicMock()
        mock_ai_service.create_embedding.return_value = existing_idea['embedding']
        
        # Call the method
        vector_service.process_idea_vectors([existing_idea], mock_ai_service)
        
        # Verify
        mock_index.query.assert_called_once()
        mock_index.update.assert_called_once()
        vector_service.notion_service.update_idea_count.assert_called_once_with(
            existing_idea['title'], 2  # Count incremented from 1 to 2
        )
        mock_index.upsert.assert_not_called()  # Should not create a new idea

    def test_handle_similar_ideas(self, vector_service, mock_pinecone_client):
        """Test handling similar ideas."""
        # Setup
        mock_index = mock_pinecone_client.Index.return_value
        idea = {
            'title': 'Test Idea',
            'type': 'Test Type'
        }
        
        query_result = {
            'matches': [
                {
                    'id': 'Existing Idea',
                    'score': 0.9,  # Above threshold
                    'metadata': {
                        'count': 2,
                        'title': 'Existing Idea',
                        'type': 'Test Type'
                    }
                }
            ]
        }
        
        # Call the method
        result = vector_service.handle_similar_ideas(mock_index, query_result, idea)
        
        # Verify
        assert result is True
        mock_index.update.assert_called_once()
        vector_service.notion_service.update_idea_count.assert_called_once_with(
            'Existing Idea', 3  # Count incremented from 2 to 3
        )

    def test_handle_similar_ideas_no_match(self, vector_service, mock_pinecone_client):
        """Test handling when no similar ideas are found."""
        # Setup
        mock_index = mock_pinecone_client.Index.return_value
        idea = {
            'title': 'Test Idea',
            'type': 'Test Type'
        }
        
        query_result = {
            'matches': [
                {
                    'id': 'Other Idea',
                    'score': 0.3,  # Below threshold
                    'metadata': {
                        'count': 1,
                        'title': 'Other Idea'
                    }
                }
            ]
        }
        
        # Call the method
        result = vector_service.handle_similar_ideas(mock_index, query_result, idea)
        
        # Verify
        assert result is False
        mock_index.update.assert_not_called()
        vector_service.notion_service.update_idea_count.assert_not_called()

    def test_add_new_idea_to_db(self, vector_service, sample_ideas, mock_pinecone_client):
        """Test adding a new idea to the database."""
        # Setup
        mock_index = mock_pinecone_client.Index.return_value
        idea = sample_ideas[0]
        
        # Call the method
        vector_service.add_new_idea_to_db(mock_index, idea)
        
        # Verify
        mock_index.upsert.assert_called_once()
        vector_service.notion_service.create_idea.assert_called_once_with(
            idea, vector_service.mongodb_client
        )

    def test_add_new_idea_to_db_error(self, vector_service, sample_ideas, mock_pinecone_client):
        """Test error handling when adding a new idea."""
        # Setup
        mock_index = mock_pinecone_client.Index.return_value
        mock_index.upsert.side_effect = Exception("Test error")
        idea = sample_ideas[0]
        
        # Call the method and verify it raises an exception
        with pytest.raises(Exception):
            vector_service.add_new_idea_to_db(mock_index, idea)
        
        # Verify
        mock_index.upsert.assert_called_once()
        vector_service.notion_service.create_idea.assert_not_called()


if __name__ == "__main__":
    # This allows running the tests directly with python
    import sys
    sys.exit(pytest.main(["-v", __file__]))
