# LinkedIn Growth Workflow Tasks

- [ ] Design the Workflow
    - [x] Define Agent Roles and Responsibilities <!-- id: 0 -->
    - [x] Define Data Flow between Agents <!-- id: 1 -->
    - [x] Create `agents.md` with detailed prompts/personas <!-- id: 2 -->
- [ ] Implement the Workflow
    - [x] Create Python script for orchestration (if automated) or Manual Process Doc <!-- id: 3 -->
    - [x] Test the workflow with a sample topic <!-- id: 4 -->
    - [x] Implement `LinkedInConnector` class <!-- id: 6 -->
    - [x] Create `requirements.txt` for dependencies <!-- id: 9 -->
    - [x] Create `.github/workflows/linkedin_scheduler.yml` <!-- id: 7 -->
- [x] Verification
    - [x] Generate one complete post package (Text + Image Prompt) <!-- id: 5 -->
    - [x] Integrate Gemini LLM for real content generation <!-- id: 11 -->
    - [x] Obtain LinkedIn API Credentials <!-- id: 10 -->
    - [x] Verify API connection (Dry Run via GitHub Actions) <!-- id: 8 -->

## Phase 2: Quality & Visuals
- [x] Improve Content Quality (The "Critic" & "Variety Engine") <!-- id: 12 -->
- [x] Implement Image Generation (Gemini/External) <!-- id: 13 -->
- [x] Upgrade LinkedIn Connector for Image Uploads <!-- id: 14 -->

## Phase 3: Intelligence & Self-Improvement
- [x] Enable HackerNews API for TrendScout (Replaces Google Search) <!-- id: 15 -->
- [x] Implement Memory System (memory.json) <!-- id: 16 -->
- [x] Connect Critic Feedback to Memory <!-- id: 17 -->

## Phase 4: Multi-Source Intelligence & Analytics
- [x] Implement NewsAPI Connector (The "News Junkie") <!-- id: 18 -->
- [x] Implement arXiv API Connector (The "Academic") <!-- id: 19 -->
- [x] Implement Tavily API Connector (The "Agent-Native") <!-- id: 20 -->
- [x] Create `ResearchManager` to aggregate data sources <!-- id: 21 -->
- [ ] Implement `AnalyticsConnector` to fetch LinkedIn post stats <!-- id: 22 -->
- [x] Build Performance Dashboard (Streamlit/Web) <!-- id: 23 -->

## Phase 5: Long-term Monitoring & Refinement
- [/] Monitor bot performance for 3-5 days (Day 1 Success: "The Contrarian") <!-- id: 24 -->
- [x] Review "Variety Engine" output for consistency <!-- id: 25 -->
- [x] Improve post structure with Introduction-Body-Conclusion format <!-- id: 27 -->
- [x] Add "The Narrator" persona (Dickensian Style) <!-- id: 29 -->
- [x] Upgrade GitHub Actions to Python 3.10+ to fix warnings <!-- id: 28 -->

## Phase 6: Growth & Engagement (The "Growth Machine")
- [x] Implement `AnalyticsConnector` (Real Feedback Loop) <!-- id: 30 -->
- [x] Update `Memory` to store "Winning" & "Losing" strategies <!-- id: 31 -->
- [x] Update `Strategist` to use performance data <!-- id: 32 -->
- [x] Create `Networker` Agent for comment drafting (Comment Pack Strategy) <!-- id: 33 -->
- [x] Refactor `TrendScout` into `ResearchManager` (Optional) <!-- id: 26 -->
