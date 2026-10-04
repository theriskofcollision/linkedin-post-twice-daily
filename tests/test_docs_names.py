"""Dead agent names must not return in markdown."""

import pathlib
import subprocess


def test_dead_names_absent_from_markdown():
    root = pathlib.Path(__file__).resolve().parents[1]
    names = ("TrendScout", "ImageGenerator")
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).split(b"\0")
    offenders = []
    for rel_b in tracked:
        if not rel_b:
            continue
        rel = rel_b.decode()
        if not rel.endswith(".md"):
            continue
        body = (root / rel).read_text(encoding="utf-8")
        for name in names:
            if name in body:
                offenders.append(rel)
                break
    assert offenders == []


def test_walkthrough_does_not_say_twice_daily():
    root = pathlib.Path(__file__).resolve().parents[1]
    body = (root / "walkthrough.md").read_text(encoding="utf-8")
    assert "twice daily" not in body
    assert "linkedin-post-twice-daily" in body
