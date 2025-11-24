import os
import json
import random
import requests
import urllib.parse
from dataclasses import dataclass
from typing import List, Optional
import google.generativeai as genai
from google.generativeai import types
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
    def run(self, input_data: str, use_search: bool = False) -> str:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print(f"⚠️  Missing GEMINI_API_KEY. Returning mock data for {self.name}.")
            return f"[{self.name} Output based on '{input_data}']"
        print(f"\n--- {self.name} ({self.role}) Working ---")
        print(f"INPUT: {input_data}")
        print(f"Thinking...")
        try:
            genai.configure(api_key=api_key)
            
            model_name = 'gemini-2.0-flash' 
            print(f"Attempting to use model: {model_name}")
            
            # Enable Google Search Tool if requested
            tools = None
            if use_search:
                try:
                    tools = [types.Tool(google_search=types.GoogleSearch())]
                    print("✅ Google Search Tool enabled.")
                except AttributeError:
                    print("⚠️  Google Search Tool not available (SDK version too old). Proceeding without search.")
                    tools = None
            
            model = genai.GenerativeModel(model_name, tools=tools)
            
            full_prompt = f"{self.system_prompt}\n\nTask Input: {input_data}"
            response = model.generate_content(full_prompt)
            
            # Handle Search Grounding Metadata
            if use_search and tools and response.candidates[0].grounding_metadata.search_entry_point:
                print("🌐 Google Search Used. Citations found.")
            
            result = response.text.strip()
            print(f"OUTPUT: {result[:100]}...") 
            return result
        except Exception as e:
            print(f"❌ Gemini Error: {e}")
            return f"[Error generating content for {self.name}]"
# --- Specific Agents ---
class TrendScout(Agent):
    def __init__(self):
        super().__init__(
            name="TrendScout",
            role="Researcher",
            system_prompt="""You are an expert AI Trend Researcher. 
Your job is to scour the web to find the latest, REAL-TIME breakthroughs in Agentic AI.
You MUST use Google Search to find data from the last 24-48 hours.
Output Format: 
- Topic: [Title]
- Source: [URL]
- Why it's hot: [Reason]
- Relevance: [Why it matters]"""
        )
    
    # Override run to force search
    def run(self, input_data: str) -> str:
        return super().run(input_data, use_search=True)
class Strategist(Agent):
    def __init__(self):
        super().__init__(
            name="Strategist",
            role="Growth Hacker",
            system_prompt="""You are a LinkedIn Growth Strategist. DO NOT be generic.
Persona: The Contrarian Tech Realist.
Goal: Find a unique, slightly controversial angle on the trend.
Output:
- Hook: A single, punchy sentence that challenges the status quo.
- Angle: The core argument (why most people are wrong).
- Target Audience: Tech leaders and developers.
- CTA: A question to provoke debate."""
        )
class Ghostwriter(Agent):
    def __init__(self):
        self.memory = Memory()
        super().__init__(
            name="Ghostwriter",
            role="Content Writer",
            system_prompt="""You are a viral LinkedIn Creator. You write like a human, not an AI.
Rules:
1. NO 'In conclusion', 'In summary', 'Delve', 'Crucial', 'Landscape'.
2. Use short, punchy sentences. Varied rhythm.
3. Use bullet points for readability.
4. Tone: Confident, slightly informal, professional but not stiff.
5. Max 1500 chars.
Structure:
- The Hook (from Strategy)
- The 'Meat' (The insight, the 'Aha!' moment)
- The Takeaway (Actionable advice)
- CTA (Question to the reader)"""
        )
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
            system_prompt="""You are a Midjourney/DALL-E Prompt Engineer.
Style: Cyberpunk, Synthwave, or Abstract Tech.
STRICT OUTPUT FORMAT (NO CHAT):
Visual Format: [Format]
Prompt: [The Prompt]
Text Overlay: [The Text]"""
        )
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
    def post_content(self, text: str, image_data: bytes = None):
        if not self.access_token or not self.author_urn:
            print("⚠️  Missing LinkedIn Credentials. Skipping API call.")
            return
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
            try:
                print(f"Response: {response.json()}")
            except json.JSONDecodeError:
                print("Response body is empty (normal for some 201 responses).")
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to post to LinkedIn: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Error Details: {e.response.text}")
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
