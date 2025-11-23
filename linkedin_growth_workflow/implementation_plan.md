# LinkedIn Growth Workflow Design

## Goal
Increase LinkedIn followers for [Hakan Köse](https://www.linkedin.com/in/hakan-köse-agentic-ai) by creating high-quality, trend-aware, and persona-aligned content using a multi-agent AI system.

## User Review Required
- **Agent Personas**: Review the proposed roles and tones for each agent.
- **Workflow Steps**: Confirm the sequence of operations.

## Proposed Workflow
1.  **Trend Research**: Identify high-potential topics.
2.  **Strategy & Hook**: Align topic with "Agentic AI" persona and define the angle.
3.  **Content Creation**: Write the post (text).
4.  **Visual Creation**: Generate image/video concepts.
5.  **Review & Refine**: Polish content.

## Agent Roster
| Agent Name | Role | Key Responsibility |
| :--- | :--- | :--- |
| **Orchestrator** | Manager | Coordinates the flow, passes data between agents. |
| **TrendScout** | Researcher | Finds trending AI/Tech news and viral LinkedIn posts. |
| **Strategist** | Planner | Decides *why* we are posting this and *who* it is for. |
| **Ghostwriter** | Writer | Crafts the actual post copy in Hakan's voice. |
| **ArtDirector** | Visuals | Creates prompts for Midjourney/DALL-E or suggests charts. |
| **Critic** | Quality Control | Reviews against best practices (hooks, readability, viral potential). |

## Implementation Steps
### Phase 1: Definition
- Create `agents.md` defining the system prompt for each agent.
- Create `workflow_graph.md` (mermaid) showing the data flow.

### Phase 2: Cloud Automation (GitHub Actions)
- **GitHub Actions Workflow**: Create `.github/workflows/linkedin_scheduler.yml` to run the script on a schedule (cron: '0 9,17 * * *').
- **Secrets Management**: Use GitHub Secrets for `LINKEDIN_ACCESS_TOKEN` and `LINKEDIN_PERSON_URN`.
- **Python Script Adaptation**: Ensure `linkedin_agents.py` runs in a headless environment (install dependencies via `requirements.txt`).

### Phase 3: Future Improvements
- Web UI (Streamlit on Cloud) for manual approval.
- Database for history tracking.

## Verification Plan
### Manual Verification
- Run a "Tabletop Exercise": Manually simulate the agents for one topic (e.g., "The future of coding is agentic").
- Output: One ready-to-publish LinkedIn post.
