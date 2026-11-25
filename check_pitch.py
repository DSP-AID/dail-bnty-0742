#!/usr/bin/env python3
"""Checks the bnty_0742 pitch against the bounty brief (one line, one idea:
job + reward + why) and against the live DAiL board, proving the idea is new.

Offline by default: reads board_snapshot.json (a real public feed sample).
  python3 check_pitch.py            # offline check
  python3 check_pitch.py --live     # re-fetch the public feed (no API key needed)
"""

import json
import os
import re
import sys
import urllib.request
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT = os.path.join(HERE, "board_snapshot.json")
PITCH = os.path.join(HERE, "pitch.txt")
FEED = "https://dail-3dci.onrender.com/world/bounties?limit=500"

# Themes a pitch must be first to occupy; all are absent from the sampled board.
THEMES = ["fuzz", "race condition", "uptime", "load test", "openapi", "regression"]
STOP = set("a an the of to in for on and or a agent by with is are as at it its this that".split())


def load_board(live: bool):
    if not live:
        return json.load(open(SNAPSHOT, encoding="utf-8")), "board_snapshot.json"
    with urllib.request.urlopen(FEED, timeout=30) as resp:
        rows = json.loads(resp.read().decode("utf-8")).get("bounties", [])
    for r in rows:  # same shape as the shipped snapshot
        r["description"] = (r.get("description") or "")[:300]
    return rows, "live feed"


def board_stats(rows):
    by_genre = defaultdict(Counter)
    for r in rows:
        m = re.match(r"^([A-Za-z ]{3,20}):", r.get("title") or "")
        genre = m.group(1).strip().lower() if m else "untagged"
        by_genre[genre][r.get("status") or "?"] += 1
    out = []
    for genre, st in sorted(by_genre.items(), key=lambda kv: -sum(kv[1].values())):
        n = sum(st.values())
        if n < 5:
            continue
        out.append((genre, n, st.get("completed", 0), st.get("expired", 0)))
    return sorted(out, key=lambda g: -(g[2] / g[1]))


def best_overlap(pitch: str, rows):
    """Highest token-Jaccard between the pitch and any existing bounty title."""
    ptoks = {t for t in re.findall(r"[a-z]+", pitch.lower()) if t not in STOP}
    best, best_title = 0.0, ""
    for r in rows:
        ttoks = {t for t in re.findall(r"[a-z]+", (r.get("title") or "").lower()) if t not in STOP}
        if not ttoks:
            continue
        j = len(ptoks & ttoks) / len(ptoks | ttoks)
        if j > best:
            best, best_title = j, r.get("title") or ""
    return best, best_title


def checks(pitch: str, rows):
    line = pitch.strip()
    reward = re.search(r"\$?\d[\d,]*\s*DAIL", line, re.I)
    why = ("because" in line.lower()) or ("\u2014" in line)
    machine_bar = bool(re.search(r"confirmed|reproducible|trace", line, re.I))
    overlap, top_title = best_overlap(line, rows)
    blob = " ".join(((r.get("title") or "") + " " + (r.get("description") or "")).lower() for r in rows)
    new_themes = [t for t in THEMES if t not in blob]
    return [
        ("one line only", "\n" not in line and len(line.splitlines()) == 1),
        ("punchy length (80-320 chars)", 80 <= len(line) <= 320),
        ("names a reward in DAIL", bool(reward)),
        ("names the job (artifact + verifier)", machine_bar),
        ("says why it is worth doing", why),
        ("novel idea (title overlap < 0.25)", overlap < 0.25),
        ("occupies a virgin theme", len(new_themes) >= 1),
    ], {"overlap": overlap, "top_title": top_title, "new_themes": new_themes}


def main():
    live = "--live" in sys.argv[1:]
    pitch = open(PITCH, encoding="utf-8").read()
    rows, source = load_board(live)
    results, detail = checks(pitch, rows)
    print(f"board sample: {len(rows)} bounties from {source}")
    failed = [name for name, ok in results if not ok]
    for name, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print(f"closest existing title ({detail['overlap']:.2f} Jaccard): {detail['top_title'][:70]}")
    print(f"themes never used by any sampled bounty: {', '.join(detail['new_themes']) or 'none'}")
    print("\ncompletion rate by genre (why doable beats ambitious):")
    for genre, n, done, expired in board_stats(rows)[:8]:
        print(f"  {genre:<16} n={n:<4} completed={done:<4} ({100 * done // n}%)  expired={expired}")
    print(f"\nRESULT: {'PASS' if not failed else 'FAIL ' + ', '.join(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
