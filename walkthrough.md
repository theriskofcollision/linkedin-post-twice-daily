# LinkedIn Growth Workflow - Walkthrough

## Project Goal

Create an autonomous AI agent team that researches trends, strategizes, writes, creates visuals, and posts directly to LinkedIn.

## Architecture

- **Orchestrator**: Manages the flow.
- **ResearchManager**: Manages intelligence gathering (HackerNews, NewsAPI, arXiv, Tavily).
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
    1. Initialize Upload
    2. Upload Binary
    3. Create Post with Asset URN

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
    1. **The Contrarian** (Cyberpunk / Critical)
    2. **The Visionary** (Solarpunk / Inspiring)
    3. **The Educator** (Minimalist / Instructional)
    4. **The Analyst** (Data Viz / Professional)
- **Result**: Dynamic content tone and visual style for every run.

## Final Success

- **Date**: 2025-11-28
- **Status**: ✅ Fully Autonomous Success (Day 1)
- **Outcome**: The bot successfully researched "LLMs as Operating Systems" using **The Contrarian** persona. It fetched data from 4 sources, applied the new "Literary Structure" (Intro-Body-Conclusion), and posted to LinkedIn.
- **Link**: [View Post: LLMs as OS? Hold on...](https://www.linkedin.com/posts/hakan-k%C3%B6se-agentic-ai_llms-as-os-hold-on-its-more-like-a-fancy-activity-7400127039476756480-oGC7)
- **Improvements**: Upgraded to Python 3.10 to ensure long-term stability.

## Phase 6: Growth & Engagement (The "Growth Machine")

- **Analytics Feedback Loop**: The bot now learns from its own success.
  - `Memory` stores post history and engagement stats (Likes/Comments).
  - `Strategist` reads this data to double down on "winning" vibes.
- **The Networker Agent**: A new agent that drafts a "Comment Pack" for every run.
  - Generates 3 types of comments (Value Add, Contrarian, Question) for you to engage with other influencers.
  - Output is saved to `memory.json` and displayed on the Dashboard.

## Dashboard 📈

A real-time command center built with Streamlit.

- **URL**: [LinkedIn Growth Dashboard](https://linkedin-post-twice-daily-h9akrsza5xz5appdzxen99l.streamlit.app)
- **Features**:
  - **Comment Pack Viewer**: Copy-paste ready-to-use comments.
  - **Analytics**: View total likes, comments, and engagement trends.
  - **Vibe Check**: See which persona is performing best.
  - **Critic Rules**: See what the bot has learned.

## How to Run

1. Ensure `GEMINI_API_KEY`, `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_PERSON_URN`, `NEWS_API_KEY`, and `TAVILY_API_KEY` are set in GitHub Secrets.
2. The workflow runs automatically on schedule (09:00 UTC).
3. To run manually: Go to GitHub Actions -> "Run LinkedIn Workflow".
4. To view the Dashboard: Visit the [Streamlit App](https://linkedin-post-twice-daily-h9akrsza5xz5appdzxen99l.streamlit.app) or run `python3 -m streamlit run dashboard.py` locally.
