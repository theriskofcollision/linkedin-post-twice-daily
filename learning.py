"""
learning.py — Self-learning layer for linkedin-post-twice-daily
================================================================
Three components:

1. RuleManager   — caps the Critic's rule list (FIFO) and distills it weekly
                   into a small set of principles via LLM.
2. VibeBandit    — epsilon-greedy selection over vibes using REAL performance
                   data (impressions from manual_feedback.json). Falls back to
                   uniform random when no data exists.
3. Reflector     — weekly reflection: reads last 7 days of posts + manual
                   stats, writes WEEKLY_BRIEF.md containing (a) a performance
                   memo, (b) the latest comment packs so the human can actually
                   use them, (c) a daily manual-action checklist.

Design constraint (important): LinkedIn's free API product is write-only
(w_member_social). Engagement stats CANNOT be fetched programmatically for a
personal profile. The only reliable reward signal is manual weekly entry via
enter_stats.py. This module is built around that reality — the bot learns
from whatever signal the human provides, and degrades gracefully to
exploration when there is none.
"""

import json
import os
import random
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger("linkedin_bot.learning")

MEMORY_PATH = "memory.json"
FEEDBACK_PATH = "manual_feedback.json"
BRIEF_PATH = "WEEKLY_BRIEF.md"

MAX_RULES = 25          # hard FIFO cap on raw Critic rules
DISTILLED_MAX = 12      # target size after weekly distillation
EPSILON = 0.30          # exploration rate for the bandit
MIN_OBSERVATIONS = 3    # per-vibe observations before we trust its mean


# ----------------------------------------------------------------------------
# 1. RuleManager
# ----------------------------------------------------------------------------

class RuleManager:
    """Keeps the Critic's rule list bounded and periodically distilled."""

    def __init__(self, memory):
        # `memory` is the existing Memory instance from linkedin_agents.py
        self.memory = memory

    def add_rule_capped(self, rule: str) -> None:
        """FIFO-capped replacement for Memory.add_rule()."""
        with self.memory.lock:
            data = self.memory._load()
            rules = data.get("rules", [])
            if rule in rules:
                return
            rules.append(rule)
            if len(rules) > MAX_RULES:
                evicted = rules[: len(rules) - MAX_RULES]
                rules = rules[-MAX_RULES:]
                logger.info(f"🧹 Rule cap: evicted {len(evicted)} oldest rule(s)")
            data["rules"] = rules
            self.memory._save(data)
            logger.info(f"🧠 Rule added ({len(rules)}/{MAX_RULES}): '{rule[:80]}'")

    def distill(self, agent_cls) -> Optional[List[str]]:
        """Compress current rules into <= DISTILLED_MAX principles via LLM.

        `agent_cls` is the Agent class from linkedin_agents.py (passed in to
        avoid a circular import).
        """
        rules = self.memory.get_rules()
        if len(rules) <= DISTILLED_MAX:
            logger.info("Distillation skipped: rule list already compact.")
            return None

        distiller = agent_cls(
            name="RuleDistiller",
            role="Editorial Standards Editor",
            system_prompt=(
                "You are an editor consolidating style feedback. You will "
                "receive a list of writing rules accumulated over time. Many "
                "overlap or say the same thing differently.\n\n"
                f"Merge them into AT MOST {DISTILLED_MAX} distinct, "
                "non-overlapping principles. Prefer positive guidance "
                "('write like X') over long lists of prohibitions where "
                "possible. Keep each principle under 20 words.\n\n"
                "Output ONLY the principles, one per line, no numbering, no "
                "preamble, no markdown."
            ),
        )
        result = distiller.run("\n".join(f"- {r}" for r in rules))
        if not result:
            logger.error("Distillation failed: LLM returned nothing. Keeping old rules.")
            return None

        principles = [ln.strip("-• \t") for ln in result.splitlines() if ln.strip()]
        principles = principles[:DISTILLED_MAX]
        if len(principles) < 3:
            logger.error("Distillation produced <3 principles; refusing to overwrite.")
            return None

        with self.memory.lock:
            data = self.memory._load()
            data["rules"] = principles
            data["rules_distilled_at"] = datetime.utcnow().isoformat()
            self.memory._save(data)
        logger.info(f"✨ Distilled {len(rules)} rules -> {len(principles)} principles")
        return principles


# ----------------------------------------------------------------------------
# 2. VibeBandit
# ----------------------------------------------------------------------------

