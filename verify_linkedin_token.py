#!/usr/bin/env python3
"""
verify_linkedin_token.py — LinkedIn Token & URN Diagnostic Verifier
===================================================================
Run this script to immediately test whether your LinkedIn access token is valid,
what scopes it possesses, and extract your exact Author Person URN.

Usage:
    # Option 1: Pass token directly as an argument
    python3 verify_linkedin_token.py "<YOUR_ACCESS_TOKEN>"

    # Option 2: Pass token and person URN
    python3 verify_linkedin_token.py "<YOUR_ACCESS_TOKEN>" "urn:li:person:<YOUR_ID>"

    # Option 3: Read from environment variables (LINKEDIN_ACCESS_TOKEN, LINKEDIN_PERSON_URN)
    python3 verify_linkedin_token.py
"""

import os
import sys
import json
import urllib.request
import urllib.error

def clean_value(val: str) -> str:
    if not val:
        return ""
    val = val.strip()
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        val = val[1:-1].strip()
    return val

def test_userinfo(token: str):
    print("=" * 65)
    print("🔍 STEP 1: Testing OpenID Connect Profile (/v2/userinfo)...")
    print("=" * 65)
    
    url = "https://api.linkedin.com/v2/userinfo"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "User-Agent": "LinkedInGrowthBotDiagnostics/1.0"
    })
    
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            body = resp.read().decode("utf-8")
            data = json.loads(body)
            
            sub = data.get("sub")
            name = data.get("name")
            email = data.get("email")
            
            print(f"✅ SUCCESS (HTTP {status})!")
            print(f"   👤 Member Name : {name}")
            print(f"   📧 Member Email: {email}")
            print(f"   🆔 Subject ID  : {sub}")
            urn = f"urn:li:person:{sub}"
            print(f"   🎯 Person URN  : {urn}\n")
            return urn, True
            
    except urllib.error.HTTPError as e:
        status = e.code
        err_body = e.read().decode("utf-8")
        print(f"❌ FAILED (HTTP {status})")
        print(f"   Response from LinkedIn: {err_body}\n")
        
        if status == 401:
            print("💡 Root-Cause Analysis for 401 Unauthorized:")
            print("   1. Token was not minted with 'openid', 'profile', and 'email' scopes.")
            print("   2. Token has expired (LinkedIn Developer Token Generator tokens expire after 60 days).")
            print("   3. Token was generated from an unverified app or without signing into the correct LinkedIn profile.")
        elif status == 403:
            print("💡 Root-Cause Analysis for 403 Forbidden:")
            print("   Your LinkedIn account is not added as a Team Member/Administrator under 'Auth > App Roles' on the app.")
        return None, False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return None, False

def test_post_permissions(token: str, urn: str):
    print("=" * 65)
    print("🔍 STEP 2: Testing Post Permissions via /rest/posts...")
    print("=" * 65)
    
    # We test with a dry payload or test post
    url = "https://api.linkedin.com/rest/posts"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": "202606"
    }
    
    # Preflight check with minimal commentary
    payload = {
        "author": urn,
        "commentary": "🤖 Diagnostic check for LinkedIn Growth Bot auth verification #test",
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED"
        },
        "lifecycleState": "PUBLISHED"
    }
    
    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=req_data, headers=headers, method="POST")
    
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            post_id = resp.headers.get("x-restli-id", "")
            print(f"✅ POSTING SUCCESS (HTTP {status})!")
            print(f"   🎉 Created test post with URN: {post_id}")
            print("   (You can delete this test post on your profile anytime)\n")
            return True
    except urllib.error.HTTPError as e:
        status = e.code
        err_body = e.read().decode("utf-8")
        print(f"❌ POSTING FAILED (HTTP {status})")
        print(f"   Response from LinkedIn: {err_body}\n")
        if status == 401 or status == 403:
            print("💡 Cause:")
            print("   Your token lacks the 'w_member_social' scope, or the app has not enabled 'Share on LinkedIn'.")
        elif status == 426:
            print("💡 Cause: LinkedIn-Version header is expired or unsupported.")
        return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

def main():
    token = ""
    urn = ""
    
    if len(sys.argv) > 1:
        token = sys.argv[1]
    if len(sys.argv) > 2:
        urn = sys.argv[2]
        
    if not token:
        token = os.environ.get("LINKEDIN_ACCESS_TOKEN", "")
    if not urn:
        urn = os.environ.get("LINKEDIN_PERSON_URN", "")
        
    token = clean_value(token)
    urn = clean_value(urn)
    
    print("\n🔍 LinkedIn Growth Bot — Token & URN Diagnostic Tool\n")
    
    if not token:
        print("⚠️ No token provided!")
        print("Please run:")
        print("    python3 verify_linkedin_token.py \"<YOUR_TOKEN_HERE>\"\n")
        print("Or set LINKEDIN_ACCESS_TOKEN in your environment.\n")
        sys.exit(1)
        
    print(f"Token (length {len(token)} chars): {token[:6]}...{token[-4:] if len(token) > 10 else ''}")
    if urn:
        print(f"Configured URN: {urn}")
    print()
    
    detected_urn, success = test_userinfo(token)
    
    final_urn = urn or detected_urn
    if success and final_urn:
        print("Would you like to test publishing permissions now? (y/n): ", end="", flush=True)
        try:
            choice = sys.stdin.readline().strip().lower()
            if choice == "y":
                test_post_permissions(token, final_urn)
        except Exception:
            pass
            
    print("=" * 65)
    print("📋 SUMMARY FOR GITHUB SECRETS:")
    print("=" * 65)
    if detected_urn or urn:
        print(f"LINKEDIN_PERSON_URN   : {detected_urn or urn}")
    print(f"LINKEDIN_ACCESS_TOKEN : {token[:8]}...[FULL_TOKEN_STRING]")
    print("\nUpdate them at: https://github.com/theriskofcollision/linkedin-post-twice-daily/settings/secrets/actions\n")

if __name__ == "__main__":
    main()
