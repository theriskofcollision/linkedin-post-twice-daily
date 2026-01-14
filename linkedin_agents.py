import os
import json
import random
import requests
import urllib.parse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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
        with self.lock:
            data = self._load()
            if rule not in data["rules"]:
                data["rules"].append(rule)
                self._save(data)
                logger.info(f"🧠 Memory Updated: Added rule '{rule}'")

    def add_post_history(self, topic: str, vibe: str, urn: str):
        with self.lock:
            data = self._load()
            if "history" not in data:
                data["history"] = []
            
            entry = {
                "date": datetime.now().isoformat(),
                "topic": topic,
                "vibe": vibe,
                "urn": urn,
                "stats": {"likes": 0, "comments": 0}
            }
            data["history"].append(entry)
            self._save(data)
            logger.info(f"📝 Memory Updated: Added post history for {topic}")

    def update_post_stats(self, urn: str, likes: int, comments: int):
        with self.lock:
            data = self._load()
            for post in data.get("history", []):
                if post.get("urn") == urn:
                    post["stats"] = {"likes": likes, "comments": comments}
                    break
            self._save(data)
            logger.info(f"🧠 Stats Updated for {urn}: {likes} likes, {comments} comments")

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
    """Connector for fetching AI-related stories from Hacker News."""

    def get_top_ai_stories(self, limit: Optional[int] = None) -> str:
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
    """Connector for fetching technology headlines from NewsAPI."""

    def get_tech_headlines(self, limit: int = 5) -> str:
        logger.info("--- NewsAPI Connector Working ---")
        api_key = os.environ.get("NEWS_API_KEY")
        if not api_key:
            logger.warning("Missing NEWS_API_KEY. Skipping NewsAPI.")
            return ""

        try:
            # Fetch top tech headlines (API key in header for security)
            url = "https://newsapi.org/v2/top-headlines?category=technology&language=en&pageSize=10"
            headers = {"X-Api-Key": api_key}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
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
    """Connector for fetching latest AI/ML papers from arXiv."""

    def get_latest_papers(self, limit: int = 3) -> str:
        logger.info("--- arXiv Connector Working ---")
        try:
            # Search for AI/LLM papers
            # cat:cs.AI = Computer Science AI
            # sortBy=submittedDate&sortOrder=descending
            url = "http://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.CL&start=0&max_results=5&sortBy=submittedDate&sortOrder=descending"
            response = requests.get(url)
            
            # Use defusedxml to prevent XML entity attacks (billion laughs, XXE)
            import defusedxml.ElementTree as ET
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
    """Connector for deep web search using Tavily API."""

    def search(self, query: str, include_images: bool = False) -> Dict[str, Any]:
        logger.info(f"--- Tavily Connector Working (Images={include_images}) ---")
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            logger.warning("Missing TAVILY_API_KEY. Skipping Tavily.")
            return {"text": "", "images": []}

        try:
            url = "https://api.tavily.com/search"
            payload = {
                "api_key": api_key,
                "query": query,
                "search_depth": "basic",
                "include_answer": True,
                "include_images": include_images,
                "max_results": 3
            }
            response = requests.post(url, json=payload)
            data = response.json()
            
            results = []
            if data.get("answer"):
                results.append(f"💡 Direct Answer: {data['answer']}")
            
            for result in data.get("results", []):
                title = result.get("title", "")
                url = result.get("url", "")
                content = result.get("content", "")[:200] + "..."
                results.append(f"- {title} ({url}): {content}")
            
            images = data.get("images", [])
            return {
                "text": "\n\n".join(results) if results else "No Tavily results found.",
                "images": images
            }
            
        except Exception as e:
            logger.error(f"Tavily Error: {e}")
            return {"text": "Error fetching Tavily data.", "images": []}

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
Your goal is to aggregate data and conceptualize unique content angles.

Input: A raw topic or search query.
Output: A structured report containing:
1. THE CORE NEWS: What is actually happening? (Cite sources)
2. THE CONTEXT: Why does this matter now?
3. CONCEPTUAL ANGLES: Provide 5 unique 'hooks' or perspectives on this news.
   - Example 1: Technical (The architecture)
   - Example 2: Story (The human impact)
   - Example 3: Controversy (The debate)
   - Example 4: Future (The prediction)
   - Example 5: Minimalist (The core truth)

