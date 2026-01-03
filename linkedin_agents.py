import os
import json
import random
import requests
import urllib.parse
import time
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

import google.generativeai as genai
import yaml
from filelock import FileLock
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
load_dotenv()

# Import structured logging
from logging_config import logger


# --- Configuration Loading ---

def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file with defaults."""
    defaults = {
        "model": {"name": "gemini-2.5-flash", "max_retries": 3, "base_delay_seconds": 5},
        "sources": {
            "hackernews": {"scan_limit": 15, "ai_results": 5},
            "newsapi": {"limit": 5},
            "arxiv": {"limit": 3},
            "tavily": {"max_results": 3}
        },
        "memory": {"file_path": "memory.json", "archive_days": 90},
        "image": {"width": 1200, "height": 628, "max_retries": 3, "timeout_seconds": 60},
        "logging": {"level": "INFO"},
        "topics": [
            "The rise of Multi-Agent Systems",
            "Why Chatbots are dead",
            "The future of coding is Agentic",
            "LLMs as Operating Systems",
            "Prompt Engineering is replaced by Flow Engineering"
        ]
    }
    
    try:
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                user_config = yaml.safe_load(f) or {}
            # Merge with defaults
            for key, value in user_config.items():
                if isinstance(value, dict) and key in defaults:
                    defaults[key].update(value)
                else:
                    defaults[key] = value
    except Exception as e:
        logger.warning(f"Could not load config.yaml: {e}. Using defaults.")
    
    return defaults


# Load config at module level
CONFIG = load_config()


# --- Data Structures ---

@dataclass
class TrendReport:
    topic: str
    source: str
    relevance: str
    details: str

@dataclass
class StrategyBrief:
    hook: str
    angle: str
    target_audience: str
    cta: str

@dataclass
class ContentDraft:
    text: str
    visual_prompt: str
    visual_text_overlay: Optional[str]

# --- Memory System ---

class Memory:
    """Persistent memory system with file locking for concurrent access."""
    
    def __init__(self, file_path: str = "memory.json"):
        self.file_path = file_path
        self.lock = FileLock(f"{file_path}.lock")
        
        if not os.path.exists(self.file_path):
            self._save({"rules": [], "history": []})

    def _load(self) -> Dict[str, Any]:
        """Load memory data with file locking."""
        try:
            with self.lock:
                with open(self.file_path, "r") as f:
                    return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Corrupted memory file: {e}. Resetting to empty.")
            return {"rules": [], "history": []}
        except FileNotFoundError:
            return {"rules": [], "history": []}
        except Exception as e:
            logger.exception(f"Unexpected error loading memory: {e}")
            return {"rules": [], "history": []}

    def _save(self, data: Dict[str, Any]) -> None:
        """Save memory data with file locking."""
        with self.lock:
            with open(self.file_path, "w") as f:
                json.dump(data, f, indent=2)

    def get_rules(self) -> List[str]:
        data = self._load()
        return data.get("rules", [])

    def add_rule(self, rule: str):
        data = self._load()
        if rule not in data["rules"]:
            data["rules"].append(rule)
            self._save(data)
            logger.info(f"🧠 Memory Updated: Added rule '{rule}'")

    def add_post_history(self, topic: str, vibe: str, urn: str):
        data = self._load()
        if "history" not in data:
            data["history"] = []
        
        entry = {
            "date": str(os.environ.get("GITHUB_RUN_ID", "manual")), # Use run ID or manual
            "topic": topic,
            "vibe": vibe,
            "urn": urn,
            "stats": {"likes": 0, "comments": 0} # Init stats
        }
        data["history"].append(entry)
        self._save(data)
        logger.info(f"🧠 Memory Updated: Logged post '{topic}' ({vibe})")

    def update_post_stats(self, urn: str, likes: int, comments: int):
        data = self._load()
        for post in data.get("history", []):
            if post["urn"] == urn:
                post["stats"] = {"likes": likes, "comments": comments}
                self._save(data)
                logger.info(f"🧠 Stats Updated for {urn}: {likes} likes, {comments} comments")
                return

    def get_performance_insights(self) -> str:
        data = self._load()
        history = data.get("history", [])
        if not history:
            return "No past performance data available."
        
        # Simple analysis
        best_post = max(history, key=lambda x: x["stats"]["likes"], default=None)
        if best_post and best_post["stats"]["likes"] > 0:
            return f"🏆 BEST PERFORMING VIBE: {best_post['vibe']} (Topic: {best_post['topic']} - {best_post['stats']['likes']} likes). REPEAT THIS STYLE."
        
        return "Not enough data to determine best vibe yet."

    def save_comment_pack(self, pack: str):
        data = self._load()
        data["latest_comment_pack"] = pack
        data["last_updated"] = str(os.environ.get("GITHUB_RUN_ID", "manual"))
        self._save(data)
        logger.info("🧠 Memory Updated: Saved latest Comment Pack.")

    def get_manual_feedback(self) -> str:
        """Read manual feedback from user-editable JSON file (Plan B)."""
        feedback_path = os.path.join(os.path.dirname(self.file_path), "manual_feedback.json")
        try:
            with open(feedback_path, "r") as f:
                data = json.load(f)
            
            stats = data.get("manual_stats", [])
            notes = data.get("feedback_notes", "")
            
            if not stats and not notes:
                return ""
            
            # Build insights from manual data
            insights = []
            if stats:
                # Find best performing vibe from manual stats
                best = max(stats, key=lambda x: x.get("likes", 0), default=None)
                if best and best.get("likes", 0) > 0:
                    insights.append(f"📊 MANUAL DATA: Best vibe is '{best.get('vibe', 'Unknown')}' with {best.get('likes')} likes.")
            
            if notes and notes != "Add your weekly observations here. Example: 'Short posts get more likes than long ones.'":
                insights.append(f"📝 USER NOTES: {notes}")
            
            return " | ".join(insights) if insights else ""
        except FileNotFoundError:
            return ""
        except Exception as e:
            logger.warning(f"Could not read manual feedback: {e}")
            return ""
    
    def archive_old_posts(self, days: int = 90) -> int:
        """Archive posts older than specified days. Returns count of archived posts."""
        data = self._load()
        history = data.get("history", [])
        
        if not history:
            return 0
        
        # Calculate cutoff timestamp
        # Posts use GitHub run ID as date which is a timestamp
        cutoff = int(time.time() * 1000) - (days * 24 * 60 * 60 * 1000)
        
        new_history = []
        archived = []
        
        for post in history:
            try:
                post_date = int(post.get("date", 0))
                if post_date > cutoff or post.get("date") == "manual":
                    new_history.append(post)
                else:
                    archived.append(post)
            except (ValueError, TypeError):
                new_history.append(post)  # Keep if can't parse date
        
        if archived:
            # Save archived posts to separate file
            archive_path = self.file_path.replace(".json", "_archive.json")
            try:
                existing_archive = []
                if os.path.exists(archive_path):
                    with open(archive_path, "r") as f:
                        existing_archive = json.load(f)
                
                existing_archive.extend(archived)
                with open(archive_path, "w") as f:
                    json.dump(existing_archive, f, indent=2)
                
                logger.info(f"📦 Archived {len(archived)} old posts to {archive_path}")
            except Exception as e:
                logger.error(f"Failed to archive posts: {e}")
            
            # Update main memory
            data["history"] = new_history
            self._save(data)
        
        return len(archived)
    
    def check_token_expiry_warning(self) -> Optional[str]:
        """Check if LinkedIn token might be expiring soon."""
        data = self._load()
        history = data.get("history", [])
        
        if len(history) >= 60:  # ~30 days of 2x daily posts
            # Token typically expires in 60 days
            first_post = history[0] if history else None
            if first_post:
                return "⚠️ WARNING: Your LinkedIn access token may expire soon. Consider refreshing it."
        return None

# --- Base Agent ---

class Agent:
    def __init__(self, name: str, role: str, system_prompt: str):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt

    def run(self, input_data: str) -> Optional[str]:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logger.warning(f"Missing GEMINI_API_KEY. Returning mock data for {self.name}.")
            return f"[{self.name} Output based on '{input_data}']"

        logger.info(f"--- {self.name} ({self.role}) Working ---")
        logger.debug(f"INPUT: {input_data[:200]}...")
        
        max_retries = CONFIG.get("model", {}).get("max_retries", 3)
        base_delay = CONFIG.get("model", {}).get("base_delay_seconds", 5)
        model_name = CONFIG.get("model", {}).get("name", "gemini-2.5-flash")
        
        for attempt in range(max_retries):
            try:
                genai.configure(api_key=api_key)
                if attempt == 0:
                    logger.info(f"Using model: {model_name}")
                else:
                    logger.warning(f"Retry attempt {attempt + 1}/{max_retries}")
                
                model = genai.GenerativeModel(model_name)
                
                full_prompt = f"{self.system_prompt}\n\nTask Input: {input_data}"
                response = model.generate_content(full_prompt)
                
                result = response.text.strip()
                logger.info(f"OUTPUT: {result[:100]}...")
                return result
                
            except requests.exceptions.Timeout as e:
                logger.warning(f"Request timed out: {e}")
                if attempt < max_retries - 1:
                    wait_time = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    time.sleep(wait_time)
                    continue
                return None
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "Resource exhausted" in error_str:
                    if attempt < max_retries - 1:
                        wait_time = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        logger.warning(f"Rate limit hit (429). Waiting {wait_time:.1f}s before retry...")
                        time.sleep(wait_time)
                        continue
                
                logger.error(f"Gemini API Error: {e}")
                return None


class HackerNewsConnector:
    def get_top_ai_stories(self, limit: int = None) -> str:
        if limit is None:
            limit = CONFIG.get("sources", {}).get("hackernews", {}).get("ai_results", 5)
        scan_limit = CONFIG.get("sources", {}).get("hackernews", {}).get("scan_limit", 15)
        
        logger.info("--- HackerNews Connector Working ---")
        try:
            # 1. Get Top Stories IDs
            top_stories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
            response = requests.get(top_stories_url, timeout=10)
            response.raise_for_status()
            story_ids = response.json()[:scan_limit]  # Reduced from 50 to 15

            stories = []
            logger.info(f"Scanning top {len(story_ids)} stories for AI/LLM content...")
            
            for sid in story_ids:
                if len(stories) >= limit:
                    break
                    
                item_url = f"https://hacker-news.firebaseio.com/v0/item/{sid}.json"
                item_resp = requests.get(item_url)
                item = item_resp.json()
                
                title = item.get('title', '')
                url = item.get('url', '')
                score = item.get('score', 0)
                
                # Simple keyword filter
                keywords = ['ai', 'llm', 'gpt', 'agent', 'model', 'neural', 'machine learning', 'robot', 'bot', 'intelligence', 'deepmind', 'openai']
                if any(k in title.lower() for k in keywords):
                    stories.append(f"- Title: {title}\n  URL: {url}\n  Score: {score}")
                    logger.debug(f"Found: {title}")

            if not stories:
                return "No specific AI stories found. Using general knowledge."
            
            return "\n\n".join(stories)
        
        except requests.exceptions.RequestException as e:
            logger.error(f"HackerNews request failed: {e}")
            return "Error fetching HackerNews data."
        except json.JSONDecodeError as e:
            logger.error(f"HackerNews returned invalid JSON: {e}")
            return "Error parsing HackerNews data."
        except Exception as e:
            logger.exception(f"Unexpected HackerNews error: {e}")
            return "Error fetching HackerNews data."

class NewsAPIConnector:
    def get_tech_headlines(self, limit: int = 5) -> str:
        logger.info("--- NewsAPI Connector Working ---")
        api_key = os.environ.get("NEWS_API_KEY")
        if not api_key:
            logger.warning("Missing NEWS_API_KEY. Skipping NewsAPI.")
            return ""

        try:
            # Fetch top tech headlines
            url = f"https://newsapi.org/v2/top-headlines?category=technology&language=en&pageSize=10&apiKey={api_key}"
            response = requests.get(url)
            data = response.json()
            
            articles = []
            logger.info(f"Scanning {len(data.get('articles', []))} articles from NewsAPI...")
            
            for article in data.get('articles', [])[:limit]:
                title = article.get('title', '')
                url = article.get('url', '')
                source = article.get('source', {}).get('name', 'Unknown')
                
                articles.append(f"- Title: {title}\n  Source: {source}\n  URL: {url}")
                logger.debug(f"Found: {title}")

            if not articles:
                return "No recent tech headlines found."
            
            return "\n\n".join(articles)
            
        except Exception as e:
            logger.error(f"NewsAPI Error: {e}")
            return "Error fetching NewsAPI data."

class ArxivConnector:
    def get_latest_papers(self, limit: int = 3) -> str:
        logger.info("--- arXiv Connector Working ---")
        try:
            # Search for AI/LLM papers
            # cat:cs.AI = Computer Science AI
            # sortBy=submittedDate&sortOrder=descending
            url = "http://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.CL&start=0&max_results=5&sortBy=submittedDate&sortOrder=descending"
            response = requests.get(url)
            
            # Simple string parsing to avoid heavy XML dependencies if possible, 
            # but standard xml.etree is safer.
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)
            
            # Namespace map
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            
            papers = []
            logger.info("Scanning arXiv for latest papers...")
            
            count = 0
            for entry in root.findall('atom:entry', ns):
                if count >= limit:
                    break
                
                title = entry.find('atom:title', ns).text.strip().replace('\n', ' ')
                link = entry.find('atom:id', ns).text.strip()
                summary = entry.find('atom:summary', ns).text.strip().replace('\n', ' ')[:200] + "..."
                
                papers.append(f"- Title: {title}\n  URL: {link}\n  Abstract: {summary}")
                logger.debug(f"Found Paper: {title[:50]}...")
                count += 1

            if not papers:
                return "No recent arXiv papers found."
            
            return "\n\n".join(papers)
            
        except Exception as e:
            logger.error(f"arXiv Error: {e}")
            return "Error fetching arXiv data."

class TavilyConnector:
    def search(self, query: str) -> str:
        logger.info("--- Tavily Connector Working ---")
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            logger.warning("Missing TAVILY_API_KEY. Skipping Tavily.")
            return ""

        try:
            url = "https://api.tavily.com/search"
            payload = {
                "api_key": api_key,
                "query": query,
                "search_depth": "basic",
                "include_answer": True,
                "max_results": 3
            }
            response = requests.post(url, json=payload)
            data = response.json()
            
            results = []
            # Check for direct answer
            if data.get("answer"):
                results.append(f"💡 Direct Answer: {data['answer']}")
            
            # Check for search results
            for result in data.get("results", []):
                title = result.get("title", "")
                url = result.get("url", "")
                content = result.get("content", "")[:200] + "..."
                results.append(f"- {title} ({url}): {content}")
                
            if not results:
                return "No Tavily results found."
                
            return "\n\n".join(results)
            
        except Exception as e:
            logger.error(f"Tavily Error: {e}")
            return "Error fetching Tavily data."

class ResearchManager(Agent):
    def __init__(self):
        self.hn_connector = HackerNewsConnector()
        self.news_connector = NewsAPIConnector()
        self.arxiv_connector = ArxivConnector()
        self.tavily_connector = TavilyConnector()
        super().__init__(
            name="ResearchManager",
            role="Chief Intelligence Officer",
            system_prompt="""You are the Chief Intelligence Officer (CIO) for a LinkedIn Influencer.
