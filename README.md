# LinkedIn Growth Workflow 🚀

This repository contains an automated agentic workflow to generate and schedule LinkedIn posts using GitHub Actions.

## 🤖 Agents
- **TrendScout**: Finds trending topics in AI.
- **Strategist**: Aligns topics with your personal brand.
- **Ghostwriter**: Writes the post content.
- **ArtDirector**: Creates visual concepts.
- **Critic**: Reviews and approves content.

## 🛠 Setup

### 1. Secrets
To enable the automation, you must add the following **Secrets** to your GitHub Repository:
1.  Go to **Settings** > **Secrets and variables** > **Actions**.
2.  Click **New repository secret**.
3.  Add:
    - `LINKEDIN_ACCESS_TOKEN`: Your OAuth 2.0 Access Token.
    - `LINKEDIN_PERSON_URN`: Your LinkedIn ID (e.g., `urn:li:person:12345`).

### 2. Schedule
The workflow is configured in `.github/workflows/linkedin_scheduler.yml` to run twice daily:
- **09:00 UTC**
- **17:00 UTC**

You can also trigger it manually from the **Actions** tab.

## 📦 Local Development
1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
2.  Run the script:
    ```bash
    python linkedin_agents.py
    ```
