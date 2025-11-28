# Phase 4 Implementation Plan: Multi-Source Intelligence & Analytics

## Goal
Expand the `TrendScout` agent's capabilities to gather intelligence from multiple high-quality sources (NewsAPI, arXiv, Tavily) and build a dashboard to track the performance of the LinkedIn bot.

## User Review Required
> [!IMPORTANT]
> **API Keys Required**: To implement these features, I will need the following API keys from you:
> - **NewsAPI Key**: Get it for free at [newsapi.org](https://newsapi.org/)
> - **Tavily API Key**: Get it for free at [tavily.com](https://tavily.com/)
>
> Please add these to your GitHub Secrets as `NEWS_API_KEY` and `TAVILY_API_KEY`.

## Proposed Changes

### 1. New Data Connectors (`linkedin_agents.py`)
We will create a modular connector system.

#### [NEW] `NewsAPIConnector`
- **Source**: NewsAPI (Top headlines from TechCrunch, Wired, etc.)
- **Function**: `get_tech_headlines(query="AI")`
- **Benefit**: High-credibility mainstream tech news.

#### [NEW] `ArxivConnector`
- **Source**: arXiv API (Academic papers)
- **Function**: `get_latest_papers(category="cs.AI")`
- **Benefit**: Deep technical insights and "thought leadership" material.

#### [NEW] `TavilyConnector`
- **Source**: Tavily (Agent-optimized search)
- **Function**: `search(query)`
- **Benefit**: Broad web search without the parsing issues of Google.

### 2. Research Manager (`linkedin_agents.py`)
- **Role**: Aggregates data from all connectors (HackerNews, NewsAPI, arXiv, Tavily).
- **Logic**:
    - Can be configured to use one or all sources.
    - Merges results into a comprehensive "Intelligence Brief" for the `TrendScout`.

### 3. Analytics & Dashboard (`dashboard.py`)
We will build a simple, interactive dashboard using **Streamlit**.

#### [NEW] `dashboard.py`
- **Framework**: Streamlit (Python-based, easy to deploy).
- **Features**:
    - **Recent Posts**: Display the last 5 posts with their status.
    - **Performance Metrics**: Likes, Comments, Views (fetched via `LinkedInConnector`).
    - **Memory Viewer**: Show the current rules in `memory.json`.
    - **Manual Trigger**: A button to run the bot manually from the dashboard.

#### [MODIFY] `LinkedInConnector`
- Add `get_post_stats(urn)` method to fetch engagement metrics.

## Verification Plan
### Automated Tests
- Run `linkedin_agents.py` with the new `ResearchManager` to verify data fetching from all sources.
- Run `streamlit run dashboard.py` locally to verify the dashboard UI.

### Manual Verification
- User checks the dashboard to see real-time stats.