Your goal is to aggregate data from multiple sources (HackerNews, NewsAPI, arXiv, Tavily) and synthesize it into a comprehensive "Trend Brief".

Input: A raw topic or search query.
Output: A structured report containing:
1. THE CORE NEWS: What is actually happening? (Cite sources)
2. THE CONTEXT: Why does this matter now?
3. THE CONTROVERSY: What are people arguing about? (HackerNews comments/Tavily results)
4. THE ACADEMIC ANGLE: Is there new research? (arXiv)

Make it dense, factual, and high-signal. No fluff."""
        )
    
    def run(self, input_data: str) -> str:
        # Fetch real data from all sources
        hn_data = self.hn_connector.get_top_ai_stories()
        news_data = self.news_connector.get_tech_headlines()
        arxiv_data = self.arxiv_connector.get_latest_papers()
        
        # Use Tavily to verify/expand on the input topic or general trends
        tavily_data = self.tavily_connector.search(f"latest critical discussions in {input_data} technology")
        
        full_input = f"{input_data}\n\nREAL-TIME HACKERNEWS DATA:\n{hn_data}\n\nREAL-TIME NEWSAPI DATA:\n{news_data}\n\nLATEST ACADEMIC PAPERS (ARXIV):\n{arxiv_data}\n\nDEEP WEB SEARCH (TAVILY):\n{tavily_data}"
        return super().run(full_input)

# --- Variety Engine ---

VIBES = {
    "The Contrarian": {
        "strategist": "Persona: The Contrarian Tech Realist.\nGoal: Challenge a popular opinion about the trend.\nOutput:\n- Hook: A single, punchy sentence that challenges the status quo.\n- Angle: The core argument (why most people are wrong).\n- Target Audience: Tech leaders.\n- CTA: A question to provoke debate.",
        "ghostwriter": "Style: Sharp, confident, direct. No filler.\nStructure: Hook → The 'Ugly Truth' → Specific Evidence → Call to Debate.\nMax length: 15 lines. Use whitespace for impact.",
        "art_director": "Style: Brutalist Web Design, Glitch Art, Raw Concrete texture, High Contrast Black and White with Red accents, Typography-heavy.\nMood: Rebellious, Raw, Bold."
    },
    "The Visionary": {
        "strategist": "Persona: The Optimistic Futurist.\nGoal: Highlight long-term impact and human potential.\nOutput:\n- Hook: An inspiring statement about the future.\n- Angle: How this changes the world for the better.\n- Target Audience: Innovators.\n- CTA: Ask readers to imagine the possibilities.",
        "ghostwriter": "Style: Flowing, evocative, but concise. Use metaphors sparingly.\nStructure: The Hook → The Shift → The Human Impact → The Call to Imagine.\nMax length: 15 lines. No fluff.",
        "art_director": "Style: Ethereal Watercolor, Soft Pastel Colors, Dreamy, Studio Ghibli Landscape, Lush Nature meets Technology.\nMood: Hopeful, Peaceful, Expansive."
    },
    "The Educator": {
        "strategist": "Persona: The Senior Engineer/Teacher.\nGoal: Demystify a complex concept.\nOutput:\n- Hook: A clear 'Did you know?' or problem statement.\n- Angle: The technical truth behind the buzzword.\n- Target Audience: Engineers.\n- CTA: Ask what they want to learn next.",
        "ghostwriter": "Style: Clear, methodical, step-by-step. Use bullet points.\nStructure: Hook → The Misconception → The 3-Step Reality → Actionable Takeaway.\nMax length: 18 lines. Get direct.",
        "art_director": "Style: Technical Blueprint, Da Vinci Sketchbook, White lines on Blue background, Schematic, Detailed Line Art.\nMood: Professional, Analytical, Precise."
    },
    "The Analyst": {
        "strategist": "Persona: The Data-Driven Analyst.\nGoal: Focus on efficiency and ROI.\nOutput:\n- Hook: A stat or efficiency claim.\n- Angle: Why this makes business sense.\n- Target Audience: Decision makers.\n- CTA: Ask about their ROI.",
        "ghostwriter": "Style: Strategic, data-backed, punchy numbers.\nStructure: Hook → The Metric → The Strategic Trade-off → The Bottom Line.\nMax length: 15 lines. No jargon.",
        "art_director": "Style: Swiss International Style, Bauhaus, Geometric Shapes, Clean Grid, Primary Colors (Red, Blue, Yellow), Minimalist Data Viz.\nMood: Sophisticated, Corporate, Smart."
    },
    "The Narrator": {
        "strategist": "Persona: The Modern Epic Poet.\nGoal: Frame the trend as a sharp paradox.\nOutput:\n- Hook: A grand, rhythmic statement of duality.\n- Angle: The tension between progress and peril.\n- Target Audience: Thought Leaders.\n- CTA: A question about human agency.",
        "ghostwriter": "Style: Cinematic, rhythmic, stark. Use short lines and anaphora.\nStructure: The Duality → The Light → The Shadow → The Question.\nMax length: 12 lines. Make it feel like a modern verse, not a novel.",
        "art_director": "Style: Cinematic Film Still, 35mm Photography, Grainy, Edward Hopper style solitude, Dramatic Lighting, Realistic.\nMood: Timeless, Epic, Profound."
    },
}

# --- Specific Agents ---

# ... (Connectors remain the same) ...

class Strategist(Agent):
    def __init__(self):
        super().__init__(
            name="Strategist",
            role="Growth Hacker",
            system_prompt="You are a LinkedIn Growth Strategist." # Placeholder, set dynamically
        )
    
    def set_vibe(self, vibe_name: str, vibe_prompt: str):
        self.system_prompt = f"""You are a LinkedIn Growth Strategist.
