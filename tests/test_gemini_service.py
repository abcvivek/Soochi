"""
Tests for the Gemini service module.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from soochi.services.gemini_service import GeminiService


@pytest.fixture
def sample_content():
    """Fixture providing sample content for testing."""
    return "This is a sample article content for testing the Gemini service."


@pytest.fixture
def sample_prompt():
    """Fixture providing a sample prompt for testing."""
    return "Extract ideas from the following content: {content}"


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
        'url_hash': 'test_hash_123'
    }


@pytest.fixture
def mock_gemini_client():
    """Fixture providing a mocked Gemini client."""
    with patch('google.genai.Client') as mock_client:
        mock_client.return_value.models = MagicMock()
        mock_client.return_value.models.generate_content = MagicMock()
        yield mock_client


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    with patch('openai.OpenAI') as mock_client:
        # Create a mock embedding data object with the expected structure
        mock_embedding_data = MagicMock()
        mock_embedding_data.embedding = [0.1] * 1536
        
        # Create a mock response with a data list containing the embedding data
        mock_response = MagicMock()
        mock_response.data = [mock_embedding_data]
        
        # Setup the mock client to return our structured response
        mock_client.return_value.embeddings.create.return_value = mock_response
        yield mock_client


@pytest.fixture
def gemini_service(mock_gemini_client, mock_openai_client):
    """Fixture providing a GeminiService instance with mocked dependencies."""
    service = GeminiService(
        google_api_key="test_google_key",
        openai_api_key="test_openai_key",
        model="gemini-pro"
    )
    # Replace the real clients with our mocked ones
    service.gemini_client = mock_gemini_client.return_value
    service.openai_client = mock_openai_client.return_value
    return service


class TestGeminiService:
    """Tests for the GeminiService."""

    def test_process_content_success(self, gemini_service, sample_content, sample_prompt, mock_gemini_client):
        """Test successful processing of content with Gemini."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "endReason": "STOP",
            "output": [
                {
                    "title": "Test Idea",
                    "type": "SaaS",
                    "problemStatement": "Problem statement",
                    "solution": "Solution",
                    "targetAudience": "Developers",
                    "innovationScore": 8.5,
                    "potentialApplications": "Various applications",
                    "prerequisites": "Python, AI knowledge",
                    "additionalNotes": "Additional notes"
                }
            ]
        })
        
        # Configure the mock client to return our mock response
        mock_gemini_client.return_value.models.generate_content.return_value = mock_response
        
        # Mock the hash_url function to return a predictable value
        with patch('soochi.services.gemini_service.hash_url', return_value="test_hash_123"):
            # Call the method
            url = "https://example.com/test"
            result = gemini_service.process_content(url, sample_content, sample_prompt)
            
            # Assertions
            assert len(result) == 1
            assert result[0]["title"] == "Test Idea"
            assert result[0]["url_hash"] == "test_hash_123"
            
            # Verify mocks were called correctly
            mock_gemini_client.return_value.models.generate_content.assert_called_once()

    def test_process_content_empty(self, gemini_service, sample_prompt, mock_gemini_client):
        """Test handling of empty content."""
        # Setup mock response for empty content
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "endReason": "STOP",
            "output": []
        })
        
        # Configure the mock to return our mock response
        gemini_service.gemini_client.models.generate_content.return_value = mock_response
        
        # Call the method with empty content
        url = "https://example.com/test"
        result = gemini_service.process_content(url, "", sample_prompt)
        
        # Assertions
        assert result == []
        
        # Verify generate_content was called (the service still calls the API even with empty content)
        gemini_service.gemini_client.models.generate_content.assert_called_once()

    @patch('soochi.services.gemini_service.logger')
    def test_process_content_exception(self, mock_logger, gemini_service, sample_content, sample_prompt, mock_gemini_client):
        """Test handling of exceptions during processing."""
        # Setup mock to raise an exception
        mock_gemini_client.return_value.models.generate_content.side_effect = Exception("Test exception")
        
        # Call the method
        url = "https://example.com/test"
        result = gemini_service.process_content(url, sample_content, sample_prompt)
        
        # Assertions
        assert result == []
        
        # Verify error was logged
        mock_logger.error.assert_called_once()

    def test_create_embedding_success(self, gemini_service):
        """Test successful creation of embeddings."""
        # Create a mock embedding with the expected structure
        mock_embedding = [0.1] * 1536
        
        # Configure the mock to return our embedding directly
        gemini_service.openai_client.embeddings.create = MagicMock()
        gemini_service.openai_client.embeddings.create.return_value.data = [
            MagicMock(embedding=mock_embedding)
        ]
        
        # Call the method
        text = "Test text for embedding"
        result = gemini_service.create_embedding(text)
        
        # Assertions
        assert len(result) == 1536
        assert result[0] == 0.1
        
        # Verify OpenAI client was called correctly
        gemini_service.openai_client.embeddings.create.assert_called_once()

    @patch('soochi.services.gemini_service.logger')
    def test_create_embedding_exception(self, mock_logger, gemini_service, mock_openai_client):
        """Test handling of exceptions during embedding creation."""
        # Setup mock to raise an exception
        mock_openai_client.return_value.embeddings.create.side_effect = Exception("Test exception")
        
        # Call the method
        text = "Test text for embedding"
        result = gemini_service.create_embedding(text)
        
        # Assertions
        assert result == []  # The method returns an empty list on error, not None
        
        # Verify error was logged
        mock_logger.error.assert_called_once()


if __name__ == "__main__":
    # This allows running the tests directly with python
    import sys
    sys.exit(pytest.main(["-v", __file__]))
