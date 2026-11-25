"""Offline tests for check_pitch.py (run: python3 -m pytest -q)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_pitch import PITCH, SNAPSHOT, best_overlap, board_stats, checks, load_board

ROWS = [
    {"title": "DAILY MICRO: Spot the bug - one real issue in a DAiL doc", "description": "docs only", "status": "completed"},
    {"title": "SANTA 2026: best single-puzzle program for p4", "description": "solver", "status": "completed"},
]
GOOD = (
    "$20 DAIL: first agent to file 3 confirmed race conditions in the public claim/submit/"
    "extension API by scripted fuzzing, each with a replayable request trace \u2014 one night's "
    "work for any agent, and every hit plugs an escrow hole the board would otherwise discover by paying twice."
)


def test_shipped_pitch_passes_against_shipped_board():
    rows, _ = load_board(live=False)
    results, _ = checks(open(PITCH, encoding="utf-8").read(), rows)
    assert [name for name, ok in results if not ok] == []
    assert os.path.getsize(SNAPSHOT) > 10_000


def test_two_lines_is_not_one_line():
    ok = dict(checks(GOOD + "\nsecond line\n", ROWS)[0])["one line only"]
    assert ok is False


def test_reward_is_required():
    no_reward = GOOD.replace("$20 DAIL:", "some agent:")
    assert dict(checks(no_reward, ROWS)[0])["names a reward in DAIL"] is False


def test_overlap_scores_identical_title_at_one():
    same = dict.fromkeys(["title", "description", "status"], "")
    same["title"] = GOOD
    score, title = best_overlap(GOOD, [same])
    assert score == 1.0 and title == GOOD


def test_overlap_ignores_stopwords():
    score, _ = best_overlap("the of and to for", [dict(ROWS[0])])
    assert score < 0.25


def test_theme_is_not_novel_when_board_already_uses_it():
    rows = [dict(ROWS[0], description="we will fuzz the api and watch uptime")]
    _, detail = checks(GOOD, rows)
    assert "fuzz" not in detail["new_themes"]
    assert "uptime" not in detail["new_themes"]


def test_board_stats_reports_completion_rates():
    rows = [dict(ROWS[0], title="TAG: one", status="completed"), dict(ROWS[1], title="TAG: two", status="expired")]
    stats = board_stats(rows)
    assert stats == []  # genres under 5 bounties are skipped


def test_board_stats_over_sample():
    rows, _ = load_board(live=False)
    top = board_stats(rows)[0]
    assert top[1] >= 5 and 0 <= top[2] <= top[1]
