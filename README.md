# LinkedIn Growth Workflow 🚀

This repository contains an automated agentic workflow to generate and schedule LinkedIn posts using GitHub Actions.

## 🤖 Agents

- **ResearchManager**: Aggregates intelligence from HackerNews, NewsAPI, arXiv, and Tavily.
- **Strategist**: Aligns topics with your personal brand using 5 distinct personas.
- **Ghostwriter**: Writes viral content with a literary structure.
- **ArtDirector**: Creates distinct visual concepts (Brutalist, Watercolor, etc.).
- **ImageGenerator**: Generates images via Pollinations.ai.
- **Critic**: Reviews content and saves rules to `memory.json`.
- **Networker**: Generates a "Comment Pack" for community engagement.

## 🛠 Setup

### 1. Secrets

To enable the automation, you must add the following **Secrets** to your GitHub Repository:

1. Go to **Settings** > **Secrets and variables** > **Actions**.
2. Click **New repository secret**.
3. Add:
    - `LINKEDIN_ACCESS_TOKEN`: Your OAuth 2.0 Access Token.
    - `LINKEDIN_PERSON_URN`: Your LinkedIn ID.
    - `GEMINI_API_KEY`: Google Gemini API Key.
    - `NEWS_API_KEY`: NewsAPI Key.
    - `TAVILY_API_KEY`: Tavily Search API Key.

### 2. Schedule

The workflow runs twice daily (09:00 & 17:00 UTC) via GitHub Actions.

## 📦 Dashboard

Run the command center locally to view analytics and comment packs:

```bash
python3 -m streamlit run dashboard.py
```
