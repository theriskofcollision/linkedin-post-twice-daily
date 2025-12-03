# Phase 6: Growth & Engagement Plan 🚀

## Goal
Shift from "Content Factory" (Output) to "Growth Machine" (Outcome). The goal is to maximize follower growth by optimizing content based on data and increasing visibility through engagement.

## The Problem
Currently, the bot is a "Fire and Forget" system. It posts and moves on. It doesn't know if a post got 1 view or 10,000 views. It also doesn't interact with the community, which is 50% of LinkedIn growth.

## Proposed Features

### 1. The Feedback Loop (Real Analytics) 📊
**"Don't just guess, learn."**
- **Feature**: Implement `AnalyticsConnector` to fetch *real* views, likes, and comments from LinkedIn API.
- **Logic**: 
    - Every 24 hours, check stats of the last 5 posts.
    - If a post > 1000 views, save its "Topic" and "Vibe" to `memory.json` as a "WINNER".
    - If a post < 50 views, save as "LOSER".
    - `Strategist` reads this memory to double down on winning topics/vibes.

### 2. The "Networker" Agent (Comment Drafting) 🤝
**"Visibility comes from comments, not just posts."**
- **Feature**: A new agent that scans top posts from specific influencers (e.g., Andrew Ng, Yann LeCun).
- **Action**: It reads the post and drafts a *high-value, contrarian, or insightful* comment.
- **Safety**: It does NOT auto-post (risky). It sends the draft to you (via email/log/dashboard) to copy-paste.
- **Why**: Commenting on viral posts captures their traffic.

### 3. The "Viral Hook" Library 🪝
**"Stop the scroll."**
- **Feature**: Upgrade `Ghostwriter` with a database of proven viral hooks (e.g., "I analyzed X...", "Unpopular opinion:...", "Here is the cheat sheet...").
- **Integration**: The `Variety Engine` will pick a "Viral Structure" in addition to a "Vibe".

## Implementation Steps
1.  [ ] **Upgrade LinkedIn Scope**: Verify if our current token allows reading Analytics (`r_organization_social` or similar).
2.  [ ] **Build `AnalyticsConnector`**: Replace mock data with real API calls.
3.  [ ] **Update `Memory`**: Add logic to store and retrieve "Performance Data".
4.  [ ] **Create `Networker` Agent**: (Optional - requires more complex API permissions to read *other* people's posts, might need to use a scraper or just stick to Analytics first).

## Recommendation
Start with **Step 1 (Analytics Feedback Loop)**. It makes the bot "smart" about what your audience actually likes.
