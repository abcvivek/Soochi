import os
import uuid
import pytest
import logging
from unittest.mock import MagicMock, patch
from dotenv import load_dotenv
from soochi.fetch_batch_status import write_ideas_to_notion, find_idea_in_notion
from soochi.mongodb_client import MongoDBClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Test data
TEST_IDEA = {
    'title': f'Test Idea {uuid.uuid4()}',  # Unique title to avoid conflicts
    'type': 'Technology',
    'problemStatement': 'This is a test problem statement',
    'solution': 'This is a test solution',
    'targetAudience': 'Test audience',
    'innovationScore': 8,
    'potentialApplications': 'Test applications',
    'prerequisites': 'Test prerequisites',
    'additionalNotes': 'Test notes',
    'url_hash': 'test_hash'
}

# Mock URL metadata
MOCK_URL_METADATA = {
    'url': 'https://example.com',
    'title': 'Example Website',
    'created_at': '2025-04-01T00:00:00'  # Changed to string date format without 'Z'
}

@pytest.fixture
def mock_mongodb_client():
    """Create a mock MongoDB client."""
    client = MagicMock()
    client.seen_urls.find_one.return_value = {
        'url': MOCK_URL_METADATA['url'],
        'title': MOCK_URL_METADATA['title'],
        'created_at': MOCK_URL_METADATA['created_at']
    }
    return client

@pytest.fixture
def mock_pinecone_client():
    """Create a mock Pinecone client."""
    with patch('soochi.fetch_batch_status.pinecone_client') as mock_client:
        mock_index = MagicMock()
        mock_client.Index.return_value = mock_index
        
        # Mock fetch method to return test data
        mock_index.fetch.return_value = {
            'vectors': {
                TEST_IDEA['title']: {
                    'metadata': {
                        'count': 1,
                        'title': TEST_IDEA['title'],
                        'type': TEST_IDEA['type'],
                        'problemStatement': TEST_IDEA['problemStatement'],
                        'solution': TEST_IDEA['solution'],
                        'targetAudience': TEST_IDEA['targetAudience'],
                        'innovationScore': TEST_IDEA['innovationScore'],
                        'potentialApplications': TEST_IDEA['potentialApplications'],
                        'prerequisites': TEST_IDEA['prerequisites'],
                        'additionalNotes': TEST_IDEA['additionalNotes']
                    }
                }
            }
        }
        yield mock_client

@pytest.fixture
def mock_notion_client():
    """Create a mock Notion client."""
    with patch('soochi.fetch_batch_status.notion_client') as mock_client:
        # Set up pages.create and pages.update as MagicMocks
        mock_client.pages.create = MagicMock()
        mock_client.pages.update = MagicMock()
        
        # Set up databases.query to return empty results initially (no existing ideas)
        mock_client.databases.query = MagicMock(return_value={'results': []})
        
        yield mock_client

def test_write_new_idea_to_notion(mock_mongodb_client, mock_pinecone_client, mock_notion_client):
    """Test writing a new idea to Notion."""
    # Ensure find_idea_in_notion returns None (idea doesn't exist)
    with patch('soochi.fetch_batch_status.find_idea_in_notion', return_value=None):
        # Call the function with our test idea
        write_ideas_to_notion([TEST_IDEA], mock_mongodb_client)
        
        # Verify that pages.create was called once
        mock_notion_client.pages.create.assert_called_once()
        
        # Verify that pages.update was not called
        mock_notion_client.pages.update.assert_not_called()
        
        # Get the call arguments
        call_args = mock_notion_client.pages.create.call_args[1]
        
        # Verify that the title matches our test idea
        title_content = call_args['properties']['Title']['title'][0]['text']['content']
        assert title_content == TEST_IDEA['title']
        
        # Verify that the count is 1 for a new idea
        assert call_args['properties']['Count']['number'] == 1
        
        logger.info(f"Successfully created new idea in Notion: {TEST_IDEA['title']}")

