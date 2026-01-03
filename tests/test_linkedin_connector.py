"""
Unit tests for the LinkedInConnector class.
Uses mocking to avoid real API calls.
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
import requests
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from linkedin_agents import LinkedInConnector


class TestLinkedInConnectorInit:
    """Test LinkedInConnector initialization."""
    
    def test_init_with_credentials(self, mock_linkedin_credentials):
        """Should initialize with environment credentials."""
        connector = LinkedInConnector()
        
        assert connector.access_token == "test_token_123"
        assert connector.author_urn == "urn:li:person:test123"
    
    def test_init_without_credentials(self, monkeypatch):
        """Should handle missing credentials gracefully."""
        monkeypatch.delenv("LINKEDIN_ACCESS_TOKEN", raising=False)
        monkeypatch.delenv("LINKEDIN_PERSON_URN", raising=False)
        
        connector = LinkedInConnector()
        
        assert connector.access_token is None
        assert connector.author_urn is None


class TestLinkedInImageUpload:
    """Test LinkedIn image upload flow."""
    
    @patch('requests.post')
    def test_register_upload_success(self, mock_post, mock_linkedin_credentials):
        """Should register upload and return URL + URN."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'value': {
                'uploadUrl': 'https://upload.linkedin.com/test',
                'image': 'urn:li:image:123'
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response
        
        connector = LinkedInConnector()
        upload_url, image_urn = connector.register_upload()
        
        assert upload_url == 'https://upload.linkedin.com/test'
        assert image_urn == 'urn:li:image:123'
    
    @patch('requests.put')
    def test_upload_image_success(self, mock_put, mock_linkedin_credentials):
        """Should upload image binary successfully."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_put.return_value = mock_response
        
        connector = LinkedInConnector()
        connector.upload_image('https://upload.linkedin.com/test', b'fake_image_data')
        
        mock_put.assert_called_once()


class TestLinkedInPosting:
    """Test LinkedIn post creation."""
    
    def test_post_without_credentials(self, monkeypatch):
        """Should skip posting if credentials missing."""
        monkeypatch.delenv("LINKEDIN_ACCESS_TOKEN", raising=False)
        monkeypatch.delenv("LINKEDIN_PERSON_URN", raising=False)
        
        connector = LinkedInConnector()
        result = connector.post_content("Test post")
        
        assert result is None
    
    @patch('requests.post')
    def test_post_text_only_success(self, mock_post, mock_linkedin_credentials):
        """Should post text-only content successfully."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {'x-restli-id': 'urn:li:share:999'}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response
        
        connector = LinkedInConnector()
        result = connector.post_content("Test post content")
        
        assert result == 'urn:li:share:999'
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_post_failure_handling(self, mock_post, mock_linkedin_credentials):
        """Should handle API errors gracefully."""
        mock_post.side_effect = requests.exceptions.HTTPError("API Error")
        
        connector = LinkedInConnector()
        result = connector.post_content("Test post")
        
        assert result is None


class TestLinkedInSocialActions:
    """Test LinkedIn social actions (stats) retrieval."""
    
    @patch('requests.get')
    def test_get_social_actions_success(self, mock_get, mock_linkedin_credentials):
        """Should retrieve likes and comments."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'likesSummary': {'totalLikes': 42},
            'commentsSummary': {'totalComments': 7}
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        connector = LinkedInConnector()
        stats = connector.get_social_actions('urn:li:share:123')
        
        assert stats['likes'] == 42
        assert stats['comments'] == 7
    
    @patch('requests.get')
    def test_get_social_actions_404(self, mock_get, mock_linkedin_credentials):
        """Should return zeros for 404 (post not found)."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        connector = LinkedInConnector()
        stats = connector.get_social_actions('urn:li:share:nonexistent')
        
        assert stats == {"likes": 0, "comments": 0}
    
    @patch('requests.get')
    def test_get_social_actions_403_permission(self, mock_get, mock_linkedin_credentials):
        """Should handle 403 permission denied."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=MagicMock(status_code=403)
        )
        mock_get.return_value = mock_response
        
        connector = LinkedInConnector()
        stats = connector.get_social_actions('urn:li:share:123')
        
        assert stats == {"likes": 0, "comments": 0}