Current Persona: {vibe_name}
{vibe_prompt}"""

class Ghostwriter(Agent):
    def __init__(self):
        self.memory = Memory()
        super().__init__(
            name="Ghostwriter",
            role="Content Writer",
            system_prompt="You are a viral LinkedIn Creator." # Placeholder
        )

    def set_vibe(self, vibe_name: str, vibe_prompt: str):
        self.system_prompt = f"""You are a viral LinkedIn Creator.
Current Persona: {vibe_name}
{vibe_prompt}
Rules:
1. NO 'In conclusion', 'In summary', 'Delve', 'Crucial', 'Landscape'.
2. Write like a human, not an AI.
3. Max 1500 chars."""

    def run(self, input_data: str) -> str:
        # Inject Memory into the prompt
        rules = self.memory.get_rules()
        memory_prompt = ""
        if rules:
            memory_prompt = "\n\n⚠️ CRITICAL FEEDBACK FROM PAST POSTS (DO NOT IGNORE):\n" + "\n".join(f"- {r}" for r in rules)
        
        full_input = input_data + memory_prompt
        return super().run(full_input)

class ArtDirector(Agent):
    def __init__(self):
        super().__init__(
            name="ArtDirector",
            role="Visual Creator",
            system_prompt="You are a Midjourney/DALL-E Prompt Engineer." # Placeholder
        )

    def set_vibe(self, vibe_name: str, vibe_prompt: str):
        self.system_prompt = f"""You are a Midjourney/DALL-E Prompt Engineer.
