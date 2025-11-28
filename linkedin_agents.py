import os
import json
import random
import requests
import urllib.parse
from dataclasses import dataclass
from typing import List, Optional
import google.generativeai as genai


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
    def __init__(self, file_path="memory.json"):
        self.file_path = file_path
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w") as f:
                json.dump({"rules": []}, f)

    def get_rules(self) -> List[str]:
        try:
            with open(self.file_path, "r") as f:
                data = json.load(f)
            return data.get("rules", [])
        except Exception:
            return []

    def add_rule(self, rule: str):
        try:
            with open(self.file_path, "r") as f:
                data = json.load(f)
            
            if rule not in data["rules"]:
                data["rules"].append(rule)
                
            with open(self.file_path, "w") as f:
                json.dump(data, f, indent=2)
            print(f"🧠 Memory Updated: Added rule '{rule}'")
        except Exception as e:
            print(f"❌ Failed to update memory: {e}")

# --- Base Agent ---

class Agent:
    def __init__(self, name: str, role: str, system_prompt: str):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt

    def run(self, input_data: str) -> str:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print(f"⚠️  Missing GEMINI_API_KEY. Returning mock data for {self.name}.")
            return f"[{self.name} Output based on '{input_data}']"

        print(f"\n--- {self.name} ({self.role}) Working ---")
        print(f"INPUT: {input_data}")
        print(f"Thinking...")

        import time
        
        max_retries = 3
        base_delay = 5  # Start with 5 seconds delay
        
        for attempt in range(max_retries):
            try:
                genai.configure(api_key=api_key)
                model_name = 'gemini-2.0-flash' 
                if attempt == 0:
                    print(f"Attempting to use model: {model_name}")
                else:
                    print(f"Retry attempt {attempt + 1}/{max_retries} for model: {model_name}")
                
                model = genai.GenerativeModel(model_name)
                
                full_prompt = f"{self.system_prompt}\n\nTask Input: {input_data}"
                response = model.generate_content(full_prompt)
                
                result = response.text.strip()
                print(f"OUTPUT: {result[:100]}...") 
                return result
                
            except Exception as e:
                if "429" in str(e) or "Resource exhausted" in str(e):
                    if attempt < max_retries - 1:
                        wait_time = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        print(f"⚠️  Rate limit hit (429). Waiting {wait_time:.1f}s before retry...")
                        time.sleep(wait_time)
                        continue
                
                print(f"❌ Gemini Error: {e}")
                return f"[Error generating content for {self.name}]"

# --- Specific Agents ---

class HackerNewsConnector:
    def get_top_ai_stories(self, limit: int = 5) -> str:
        print("\n--- HackerNews Connector Working ---")
        try:
            # 1. Get Top Stories IDs
            top_stories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
            response = requests.get(top_stories_url)
            story_ids = response.json()[:50] # Get top 50 to filter

            stories = []
            print(f"Scanning top {len(story_ids)} stories for AI/LLM content...")
            
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
                    print(f"Found: {title}")

            if not stories:
                return "No specific AI stories found in top 50. Using general knowledge."
            
            return "\n\n".join(stories)
            
        except Exception as e:
            print(f"❌ HackerNews Error: {e}")
            return "Error fetching HackerNews data."

class NewsAPIConnector:
    def get_tech_headlines(self, limit: int = 5) -> str:
        print("\n--- NewsAPI Connector Working ---")
        api_key = os.environ.get("NEWS_API_KEY")
        if not api_key:
            print("⚠️  Missing NEWS_API_KEY. Skipping NewsAPI.")
            return ""

        try:
            # Fetch top tech headlines
            url = f"https://newsapi.org/v2/top-headlines?category=technology&language=en&pageSize=10&apiKey={api_key}"
            response = requests.get(url)
            data = response.json()
            
            articles = []
            print(f"Scanning {len(data.get('articles', []))} articles from NewsAPI...")
            
            for article in data.get('articles', [])[:limit]:
                title = article.get('title', '')
                url = article.get('url', '')
                source = article.get('source', {}).get('name', 'Unknown')
                
                articles.append(f"- Title: {title}\n  Source: {source}\n  URL: {url}")
                print(f"Found: {title}")

            if not articles:
                return "No recent tech headlines found."
            
            return "\n\n".join(articles)
            
        except Exception as e:
            print(f"❌ NewsAPI Error: {e}")
            return "Error fetching NewsAPI data."

