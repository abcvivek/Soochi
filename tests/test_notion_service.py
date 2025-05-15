"""
Unit tests for the Notion Service.
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime

from soochi.services.notion_service import NotionService


@pytest.fixture
def sample_idea():
    """Fixture providing a sample idea for testing."""
    return {
        'title': 'Test Idea',
        'type': 'SaaS',
        'problemStatement': 'Problem statement for test idea',
        'solution': 'Solution for test idea',
        'targetAudience': 'Developers',
        'innovationScore': 8.5,
        'potentialApplications': 'Various applications',
        'prerequisites': 'Python, AI knowledge',
        'additionalNotes': 'Additional notes for testing',
        'url_hash': 'test_hash_123',
        'embedding': [0.1] * 1536
    }


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
    """Fixture providing a NotionService instance with mocked dependencies."""
    return NotionService(
        notion_client=mock_notion_client,
        database_id="test-database-id"
    )


class TestNotionService:
    """Tests for the NotionService."""

    def test_update_idea_count_existing(self, notion_service, mock_notion_client):
        """Test updating the count of an existing idea."""
        # Setup
        existing_page = {
            'id': 'page-id-123',
            'properties': {
                'Title': {
                    'title': [{'text': {'content': 'Test Idea'}}]
                },
                'Count': {'number': 1}
            }
        }
        mock_notion_client.databases.query.return_value = {'results': [existing_page]}
        
        # Call the method
        result = notion_service.update_idea_count('Test Idea', 2)
        
        # Verify
        assert result is True
        mock_notion_client.databases.query.assert_called_once()
        mock_notion_client.pages.update.assert_called_once_with(
            page_id='page-id-123',
            properties={'Count': {'number': 2}}
        )

    def test_update_idea_count_not_found(self, notion_service, mock_notion_client):
        """Test updating the count of a non-existent idea."""
        # Setup
        mock_notion_client.databases.query.return_value = {'results': []}
        
        # Call the method
        result = notion_service.update_idea_count('Non-existent Idea', 2)
        
        # Verify
        assert result is False
        mock_notion_client.databases.query.assert_called_once()
        mock_notion_client.pages.update.assert_not_called()

    def test_update_idea_count_error(self, notion_service, mock_notion_client):
        """Test error handling when updating idea count."""
        # Setup
        mock_notion_client.databases.query.side_effect = Exception("Test error")
        
        # Call the method
        result = notion_service.update_idea_count('Test Idea', 2)
        
        # Verify
        assert result is False
        mock_notion_client.databases.query.assert_called_once()
        mock_notion_client.pages.update.assert_not_called()

    def test_create_idea(self, notion_service, sample_idea, mock_notion_client, mock_mongodb_client):
        """Test creating a new idea in Notion."""
        # Call the method
        result = notion_service.create_idea(sample_idea, mock_mongodb_client)
        
        # Verify
        assert result is True
        mock_notion_client.pages.create.assert_called_once()
        
        # Verify properties in the create call
        call_args = mock_notion_client.pages.create.call_args[1]
        assert call_args['parent']['database_id'] == 'test-database-id'
        assert call_args['properties']['Title']['title'][0]['text']['content'] == sample_idea['title']
        assert call_args['properties']['Count']['number'] == 1
        assert call_args['properties']['Type']['rich_text'][0]['text']['content'] == sample_idea['type']

    def test_create_idea_error(self, notion_service, sample_idea, mock_notion_client, mock_mongodb_client):
        """Test error handling when creating an idea."""
        # Setup
        mock_notion_client.pages.create.side_effect = Exception("Test error")
        
        # Call the method
        result = notion_service.create_idea(sample_idea, mock_mongodb_client)
        
        # Verify
        assert result is False
        mock_notion_client.pages.create.assert_called_once()

    def test_find_idea_in_notion(self, notion_service, mock_notion_client):
        """Test finding an idea in Notion."""
        # Setup
        existing_page = {
            'id': 'page-id-123',
            'properties': {
                'Title': {
                    'title': [{'text': {'content': 'Test Idea'}}]
                }
            }
        }
        mock_notion_client.databases.query.return_value = {'results': [existing_page]}
        
        # Call the method
        result = notion_service.find_idea_in_notion('Test Idea')
        
        # Verify
        assert result == existing_page
        mock_notion_client.databases.query.assert_called_once_with(
            database_id='test-database-id',
            filter={
                'property': 'Title',
                'title': {
                    'equals': 'Test Idea'
                }
            }
        )

    def test_fetch_url_metadata(self, notion_service, mock_mongodb_client):
        """Test fetching URL metadata."""
        # Call the method
        result = notion_service.fetch_url_metadata(mock_mongodb_client, 'test_hash_123')
        
        # Verify
        assert 'url' in result
        assert 'title' in result
        assert 'created_at' in result
        mock_mongodb_client.fetch_url_metadata.assert_called_once_with('test_hash_123')

    def test_fetch_url_metadata_not_found(self, notion_service, mock_mongodb_client):
        """Test fetching URL metadata when not found."""
        # Setup
        mock_mongodb_client.fetch_url_metadata.return_value = None
        
        # Call the method
        result = notion_service.fetch_url_metadata(mock_mongodb_client, 'non_existent_hash')
        
        # Verify
        assert result == {'url': '', 'title': '', 'created_at': ''}
        mock_mongodb_client.fetch_url_metadata.assert_called_once_with('non_existent_hash')

    def test_fetch_url_metadata_error(self, notion_service, mock_mongodb_client):
        """Test error handling when fetching URL metadata."""
        # Setup
        mock_mongodb_client.fetch_url_metadata.side_effect = Exception("Test error")
        
        # Call the method
        result = notion_service.fetch_url_metadata(mock_mongodb_client, 'test_hash_123')
        
        # Verify
        assert result == {'url': '', 'title': '', 'created_at': ''}
        mock_mongodb_client.fetch_url_metadata.assert_called_once_with('test_hash_123')


if __name__ == "__main__":
    # This allows running the tests directly with python
    import sys
    sys.exit(pytest.main(["-v", __file__]))
