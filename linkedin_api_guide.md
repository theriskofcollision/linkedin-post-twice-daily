# How to Get Your LinkedIn API Tokens

To allow the bot to post for you, you need to create a "App" on LinkedIn. It’s free and takes about 5 minutes.

## Step 1: Create a LinkedIn App
1.  Go to the [LinkedIn Developer Portal](https://www.linkedin.com/developers/apps/new).
2.  **App Name**: Enter something like "Hakan Growth Bot".
3.  **LinkedIn Page**: You must link it to a LinkedIn Page.
    *   *Tip*: If you don't have a Company Page, create a dummy one (e.g., "Hakan's Lab") just for this purpose. You cannot link a personal profile directly here, but the bot *will* be able to post to your personal profile later.
4.  **Privacy Policy URL**: You can use `http://example.com` if you don't have one.
5.  Upload a logo (any image works).
6.  Check the "Legal" box and click **Create App**.

## Step 2: Request Permissions
1.  Once the app is created, go to the **Products** tab.
2.  Find **"Share on LinkedIn"** and click **Request Access**.
3.  It might ask you to verify the Page. Follow the link to verify it.

## Step 3: Get Your User URN (`LINKEDIN_PERSON_URN`)
1.  Go to the [LinkedIn Token Generator](https://www.linkedin.com/developers/tools/oauth/token-generator).
2.  Select your App.
3.  Check the scope **`w_member_social`** (this allows posting).
4.  Click **Request Access Token**.
5.  Log in with your LinkedIn account.
6.  **COPY THE ACCESS TOKEN**. This is your `LINKEDIN_ACCESS_TOKEN`.
    *   *Note*: This token lasts for 60 days. You will need to refresh it manually every 2 months.
7.  **Find your URN**:
    *   Look at the "Response" box on the right side of the Token Generator.
    *   Look for the field `"sub": "urn:li:person:..."` or `"id": "..."`.
    *   If you can't see it, open your terminal and run this command (replace `YOUR_ACCESS_TOKEN` with the long token you just copied):
        ```bash
        curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" https://api.linkedin.com/v2/me
        ```
    *   The output will look like: `{"id":"12345abcde", ...}`.
    *   Your URN is `urn:li:person:12345abcde` (append `urn:li:person:` to the ID).

## Step 4: Add to GitHub
1.  Go back to your GitHub Repo > Settings > Secrets > Actions.
2.  Add `LINKEDIN_ACCESS_TOKEN` and `LINKEDIN_PERSON_URN`.
