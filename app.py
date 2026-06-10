#!/usr/bin/env python3
"""NERC26 live seeding ceremony — minimal Flask app.

One ceremonial DRAW button randomly seeds the solo-run order for all five
scheduled categories at once, reveals them on the big screen, and writes the
result to docs/draw.json so a single `git push` publishes it on the website.

Reuses the seeding logic from seed.py directly. Reads the fixed teams file at
data/Teams_NERC_26.csv (operator copies the final list there before the ceremony).

Run:  python3 app.py    then open http://localhost:5000
"""

import csv
import json
import secrets
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, send_from_directory

import seed  # reuse load_teams / load_schedule / build_seeding / SLUG
from seed import SLUG

ROOT = Path(__file__).parent
DOCS_DIR = ROOT / "docs"
DRAW_FILE = DOCS_DIR / "draw.json"
RESULTS_DIR = ROOT / "results"  # per-category heats CSVs (operator fills score/time)

RUN_GAP_MIN = 5  # minutes between consecutive runs (if the window allows)

app = Flask(__name__)


def _hhmm_to_min(s):
    s = s.strip()
    return int(s[:2]) * 60 + int(s[2:])


def add_run_times(categories, gap=RUN_GAP_MIN):
    """Add an estimated run_time (HH:MM) to each team.

    A category with an overflow slot (see seed.HEATS_OVERFLOW) has its trailing
    teams timed in that slot; everyone else runs in the main scheduled window.
    """
    for info in categories.values():
        teams = info["teams"]
        over = info.get("overflow")
        cut = over["from_seed"] - 1 if over else len(teams)
        _time_runs(teams[:cut], info.get("schedule") or {}, gap)
        if over:
            _time_runs(teams[cut:], over, gap)


def _time_runs(teams, sched, gap):
    """Assign run_time to `teams` within one slot's HHMM-HHMM window.

    Uses `gap` minutes between runs; if that would overflow the window
    (e.g. 53 runs * 5 min > 4 hours), spreads the runs evenly instead.
    """
    n = len(teams)
    try:
        start_s, end_s = sched.get("time", "").split("-")
        start = _hhmm_to_min(start_s)
        window = _hhmm_to_min(end_s) - start
    except (ValueError, AttributeError):
        for t in teams:
            t["run_time"] = ""
        return
    interval = gap if n <= 1 or (n - 1) * gap <= window else window / n
    for i, t in enumerate(teams):
        total = int(round(start + i * interval))
        t["run_time"] = f"{total // 60:02d}:{total % 60:02d}"


def write_result_csvs(categories):
    """Write one results/<slug>.csv per category for operators to fill in.

    Columns are the draw fields plus blank `score` and `time`, recorded during
    the heats and later ranked by bracket.py. A fresh draw overwrites these
    (the draw defines the seeding, so re-drawing resets results).
    """
    RESULTS_DIR.mkdir(exist_ok=True)
    for event, info in categories.items():
        slug = SLUG.get(event)
        if not slug:
            continue
        with open(RESULTS_DIR / f"{slug}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["seed", "team_no", "team_name", "institution", "score", "time"])
            for t in info["teams"]:
                w.writerow([t["seed"], t["team_no"], t["team_name"],
                            t["institution"], "", ""])


def run_draw():
    """Generate a fresh random draw across all scheduled categories."""
    rng_seed = secrets.randbelow(1_000_000)
    teams = seed.load_teams()
    schedule = seed.load_schedule()
    categories = seed.build_seeding(teams, schedule, rng_seed)
    add_run_times(categories)
    write_result_csvs(categories)
    return {
        "rng_seed": rng_seed,
        "drawn_at": datetime.now().isoformat(timespec="seconds"),
        "categories": categories,
    }


def load_existing():
    if DRAW_FILE.exists():
        return json.loads(DRAW_FILE.read_text())
    return None


@app.route("/")
def index():
    return render_template("screen.html")


@app.route("/site/")
@app.route("/site/<path:filename>")
def site(filename="draws.html"):
    """Serve the public docs/ site locally (for the 'Go to website' option)."""
    return send_from_directory(DOCS_DIR, filename)


@app.route("/api/draw", methods=["GET"])
def get_draw():
    return jsonify(load_existing() or {})


@app.route("/api/draw", methods=["POST"])
def post_draw():
    # One ceremonial press = one fresh random draw (overwrites any prior/test draw).
    result = run_draw()
    DRAW_FILE.parent.mkdir(exist_ok=True)
    DRAW_FILE.write_text(json.dumps(result, indent=2))
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
