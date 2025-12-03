# Project Handover: LinkedIn Growth Machine 🚀

## 1. Project Overview

This is an autonomous AI agent system that researches, strategizes, creates, and posts content to LinkedIn. It also engages with the community via a "Networker" agent and tracks performance via a Streamlit dashboard.

## 2. Current Architecture

* **Orchestrator**: Main controller (`linkedin_agents.py`).
* **ResearchManager** (formerly TrendScout): Aggregates data from HackerNews, NewsAPI, arXiv, and Tavily.
* **Strategist**: Determines the angle based on "Vibes" (Personas).
* **Ghostwriter**: Writes content using a literary structure.
* **ArtDirector & ImageGenerator**: Creates visuals (Pollinations.ai).
* **Critic**: Reviews content and saves rules to `memory.json`.
* **Networker**: Generates a "Comment Pack" for engagement.
* **LinkedInConnector**: Handles posting and stats retrieval.

## 3. Key Files

* `linkedin_agents.py`: Core logic and agent definitions.
* `dashboard.py`: Streamlit command center for analytics and tools.
* `memory.json`: Persistent storage for history, stats, and learned rules.
* `.github/workflows/linkedin_scheduler.yml`: Automation workflow (runs 09:00 & 17:00 UTC).
* `task.md`: Project roadmap and status.

## 4. Environment Variables (GitHub Secrets)

* `LINKEDIN_ACCESS_TOKEN`
* `LINKEDIN_PERSON_URN`
* `GEMINI_API_KEY`
* `NEWS_API_KEY`
* `TAVILY_API_KEY`

## 5. Recent Changes (Phase 6)

* **Refactor**: `TrendScout` -> `ResearchManager`.
* **Feature**: Added `Networker` agent for comment generation.
* **Feature**: Built `dashboard.py` with real-time analytics from `memory.json`.
* **Fix**: Resolved GitHub Actions permission issues for saving memory.

## 6. Next Steps / Known Issues

* **Monitoring**: Watch the bot's performance over the next few days.
* **Dashboard**: Currently runs locally or needs deployment to Streamlit Cloud.
* **Future**: Consider adding a "Deep Dive" mode or cross-posting to X/Twitter.

## 7. How to Run

* **Bot**: Runs automatically via GitHub Actions. Manual trigger available in Actions tab.
* **Dashboard**: `python3 -m streamlit run dashboard.py` locally.