Make it dense, factual, and high-signal."""
        )
    
    def run(self, input_data: str) -> Optional[str]:
        """Fetch research data from all sources in parallel and generate report."""
        # Define data fetching tasks
        def fetch_hackernews() -> tuple:
            return ("hackernews", self.hn_connector.get_top_ai_stories())

        def fetch_newsapi() -> tuple:
            return ("newsapi", self.news_connector.get_tech_headlines())

        def fetch_arxiv() -> tuple:
            return ("arxiv", self.arxiv_connector.get_latest_papers())

        def fetch_tavily() -> tuple:
            resp = self.tavily_connector.search(f"latest critical discussions in {input_data} technology")
            return ("tavily", resp["text"])

        # Execute all fetches in parallel
        results = {}
        logger.info("📡 Fetching research data from all sources in parallel...")

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(fetch_hackernews),
                executor.submit(fetch_newsapi),
                executor.submit(fetch_arxiv),
                executor.submit(fetch_tavily),
            ]

            for future in as_completed(futures):
                try:
                    source, data = future.result(timeout=30)
                    results[source] = data
                    logger.debug(f"✓ {source} data fetched")
                except Exception as e:
                    logger.warning(f"Failed to fetch from a source: {e}")

        # Extract results with fallbacks
        hn_data = results.get("hackernews", "HackerNews data unavailable.")
        news_data = results.get("newsapi", "NewsAPI data unavailable.")
        arxiv_data = results.get("arxiv", "arXiv data unavailable.")
        tavily_data = results.get("tavily", "Tavily data unavailable.")

        full_input = (
            f"{input_data}\n\n"
            f"REAL-TIME HACKERNEWS DATA:\n{hn_data}\n\n"
            f"REAL-TIME NEWSAPI DATA:\n{news_data}\n\n"
            f"LATEST ACADEMIC PAPERS (ARXIV):\n{arxiv_data}\n\n"
            f"DEEP WEB SEARCH (TAVILY):\n{tavily_data}"
        )
        return super().run(full_input)

# --- Style & Variety Engine ---

STYLE_MATRIX = {
    "mediums": [
        # Photography styles (professional, editorial)
        "Editorial magazine photography", "Documentary photography", "Portrait photography with shallow depth of field",
        "Street photography candid shot", "Product photography on white background", "Architectural photography",
        "Lifestyle photography natural moment", "Corporate headshot style", "Photojournalism style",
        # Clean design styles
        "Minimalist flat design illustration", "Isometric technical illustration", "Infographic style clean vectors",
        "Whiteboard sketch hand-drawn", "Simple line art illustration", "Geometric abstract shapes",
        # Artistic but professional
        "Watercolor soft illustration", "Charcoal sketch on paper", "Vintage film photography 35mm",
        "Black and white fine art photography", "Double exposure artistic portrait", "Aerial drone photography",
        # Unique but tasteful
        "Paper cut-out layered art", "Woodblock print Japanese style", "Risograph print texture",
        "Vintage poster 1960s style", "Blueprint technical drawing", "Botanical scientific illustration"
    ],
    "lighting": [
        # Natural lighting (most professional)
        "Soft natural window light", "Golden hour warm sunlight", "Overcast diffused daylight",
        "Morning blue hour soft light", "Dappled sunlight through trees", "Clean studio softbox lighting",
        # Professional studio
        "High-key bright and airy", "Low-key dramatic shadows", "Rembrandt portrait lighting",
        "Backlit silhouette rim light", "Soft fill light minimal shadows", "Side lighting texture emphasis",
        # Atmospheric
        "Foggy atmospheric haze", "Warm tungsten indoor glow", "Cool shade open shadow"
    ],
    "palettes": [
        # Professional and clean
        "Clean white with navy accents", "Warm neutrals (beige, cream, tan)", "Cool greys with teal accent",
        "Black and white high contrast", "Muted earth tones (sage, terracotta, sand)",
        # Modern professional
        "Soft blue and white minimal", "Warm wood tones and white", "Charcoal grey with gold accent",
        "Forest green and cream", "Deep navy and warm brass",
        # Subtle and sophisticated
        "Dusty rose and grey", "Ocean blues gradient", "Sunset warm oranges and coral",
        "Vintage faded film tones", "Coffee browns and cream"
    ]
}

POST_FORMATS = [
    "The Paradox: Start with two conflicting truths.",
    "The 3-Step Guide: Direct, actionable value.",
    "The Manifesto: A bold declaration of beliefs.",
    "The Day-in-a-life: A narrative story of a specific moment.",
    "The Open Letter: Addressing a specific group or concept.",
    "The Satirical Rant: Using humor to highlight a problem.",
    "The Zero-to-One Story: How something was built from nothing.",
    "The Q&A: Addressing a common but misunderstood question.",
    "The Contrarian Take: Why the popular opinion is wrong.",
    "The Research Deep Dive: Synthesizing complex data into insight.",
    "The Tool Review: A sharp look at a specific piece of tech.",
    "The Productivity Audit: How to optimize a specific workflow.",
    "The Future Timeline: Steps to a specific future state.",
    "The Philosophical Prompt: Asking a question that lingers.",
    "The Comparison: Post-A vs Post-B framework.",
    "The 'Unpopular Opinion': Highlighting a hidden truth.",
    "The Technical Teardown: How it actually works under the hood."
]

VIBES = {
    "The Contrarian": {
        "strategist": "Persona: The Contrarian Tech Realist.\nGoal: I'm challenging a popular opinion I see about this trend.",
        "ghostwriter": "Style: Sharp, confident, direct. I'm sharing my counter-intuitive take. No lecturing.",
        "is_organic": False
    },
    "The Visionary": {
        "strategist": "Persona: The Optimistic Futurist.\nGoal: I'm exploring the long-term impact and human potential I see here.",
        "ghostwriter": "Style: Flowing, evocative, but concise. My personal vision for the future.",
        "is_organic": False
    },
    "The Educator": {
        "strategist": "Persona: The Senior Engineer/Teacher.\nGoal: I'm demystifying a complex concept I recently simplified.",
        "ghostwriter": "Style: Clear, methodical, narrative steps. 'I found that...' or 'I built it this way...'. No listicles.",
        "is_organic": False
    },
    "The Analyst": {
        "strategist": "Persona: The Data-Driven Analyst.\nGoal: My focus is on the efficiency and ROI I've observed.",
        "ghostwriter": "Style: Strategic, punchy numbers from my perspective. 'What I've noticed in the data...'.",
        "is_organic": False
    },
    "The Narrator": {
        "strategist": "Persona: The Modern Epic Poet.\nGoal: I'm framing this trend as a sharp paradox I've noticed.",
        "ghostwriter": "Style: Cinematic, rhythmic, stark. My observations on the duality of tech.",
        "is_organic": False
    },
    "The Storyteller": {
        "strategist": "Persona: The Narrative Architect.\nGoal: I'm telling a human-centric story about the technology I'm seeing.",
        "ghostwriter": "Style: Personal, warm, descriptive. I'm focusing on a specific scenario I encountered. No lecturing.",
        "is_organic": True
    },
    "The Provocateur": {
        "strategist": "Persona: The Digital Firebrand.\nGoal: I'm sparking a debate by taking a bold stance I've been considering.",
        "ghostwriter": "Style: Bold, aggressive, questioning. My strong personal opinion. Use short sentences.",
        "is_organic": False
    },
    "The Minimalist": {
        "strategist": "Persona: The Zen Architect.\nGoal: I'm extracting the core essence of this topic as I understand it.",
        "ghostwriter": "Style: Ultra-concise, profound. My distillation of the truth. Max 5 lines.",
        "is_organic": False
    },
    "The Oracle": {
        "strategist": "Persona: The Predictive Sage.\nGoal: I'm projecting my predictions for 2035 based on what I see today.",
        "ghostwriter": "Style: Authority based on my research. 'What I see coming...' or 'My projections...'.",
        "is_organic": False
    },
    "The Pragmatist": {
        "strategist": "Persona: The Execution Specialist.\nGoal: I'm focusing on the implementation steps 'I've' used to get results.",
        "ghostwriter": "Style: No-nonsense, tactical. 'I do this by...' or 'My workflow is...'. Not a lecture.",
        "is_organic": True
    },
    "The Anthropologist": {
        "strategist": "Persona: The Tech Sociologist.\nGoal: I'm observing how tech changes the human behavior I see around me.",
        "ghostwriter": "Style: Observational, curious. 'I've noticed...' or 'My observations on societies...'.",
        "is_organic": True
    },
    "The Debunker": {
        "strategist": "Persona: The Hype-Slayer.\nGoal: I'm dismantling a trending claim that I've found to be flawed.",
        "ghostwriter": "Style: Skeptical, logic-based. 'I looked into X and found Y...'. My own investigative path.",
        "is_organic": False
    },
    "The Curator": {
        "strategist": "Persona: The Synthesis Artist.\nGoal: I'm connecting 3 unrelated items into a single insight I've developed.",
        "ghostwriter": "Style: Connection-focused. 'I've been connecting the dots between...'.",
        "is_organic": True
    },
    "The Architect": {
        "strategist": "Persona: The System Designer.\nGoal: I'm focusing on the infrastructure and 'plumbing' I've analyzed.",
        "ghostwriter": "Style: Engineering-focused. 'My analysis of the plumbing...' or 'How I view the stack...'.",
        "is_organic": False
    },
    "The Rebel": {
        "strategist": "Persona: The Open-Source Advocate.\nGoal: I'm championing the anti-corporate tech path I believe in.",
        "ghostwriter": "Style: Passionate, raw. 'Why I choose open-source...' or 'My fight against gatekeeping...'.",
        "is_organic": True
    },
    "The Zen Coder": {
        "strategist": "Persona: The Deep Work Master.\nGoal: I'm focusing on the mental state I cultivate while building.",
        "ghostwriter": "Style: Calm, rhythmic. 'My state of mind is...' or 'How I find focus...'.",
        "is_organic": True
    },
    "The Data Detective": {
        "strategist": "Persona: The Pattern Matcher.\nGoal: I'm finding a hidden truth in the datasets I've been studying.",
        "ghostwriter": "Style: Investigative. 'I dug into the data and saw...' or 'My meticulous findings...'.",
        "is_organic": False
    },
    "The Satirist": {
        "strategist": "Persona: The Cynical Insider.\nGoal: I'm using irony to highlight the absurdity I see in the current hype.",
        "ghostwriter": "Style: Ironical, bitingly honest. 'I can't help but laugh at...' or 'My cynical take on...'.",
        "is_organic": False
    },
    "The Archivist": {
        "strategist": "Persona: The Tech Historian.\nGoal: I'm comparing today's shift to historical patterns I've studied.",
        "ghostwriter": "Style: Nostalgic, comparative. 'I'm reminded of...' or 'My historical analysis shows...'.",
        "is_organic": True
    },
    "The Fresh Eye": {
        "strategist": "Persona: The Profound Beginner.\nGoal: I'm asking simple questions about the things I'm just starting to see.",
        "ghostwriter": "Style: Questioning, clear. 'I'm curious about...' or 'What I'm learning is...'.",
        "is_organic": True
    },
    "The Maxer": {
        "strategist": "Persona: The Efficiency Maximalist.\nGoal: I'm optimizing every second of the workflow I use.",
        "ghostwriter": "Style: High-energy. 'How I max my output...' or 'My speed-focused setup...'.",
        "is_organic": False
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

    def set_vibe(self, vibe_name: str, vibe_prompt: str, post_format: str = ""):
        self.system_prompt = f"""Write a LinkedIn post. Output ONLY the post text. Nothing else.

