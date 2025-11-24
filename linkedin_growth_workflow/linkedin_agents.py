import os
import json
import random
import requests
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
        try:
            genai.configure(api_key=api_key)
            
            # Use the model explicitly found in your logs
            model_name = 'gemini-2.0-flash' 
            # If 2.0 fails, you can try 'gemini-flash-latest'
            
            print(f"Attempting to use model: {model_name}")
            model = genai.GenerativeModel(model_name)
            
            full_prompt = f"{self.system_prompt}\n\nTask Input: {input_data}"
            response = model.generate_content(full_prompt)
            
            result = response.text.strip()
            print(f"OUTPUT: {result[:100]}...") # Print first 100 chars
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
            system_prompt="""You are an expert AI Trend Researcher. Your job is to scour sources to find the latest breakthroughs in Agentic AI.
Output Format: Topic, Source, Why it's hot, Relevance."""
        )
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
class ArtDirector(Agent):
    def __init__(self):
        super().__init__(
            name="ArtDirector",
            role="Visual Creator",
            system_prompt="""You are a Midjourney/DALL-E Prompt Engineer.
Style: Cyberpunk, Synthwave, or Abstract Tech.
Output:
- Visual Format: (e.g., 'Digital Illustration', '3D Render')
- Prompt: A detailed, descriptive prompt for an image generator.
- Text Overlay: A short, catchy phrase to put on the image."""
        )
class Critic(Agent):
    def __init__(self):
        super().__init__(
            name="Critic",
            role="Quality Control",
            system_prompt="""You are a harsh LinkedIn Critic. Review the draft post.
If it sounds like ChatGPT, say so.
Checklist: 
- Is the hook boring? 
- Are there too many adjectives? 
- Is the formatting scannable?"""
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
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("⚠️ Missing GEMINI_API_KEY for image generation.")
            return None
        print(f"\n--- {self.name} ({self.role}) Working ---")
        print(f"Generating image for prompt: {prompt[:50]}...")
        try:
            genai.configure(api_key=api_key)
            # Use the model explicitly found in logs that supports images
            model = genai.GenerativeModel('gemini-2.0-flash') 
            
            response = model.generate_content(prompt)
            
            # Check if response contains image data
            if response.parts:
                for part in response.parts:
                    if part.inline_data:
                        print("✅ Image generated successfully!")
                        return part.inline_data.data
            
            print("❌ No image data found in response.")
            return None
            
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
        url = "https://api.linkedin.com/v2/assets?action=registerUpload"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "owner": self.author_urn,
                "serviceRelationships": [{
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent"
                }]
            }
        }
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        
        upload_url = data['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
        asset_urn = data['value']['asset']
        return upload_url, asset_urn
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