Current Style: {vibe_name}
{vibe_prompt}
STRICT OUTPUT FORMAT (NO CHAT):
Visual Format: [Format]
Prompt: [The Prompt]
Text Overlay: [The Text]"""

class Critic(Agent):
    def __init__(self):
        self.memory = Memory()
        super().__init__(
            name="Critic",
            role="Quality Control",
            system_prompt="""You are a harsh LinkedIn Critic. Review the draft post.
If it sounds like ChatGPT, say so.
Checklist: 
- Is the hook boring? 
- Are there too many adjectives? 
- Is the formatting scannable?

If you find a recurring mistake, output a line starting with "RULE:" to save it to memory.
Example: "RULE: Never use the word 'unleash'." """
        )

    def run(self, input_data: str) -> str:
        feedback = super().run(input_data)
        
        # Parse for new rules
        for line in feedback.split('\n'):
            if line.strip().startswith("RULE:"):
                new_rule = line.strip().replace("RULE:", "").strip()
                self.memory.add_rule(new_rule)
                
        return feedback

# --- Networker Agent ---

class Networker(Agent):
    def __init__(self):
        super().__init__(
            name="Networker",
            role="Comment Strategist",
            system_prompt="""You are a Networking Expert. Your goal is to help the user grow by commenting on OTHER people's posts.