Style: {vibe_name}
{vibe_prompt}

Inspiration: {post_format}

THE GOLDEN RULE: Write like you're texting a smart friend at 11pm. Casual. Real. No performance.

ABSOLUTE BANS (instant fail if you use these):
- NO percentages or stats ("35% faster", "10x improvement")
- NO buzzwords: synergy, leverage, ecosystem, scalable, robust, streamline, optimize, paradigm, innovative, cutting-edge, game-changer, revolutionize, empower, unlock, harness
- NO corporate phrases: "at the end of the day", "moving forward", "in terms of", "when it comes to", "the reality is", "the truth is"
- NO rhetorical questions to the audience ("What do you think?", "Have you tried this?", "What's your experience?")
- NO calls-to-action ("Follow for more", "Like if you agree", "Comment below")
- NO hashtags in the middle of text
- NO "I've been thinking about X lately"
- NO humble brags disguised as insights
- NO lecturing or teaching tone
- NO bullet points, numbered lists, or structured formats
- NO em-dashes for dramatic effect

VOICE:
- Talk about what YOU did, saw, or realized. Be specific and personal.
- Use contractions: "I'm", "don't", "wasn't", "it's"
- Use casual transitions: "honestly", "tbh", "anyway", "so yeah"
- Incomplete sentences are fine. Fragments too.
- Sound like you're sharing a quick thought, not delivering a TED talk

