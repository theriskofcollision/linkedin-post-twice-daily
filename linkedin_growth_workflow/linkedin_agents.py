import os
import json
import random
import requests
from dataclasses import dataclass
from typing import List, Optional

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
        # In a real implementation, this would call an LLM API (Gemini, GPT, etc.)
        # For this simulation, we will print the prompt and return a placeholder or mock response.
        print(f"\n--- {self.name} ({self.role}) Working ---")
        print(f"INPUT: {input_data}")
        print(f"Thinking...")
        # Mocking output for demonstration purposes
        return f"[{self.name} Output based on '{input_data}']"

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
            system_prompt="""You are a LinkedIn Growth Strategist. Analyze trends and align them with Hakan's persona.
Define: The Hook, The Angle, Target Audience, CTA."""
        )

class Ghostwriter(Agent):
    def __init__(self):
        super().__init__(
            name="Ghostwriter",
            role="Content Writer",
            system_prompt="""You are a top-tier LinkedIn Ghostwriter. Write punchy, readable posts.
Structure: Hook, Meat, Takeaway, CTA. Max 1500 chars."""
        )

class ArtDirector(Agent):
    def __init__(self):
        super().__init__(
            name="ArtDirector",
            role="Visual Creator",
            system_prompt="""You are an AI Art Director. Design visual concepts (Cyberpunk/Neon/Deep Space).
Output: Visual Format, Image Prompt, Text Overlay."""
        )

class Critic(Agent):
    def __init__(self):
        super().__init__(
            name="Critic",
            role="Quality Control",
            system_prompt="""You are a harsh LinkedIn Critic. Review the draft post and visual concept.
Checklist: Hook weak? Too long? Readable? Value clear?"""
        )

# --- LinkedIn Connector ---

class LinkedInConnector:
    def __init__(self):
        self.access_token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
        self.author_urn = os.environ.get("LINKEDIN_PERSON_URN") # e.g., "urn:li:person:12345"

    def post_content(self, text: str, image_url: str = None):
        if not self.access_token or not self.author_urn:
            print("⚠️  Missing LinkedIn Credentials (LINKEDIN_ACCESS_TOKEN or LINKEDIN_PERSON_URN). Skipping API call.")
            return

        url = "https://api.linkedin.com/rest/posts"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": "202401" # Use latest version
        }

        # Construct the payload
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
        
        # Note: Image uploading is a multi-step process (Initialize -> Upload -> Finalize).
        # For this v1, we will stick to text-only posts to ensure reliability, 
        # or we would need to implement the full image upload flow.
        # If image_url is provided (e.g. from an external host), we could try to link it, 
        # but native image posts require the asset upload workflow.
        
        try:
            response = requests.post(url, headers=headers, json=post_data)
            response.raise_for_status()
            print(f"✅ Successfully posted to LinkedIn! Status Code: {response.status_code}")
            print(f"Response: {response.json()}")
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
        
        # Step 3: Content Creation (Parallel-ish)
        draft_text = self.ghostwriter.run(strategy)
        visual_concept = self.art_director.run(strategy)
        
        # Step 4: Review
        full_package = f"{draft_text}\n\n(Visual Concept: {visual_concept})"
        feedback = self.critic.run(full_package)
        
        print("\n✅ Workflow Complete. Preparing to Post...")
        
        # Step 5: Publish
        # We pass the text content to the LinkedIn Connector
        self.linkedin.post_content(draft_text)

if __name__ == "__main__":
    orch = Orchestrator()
    # Run without arguments to let the randomizer pick a topic
    orch.run_workflow()
