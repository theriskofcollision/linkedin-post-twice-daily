# LinkedIn Developer Auth Runbook (2026 Strict Guide)

> **Purpose**: Step-by-step operational runbook to configure the LinkedIn Developer App, mint a working OAuth 2.0 token, resolve the `INVALID_ACCESS_TOKEN` error, fetch the personal author URN, configure GitHub Secrets, and run a successful test publish.  
> **Target Audience**: Grok Bot / Lead Developer  
> **Security Mandate**: Never paste real tokens or secrets into this file, issue logs, or git commits.

---

## Phase 1: App Audit & Prerequisite Configuration

LinkedIn's OAuth 2.0 gateway enforces product verification before allowing API calls. Between your two existing apps ("hakan growth bot" and "github 1"), use **"github 1"**.

### Step 1.1: Open App in LinkedIn Developer Portal
1. Navigate to: [https://www.linkedin.com/developers/apps](https://www.linkedin.com/developers/apps).
2. Select application **"github 1"**.

### Step 1.2: Verify Company Page Association
1. Go to **Settings** &rarr; **Company Page Association**.
2. **Status Check**:
   - If status says **"Verified"**: Proceed to Step 1.3.
   - If status says **"Pending Verification"** or **"Action Required"**:
     1. Click **Verify URL** or **Request verification**.
     2. Copy the generated verification link.
     3. Open the link in a browser where you are logged in as the **Administrator of that Company Page**.
     4. Click **Approve**.
3. **App Settings Health**:
   - Ensure a valid Business Email is saved.
   - Ensure Privacy Policy URL is set to a live URL (e.g. `https://hakankose.com/privacy` or a valid public markdown URL, not a generic placeholder).

### Step 1.3: Enable the Two Required Products
Go to the **Products** tab and verify the following:
1. **Share on LinkedIn**:
   - Required for: `w_member_social` (enables posting to personal profile).
   - Status must show: **Added** (green badge).
2. **Sign In with LinkedIn using OpenID Connect**:
   - Required for: `openid`, `profile`, `email` (enables member identification and user profile resolution).
   - Status must show: **Added** (green badge).

> [!IMPORTANT]
> Do NOT use "hakan growth bot" because it lacks OpenID Connect (OIDC). Without OIDC, calling `/v2/userinfo` fails, making it impossible to resolve your Member URN programmatically.

### Step 1.4: Confirm App Team Member Roles
1. Go to **Auth** &rarr; **App Roles** (or **Developer Settings**).
2. Ensure your personal LinkedIn account (the one you want to post from) is assigned as an **Administrator** or **Developer**.
3. In LinkedIn's "Development" app tier, only explicitly registered team members can authenticate and publish.

---

## Phase 2: Mint a Valid Token (Token Generator)

1. Open the [LinkedIn OAuth Token Generator](https://www.linkedin.com/developers/tools/oauth/token-generator).
2. In the **Application** dropdown, select **`github 1`**.
3. **Select Scopes (Check ALL 4)**:
   - [x] `openid`
   - [x] `profile`
   - [x] `email`
   - [x] `w_member_social`
4. Click **Request Access Token**.
5. When the LinkedIn authorization dialog appears:
   - Confirm you are logged in as Hakan Köse.
   - Click **Allow** to grant permissions to "github 1".
6. In the modal that displays your token:
   - Click the copy button.
   - **Important**: Paste it temporarily into a clean scratch text file without quotes or trailing newlines. This token is valid for **60 days**.

---

## Phase 3: Validate Token & Fetch Person URN in Terminal

Before updating GitHub Secrets, verify the token locally via terminal.

### Step 3.1: Export Token in Your Local Shell
```bash
# Export token cleanly (replace <YOUR_MINTED_TOKEN> with actual token string)
export LINKEDIN_ACCESS_TOKEN="<YOUR_MINTED_TOKEN>"
```

### Step 3.2: Fetch User Info via OpenID Connect
> [!WARNING]
> Do **NOT** call `https://api.linkedin.com/v2/me`! In 2026, `/v2/me` is deprecated for modern OIDC apps and permanently returns `401 Unauthorized: INVALID_ACCESS_TOKEN`. You must use `/v2/userinfo`.

Run:
```bash
curl -s -X GET "https://api.linkedin.com/v2/userinfo" \
  -H "Authorization: Bearer $LINKEDIN_ACCESS_TOKEN"
```

**Expected JSON Response (HTTP 200)**:
```json
{
  "sub": "7ABCde123X",
  "name": "Hakan Köse",
  "given_name": "Hakan",
  "family_name": "Köse",
  "picture": "https://media.licdn.com/dms/image/...",
  "email": "your_email@example.com"
}
```

### Step 3.3: Construct Author Person URN
- Read the string value from the `"sub"` field (e.g. `7ABCde123X`).
- Construct the Person URN:
  ```text
  urn:li:person:7ABCde123X
  ```
- Export it for verification:
  ```bash
  export LINKEDIN_PERSON_URN="urn:li:person:7ABCde123X"
  ```

### Step 3.4: Test Personal Post Permission (Dry-Run / Verification)
Test publishing permissions directly using LinkedIn's REST API:
```bash
curl -s -X POST "https://api.linkedin.com/rest/posts" \
  -H "Authorization: Bearer $LINKEDIN_ACCESS_TOKEN" \
  -H "LinkedIn-Version: 202606" \
  -H "X-Restli-Protocol-Version: 2.0.0" \
  -H "Content-Type: application/json" \
  -d '{
    "author": "'"$LINKEDIN_PERSON_URN"'",
    "commentary": "Diagnostics test from automated growth engine #AI",
    "visibility": "PUBLIC",
    "distribution": {
      "feedDistribution": "MAIN_FEED",
      "targetEntities": [],
      "thirdPartyDistributionChannels": []
    },
    "lifecycleState": "PUBLISHED",
    "isReshareDisabledByAuthor": false
  }'
```
- **Success status**: `201 Created` with header `x-restli-id: urn:li:share:...` or `urn:li:restPost:...`.
- (You can delete this test post immediately from your LinkedIn profile).

---

## Phase 4: Configure GitHub Actions Secrets

1. Navigate to your GitHub repository:
   `https://github.com/theriskofcollision/linkedin-post-twice-daily/settings/secrets/actions`
2. Create or update the following secrets:

| Secret Name | Exact Value To Enter |
|---|---|
| `LINKEDIN_ACCESS_TOKEN` | The 60-day token minted in Phase 2 |
| `LINKEDIN_PERSON_URN` | The Person URN from Phase 3 (`urn:li:person:{sub}`) |
| `GROQ_API_KEY` | Your active Groq API Key (`gsk_...`) |

*(Leave `NEWS_API_KEY` and `TAVILY_API_KEY` as-is if already populated).*

---

## Phase 5: Code & Schedule Alignment

Ensure repository configuration files reflect recent infrastructure updates:

### 5.1: Model Update in `config.yaml`
Because `llama-3.3-70b-versatile` was retired on Groq developer tiers in August 2026, update lines 5-6 in [config.yaml](file:///Users/hakankose/Documents/linkedin_growth_workflow/config.yaml):
```yaml
model:
  name: "openai/gpt-oss-120b"
  max_retries: 3
  base_delay_seconds: 5
```

### 5.2: Schedule Update in `.github/workflows/linkedin_scheduler.yml`
To run once daily at **07:00 UTC** (10:00 Istanbul), update line 7:
```yaml
on:
  schedule:
    - cron: '0 7 * * *'
  workflow_dispatch:
```

### 5.3: LinkedIn Connector Compatibility in `linkedin_agents.py`
In [linkedin_agents.py](file:///Users/hakankose/Documents/linkedin_growth_workflow/linkedin_agents.py#L1203), `LinkedInConnector` uses:
- `v2/assets?action=registerUpload` (L1169)
- `v2/ugcPosts` (L1219)

If the new token still returns 401 on `v2/ugcPosts` because LinkedIn deprecated v2 for newly minted 2026 tokens, update `LinkedInConnector` to use the `/rest/` endpoints:
```python
# Modern REST endpoints
url_post = "https://api.linkedin.com/rest/posts"
headers = {
    "Authorization": f"Bearer {self.access_token}",
    "Content-Type": "application/json",
    "X-Restli-Protocol-Version": "2.0.0",
    "LinkedIn-Version": "202606"
}
```

---

## Phase 6: Execute Manual Run via `workflow_dispatch`

1. Go to your GitHub repository **Actions** tab.
2. Under "All workflows", click **LinkedIn Growth Bot**.
3. Click the **Run workflow** dropdown on the right:
   - Branch: `main`
   - Click **Run workflow**.
4. Click on the running job `run-bot`.

### What Success Looks Like in GitHub Actions Logs

```text
============================= FLIGHT CHECK =============================
🚀 Starting LinkedIn Growth Workflow
Using model: openai/gpt-oss-120b
🎲 Vibe Selected: The Contrarian
📋 Format Selected: Story
🔍 Researching & Conceptualizing: Multi-Agent Systems and how they actually work
✍️ Drafting Post...
🎨 Designing Visuals...
🤖 Generating AI Visual...
Step 1/2: Registering image upload...
Step 2/2: Uploading image binary...
✅ Image uploaded to LinkedIn server.
✅ Preparing to Post...
✅ Successfully posted to LinkedIn! Status: 201
🆔 New Post URN: urn:li:share:7465...
🧠 Update bot memory [skip ci]
✅ Script completed successfully.
========================================================================
```

---

## Phase 7: Diagnostic & Troubleshooting Matrix

| Error Symptom | Exact Root Cause | Immediate Remediation |
|---|---|---|
| `401 Unauthorized` / `INVALID_ACCESS_TOKEN` on `/v2/me` | Calling deprecated legacy endpoint | Replace `/v2/me` with `https://api.linkedin.com/v2/userinfo`. |
| `401 Unauthorized` on `/v2/userinfo` | Token minted without `openid` scope | Re-mint token in Token Generator with `openid`, `profile`, `email` checked. |
| `403 Forbidden` / `ACCESS_DENIED` on `/rest/posts` | Missing `w_member_social` scope | Re-mint token with `w_member_social` checked. |
| `401 Unauthorized` / `426 Upgrade Required` on `/rest/posts` | Missing or outdated `LinkedIn-Version` header | Pass `-H "LinkedIn-Version: 202606"` and `-H "X-Restli-Protocol-Version: 2.0.0"`. |
| `403 Forbidden` on personal publish | App company page association unverified | Go to Developer Portal Settings and approve the Company Page association URL. |
| `403 Forbidden` ("Not a team member") | User not added to App Roles | Add Hakan's LinkedIn account under **Auth > App Roles** as Administrator. |
| `Groq API Error: model_retired` | Using `llama-3.3-70b-versatile` | Update `config.yaml` to `openai/gpt-oss-120b`. |
| Token expired after 60 days | Developer tokens expire every 60 days | Mint fresh token from Token Generator and paste into GitHub Secret `LINKEDIN_ACCESS_TOKEN`. |