GOOD EXAMPLE:
"Spent 3 hours yesterday trying to get an LLM to stop hallucinating product names. Finally just gave it a JSON list to pick from. Sometimes the dumb solution wins."

BAD EXAMPLE:
"LLMs are revolutionizing how we build software. By leveraging semantic memory, teams can achieve 35% faster development cycles. What's your experience with AI-powered development?"

Max 300 chars. Short and punchy. Just the post, nothing else."""

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
            system_prompt="You are a Midjourney/DALL-E Prompt Engineer."
        )
        self.current_medium = "Photography"
        self.current_lighting = "Natural"
        self.current_palette = "Vibrant"

    def set_vibe(self, vibe_name: str, vibe_prompt: str):
        # Randomize style matrix
        self.current_medium = random.choice(STYLE_MATRIX["mediums"])
        self.current_lighting = random.choice(STYLE_MATRIX["lighting"])
        self.current_palette = random.choice(STYLE_MATRIX["palettes"])

        self.system_prompt = f"""You are a visual director creating LinkedIn-appropriate imagery.

Assigned Style:
- Medium: {self.current_medium}
- Lighting: {self.current_lighting}
- Palette: {self.current_palette}

CRITICAL RULES:
1. Create professional, editorial-quality visuals suitable for LinkedIn
2. Focus on REAL subjects: people working, objects, spaces, nature - NOT abstract sci-fi
3. Incorporate the assigned medium, lighting, and palette