Input: A trend or topic summary.
Output: A "Comment Pack" containing 3 distinct types of comments the user can copy-paste onto relevant posts by influencers.

Types:
1. The "Value Add": Agree with the premise but add a specific example or data point.
2. The "Contrarian": Respectfully disagree or point out a missing nuance.
3. The "Question": Ask a deep, thoughtful question that invites reply.

Format:
### 🤝 Comment Pack for [Topic]
**1. Value Add:** [Draft]
**2. Contrarian:** [Draft]
**3. Question:** [Draft]"""
        )

# --- Image Generator Agent ---

class ImageGenerator(Agent):
    def __init__(self):
        super().__init__(
            name="ImageGenerator",
            role="Visual Artist",
            system_prompt="You are an AI Artist. Generate a high-quality image based on the prompt."
        )

    def generate_image(self, prompt: str) -> Optional[bytes]:
        logger.info(f"--- {self.name} ({self.role}) Working ---")
        
        # Robust Cleaning
        clean_prompt = prompt
        if "Prompt:" in prompt:
            # Extract everything after "Prompt:"
            clean_prompt = prompt.split("Prompt:", 1)[1]
            # If there is a "Text Overlay:", stop there
            if "Text Overlay:" in clean_prompt:
                clean_prompt = clean_prompt.split("Text Overlay:", 1)[0]
        
        # Remove common prefixes/suffixes
        clean_prompt = clean_prompt.replace("Generate a high quality image:", "").strip()
        
        # Truncate to avoid URL length limits
        clean_prompt = clean_prompt[:800]
        
        logger.info(f"Generating image for: {clean_prompt[:50]}...")

        # Primary: Pollinations.ai with retry
        encoded_prompt = urllib.parse.quote(clean_prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1200&height=628&nologo=true"
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempt {attempt + 1}/{max_retries}: Pollinations.ai...")
                response = requests.get(url, timeout=60)  # 60s timeout
                response.raise_for_status()
                logger.info("✅ Image generated successfully (via Pollinations)!")
                return response.content
            except requests.exceptions.RequestException as e:
                logger.warning(f"Pollinations attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    import time
                    wait_time = (attempt + 1) * 5  # 5s, 10s, 15s
                    logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
        
        # Fallback: Try alternative model on Pollinations
        logger.info("Trying fallback: Pollinations Flux model...")
        try:
            fallback_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1200&height=628&model=flux&nologo=true"
            response = requests.get(fallback_url, timeout=90)
            response.raise_for_status()
            logger.info("✅ Image generated successfully (Pollinations Flux)!")
            return response.content
        except Exception as e:
            logger.error(f"All image generation attempts failed: {e}")
            return None

# --- LinkedIn Connector ---

class LinkedInConnector:
    def __init__(self):
        self.access_token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
        self.author_urn = os.environ.get("LINKEDIN_PERSON_URN") # e.g., "urn:li:person:12345"

    def register_upload(self):
        """Step 1: Register the image upload with LinkedIn"""
        # Use the new Images API which is compatible with /rest/posts
        url = "https://api.linkedin.com/rest/images?action=initializeUpload"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": "202411"
        }
        payload = {
            "initializeUploadRequest": {
                "owner": self.author_urn
            }
        }
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        
        # The response structure is different for rest/images
        upload_url = data['value']['uploadUrl']
        image_urn = data['value']['image']
        return upload_url, image_urn

    def upload_image(self, upload_url, image_data):
        """Step 2: Upload the binary image data"""
        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = requests.put(upload_url, headers=headers, data=image_data)
        response.raise_for_status()
        logger.info("✅ Image uploaded to LinkedIn server.")

    def post_content(self, text: str, image_data: bytes = None) -> Optional[str]:
        if not self.access_token or not self.author_urn:
            logger.warning("Missing LinkedIn Credentials. Skipping API call.")
            return None

        asset_urn = None
        if image_data:
            try:
                logger.info("Step 1/3: Registering image upload...")
                upload_url, asset = self.register_upload()
                logger.info("Step 2/3: Uploading image binary...")
                self.upload_image(upload_url, image_data)
                asset_urn = asset
                logger.info(f"Step 3/3: Creating post with asset")
            except Exception as e:
                logger.error(f"Image upload failed: {e}. Falling back to text-only.")

        url = "https://api.linkedin.com/rest/posts"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": "202411"
        }

        post_data = {
            "author": self.author_urn,
            "commentary": text,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": []
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False
        }

        if asset_urn:
            post_data["content"] = {
                "media": {
                    "id": asset_urn
                }
            }

        try:
            response = requests.post(url, headers=headers, json=post_data)
            response.raise_for_status()
            logger.info(f"✅ Successfully posted to LinkedIn! Status: {response.status_code}")
            
            # Extract URN
            post_urn = response.headers.get("x-restli-id")
            if not post_urn:
                # Try parsing body if header is missing
                try:
                    post_urn = response.json().get("id")
                except:
                    pass
            
            logger.info(f"🆔 New Post URN: {post_urn}")
            return post_urn

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to post to LinkedIn: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.debug(f"Error Details: {e.response.text}")
            return None

    def get_social_actions(self, urn: str):
        """Fetch real engagement stats (likes/comments) for a specific post URN"""
        if not self.access_token:
            return None
            
        # Extract the ID part if it's a full URN (urn:li:share:123 -> 123)
        # The socialActions API expects the full URN usually, but let's be safe.
        # Endpoint: https://api.linkedin.com/rest/socialActions/{urn}
        
        encoded_urn = urllib.parse.quote(urn)
        url = f"https://api.linkedin.com/rest/socialActions/{encoded_urn}"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": "202411"
        }
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 404:
                logger.warning(f"Stats not found for {urn}")
                return {"likes": 0, "comments": 0}
                
            response.raise_for_status()
            data = response.json()
            
            likes = data.get("likesSummary", {}).get("totalLikes", 0)
            comments = data.get("commentsSummary", {}).get("totalComments", 0)
            
            return {"likes": likes, "comments": comments}
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logger.warning(f"Permission Denied (403). Consider applying for Marketing Developer Platform.")
                # Hint moved to warning above
                return {"likes": 0, "comments": 0}
            else:
                logger.error(f"Failed to fetch stats: {e}")
                return {"likes": 0, "comments": 0}

        except Exception as e:
            logger.error(f"Failed to fetch stats: {e}")
            return {"likes": 0, "comments": 0}

# --- Orchestrator ---

class Orchestrator:
    def __init__(self):
        self.research_manager = ResearchManager()
        self.strategist = Strategist()
        self.ghostwriter = Ghostwriter()
        self.art_director = ArtDirector()
        self.critic = Critic()
        self.image_gen = ImageGenerator()
        self.linkedin = LinkedInConnector()
        self.memory = Memory() # Direct access to memory for orchestrator
        self.networker = Networker()

    def review_past_performance(self):
        logger.info("📊 Reviewing Past Performance...")
        logger.info("ℹ️ Healer disabled (Personal Profile Mode). Using manual feedback.")
        return

        # data = self.memory._load()
        # history = data.get("history", [])
        # 
        # updated_count = 0
        # for post in history:
        #     urn = post.get("urn")
        #     if urn:
        #         stats = self.linkedin.get_social_actions(urn)
        #         if stats:
        #             self.memory.update_post_stats(urn, stats["likes"], stats["comments"])
        #             updated_count += 1
        # 
        # if updated_count > 0:
        #     print(f"✅ Updated stats for {updated_count} past posts.")
        # else:
        #     print("ℹ️ No past posts to update or API unavailable.")

    def run_workflow(self, initial_topic: str = None):
        logger.info("🚀 Starting LinkedIn Growth Workflow")
        
        # Step 0: Review Past Performance (The Feedback Loop)
        self.review_past_performance()
        performance_insights = self.memory.get_performance_insights()
        
        # Step 0.1: Check for Manual Feedback (Plan B)
        manual_feedback = self.memory.get_manual_feedback()
        if manual_feedback:
            logger.info(f"📊 Manual Feedback Detected: {manual_feedback}")
            performance_insights = f"{performance_insights} | {manual_feedback}"
        
        logger.info(f"💡 Performance Insight: {performance_insights}")
        
        # 0.5. Select Vibe
        forced_vibe = os.getenv("FORCED_VIBE")
        if forced_vibe and forced_vibe in VIBES:
            vibe_name = forced_vibe
            logger.info(f"📌 Vibe FORCED: {vibe_name}")
        else:
            vibe_name = random.choice(list(VIBES.keys()))
            logger.info(f"🎲 Vibe Selected: {vibe_name}")
            
        vibe_config = VIBES[vibe_name]
        
        # Apply Vibe to Agents
        # Append performance insights to Strategist's prompt
        strategist_prompt = f"{vibe_config['strategist']}\n\nDATA FEEDBACK: {performance_insights}"
        self.strategist.set_vibe(vibe_name, strategist_prompt)
        
        self.ghostwriter.set_vibe(vibe_name, vibe_config["ghostwriter"])
        self.art_director.set_vibe(vibe_name, vibe_config["art_director"])
        
        # Step 1: Research
        if initial_topic:
            logger.info(f"Topic provided by user: {initial_topic}")
            trend_data = f"User Topic: {initial_topic}"
        else:
            # Add randomness to prevent duplicate posts during testing
            topics = [
                "The rise of Multi-Agent Systems",
                "Why Chatbots are dead",
                "The future of coding is Agentic",
                "LLMs as Operating Systems",
                "Prompt Engineering is replaced by Flow Engineering"
            ]
            selected_topic = random.choice(topics)
            trend_data = self.research_manager.run(f"Find current hot topics in Agentic AI. Selected: {selected_topic}")
        
        # Abort if research failed (API Error)
        if not trend_data:
            logger.error("Workflow Aborted: Research failed (likely quota exceeded).")
            return
        
        # Step 1.5: Generate Comment Pack (The Networker) - Non-critical, continue if fails
        comment_pack = self.networker.run(trend_data)
        if comment_pack:
            logger.info(f"Comment Pack generated:\n{comment_pack}")
            self.memory.save_comment_pack(comment_pack)
        else:
            logger.warning("Networker failed (non-critical). Continuing.")
        
        # Step 2: Strategy
        strategy = self.strategist.run(trend_data)
        
        # Abort if strategy failed
        if not strategy:
            logger.error("Workflow Aborted: Strategy generation failed.")
            return
        
        # Step 3: Content Creation
        draft_text = self.ghostwriter.run(strategy)
        visual_concept = self.art_director.run(strategy)

        if not draft_text or not visual_concept:
            logger.error("Workflow Aborted: Content generation failed.")
            return
        
        # Step 4: Image Generation
        # Extract prompt from visual_concept (simplified for now, just use the whole output)
        image_prompt = f"Generate a high quality image: {visual_concept}"
        image_data = self.image_gen.generate_image(image_prompt)
        
        # Step 5: Review
        full_package = f"{draft_text}\n\n(Visual Concept: {visual_concept})"
        feedback = self.critic.run(full_package)
        
        logger.info("✅ Workflow Complete. Preparing to Post...")
        
        # Step 6: Publish
        post_urn = self.linkedin.post_content(draft_text, image_data)
        
        # Step 7: Save to Memory
        if post_urn:
            # Extract topic from trend_data (simplified)
            topic_summary = initial_topic if initial_topic else selected_topic
            self.memory.add_post_history(topic_summary, vibe_name, post_urn)

if __name__ == "__main__":
    exit_code = 0
    
    try:
        logger.info("🚀 Starting LinkedIn Growth Workflow")
        
        # Initialize orchestrator
        orch = Orchestrator()
        
        # Archive old posts to keep memory.json manageable
        archive_days = CONFIG.get("memory", {}).get("archive_days", 90)
        archived = orch.memory.archive_old_posts(days=archive_days)
        if archived > 0:
            logger.info(f"📦 Archived {archived} posts older than {archive_days} days")
        
        # Check token expiry warning
        warning = orch.memory.check_token_expiry_warning()
        if warning:
            logger.warning(warning)
        
        # Run the main workflow
        orch.run_workflow()
        
        logger.info("✅ Script completed successfully.")
        
    except KeyboardInterrupt:
        logger.info("Workflow interrupted by user.")
        exit_code = 0
        
    except Exception as e:
        logger.exception(f"❌ Script failed with error: {e}")
        exit_code = 1  # Signal failure to GitHub Actions
    
    exit(exit_code)
