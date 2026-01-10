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
    
    def run(self, input_data: str) -> str:
        # Fetch real data from all sources
        hn_data = self.hn_connector.get_top_ai_stories()
        news_data = self.news_connector.get_tech_headlines()
        arxiv_data = self.arxiv_connector.get_latest_papers()
        
        # Use Tavily to verify/expand on the input topic or general trends
        tavily_resp = self.tavily_connector.search(f"latest critical discussions in {input_data} technology")
        tavily_data = tavily_resp["text"]
        
        full_input = f"{input_data}\n\nREAL-TIME HACKERNEWS DATA:\n{hn_data}\n\nREAL-TIME NEWSAPI DATA:\n{news_data}\n\nLATEST ACADEMIC PAPERS (ARXIV):\n{arxiv_data}\n\nDEEP WEB SEARCH (TAVILY):\n{tavily_data}"
        return super().run(full_input)

# --- Style & Variety Engine ---

STYLE_MATRIX = {
    "mediums": [
        "Cyberpunk Digital Art", "Vaporwave Aesthetic", "Minimalist Bauhaus Print", "Claymation / Stop-Motion",
        "Double Exposure Photography", "Ukiyo-e Woodblock Print", "Vintage Polaroid", "19th Century Lithograph",
        "Technical Blueprint / Schematic", "Macro Macro Photography", "8-bit Pixel Art", "Oil Painting on Canvas",
        "Street Art / Graffiti", "Architectural Render", "Pencil Sketch", "Watercolor Illustration",
        "Glassmorphism UI", "Brutalist Graphic Design", "Surrealist Collage", "Neon-Noir Photography",
        "Low Poly 3D Model", "Infographic Paper Cutout", "Mid-Century Modern Poster", "Cinematic Film Still",
        "Anatomical Drawing", "Satellite Imagery", "Microscopic View", "Retro-Futurism Illustration",
        "Cybernetic Organism Art", "Pop Art", "Impressionist Landscape", "Dadaist Photomontage",
        "Stark Black and White Noir", "Hyper-Realistic 3D", "Glitch Art", "Paper Quilling Architecture",
        "Art Deco Geometric", "Charcoal Portrait", "Abstract Expressionism", "Voxel Art"
    ],
    "lighting": [
        "God Rays / Volumetric Sunlight", "Neon Cyber-Glow", "Soft Golden Hour", "Dramatic Chiaroscuro",
        "Studio High-Key", "Noire Hard Shadows", "Bioluminescent Glow", "Natural Overcast Light",
        "Cinematic Rim Lighting", "Harsh Midday Sun", "Muted Twilight", "Flickering Candlelight",
        "Ultraviolet / Blacklight", "Prismatic Refraction", "Soft Bokeh / Out of Focus",
        "Dramatic Silhouette", "Subsurface Scattering", "Moonlit Mist", "Fairy Light Sparkle", "Static Noise Texture"
    ],
    "palettes": [
        "Monochrome (Black, White, Grey)", "Earthy Tones (Forest Green, Brown, Ochre)", "Acidic Neon (Lime, Magenta, Cyan)",
        "Soft Pastel (Lilac, Mint, Peach)", "Primary Colors (Red, Blue, Yellow)", "Cyberpunk (Purple, Teal, Pink)",
        "Vintage Sepia", "High Contrast B&W with one accent color", "Deep Ocean Blues and Greens",
        "Sunset Fire (Orange, Red, Violet)", "Metallic (Silver, Gold, Copper)", "Nordic Cold (White, Blue, Grey)"
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
        "strategist": "Persona: The Contrarian Tech Realist.\nGoal: Challenge a popular opinion about the trend.",
        "ghostwriter": "Style: Sharp, confident, direct. No filler.",
        "is_organic": False
    },
    "The Visionary": {
        "strategist": "Persona: The Optimistic Futurist.\nGoal: Highlight long-term impact and human potential.",
        "ghostwriter": "Style: Flowing, evocative, but concise.",
        "is_organic": False
    },
    "The Educator": {
        "strategist": "Persona: The Senior Engineer/Teacher.\nGoal: Demystify a complex concept.",
        "ghostwriter": "Style: Clear, methodical, narrative steps. No listicles.",
        "is_organic": False
    },
    "The Analyst": {
        "strategist": "Persona: The Data-Driven Analyst.\nGoal: Focus on efficiency and ROI.",
        "ghostwriter": "Style: Strategic, data-backed, punchy numbers.",
        "is_organic": False
    },
    "The Narrator": {
        "strategist": "Persona: The Modern Epic Poet.\nGoal: Frame the trend as a sharp paradox.",
        "ghostwriter": "Style: Cinematic, rhythmic, stark.",
        "is_organic": False
    },
    "The Storyteller": {
        "strategist": "Persona: The Narrative Architect.\nGoal: Tell a human-centric story about the technology.",
        "ghostwriter": "Style: Personal, warm, descriptive. Focus on a character or specific scenario.",
        "is_organic": True
    },
    "The Provocateur": {
        "strategist": "Persona: The Digital Firebrand.\nGoal: Spark a heated debate by taking an extreme stance.",
        "ghostwriter": "Style: Bold, aggressive, questioning. Use short sentences.",
        "is_organic": False
    },
    "The Minimalist": {
        "strategist": "Persona: The Zen Architect.\nGoal: Extract the absolute core essence of a topic.",
        "ghostwriter": "Style: Ultra-concise, profound. Max 5-7 lines. Plenty of white space.",
        "is_organic": False
    },
    "The Oracle": {
        "strategist": "Persona: The Predictive Sage.\nGoal: Project current trends into the year 2035.",
        "ghostwriter": "Style: Cryptic but authoritative. Use 'When... then...' structures.",
        "is_organic": False
    },
    "The Pragmatist": {
        "strategist": "Persona: The Execution Specialist.\nGoal: Focus on immediate implementation and 'how-to'.",
        "ghostwriter": "Style: No-nonsense, tactical, instructional.",
        "is_organic": True
    },
    "The Anthropologist": {
        "strategist": "Persona: The Tech Sociologist.\nGoal: Observe how tech changes human behavior and culture.",
        "ghostwriter": "Style: Observational, curious, analytical about societies.",
        "is_organic": True
    },
    "The Debunker": {
        "strategist": "Persona: The Hype-Slayer.\nGoal: Dismantle a trending but flawed AI claim.",
        "ghostwriter": "Style: Skeptical, evidence-based, logical.",
        "is_organic": False
    },
    "The Curator": {
        "strategist": "Persona: The Synthesis Artist.\nGoal: Connect 3 unrelated news items into a single insight.",
        "ghostwriter": "Style: Connection-focused, broad, insightful.",
        "is_organic": True
    },
    "The Architect": {
        "strategist": "Persona: The System Designer.\nGoal: Focus on the 'plumbing' and infrastructure of AI.",
        "ghostwriter": "Style: Structural, detailed, engineering-focused.",
        "is_organic": False
    },
    "The Rebel": {
        "strategist": "Persona: The Open-Source Advocate.\nGoal: Champion decentralization and anti-corporate tech.",
        "ghostwriter": "Style: Passionate, anti-gatekeeping, raw.",
        "is_organic": True
    },
    "The Zen Coder": {
        "strategist": "Persona: The Deep Work Master.\nGoal: Focus on the mental state and philosophy of building.",
        "ghostwriter": "Style: Calm, rhythmic, focusing on clarity over features.",
        "is_organic": True
    },
    "The Data Detective": {
        "strategist": "Persona: The Pattern Matcher.\nGoal: Find a hidden truth in recent benchmarks or datasets.",
        "ghostwriter": "Style: Investigative, meticulous, revealing.",
        "is_organic": False
    },
    "The Satirist": {
        "strategist": "Persona: The Cynical Insider.\nGoal: Use irony to highlight the absurdity of modern 'Hype'.",
        "ghostwriter": "Style: Sarcastic, funny, bitingly honest.",
        "is_organic": False
    },
    "The Archivist": {
        "strategist": "Persona: The Tech Historian.\nGoal: Compare today's AI to historically similar tech shifts.",
        "ghostwriter": "Style: Nostalgic but relevant, educational, comparative.",
        "is_organic": True
    },
    "The Fresh Eye": {
        "strategist": "Persona: The Profound Beginner.\nGoal: Ask simple questions that reveal complex truths.",
        "ghostwriter": "Style: Naive but insightful, questioning, clear.",
        "is_organic": True
    },
    "The Maxer": {
        "strategist": "Persona: The Efficiency Maximalist.\nGoal: Optimize every second of the AI workflow.",
        "ghostwriter": "Style: High-energy, speed-focused, condensed.",
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
        self.system_prompt = f"""You are a viral LinkedIn Creator.
Current Persona: {vibe_name}
{vibe_prompt}

Post Format to Enforce: {post_format}

Rules:
1. MAX 500 characters. Be ultra-concise.
2. NO 'In conclusion', 'In summary', 'Delve', 'Crucial', 'Landscape'.
3. NO robotic numbering like '**1.**', '**2.**' or '1)', '2)'.
4. NO markdown asterisks ('*') for bullet points. Use soft line breaks or single emojis if needed.
5. Write like a human sharing a thought, not an AI writing a blog post."""

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
        
        self.system_prompt = f"""You are a Midjourney/DALL-E Prompt Engineer.
Current Style: {vibe_name}
Assigned Artistic Medium: {self.current_medium}
Assigned Lighting: {self.current_lighting}
Assigned Color Palette: {self.current_palette}

Rules:
1. Generate ONE extremely high-quality, creative prompt.
2. Incorporate the medium, lighting, and palette explicitly.
3. OUTPUT ONLY the final structured format.

STRICT OUTPUT FORMAT (NO CHAT):
Visual Format: [Format]
Prompt: [The Prompt]
Text Overlay: [Brief headline if appropriate]"""

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
            system_prompt="""You are a harsh LinkedIn Critic. Review the draft post.
Checklist: 
1. LENGTH: Is it over 500 characters? (Reject immediately if so)
2. BOT FORMATTING: Does it use **1.**, **2.** or similar robotic numbering?
3. BULLETS: Does it use markdown asterisks (*)?
4. AI TONE: Does it sound like a ChatGPT template?

If you find a recurring mistake, output a line starting with "RULE:" to save it to memory.
Example: "RULE: Never use markdown asterisks for bullets." """
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
        self.organic_searcher = OrganicImageSearcher()
        self.critic = Critic()
        self.image_gen = ArtDirector() # Using ArtDirector as the image gen manager
        self.linkedin = LinkedInConnector()
        self.memory = Memory() # Direct access to memory for orchestrator
        self.networker = Networker()
        self.config = CONFIG # Global config from top of file

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
        logger.info("🚀 Starting LinkedIn Growth Workflow (V2: Variety Engine)")
        
        # Step 0: Review Past Performance
        self.review_past_performance()
        performance_insights = self.memory.get_performance_insights()
        
        # Step 0.1: entropy and Config
        variety_cfg = self.config.get("variety", {})
        image_pref = variety_cfg.get("image_mode_preference", "hybrid")
        
        # 0.5. Select Vibe
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
        
        # 0.6 Select Format
        post_format = random.choice(POST_FORMATS)
        logger.info(f"📋 Format Selected: {post_format.split(':')[0]}")

        # Apply Vibe to Agents
        strategist_prompt = f"{vibe_config['strategist']}\n\nDATA FEEDBACK: {performance_insights}\n\nConstraint: Focus on the perspective of {vibe_name}."
        self.strategist.set_vibe(vibe_name, strategist_prompt)
        
        self.ghostwriter.set_vibe(vibe_name, vibe_config["ghostwriter"], post_format=post_format)
        self.art_director.set_vibe(vibe_name, "") # Prompt is generated dynamically in set_vibe's new version
        
        # Step 1: Research & Conceptualization
        if initial_topic:
            topic_query = initial_topic
        else:
            raw_topics = self.config.get("topics", ["AI agents"])
            topic_query = random.choice(raw_topics)
            
        logger.info(f"🔍 Researching & Conceptualizing: {topic_query}")
        trend_brief = self.research_manager.run(topic_query)
        
        if not trend_brief:
            logger.error("Workflow Aborted: Research failed.")
            return

        # Step 1.5: Networker
        comment_pack = self.networker.run(trend_brief)
        if comment_pack:
            self.memory.save_comment_pack(comment_pack)

        # Step 2: Strategy (Picking an Angle)
        logger.info("🧠 Strategizing...")
        strategy = self.strategist.run(trend_brief)
        if not strategy:
            logger.error("Workflow Aborted: Strategy failed.")
            return

        # Step 3: Content Creation
        logger.info("✍️ Drafting Post...")
        draft_text = self.ghostwriter.run(strategy)
        
        logger.info("🎨 Designing Visuals...")
        visual_concept = self.art_director.run(strategy)

        if not draft_text:
            logger.error("Workflow Aborted: Ghostwriting failed.")
            return
        
        # Step 4: Visual Sourcing (AI vs Organic)
        image_data = None
        use_organic = False
        
        if vibe_config.get("is_organic") and self.config.get("features", {}).get("enable_organic_visuals"):
            # Check probability or preference
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
        
        # Step 5: Review
        full_package = f"{draft_text}\n\n(Visual: {visual_concept})"
        feedback = self.critic.run(full_package)
        
        # Step 6: Publish
        logger.info("✅ Preparing to Post...")
        post_urn = self.linkedin.post_content(draft_text, image_data)
        
        # Step 7: Save to Memory
        if post_urn:
            self.memory.add_post_history(topic_query, vibe_name, post_urn)
            return post_urn

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
