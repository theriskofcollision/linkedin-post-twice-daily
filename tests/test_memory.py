"""
Unit tests for the Memory class.
"""

import pytest
import json
import os
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor

# Import will work after we update linkedin_agents.py
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from linkedin_agents import Memory


class TestMemoryBasics:
    """Test basic Memory operations."""
    
    def test_memory_creates_file_if_not_exists(self, tmp_path):
        """Memory should create a new file if it doesn't exist."""
        memory_path = tmp_path / "new_memory.json"
        memory = Memory(str(memory_path))
        
        assert memory_path.exists()
        with open(memory_path) as f:
            data = json.load(f)
        assert data == {"rules": [], "history": []}
    
    def test_memory_loads_existing_file(self, temp_memory_file, sample_memory_data):
        """Memory should load existing data correctly."""
        # Write sample data to temp file
        with open(temp_memory_file, 'w') as f:
            json.dump(sample_memory_data, f)
        
        memory = Memory(temp_memory_file)
        rules = memory.get_rules()
        
        assert len(rules) == 2
        assert "Never use the word 'unleash'" in rules
    
    def test_memory_handles_corrupted_file(self, tmp_path):
        """Memory should handle corrupted JSON gracefully."""
        memory_path = tmp_path / "corrupted.json"
        memory_path.write_text("not valid json {{{")
        
        memory = Memory(str(memory_path))
        rules = memory.get_rules()
        
        assert rules == []  # Should return empty, not crash


class TestMemoryRules:
    """Test Memory rule operations."""
    
    def test_add_rule(self, temp_memory_file):
        """Should add a new rule."""
        memory = Memory(temp_memory_file)
        memory.add_rule("Test rule 1")
        
        rules = memory.get_rules()
        assert "Test rule 1" in rules
    
    def test_add_duplicate_rule(self, temp_memory_file):
        """Should not add duplicate rules."""
        memory = Memory(temp_memory_file)
        memory.add_rule("Test rule")
        memory.add_rule("Test rule")  # Duplicate
        
        rules = memory.get_rules()
        assert rules.count("Test rule") == 1


class TestMemoryHistory:
    """Test Memory history operations."""
    
    def test_add_post_history(self, temp_memory_file):
        """Should add post to history."""
        memory = Memory(temp_memory_file)
        memory.add_post_history("AI Topic", "The Analyst", "urn:li:share:123")
        
        data = memory._load()
        assert len(data["history"]) == 1
        assert data["history"][0]["topic"] == "AI Topic"
        assert data["history"][0]["vibe"] == "The Analyst"
    
    def test_update_post_stats(self, temp_memory_file):
        """Should update stats for existing post."""
        memory = Memory(temp_memory_file)
        memory.add_post_history("Topic", "Vibe", "urn:li:share:456")
        memory.update_post_stats("urn:li:share:456", likes=25, comments=10)
        
        data = memory._load()
        assert data["history"][0]["stats"]["likes"] == 25
        assert data["history"][0]["stats"]["comments"] == 10


class TestMemoryPerformance:
    """Test Memory performance insights."""
    
    def test_get_performance_insights_empty(self, temp_memory_file):
        """Should handle empty history."""
        memory = Memory(temp_memory_file)
        insights = memory.get_performance_insights()
        
        assert "No past performance data" in insights
    
    def test_get_performance_insights_with_data(self, temp_memory_file, sample_memory_data):
        """Should return best performing vibe."""
        with open(temp_memory_file, 'w') as f:
            json.dump(sample_memory_data, f)
        
        memory = Memory(temp_memory_file)
        insights = memory.get_performance_insights()
        
        assert "The Analyst" in insights


class TestMemoryConcurrency:
    """Test Memory concurrent access (file locking)."""
    
    def test_concurrent_writes(self, temp_memory_file):
        """Multiple threads should not corrupt the file."""
        memory = Memory(temp_memory_file)
        
        def add_rules(thread_id):
            for i in range(5):
                memory.add_rule(f"Rule from thread {thread_id} - {i}")
        
        # Run multiple threads
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(add_rules, i) for i in range(3)]
            for f in futures:
                f.result()
        
        # Verify file is valid JSON and has all rules
        data = memory._load()
        assert len(data["rules"]) == 15  # 3 threads * 5 rules each


class TestMemoryArchive:
    """Test Memory archival functionality."""
    
    def test_archive_old_posts(self, temp_memory_file):
        """Should archive posts older than threshold."""
        import time
        
        # Create timestamps: one very old (will be archived), one recent (won't be)
        old_timestamp = "1"  # Very old
        new_timestamp = str(int(time.time() * 1000))  # Current time in ms
        
        old_data = {
            "rules": [],
            "history": [
                {"date": old_timestamp, "topic": "Old", "vibe": "V", "urn": "u1", "stats": {}},
                {"date": new_timestamp, "topic": "New", "vibe": "V", "urn": "u2", "stats": {}},
            ]
        }
        with open(temp_memory_file, 'w') as f:
            json.dump(old_data, f)
        
        memory = Memory(temp_memory_file)
        archived = memory.archive_old_posts(days=90)
        
        # Should have archived the old post
        assert archived == 1
        data = memory._load()
        assert len(data["history"]) == 1
        assert data["history"][0]["topic"] == "New"
