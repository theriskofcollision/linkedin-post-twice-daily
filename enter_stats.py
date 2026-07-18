"""
enter_stats.py — 5-minute weekly stats entry
=============================================
LinkedIn's free API cannot read engagement for personal profiles, so this is
the bot's ONLY real learning signal. Open linkedin.com/analytics (or each
post's "View analytics"), then run:

    python enter_stats.py

It walks through the last 7 days of posts from memory.json and asks only for
impressions (+ optional likes/comments). Press Enter to skip a post.
"""

import json
import sys
from datetime import datetime, timedelta

MEMORY_PATH = "memory.json"
FEEDBACK_PATH = "manual_feedback.json"


def main(days: int = 7) -> None:
    try:
        with open(MEMORY_PATH) as f:
            memory = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        sys.exit(f"Cannot read {MEMORY_PATH}: {e}")

    try:
        with open(FEEDBACK_PATH) as f:
            feedback = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        feedback = {"manual_stats": [], "feedback_notes": ""}

    # Drop the shipped template entry if still present
    feedback["manual_stats"] = [
        e for e in feedback.get("manual_stats", [])
        if "template" not in str(e.get("notes", "")).lower()
    ]
    already = {e.get("urn") for e in feedback["manual_stats"] if e.get("urn")}

    cutoff = datetime.utcnow() - timedelta(days=days)
    recent = []
    for p in memory.get("history", []):
        try:
            if datetime.fromisoformat(p["date"]) >= cutoff:
                recent.append(p)
        except (KeyError, ValueError):
            continue

    if not recent:
        sys.exit("No posts in the last 7 days found in memory.json.")

    print(f"\n{len(recent)} posts in the last {days} days. Enter impressions "
          f"from LinkedIn analytics (Enter = skip, q = quit & save).\n")

    added = 0
    for p in recent:
        if p.get("urn") in already:
            continue
        print(f"— {p['date'][:10]} · {p['vibe']} · {p['topic'][:60]}")
        raw = input("  impressions: ").strip()
        if raw.lower() == "q":
            break
        if not raw:
            continue
        try:
            impressions = int(raw)
        except ValueError:
            print("  (not a number, skipped)")
            continue
        likes = input("  likes (optional): ").strip()
        comments = input("  comments (optional): ").strip()
        feedback["manual_stats"].append({
            "urn": p.get("urn"),
            "date": p["date"][:10],
            "vibe": p["vibe"],
            "topic": p["topic"],
            "impressions": impressions,
            "likes": int(likes) if likes.isdigit() else 0,
            "comments": int(comments) if comments.isdigit() else 0,
        })
        added += 1

    note = input("\nWeekly observation (optional, e.g. 'short posts did better'): ").strip()
    if note:
        feedback["feedback_notes"] = note

    with open(FEEDBACK_PATH, "w") as f:
        json.dump(feedback, f, indent=2)
    print(f"\nSaved {added} new entries to {FEEDBACK_PATH}. "
          f"Commit and push so the bot can learn:\n"
          f"  git add {FEEDBACK_PATH} && git commit -m '📊 weekly stats' && git push")


if __name__ == "__main__":
    main()
