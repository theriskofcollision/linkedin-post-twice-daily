import pytest
from unittest.mock import MagicMock, patch
from linkedin_agents import ArtDirector, STYLE_MATRIX, VIBES, POST_FORMATS, OrganicImageSearcher, Orchestrator
import json
import os

def test_art_director_randomizes_style():
    ad = ArtDirector()
    ad.set_vibe("The Contrarian", "Challenge status quo")
    
    assert ad.current_medium in STYLE_MATRIX["mediums"]
    assert ad.current_lighting in STYLE_MATRIX["lighting"]
    assert ad.current_palette in STYLE_MATRIX["palettes"]
    
    # Check if prompt contains the styles
    assert ad.current_medium in ad.system_prompt
    assert ad.current_lighting in ad.system_prompt
    assert ad.current_palette in ad.system_prompt

def test_organic_image_searcher_logic():
    with patch("linkedin_agents.TavilyConnector.search") as mock_search:
        mock_search.return_value = {
            "text": "Some text",
            "images": ["https://example.com/img1.jpg", "https://example.com/img2.jpg"]
        }
        
        with patch("requests.get") as mock_get:
            mock_get.return_value.content = b"fake_image_data"
            mock_get.return_value.status_code = 200
            
            searcher = OrganicImageSearcher()
            img_data = searcher.get_organic_image("AI agents")
            
            assert img_data == b"fake_image_data"
            mock_search.assert_called_once()
            assert "include_images=True" in str(mock_search.call_args) or mock_search.call_args[1].get("include_images") == True

def test_orchestrator_selects_format_and_vibe():
    with patch("linkedin_agents.ResearchManager.run") as mock_research:
        mock_research.return_value = "Trend brief"
        with patch("linkedin_agents.Strategist.run") as mock_strat:
            mock_strat.return_value = "Strategy"
            with patch("linkedin_agents.Ghostwriter.run") as mock_write:
                mock_write.return_value = "Post text"
                with patch("linkedin_agents.ArtDirector.run") as mock_art:
                    mock_art.return_value = "Visual concept"
                    with patch("linkedin_agents.LinkedInConnector.post_content") as mock_post:
                        mock_post.return_value = "urn:li:share:123"
                        
                        orch = Orchestrator()
                        # Mock config to avoid file load issues if any
                        orch.config = {
                            "variety": {"entropy_level": "high", "enabled_personas": "all"},
                            "topics": ["AI"],
                            "features": {"enable_image_generation": True}
                        }
                        
                        orch.run_workflow()
                        
                        # Verify vibe and format were selected
                        assert orch.ghostwriter.system_prompt is not None
                        assert "Post Format to Enforce:" in orch.ghostwriter.system_prompt
                        assert "MAX 500 characters" in orch.ghostwriter.system_prompt

def test_vibes_structure():
    for vibe, config in VIBES.items():
        assert "strategist" in config
        assert "ghostwriter" in config
        assert "is_organic" in config

def test_post_formats_list():
    assert len(POST_FORMATS) >= 15
    for fmt in POST_FORMATS:
        assert ":" in fmt # Format: Description