ABSOLUTELY BANNED (will look like generic AI art):
- Purple/pink/cyan neon colors
- Cyberpunk aesthetics
- Glowing eyes or circuits
- Robots shaking hands with humans
- Futuristic cityscapes
- Holographic interfaces
- Matrix-style code rain
- Any "tech bro" clichés

AIM FOR: Something that could be a stock photo, magazine editorial, or clean illustration.
Think: Apple marketing, NYT editorial, Unsplash photography - clean, professional, human.

OUTPUT FORMAT (nothing else):
Visual Format: [Format]
Prompt: [The detailed prompt - include "professional, editorial quality, clean composition"]
Text Overlay: [Optional - only if truly needed]"""

    def generate_image(self, prompt: str) -> Optional[bytes]:
        logger.info(f"--- {self.name} ({self.role}) Working ---")
        
        # Robust Cleaning
        clean_prompt = prompt
        if "Prompt:" in prompt:
            clean_prompt = prompt.split("Prompt:", 1)[1]
            if "Text Overlay:" in clean_prompt:
                clean_prompt = clean_prompt.split("Text Overlay:", 1)[0]
        
        clean_prompt = clean_prompt.replace("Generate image:", "").strip()
        clean_prompt = clean_prompt[:800]
        
        logger.info(f"Generating image with style: {self.current_medium}...")

        encoded_prompt = urllib.parse.quote(clean_prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1200&height=628&nologo=true"
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempt {attempt + 1}/{max_retries}: Pollinations.ai...")
                response = requests.get(url, timeout=60)
                response.raise_for_status()
                return response.content
            except Exception as e:
                logger.warning(f"Pollinations attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep((attempt + 1) * 5)
        
        return None

class Critic(Agent):
    def __init__(self):
        self.memory = Memory()
        super().__init__(
            name="Critic",
            role="Quality Control",
            system_prompt="""You are a brutal LinkedIn authenticity detector. Your job: catch AI-sounding posts.

INSTANT REJECT if you find ANY of these:
1. STATS/PERCENTAGES: "35% faster", "10x", "reduced by 40%" - real humans don't talk like pitch decks
2. BUZZWORDS: leverage, ecosystem, scalable, robust, streamline, optimize, paradigm, innovative, cutting-edge, game-changer, revolutionize, empower, unlock, harness, synergy
3. CORPORATE SPEAK: "at the end of the day", "moving forward", "in terms of", "the reality is"
4. FAKE QUESTIONS: "What do you think?", "Have you tried?", "What's your take?" - engagement bait
5. LISTICLES: Any numbered lists, bullet points, or structured formats
6. LECTURE TONE: "You should", "You need to", "Here's why" - preachy teaching mode
7. AI PATTERNS: "Not just X, but Y", "The key is", "Here's the thing", "Let me explain"
8. HUMBLE BRAGS: Disguised boasting as insights
9. GENERIC OPENERS: "I've been thinking about", "Let me share", "Here's my take"

