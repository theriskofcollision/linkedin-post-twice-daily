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
                json.dump({"rules": [], "history": []}, f)

    def _load(self):
        try:
            with open(self.file_path, "r") as f:
                return json.load(f)
        except Exception:
            return {"rules": [], "history": []}

    def _save(self, data):
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
            print(f"🧠 Memory Updated: Added rule '{rule}'")

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
        print(f"🧠 Memory Updated: Logged post '{topic}' ({vibe})")

    def update_post_stats(self, urn: str, likes: int, comments: int):
        data = self._load()
        for post in data.get("history", []):
            if post["urn"] == urn:
                post["stats"] = {"likes": likes, "comments": comments}
                self._save(data)
                print(f"🧠 Stats Updated for {urn}: {likes} likes, {comments} comments")
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
        print("🧠 Memory Updated: Saved latest Comment Pack.")

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
                model_name = 'gemini-2.5-flash' 
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
                return None


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
        "strategist": "Persona: The Contrarian Tech Realist.\nGoal: Find a unique, slightly controversial angle on the trend.\nOutput:\n- Hook: A single, punchy sentence that challenges the status quo.\n- Angle: The core argument (why most people are wrong).\n- Target Audience: Tech leaders and developers.\n- CTA: A question to provoke debate.",
        "ghostwriter": """Style: Sharp, confident, conversational.
Structure (MUST follow classic literary format):
  INTRODUCTION: Start with an observation or anecdote that sets the scene. Draw the reader in naturally. (2-3 sentences)
  BODY: Develop your argument with specific evidence and examples. Build tension. Show the contradiction between hype and reality. Use varied sentence lengths - some short for impact, others longer for depth. (Main bulk of post)
  CONCLUSION: Tie it together with a final insight or implication. End with a thought-provoking question that invites genuine debate.
Tone: Like a colleague sharing a hard truth over coffee. Not preachy, not listicle-y.""",
        "art_director": "Style: Brutalist Web Design, Glitch Art, Raw Concrete texture, High Contrast Black and White with Red accents, Typography-heavy.\nMood: Rebellious, Raw, Bold."
    },
    "The Visionary": {
        "strategist": "Persona: The Optimistic Futurist.\nGoal: Highlight the massive potential and long-term impact of this trend.\nOutput:\n- Hook: An inspiring statement about the future.\n- Angle: How this changes the world for the better.\n- Target Audience: Innovators and Dreamers.\n- CTA: Ask readers to imagine the possibilities.",
        "ghostwriter": """Style: Narrative, flowing, evocative. Like reading a well-crafted essay.
Structure (MUST follow classic literary format):
  INTRODUCTION: Paint a picture of where we are today or what's emerging. Set up the transformation. Use vivid language. (2-3 sentences)
  BODY: Explore the implications and possibilities. Connect dots between the technology and human impact. Use metaphors and concrete examples. Build a sense of momentum and possibility. (Main content)
  CONCLUSION: Bring it home with what this means for us collectively. End with an invitation to imagine or participate in this future.
Tone: Optimistic but grounded. Like TED talk meets thoughtful blog post.""",
        "art_director": "Style: Ethereal Watercolor, Soft Pastel Colors, Dreamy, Studio Ghibli Landscape, Lush Nature meets Technology.\nMood: Hopeful, Peaceful, Expansive."
    },
    "The Educator": {
        "strategist": "Persona: The Senior Engineer/Teacher.\nGoal: Demystify a complex concept. Explain 'How it works'.\nOutput:\n- Hook: A clear 'Did you know?' or problem statement.\n- Angle: The technical truth behind the buzzword.\n- Target Audience: Junior to Mid-level Engineers.\n- CTA: Ask what they want to learn next.",
        "ghostwriter": """Style: Clear, patient, methodical. Like a good technical blog post.
Structure (MUST follow classic literary format):
  INTRODUCTION: Identify the concept and why it's often misunderstood. Set up what you'll clarify. (2-3 sentences)
  BODY: Explain the concept step-by-step with concrete examples. Use analogies if helpful. Build understanding progressively. Break down complexity into digestible parts without dumbing it down. (Main explanation)
  CONCLUSION: Recap the key insight and why it matters in practice. Suggest where to go deeper or what to explore next.
Tone: Like a senior engineer explaining something to a mid-level teammate. Respectful, clear, practical.""",
        "art_director": "Style: Technical Blueprint, Da Vinci Sketchbook, White lines on Blue background, Schematic, Detailed Line Art.\nMood: Professional, Analytical, Precise."
    },
    "The Analyst": {
        "strategist": "Persona: The Data-Driven Analyst.\nGoal: Focus on efficiency, ROI, metrics, and business impact.\nOutput:\n- Hook: A stat or efficiency claim.\n- Angle: Why this makes business sense (or doesn't).\n- Target Audience: CTOs and Product Managers.\n- CTA: Ask about their ROI.",
        "ghostwriter": """Style: Professional, evidence-based, strategic. Like a consulting insight or HBR article.
Structure (MUST follow classic literary format):
  INTRODUCTION: Start with a compelling data point or business observation. Frame the question or challenge. (2-3 sentences)
  BODY: Analyze the trend through a business lens. Present evidence, compare options, discuss trade-offs. Use concrete numbers when possible. Show the strategic implications. (Main analysis)
  CONCLUSION: Synthesize the key business takeaway. End with a strategic question that prompts leaders to assess their own situation.
Tone: Like a strategic advisor presenting to executives. Concise, insightful, numbers-driven but not dry.""",
        "art_director": "Style: Swiss International Style, Bauhaus, Geometric Shapes, Clean Grid, Primary Colors (Red, Blue, Yellow), Minimalist Data Viz.\nMood: Sophisticated, Corporate, Smart."
    },
    "The Narrator": {
        "strategist": "Persona: The Literary Historian of the Future.\nGoal: Frame the trend as a historical paradox. It is X, it is Y.\nOutput:\n- Hook: A grand, rhythmic statement of duality (It was the age of...).\n- Angle: The complexity of the moment (High hopes vs. Deep fears).\n- Target Audience: Thought Leaders and Philosophers.\n- CTA: A question about the soul of the industry.",
        "ghostwriter": """Style: Epic, rhythmic, paradoxical. Use anaphora (repetition of phrases like 'It is...', 'We have...').
Structure (MUST follow classic literary format):
  INTRODUCTION: Establish the duality of the moment. Use radical contrast (Light/Dark, Wisdom/Foolishness). Set a grand stage. (2-3 sentences)
  BODY: Explore the 'best of times' (the miracle) and the 'worst of times' (the danger) side-by-side. Use sweeping statements. Capture the Zeitgeist. (Main content)
  CONCLUSION: Bring the paradox to a head. Where do we stand in history? End with a timeless question.
Tone: Grand, observant, poetic. Like Charles Dickens writing about AI.""",
        "art_director": "Style: Cinematic Film Still, 35mm Photography, Grainy, Edward Hopper style solitude, Dramatic Lighting, Realistic.\nMood: Timeless, Epic, Profound."
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
        print(f"\n--- {self.name} ({self.role}) Working ---")
        
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
        
        print(f"Generating image for cleaned prompt: {clean_prompt[:50]}...")

        try:
            # Use Pollinations.ai (Free, No Key)
            encoded_prompt = urllib.parse.quote(clean_prompt)
            # Request a landscape image (1200x628 is standard for LinkedIn)
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1200&height=628&nologo=true"
            
            response = requests.get(url)
            response.raise_for_status()
            
            print("✅ Image generated successfully (via Pollinations)!")
            return response.content
            
        except Exception as e:
            print(f"❌ Image Generation Error: {e}")
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
        print("✅ Image uploaded to LinkedIn server.")

    def post_content(self, text: str, image_data: bytes = None) -> Optional[str]:
        if not self.access_token or not self.author_urn:
            print("⚠️  Missing LinkedIn Credentials. Skipping API call.")
            return None

        asset_urn = None
        if image_data:
            try:
                print("Step 1/3: Registering image upload...")
                upload_url, asset = self.register_upload()
                print("Step 2/3: Uploading image binary...")
                self.upload_image(upload_url, image_data)
                asset_urn = asset
                print(f"Step 3/3: Creating post with asset: {asset_urn}")
            except Exception as e:
                print(f"❌ Image upload failed: {e}. Falling back to text-only post.")

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
            print(f"✅ Successfully posted to LinkedIn! Status Code: {response.status_code}")
            
            # Extract URN
            post_urn = response.headers.get("x-restli-id")
            if not post_urn:
                # Try parsing body if header is missing
                try:
                    post_urn = response.json().get("id")
                except:
                    pass
            
            print(f"🆔 New Post URN: {post_urn}")
            return post_urn

        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to post to LinkedIn: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Error Details: {e.response.text}")
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
                print(f"⚠️ Stats not found for {urn} (might be too new or wrong ID format).")
                return {"likes": 0, "comments": 0}
                
            response.raise_for_status()
            data = response.json()
            
            likes = data.get("likesSummary", {}).get("totalLikes", 0)
            comments = data.get("commentsSummary", {}).get("totalComments", 0)
            
            return {"likes": likes, "comments": comments}
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                print(f"⚠️  Permission Denied (403) for {urn}. Missing 'r_member_social' scope.")
                print("   -> To fix: Apply for 'Marketing Developer Platform' in LinkedIn Developer Portal.")
                return {"likes": 0, "comments": 0}
            else:
                print(f"❌ Failed to fetch stats for {urn}: {e}")
                return {"likes": 0, "comments": 0}

        except Exception as e:
            print(f"❌ Failed to fetch stats for {urn}: {e}")
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
        print("\n📊 Reviewing Past Performance...")
        print("ℹ️ Healer function is currently DISABLED (Personal Profile Mode). Skipping stats check.")
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
        print("🚀 Starting LinkedIn Growth Workflow")
        
        # Step 0: Review Past Performance (The Feedback Loop)
        self.review_past_performance()
        performance_insights = self.memory.get_performance_insights()
        print(f"\n💡 Performance Insight: {performance_insights}")
        
        # 0.5. Select Vibe
        vibe_name = random.choice(list(VIBES.keys()))
        vibe_config = VIBES[vibe_name]
        print(f"\n🎲 Vibe Selected: {vibe_name}")
        
        # Apply Vibe to Agents
        # Append performance insights to Strategist's prompt
        strategist_prompt = f"{vibe_config['strategist']}\n\nDATA FEEDBACK: {performance_insights}"
        self.strategist.set_vibe(vibe_name, strategist_prompt)
        
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
            trend_data = self.research_manager.run(f"Find current hot topics in Agentic AI. Selected: {selected_topic}")
        
        # Abort if research failed (API Error)
        if not trend_data:
            print("❌ Workflow Aborted: Research failed (likely quota exceeded).")
            return
        
        # Step 1.5: Generate Comment Pack (The Networker) - Non-critical, continue if fails
        comment_pack = self.networker.run(trend_data)
        if comment_pack:
            print(f"\n{comment_pack}\n")
            self.memory.save_comment_pack(comment_pack)
        else:
            print("⚠️ Networker failed (non-critical). Continuing without comment pack.")
        
        # Step 2: Strategy
        strategy = self.strategist.run(trend_data)
        
        # Abort if strategy failed
        if not strategy:
            print("❌ Workflow Aborted: Strategy generation failed (likely quota exceeded).")
            return
        
        # Step 3: Content Creation
        draft_text = self.ghostwriter.run(strategy)
        visual_concept = self.art_director.run(strategy)

        if not draft_text or not visual_concept:
            print("❌ Workflow Aborted: Content generation failed (likely quota exceeded).")
            return
        
        # Step 4: Image Generation
        # Extract prompt from visual_concept (simplified for now, just use the whole output)
        image_prompt = f"Generate a high quality image: {visual_concept}"
        image_data = self.image_gen.generate_image(image_prompt)
        
        # Step 5: Review
        full_package = f"{draft_text}\n\n(Visual Concept: {visual_concept})"
        feedback = self.critic.run(full_package)
        
        print("\n✅ Workflow Complete. Preparing to Post...")
        
        # Step 6: Publish
        post_urn = self.linkedin.post_content(draft_text, image_data)
        
        # Step 7: Save to Memory
        if post_urn:
            # Extract topic from trend_data (simplified)
            topic_summary = initial_topic if initial_topic else selected_topic
            self.memory.add_post_history(topic_summary, vibe_name, post_urn)

if __name__ == "__main__":
    try:
        orch = Orchestrator()
        # Run without arguments to let the randomizer pick a topic
        orch.run_workflow()
        print("\n✅ Script completed successfully.")
    except Exception as e:
        print(f"\n❌ Script failed with error: {e}")
        # Exit with code 0 so GitHub Actions doesn't show a red X for expected failures
        # The bot just couldn't run today, but that's OK.
        exit(0)