class VibeBandit:
    """Epsilon-greedy vibe selection driven by manually entered impressions.

    Reward = impressions per post (likes are too sparse at small network
    size to carry signal; impressions are visible in LinkedIn's own
    analytics UI for every post).
    """

    def __init__(self, feedback_path: str = FEEDBACK_PATH):
        self.feedback_path = feedback_path

    def _load_observations(self) -> Dict[str, List[float]]:
        """Return {vibe_name: [impressions, ...]} from manual stats."""
        obs: Dict[str, List[float]] = {}
        try:
            with open(self.feedback_path, "r") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return obs
        for entry in data.get("manual_stats", []):
            vibe = entry.get("vibe")
            imp = entry.get("impressions")
            if not vibe or imp is None:
                continue
            # Skip the shipped template example
            if "template" in str(entry.get("notes", "")).lower():
                continue
            try:
                obs.setdefault(vibe, []).append(float(imp))
            except (TypeError, ValueError):
                continue
        return obs

    def select(self, candidates: List[str]) -> str:
        obs = self._load_observations()
        scored = {
            v: sum(vals) / len(vals)
            for v, vals in obs.items()
            if v in candidates and len(vals) >= MIN_OBSERVATIONS
        }

        if not scored or random.random() < EPSILON:
            # Explore: prefer vibes with the least data
            counts = {v: len(obs.get(v, [])) for v in candidates}
            least_seen = min(counts.values())
            pool = [v for v, c in counts.items() if c == least_seen]
            choice = random.choice(pool)
            logger.info(f"🎲 Bandit EXPLORE -> {choice} (observations: {counts.get(choice, 0)})")
            return choice

        choice = max(scored, key=scored.get)
        logger.info(
            f"🎯 Bandit EXPLOIT -> {choice} "
            f"(mean impressions: {scored[choice]:.0f} over {len(obs[choice])} posts)"
        )
        return choice


# ----------------------------------------------------------------------------
# 3. Reflector (weekly)
# ----------------------------------------------------------------------------

class Reflector:
    """Weekly reflection cycle. Run from the weekly GitHub Action."""

    def __init__(self, memory, agent_cls):
        self.memory = memory
        self.agent_cls = agent_cls
        self.rule_manager = RuleManager(memory)
        self.bandit = VibeBandit()

    def _recent_posts(self, days: int = 7) -> List[dict]:
        cutoff = datetime.utcnow() - timedelta(days=days)
        out = []
        for p in self.memory._load().get("history", []):
            try:
                if datetime.fromisoformat(p["date"]) >= cutoff:
                    out.append(p)
            except (KeyError, ValueError):
                continue
        return out

    def _performance_memo(self) -> str:
        obs = self.bandit._load_observations()
        if not obs:
            return (
                "**No manual stats entered yet.** The bandit is running blind "
                "(pure exploration). Run `python enter_stats.py` after checking "
                "your LinkedIn post analytics — 5 minutes/week gives the bot "
                "its only real learning signal."
            )
        lines = ["| Vibe | Posts tracked | Mean impressions |", "|---|---|---|"]
        for v, vals in sorted(obs.items(), key=lambda kv: -sum(kv[1]) / len(kv[1])):
            lines.append(f"| {v} | {len(vals)} | {sum(vals) / len(vals):.0f} |")
        return "\n".join(lines)

    def run(self) -> str:
        # 1. Distill rules
        self.rule_manager.distill(self.agent_cls)

        # 2. Gather material
        recent = self._recent_posts(7)
        comment_pack = self.memory._load().get("latest_comment_pack", "")

        # 3. Compose the brief
        brief = f"""# Weekly Brief — {datetime.utcnow().strftime('%Y-%m-%d')}

## 📊 Performance (from your manual stats)
{self._performance_memo()}
## 📝 Posts published this week: {len(recent)}
{chr(10).join(f"- {p['date'][:10]} · **{p['vibe']}** · {p['topic']}" for p in recent) or "- none"}

## 🤝 Comment pack (USE THESE — this is the growth lever)
{comment_pack or "_No comment pack generated this week._"}

## ✅ Your daily 20-minute checklist (the bot cannot do these for you)
1. Send **5 connection requests** with a personal note (search: SMB owners in
   Türkiye/Riau, maritime contacts, AI practitioners). Acceptance ~30% ⇒
   ~10 new connections/week.
2. Post **2–3 comments** on posts by accounts your targets follow — adapt the
   comment pack above. Comments on others' posts reach *their* audience.
3. Reply to every comment on your own posts within 1 hour of posting.
4. Once a week: run `python enter_stats.py` with impressions from
   LinkedIn analytics so the bandit can learn.

_Generated automatically by the weekly reflection workflow._
"""
        with open(BRIEF_PATH, "w") as f:
            f.write(brief)
        logger.info(f"📋 Weekly brief written to {BRIEF_PATH}")
        return brief


if __name__ == "__main__":
    # Entry point for the weekly workflow
    logging.basicConfig(level=logging.INFO)
    from linkedin_agents import Memory, Agent  # noqa: import here to avoid cycles
    Reflector(Memory(MEMORY_PATH), Agent).run()
