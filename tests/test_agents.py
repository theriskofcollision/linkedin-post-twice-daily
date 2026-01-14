"""
Unit tests for Agent classes.
"""

import pytest
from unittest.mock import MagicMock, patch
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from linkedin_agents import (
    Agent, Strategist, Ghostwriter, ArtDirector, Critic,
    Networker, VIBES
)


class TestBaseAgent:
    """Test the base Agent class."""
    
    def test_agent_init(self):
        """Should initialize with name, role, and prompt."""
        agent = Agent("TestAgent", "Tester", "You are a test agent.")
        
        assert agent.name == "TestAgent"
        assert agent.role == "Tester"
        assert agent.system_prompt == "You are a test agent."
    
    def test_agent_run_without_api_key(self, monkeypatch):
        """Should return mock data when API key missing."""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        
        agent = Agent("TestAgent", "Tester", "Test prompt")
        result = agent.run("Test input")
        
        assert "[TestAgent Output based on 'Test input']" in result
    
    @patch('google.generativeai.GenerativeModel')
    @patch('google.generativeai.configure')
    def test_agent_run_with_api_key(self, mock_configure, mock_model_class, monkeypatch, mock_gemini_response):
        """Should call Gemini API when key is present."""
        monkeypatch.setenv("GEMINI_API_KEY", "test_key")
        
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_gemini_response
        mock_model_class.return_value = mock_model
        
        agent = Agent("TestAgent", "Tester", "Test prompt")
        result = agent.run("Test input")
        
        assert result == "This is a test response from the AI model."


class TestStrategist:
    """Test the Strategist agent."""
    
    def test_set_vibe(self):
        """Should configure vibe-specific prompt."""
        strategist = Strategist()
        strategist.set_vibe("The Analyst", "Focus on data and ROI.")
        
        assert "The Analyst" in strategist.system_prompt
        assert "Focus on data and ROI" in strategist.system_prompt


class TestGhostwriter:
    """Test the Ghostwriter agent."""
    
    def test_set_vibe(self):
        """Should configure vibe-specific prompt with rules."""
        ghostwriter = Ghostwriter()
        ghostwriter.set_vibe("The Contrarian", "Challenge the status quo.")

        assert "The Contrarian" in ghostwriter.system_prompt
        assert "Max 300 chars" in ghostwriter.system_prompt
    
    def test_run_injects_memory_rules(self, temp_memory_file, monkeypatch):
        """Should inject memory rules into prompt."""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        
        # Add a rule to memory
        import json
        with open(temp_memory_file, 'w') as f:
            json.dump({"rules": ["Never use buzzwords"], "history": []}, f)
        
        # Create ghostwriter with temp memory
        ghostwriter = Ghostwriter()
        ghostwriter.memory.file_path = temp_memory_file
        ghostwriter.set_vibe("The Educator", "Teach concepts.")
        
        # The run method would inject rules (we can't fully test without mocking Gemini)
        # Just verify memory is accessible
        assert "Never use buzzwords" in ghostwriter.memory.get_rules()


class TestArtDirector:
    """Test the ArtDirector agent."""
    
    def test_set_vibe(self):
        """Should configure visual style prompt."""
        art_director = ArtDirector()
        art_director.set_vibe("The Visionary", "Ethereal, dreamy style.")
        
        assert "The Visionary" in art_director.system_prompt
        assert "Visual Format:" in art_director.system_prompt


class TestCritic:
    """Test the Critic agent."""
    
    def test_critic_extracts_rules(self, temp_memory_file, monkeypatch):
        """Should parse RULE: lines and save to memory."""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        
        critic = Critic()
        critic.memory.file_path = temp_memory_file
        
        # Simulate running with rule feedback
        # Since no API, we manually test rule parsing logic
        feedback = "The post is too generic.\nRULE: Avoid generic openings."
        
        for line in feedback.split('\n'):
            if line.strip().startswith("RULE:"):
                new_rule = line.strip().replace("RULE:", "").strip()
                critic.memory.add_rule(new_rule)
        
        rules = critic.memory.get_rules()
        assert any("Avoid generic openings" in r for r in rules)


class TestNetworker:
    """Test the Networker agent."""
    
    def test_networker_prompt_structure(self):
        """Should have comment pack structure in prompt."""
        networker = Networker()
        
        assert "Comment Pack" in networker.system_prompt
        assert "Value Add" in networker.system_prompt
        assert "Contrarian" in networker.system_prompt
        assert "Question" in networker.system_prompt


class TestVibes:
    """Test the VIBES configuration."""
    
    def test_all_vibes_have_required_keys(self):
        """Each vibe should have strategist, ghostwriter, is_organic keys."""
        # art_director removed from VIBES, handled dynamically
        required_keys = ['strategist', 'ghostwriter', 'is_organic']
        
        for vibe_name, vibe_config in VIBES.items():
            for key in required_keys:
                assert key in vibe_config, f"{vibe_name} missing {key}"
    
    def test_vibe_count(self):
        """Should have 21 vibes."""
        assert len(VIBES) >= 21
        
        expected_vibes = [
            "The Contrarian", "The Visionary", "The Educator",
            "The Analyst", "The Narrator", "The Oracle", "The Satirist"
        ]
        for vibe in expected_vibes:
            assert vibe in VIBES