class ArxivConnector:
    def get_latest_papers(self, limit: int = 3) -> str:
        print("\n--- arXiv Connector Working ---")
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
            print(f"Scanning arXiv for latest papers...")
            
            count = 0
            for entry in root.findall('atom:entry', ns):
                if count >= limit:
                    break
                
                title = entry.find('atom:title', ns).text.strip().replace('\n', ' ')
                link = entry.find('atom:id', ns).text.strip()
                summary = entry.find('atom:summary', ns).text.strip().replace('\n', ' ')[:200] + "..."
                
                papers.append(f"- Title: {title}\n  URL: {link}\n  Abstract: {summary}")
                print(f"Found Paper: {title[:50]}...")
                count += 1

            if not papers:
                return "No recent arXiv papers found."
            
            return "\n\n".join(papers)
            
        except Exception as e:
            print(f"❌ arXiv Error: {e}")
            return "Error fetching arXiv data."

class TavilyConnector:
    def search(self, query: str) -> str:
        print("\n--- Tavily Connector Working ---")
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            print("⚠️  Missing TAVILY_API_KEY. Skipping Tavily.")
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
            print(f"❌ Tavily Error: {e}")
            return "Error fetching Tavily data."

class TrendScout(Agent):
    def __init__(self):
        self.hn_connector = HackerNewsConnector()
        self.news_connector = NewsAPIConnector()
        self.arxiv_connector = ArxivConnector()
        self.tavily_connector = TavilyConnector()
        super().__init__(
            name="TrendScout",
            role="Researcher",
            system_prompt="""You are an expert AI Trend Researcher. 
Your job is to analyze the provided stories (HackerNews + NewsAPI + arXiv) AND perform a deep-dive search using Tavily to find the absolute latest context.
Output Format: 
- Topic: [Title]
- Source: [URL]
- Why it's hot: [Reason based on score/title/source]
- Relevance: [Why it matters to tech professionals]"""
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
        "strategist": "Persona: The Contrarian Tech Realist.\nGoal: Find a unique, slightly controversial angle on the trend.\nOutput:\n- Hook: A single, punchy sentence that challenges the status quo.\n- Angle: The core argument (why most people are wrong).\n- Target Audience: Tech leaders and developers.\n- CTA: A question to provoke debate.",
        "ghostwriter": """Style: Sharp, confident, conversational.
Structure (MUST follow classic literary format):
  INTRODUCTION: Start with an observation or anecdote that sets the scene. Draw the reader in naturally. (2-3 sentences)
  BODY: Develop your argument with specific evidence and examples. Build tension. Show the contradiction between hype and reality. Use varied sentence lengths - some short for impact, others longer for depth. (Main bulk of post)
  CONCLUSION: Tie it together with a final insight or implication. End with a thought-provoking question that invites genuine debate.
Tone: Like a colleague sharing a hard truth over coffee. Not preachy, not listicle-y.""",
        "art_director": "Style: Cyberpunk, Synthwave, Dark Mode, Neon accents.\nMood: Intense, High-Tech, Mysterious."
    },
    "The Visionary": {
        "strategist": "Persona: The Optimistic Futurist.\nGoal: Highlight the massive potential and long-term impact of this trend.\nOutput:\n- Hook: An inspiring statement about the future.\n- Angle: How this changes the world for the better.\n- Target Audience: Innovators and Dreamers.\n- CTA: Ask readers to imagine the possibilities.",
        "ghostwriter": """Style: Narrative, flowing, evocative. Like reading a well-crafted essay.
Structure (MUST follow classic literary format):
  INTRODUCTION: Paint a picture of where we are today or what's emerging. Set up the transformation. Use vivid language. (2-3 sentences)
  BODY: Explore the implications and possibilities. Connect dots between the technology and human impact. Use metaphors and concrete examples. Build a sense of momentum and possibility. (Main content)
  CONCLUSION: Bring it home with what this means for us collectively. End with an invitation to imagine or participate in this future.
Tone: Optimistic but grounded. Like TED talk meets thoughtful blog post.""",
        "art_director": "Style: Solarpunk, Bright, Futuristic Utopia, Studio Ghibli vibes, lush greenery meets high tech.\nMood: Hopeful, Expansive, Bright."
    },
    "The Educator": {
        "strategist": "Persona: The Senior Engineer/Teacher.\nGoal: Demystify a complex concept. Explain 'How it works'.\nOutput:\n- Hook: A clear 'Did you know?' or problem statement.\n- Angle: The technical truth behind the buzzword.\n- Target Audience: Junior to Mid-level Engineers.\n- CTA: Ask what they want to learn next.",
        "ghostwriter": """Style: Clear, patient, methodical. Like a good technical blog post.
Structure (MUST follow classic literary format):
  INTRODUCTION: Identify the concept and why it's often misunderstood. Set up what you'll clarify. (2-3 sentences)
  BODY: Explain the concept step-by-step with concrete examples. Use analogies if helpful. Build understanding progressively. Break down complexity into digestible parts without dumbing it down. (Main explanation)
  CONCLUSION: Recap the key insight and why it matters in practice. Suggest where to go deeper or what to explore next.
Tone: Like a senior engineer explaining something to a mid-level teammate. Respectful, clear, practical.""",
        "art_director": "Style: Minimalist 3D, Isometric, Blueprint, Clean lines, White/Light background.\nMood: Professional, Organized, Clarity."
    },
    "The Analyst": {
        "strategist": "Persona: The Data-Driven Analyst.\nGoal: Focus on efficiency, ROI, metrics, and business impact.\nOutput:\n- Hook: A stat or efficiency claim.\n- Angle: Why this makes business sense (or doesn't).\n- Target Audience: CTOs and Product Managers.\n- CTA: Ask about their ROI.",
        "ghostwriter": """Style: Professional, evidence-based, strategic. Like a consulting insight or HBR article.
Structure (MUST follow classic literary format):
  INTRODUCTION: Start with a compelling data point or business observation. Frame the question or challenge. (2-3 sentences)
  BODY: Analyze the trend through a business lens. Present evidence, compare options, discuss trade-offs. Use concrete numbers when possible. Show the strategic implications. (Main analysis)
  CONCLUSION: Synthesize the key business takeaway. End with a strategic question that prompts leaders to assess their own situation.
Tone: Like a strategic advisor presenting to executives. Concise, insightful, numbers-driven but not dry.""",
        "art_director": "Style: Abstract Data Visualization, Geometric patterns, Network nodes, Corporate but premium.\nMood: Sophisticated, Complex, Smart."
    }
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

