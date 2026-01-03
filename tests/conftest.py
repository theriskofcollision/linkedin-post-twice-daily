"""
Pytest fixtures and configuration for LinkedIn Growth Workflow tests.
"""

import pytest
import json
import os
import tempfile
from unittest.mock import MagicMock, patch


@pytest.fixture
def temp_memory_file():
    """Create a temporary memory.json file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({"rules": [], "history": []}, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)
    # Also cleanup lock file
    lock_path = f"{temp_path}.lock"
    if os.path.exists(lock_path):
        os.remove(lock_path)


@pytest.fixture
def sample_memory_data():
    """Sample memory data for testing."""
    return {
        "rules": [
            "Never use the word 'unleash'",
            "Avoid corporate buzzwords"
        ],
        "history": [
            {
                "date": "12345",
                "topic": "Test Topic",
                "vibe": "The Analyst",
                "urn": "urn:li:share:123456",
                "stats": {"likes": 10, "comments": 5}
            }
        ],
        "latest_comment_pack": "Test comment pack"
    }


@pytest.fixture
def mock_gemini_response():
    """Mock Gemini API response."""
    mock_response = MagicMock()
    mock_response.text = "This is a test response from the AI model."
    return mock_response


@pytest.fixture
def mock_linkedin_credentials(monkeypatch):
    """Set up mock LinkedIn credentials."""
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "test_token_123")
    monkeypatch.setenv("LINKEDIN_PERSON_URN", "urn:li:person:test123")


@pytest.fixture
def mock_api_keys(monkeypatch):
    """Set up all mock API keys."""
    monkeypatch.setenv("GEMINI_API_KEY", "test_gemini_key")
    monkeypatch.setenv("NEWS_API_KEY", "test_news_key")
    monkeypatch.setenv("TAVILY_API_KEY", "test_tavily_key")


@pytest.fixture
def sample_hackernews_story():
    """Sample HackerNews story response."""
    return {
        "id": 12345,
        "title": "New AI Agent Framework Released",
        "url": "https://example.com/ai-agent",
        "score": 150
    }


@pytest.fixture
def sample_arxiv_response():
    """Sample arXiv API response XML."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
        <entry>
            <title>Large Language Models for Code Generation</title>
            <id>http://arxiv.org/abs/2301.00001</id>
            <summary>This paper explores the use of LLMs for automated code generation...</summary>
        </entry>
    </feed>'''