def test_update_existing_idea_in_notion(mock_mongodb_client, mock_pinecone_client, mock_notion_client):
    """Test updating an existing idea in Notion."""
    # Mock an existing page in Notion
    existing_page = {
        'id': 'test-page-id',
        'properties': {
            'Title': {
                'title': [{'text': {'content': TEST_IDEA['title']}}]
            },
            'Count': {
                'number': 1
            }
        }
    }
    
    # Update the mock Pinecone data to have a count of 2
    mock_pinecone_client.Index().fetch.return_value['vectors'][TEST_IDEA['title']]['metadata']['count'] = 2
    
    # Ensure find_idea_in_notion returns our existing page
    with patch('soochi.fetch_batch_status.find_idea_in_notion', return_value=existing_page):
        # Call the function with our test idea
        write_ideas_to_notion([TEST_IDEA], mock_mongodb_client)
        
        # Verify that pages.update was called once
        mock_notion_client.pages.update.assert_called_once()
        
        # Verify that pages.create was not called
        mock_notion_client.pages.create.assert_not_called()
        
        # Get the call arguments
        call_args = mock_notion_client.pages.update.call_args[1]
        
        # Verify that the page ID matches our existing page
        assert call_args['page_id'] == existing_page['id']
        
        # Verify that the count is updated to 2
        assert call_args['properties']['Count']['number'] == 2
        
        logger.info(f"Successfully updated existing idea in Notion: {TEST_IDEA['title']}")

def test_find_idea_in_notion(mock_notion_client):
    """Test finding an idea in Notion."""
    # Mock a response with results
    mock_notion_client.databases.query.return_value = {
        'results': [{
            'id': 'test-page-id',
            'properties': {
                'Title': {
                    'title': [{'text': {'content': TEST_IDEA['title']}}]
                }
            }
        }]
    }
    
    # Call the function
    result = find_idea_in_notion(TEST_IDEA['title'])
    
    # Verify that databases.query was called with the correct filter
    mock_notion_client.databases.query.assert_called_once()
    call_args = mock_notion_client.databases.query.call_args[1]
    assert call_args['filter']['property'] == 'Title'
    assert call_args['filter']['title']['equals'] == TEST_IDEA['title']
    
    # Verify that the result matches our expected page
    assert result['id'] == 'test-page-id'
    
    logger.info(f"Successfully found idea in Notion: {TEST_IDEA['title']}")

def test_find_nonexistent_idea_in_notion(mock_notion_client):
    """Test finding a nonexistent idea in Notion."""
    # Mock an empty response
    mock_notion_client.databases.query.return_value = {'results': []}
    
    # Call the function
    result = find_idea_in_notion('Nonexistent Idea')
    
    # Verify that databases.query was called
    mock_notion_client.databases.query.assert_called_once()
    
    # Verify that the result is None
    assert result is None
    
    logger.info("Successfully verified that nonexistent idea returns None")

def test_error_handling_in_find_idea(mock_notion_client):
    """Test error handling in find_idea_in_notion."""
    # Mock an exception
    mock_notion_client.databases.query.side_effect = Exception("Test exception")
    
    # Call the function
    result = find_idea_in_notion(TEST_IDEA['title'])
    
    # Verify that the result is None
    assert result is None
    
    logger.info("Successfully handled error in find_idea_in_notion")

def test_error_handling_in_write_ideas(mock_mongodb_client, mock_pinecone_client, mock_notion_client):
    """Test error handling in write_ideas_to_notion."""
    # Mock an exception when fetching from Pinecone
    mock_pinecone_client.Index().fetch.side_effect = Exception("Test exception")
    
    # Ensure find_idea_in_notion returns an existing page
    existing_page = {
        'id': 'test-page-id',
        'properties': {
            'Title': {
                'title': [{'text': {'content': TEST_IDEA['title']}}]
            }
        }
    }
    
    with patch('soochi.fetch_batch_status.find_idea_in_notion', return_value=existing_page):
        # Call the function
        write_ideas_to_notion([TEST_IDEA], mock_mongodb_client)
        
        # Verify that pages.update was called with a default count of 1
        mock_notion_client.pages.update.assert_called_once()
        call_args = mock_notion_client.pages.update.call_args[1]
        assert call_args['properties']['Count']['number'] == 1
        
        logger.info("Successfully handled error in write_ideas_to_notion")

if __name__ == "__main__":
    # This allows running the tests directly with python
    import sys
    sys.exit(pytest.main(["-v", __file__]))