# ... (Critic and ImageGenerator remain the same) ...

# --- Orchestrator ---

class Orchestrator:
    def __init__(self):
        self.trend_scout = TrendScout()
        self.strategist = Strategist()
        self.ghostwriter = Ghostwriter()
        self.art_director = ArtDirector()
        self.critic = Critic()
        self.image_gen = ImageGenerator()
        self.linkedin = LinkedInConnector()

    def run_workflow(self, initial_topic: str = None):
        print("🚀 Starting LinkedIn Growth Workflow")
        
        # 0. Select Vibe
        vibe_name = random.choice(list(VIBES.keys()))
        vibe_config = VIBES[vibe_name]
        print(f"\n🎲 Vibe Selected: {vibe_name}")
        
        # Apply Vibe to Agents
        self.strategist.set_vibe(vibe_name, vibe_config["strategist"])
        self.ghostwriter.set_vibe(vibe_name, vibe_config["ghostwriter"])
        self.art_director.set_vibe(vibe_name, vibe_config["art_director"])
        
        # Step 1: Research
        if initial_topic:
            print(f"Topic provided by user: {initial_topic}")
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
            trend_data = self.trend_scout.run(f"Find current hot topics in Agentic AI. Selected: {selected_topic}")
        
        # Step 2: Strategy
        strategy = self.strategist.run(trend_data)
        
        # Step 3: Content Creation
        draft_text = self.ghostwriter.run(strategy)
        visual_concept = self.art_director.run(strategy)
        
        # Step 4: Image Generation
        # Extract prompt from visual_concept (simplified for now, just use the whole output)
        image_prompt = f"Generate a high quality image: {visual_concept}"
        image_data = self.image_gen.generate_image(image_prompt)
        
        # Step 5: Review
        full_package = f"{draft_text}\n\n(Visual Concept: {visual_concept})"
        feedback = self.critic.run(full_package)
        
        print("\n✅ Workflow Complete. Preparing to Post...")
        
        # Step 6: Publish
        self.linkedin.post_content(draft_text, image_data)

if __name__ == "__main__":
    orch = Orchestrator()
    # Run without arguments to let the randomizer pick a topic
    orch.run_workflow()
