#!/usr/bin/env python3
"""NERC26 live seeding ceremony — minimal Flask app.

One ceremonial DRAW button randomly seeds the solo-run order for all five
scheduled categories at once, reveals them on the big screen, and writes the
result to docs/draw.json so a single `git push` publishes it on the website.

Reuses the seeding logic from seed.py directly. Reads the fixed teams file at
data/Teams_NERC_26.csv (operator copies the final list there before the ceremony).

Run:  python3 app.py    then open http://localhost:5000
"""

import json
import secrets
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request

import seed  # reuse load_teams / load_schedule / build_seeding

ROOT = Path(__file__).parent
DRAW_FILE = ROOT / "docs" / "draw.json"

app = Flask(__name__)


def run_draw():
    """Generate a fresh random draw across all scheduled categories."""
    rng_seed = secrets.randbelow(1_000_000)
    teams = seed.load_teams()
    schedule = seed.load_schedule()
    categories = seed.build_seeding(teams, schedule, rng_seed)
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


@app.route("/api/draw", methods=["GET"])
def get_draw():
    return jsonify(load_existing() or {})


@app.route("/api/draw", methods=["POST"])
def post_draw():
    # Guard the official draw: don't silently overwrite unless forced (redo).
    if load_existing() and not request.args.get("force"):
        return jsonify({"error": "already_drawn"}), 409
    result = run_draw()
    DRAW_FILE.parent.mkdir(exist_ok=True)
    DRAW_FILE.write_text(json.dumps(result, indent=2))
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
