# LinkedIn Growth Workflow - Walkthrough

## Project Goal
Create an autonomous AI agent team that researches trends, strategizes, writes, creates visuals, and posts directly to LinkedIn.

## Architecture
- **Orchestrator**: Manages the flow.
- **TrendScout**: Finds hot topics using **HackerNews API** (Real-time data).
- **Strategist**: Defines the angle/hook.
- **Ghostwriter**: Writes the post (with Memory of past feedback).
- **ArtDirector**: Creates image prompts.
- **ImageGenerator**: Generates images via Pollinations.ai.
- **Critic**: Reviews content and saves rules to `memory.json`.
- **LinkedInConnector**: Handles API authentication and posting.

## Key Features Implemented

### 1. Real-Time Grounding (HackerNews)
- Replaced Google Search with **HackerNews API**.
- Fetches top stories from the last 24 hours.
- Filters for AI/LLM keywords to ensure relevance.
- **Benefit**: Free, reliable, and highly relevant for tech audiences.

### 2. Visuals & Uploads
- **Image Generation**: Uses Pollinations.ai (No API key required).
- **LinkedIn Uploads**: Implemented the 3-step `rest/images` protocol:
    1.  Initialize Upload
    2.  Upload Binary
    3.  Create Post with Asset URN

### 3. Intelligence & Robustness
- **Memory System**: `memory.json` stores "Rules" from the Critic (e.g., "Don't use the word 'delve'").
- **Retry Mechanism**: Implemented exponential backoff for Gemini API `429 Resource exhausted` errors.
    - Retries up to 3 times.
    - Prevents "visual-only" posts when the LLM is busy.

## Phase 4: Multi-Source Intelligence & Analytics (Completed)
- **NewsAPI ("The News Junkie")**: Fetches mainstream tech headlines (TechCrunch, Wired, etc.).
- **arXiv API ("The Academic")**: Retrieves the latest AI research papers.
- **Tavily API ("The Agent-Native")**: Performs deep-dive web searches for context.
- **Tavily API ("The Agent-Native")**: Performs deep-dive web searches for context.
- **Performance Dashboard**: A Streamlit web app to track bot activity and "Critic" rules.

### 4. The "Variety Engine" 🎲
- **Problem**: Bot content became repetitive (same tone, same visuals).
- **Solution**: Implemented a randomized "Vibe" selector that rotates between 4 personas:
    1.  **The Contrarian** (Cyberpunk / Critical)
    2.  **The Visionary** (Solarpunk / Inspiring)
    3.  **The Educator** (Minimalist / Instructional)
    4.  **The Analyst** (Data Viz / Professional)
- **Result**: Dynamic content tone and visual style for every run.

## Final Success
- **Date**: 2025-11-24
- **Status**: ✅ Fully Autonomous Success
- **Outcome**: The bot successfully researched a topic using **4 different intelligence sources**, generated a contrarian post, created a visual, and posted it to LinkedIn.
- **Link**: [View Final Post](https://www.linkedin.com/posts/hakan-k%C3%B6se-agentic-ai_multi-agent-ai-shiny-distracting-maybe-activity-7398842062307028992-gqaZ)

## How to Run
1.  Ensure `GEMINI_API_KEY`, `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_PERSON_URN`, `NEWS_API_KEY`, and `TAVILY_API_KEY` are set in GitHub Secrets.
2.  The workflow runs automatically on schedule (09:00 UTC).
3.  To run manually: Go to GitHub Actions -> "Run LinkedIn Workflow".
4.  To view the Dashboard: Run `streamlit run dashboard.py` locally (or in Codespaces).