PASS ONLY IF:
- Sounds like a real person texting a friend
- Has specific personal details (what they actually did/saw)
- Uses contractions and casual language
- Short, punchy, no performance

If you find a pattern to remember, output: "RULE: [the pattern to avoid]"

Rate: PASS or REJECT with one-line reason."""
        )

    def run(self, input_data: str) -> str:
        feedback = super().run(input_data)
        
        # Handle case where API call failed
        if not feedback:
            return None
        
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


class OrganicImageSearcher:
    """Finds real photography via Tavily."""
    def __init__(self):
        self.tavily = TavilyConnector()

    def get_organic_image(self, topic: str) -> Optional[bytes]:
        logger.info(f"--- Organic Image Searcher Working for: {topic} ---")
        try:
            # Search specifically for high quality photography
            query = f"high quality photography {topic} unsplash pexels"
            resp = self.tavily.search(query, include_images=True)
            
            image_urls = resp.get("images", [])
            if not image_urls:
                logger.warning("No organic images found.")
                return None
            
            # Pick a random one from top 3
            lucky_url = random.choice(image_urls[:3])
            logger.info(f"Found organic image: {lucky_url}")
            
            img_resp = requests.get(lucky_url, timeout=30)
            img_resp.raise_for_status()
            return img_resp.content
            
        except Exception as e:
            logger.error(f"Organic search failed: {e}")
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
                except (json.JSONDecodeError, ValueError):
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
            response = requests.get(url, headers=headers, timeout=30)
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
        self.organic_searcher = OrganicImageSearcher()
        self.critic = Critic()
        self.image_gen = ArtDirector() # Using ArtDirector as the image gen manager
        self.linkedin = LinkedInConnector()
        self.memory = Memory() # Direct access to memory for orchestrator
        self.networker = Networker()
        self.config = CONFIG # Global config from top of file

    def review_past_performance(self) -> None:
        """Review past post performance (disabled for personal profile mode)."""
        logger.info("📊 Reviewing Past Performance...")
        logger.info("ℹ️ Healer disabled (Personal Profile Mode). Using manual feedback.")

    def _select_vibe_and_format(self) -> tuple:
        """Select vibe and post format for this run.

        Returns:
            Tuple of (vibe_name, vibe_config, post_format, variety_cfg)
        """
        variety_cfg = self.config.get("variety", {})

        # Select Vibe
        forced_vibe = os.getenv("FORCED_VIBE")
        if forced_vibe and forced_vibe in VIBES:
            vibe_name = forced_vibe
        else:
            enabled = variety_cfg.get("enabled_personas", "all")
            if enabled == "all":
                vibe_name = random.choice(list(VIBES.keys()))
            else:
                vibe_name = random.choice(enabled)

        logger.info(f"🎲 Vibe Selected: {vibe_name}")
        vibe_config = VIBES[vibe_name]

        # Select Format
        post_format = random.choice(POST_FORMATS)
        logger.info(f"📋 Format Selected: {post_format.split(':')[0]}")

        return vibe_name, vibe_config, post_format, variety_cfg

    def _configure_agents(self, vibe_name: str, vibe_config: Dict[str, Any],
                          post_format: str, performance_insights: str) -> None:
        """Apply vibe configuration to all agents."""
        strategist_prompt = (
            f"{vibe_config['strategist']}\n\n"
            f"DATA FEEDBACK: {performance_insights}\n\n"
            f"Constraint: Focus on the perspective of {vibe_name}."
        )
        self.strategist.set_vibe(vibe_name, strategist_prompt)
        self.ghostwriter.set_vibe(vibe_name, vibe_config["ghostwriter"], post_format=post_format)
        self.art_director.set_vibe(vibe_name, "")

    def _research_phase(self, initial_topic: Optional[str]) -> tuple:
        """Execute research phase.

        Returns:
            Tuple of (topic_query, trend_brief) or (None, None) on failure
        """
        if initial_topic:
            topic_query = initial_topic
        else:
            raw_topics = self.config.get("topics", ["AI agents"])
            topic_query = random.choice(raw_topics)

        logger.info(f"🔍 Researching & Conceptualizing: {topic_query}")
        trend_brief = self.research_manager.run(topic_query)

        if not trend_brief:
            logger.error("Workflow Aborted: Research failed.")
            return None, None

        # Generate comment pack for networking
        comment_pack = self.networker.run(trend_brief)
        if comment_pack:
            self.memory.save_comment_pack(comment_pack)

        return topic_query, trend_brief

    def _strategy_phase(self, trend_brief: str) -> Optional[str]:
        """Execute strategy phase.

        Returns:
            Strategy string or None on failure
        """
        logger.info("🧠 Strategizing...")
        strategy = self.strategist.run(trend_brief)
        if not strategy:
            logger.error("Workflow Aborted: Strategy failed.")
        return strategy

    def _content_phase(self, strategy: str) -> tuple:
        """Execute content creation phase.

        Returns:
            Tuple of (draft_text, visual_concept) or (None, None) on failure
        """
        logger.info("✍️ Drafting Post...")
        draft_text = self.ghostwriter.run(strategy)

        logger.info("🎨 Designing Visuals...")
        visual_concept = self.art_director.run(strategy)

        if not draft_text:
            logger.error("Workflow Aborted: Ghostwriting failed.")
            return None, None

        return draft_text, visual_concept

    def _visual_phase(self, vibe_config: Dict[str, Any], variety_cfg: Dict[str, Any],
                      topic_query: str, visual_concept: str) -> Optional[bytes]:
        """Source or generate visual content.

        Returns:
            Image data bytes or None
        """
        image_data = None
        use_organic = False
        image_pref = variety_cfg.get("image_mode_preference", "hybrid")

        if vibe_config.get("is_organic") and self.config.get("features", {}).get("enable_organic_visuals"):
            if image_pref == "always_real":
                use_organic = True
            elif image_pref == "hybrid":
                if random.random() < variety_cfg.get("organic_vibe_threshold", 0.5):
                    use_organic = True

        if use_organic:
            logger.info("🌿 Sourcing Organic Visual...")
            image_data = self.organic_searcher.get_organic_image(topic_query)

        if not image_data and self.config.get("features", {}).get("enable_image_generation"):
            logger.info("🤖 Generating AI Visual...")
            image_prompt = f"Generate image: {visual_concept}"
            image_data = self.art_director.generate_image(image_prompt)

        return image_data

    def _publish_phase(self, draft_text: str, visual_concept: str,
                       image_data: Optional[bytes], topic_query: str,
                       vibe_name: str) -> Optional[str]:
        """Review and publish content.

        Returns:
            Post URN or None
        """
        # Review
        full_package = f"{draft_text}\n\n(Visual: {visual_concept})"
        self.critic.run(full_package)

        # Publish
        logger.info("✅ Preparing to Post...")
        post_urn = self.linkedin.post_content(draft_text, image_data)

        # Save to Memory
        if post_urn:
            self.memory.add_post_history(topic_query, vibe_name, post_urn)

        return post_urn

    def run_workflow(self, initial_topic: str = None) -> Optional[str]:
        """Execute the full LinkedIn content workflow.

        Args:
            initial_topic: Optional topic to use instead of random selection

        Returns:
            Post URN if successful, None otherwise
        """
        logger.info("🚀 Starting LinkedIn Growth Workflow (V2: Variety Engine)")

        # Step 0: Review past performance
        self.review_past_performance()
        performance_insights = self.memory.get_performance_insights()

        # Step 1: Select vibe and format
        vibe_name, vibe_config, post_format, variety_cfg = self._select_vibe_and_format()

        # Step 2: Configure agents with selected vibe
        self._configure_agents(vibe_name, vibe_config, post_format, performance_insights)

        # Step 3: Research phase
        topic_query, trend_brief = self._research_phase(initial_topic)
        if not trend_brief:
            return None

        # Step 4: Strategy phase
        strategy = self._strategy_phase(trend_brief)
        if not strategy:
            return None

        # Step 5: Content creation phase
        draft_text, visual_concept = self._content_phase(strategy)
        if not draft_text:
            return None

        # Step 6: Visual sourcing phase
        image_data = self._visual_phase(vibe_config, variety_cfg, topic_query, visual_concept)

        # Step 7: Publish phase
        return self._publish_phase(draft_text, visual_concept, image_data, topic_query, vibe_name)

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
