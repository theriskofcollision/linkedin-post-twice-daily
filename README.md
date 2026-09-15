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
    - `GROQ_API_KEY`: Groq API Key (used by the workflow; model is set in `config.yaml`, currently `llama-3.3-70b-versatile`).
    - `NEWS_API_KEY`: NewsAPI Key.
    - `TAVILY_API_KEY`: Tavily Search API Key.

> **Note:** Older docs mentioned `GEMINI_API_KEY`. The live GitHub Action expects **`GROQ_API_KEY`** only — do not set Gemini for this bot.

### 2. Schedule

The workflow runs **once daily** at **07:00 UTC** (10:00 Istanbul) via GitHub Actions. You can also trigger it manually from the Actions tab (`workflow_dispatch`).

## 📦 Dashboard

Run the command center locally to view analytics and comment packs:

```bash
python3 -m streamlit run dashboard.py
```
