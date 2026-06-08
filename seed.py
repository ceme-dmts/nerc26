#!/usr/bin/env python3
"""Build a randomized solo-run seeding of teams per category for NERC26.

Each team gets one timed solo run ("heat") per category. For each category in
the timing plan, this shuffles the registered teams and assigns a run order
(1..N). Randomness is reproducible: the same --seed always produces the same
order, so the draw can be re-verified / audited later. (Brackets are out of
scope — these are solo-run orders only.)

Only categories present in data/Timing Plan.csv are seeded; other events in the
teams file (Aero, SumoWars, etc.) are ignored here.

Outputs:
  - output/seeding.md     (human-readable, per-category tables)
  - output/seeding.json   (machine-readable)

Usage:
  python3 seed.py              # default RNG seed (26)
  python3 seed.py --seed 123   # different draw
"""

import argparse
import csv
import json
import random
from pathlib import Path

ROOT = Path(__file__).parent
TEAMS_CSV = ROOT / "data" / "Teams_NERC_26.csv"
TIMING_CSV = ROOT / "data" / "Timing Plan.csv"
OUT_DIR = ROOT / "output"

# Maps the event label used in Timing Plan.csv -> the Event value in the teams CSV.
TIMING_TO_EVENT = {
    "RTR School Heats": "Ready to Race-School",
    "Indigenous Heats": "Indigenous Category",
    "Modular School": "Modular School",
    "RTR Uni": "Ready to Race-University",
    "Modular Uni": "Modular University",
}


def load_teams():
    with open(TEAMS_CSV, newline="", encoding="utf-8", errors="replace") as f:
        return list(csv.DictReader(f))


def load_schedule():
    """Return {data_event_name: {day, time, venue}} from the timing plan."""
    schedule = {}
    with open(TIMING_CSV, newline="", encoding="utf-8", errors="replace") as f:
        for row in csv.DictReader(f):
            event = TIMING_TO_EVENT.get((row.get("Event") or "").strip())
            if not event:
                continue
            day = " ".join((row.get("Day ") or "").split())  # flatten multiline
            schedule[event] = {
                "day": day,
                "time": (row.get("Time") or "").strip(),
                "venue": (row.get("Venue") or "").strip(),
            }
    return schedule


def build_seeding(teams, schedule, rng_seed):
    # Group teams by event, keeping only categories that appear in the timing plan.
    scheduled_events = set(TIMING_TO_EVENT.values())
    by_event = {}
    for t in teams:
        event = t["Event"].strip()
        if event in scheduled_events:
            by_event.setdefault(event, []).append(t)

    result = {}
    for event in sorted(by_event):
        rng = random.Random(f"{rng_seed}|{event}")  # per-event stream, reproducible
        group = by_event[event][:]
        rng.shuffle(group)
        seeded = [
            {
                "seed": i,
                "team_no": t.get("Team #", "").strip(),
                "team_name": t.get("Team Name", "").strip(),
                "institution": t.get("institution", "").strip(),
                "city": t.get("City", "").strip(),
            }
            for i, t in enumerate(group, start=1)
        ]
        result[event] = {
            "schedule": schedule.get(event),
            "team_count": len(seeded),
            "teams": seeded,
        }
    return result


def write_outputs(seeding, rng_seed):
    OUT_DIR.mkdir(exist_ok=True)
    payload = {"rng_seed": rng_seed, "categories": seeding}
    (OUT_DIR / "seeding.json").write_text(json.dumps(payload, indent=2))

    lines = [
        "# NERC26 — Randomized Solo-Run Seeding",
        "",
        f"Reproducible draw (RNG seed = `{rng_seed}`). "
        "Re-run `python3 seed.py` with the same seed to reproduce.",
        "",
    ]
    for event, info in seeding.items():
        lines.append(f"## {event}  ({info['team_count']} teams)")
        sch = info["schedule"]
        if sch:
            lines.append(
                f"_Schedule: {sch['day']} · {sch['time']} · {sch['venue']}_"
            )
        else:
            lines.append("_Schedule: TBD_")
        lines += ["", "| Seed | Team # | Team Name | Institution | City |",
                  "| ---: | --- | --- | --- | --- |"]
        for s in info["teams"]:
            lines.append(
                f"| {s['seed']} | {s['team_no']} | {s['team_name']} | "
                f"{s['institution']} | {s['city']} |"
            )
        lines.append("")

    (OUT_DIR / "seeding.md").write_text("\n".join(lines))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=26,
                    help="RNG seed for the draw (default: 26)")
    args = ap.parse_args()

    teams = load_teams()
    schedule = load_schedule()
    seeding = build_seeding(teams, schedule, args.seed)
    write_outputs(seeding, args.seed)

    print(f"Seeded {len(seeding)} categories (RNG seed = {args.seed}):")
    for event, info in seeding.items():
        tag = "scheduled" if info["schedule"] else "TBD"
        print(f"  {event:<28} {info['team_count']:>3} teams  [{tag}]")
    print(f"Wrote {OUT_DIR/'seeding.md'} and {OUT_DIR/'seeding.json'}.")


if __name__ == "__main__":
    main()
