# How to Get Your LinkedIn API Tokens

To allow the bot to post for you, you need to create a "App" on LinkedIn.

## Step 1: Create a LinkedIn App

1. Go to the [LinkedIn Developer Portal](https://www.linkedin.com/developers/apps/new).
2. **App Name**: Enter something like "Hakan Growth Bot".
3. **LinkedIn Page**: You must link it to a LinkedIn Page.
    * *Tip*: If you don't have a Company Page, create a dummy one (e.g., "Hakan's Lab") just for this purpose.
4. **Privacy Policy URL**: `http://example.com` (if you don't have one).
5. Upload a logo.
6. Check "Legal" and click **Create App**.

## Step 2: Choose Your Path

LinkedIn has recently restricted access to **Personal Profile Stats** (`r_member_social`). This means you have two choices:

### Option A: Personal Profile (Easiest, but No "Healer")

* **Pros**: Posts directly to your personal profile.
* **Cons**: The bot **CANNOT** read likes/comments. The "Healer" (self-improvement) function will be disabled.
* **Permissions Needed**: `w_member_social` (from "Share on LinkedIn").

### Option B: Company Page (Full Power)

* **Pros**: The bot **CAN** read likes/comments. The "Healer" works fully.
* **Cons**: Posts to a Company Page (e.g., "Hakan's Newsletter") instead of your personal profile.
* **Permissions Needed**: `w_organization_social` and `r_organization_social` (from "Community Management API").

---

## Step 3: Request Permissions

### For Option A (Personal)

1. Go to **Products** tab.
2. Request **"Share on LinkedIn"**.
3. That's it. You can't get stats permissions currently.

### For Option B (Company Page)

1. Go to **Products** tab.
2. Request **"Community Management API"** (It should be in your "Available products" list).
3. Fill out the form (Reason: "Managing my company page community").
4. Once approved, you get `w_organization_social` and `r_organization_social`.

---

## Step 4: Get Your Access Token

1. Go to the [LinkedIn Token Generator](https://www.linkedin.com/developers/tools/oauth/token-generator).
2. Select your App.
3. **Select Scopes**:
    * **Option A**: Check `w_member_social`, `email`, `openid`, `profile`.
    * **Option B**: Check `w_organization_social`, `r_organization_social`, `email`, `openid`, `profile`.
4. Click **Request Access Token**.
5. Log in.
6. **COPY THE ACCESS TOKEN**.

## Step 5: Get Your URN

### For Option A (Personal)

1. Run this in terminal:

    ```bash
    curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" https://api.linkedin.com/v2/me
    ```

2. Your URN is `urn:li:person:ID` (e.g., `urn:li:person:12345`).

### For Option B (Company Page)

1. Go to your Company Page on LinkedIn.com.
2. Look at the URL: `https://www.linkedin.com/company/12345678/`
3. Your URN is `urn:li:organization:12345678`.

## Step 6: Update GitHub Secrets

1. Update `LINKEDIN_ACCESS_TOKEN`.
2. Update `LINKEDIN_PERSON_URN` (with either the Person URN or Organization URN).
