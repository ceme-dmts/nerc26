#!/usr/bin/env python3
"""Build single-elimination knockout brackets from the NERC26 heat results.

Each of the five scheduled categories runs as timed solo "heats". Operators
record each team's `score` and `time` in results/<slug>.csv (created by app.py
when the draw is pressed). This script ranks every category by score (desc),
breaking ties by time (asc), seeds the top-N teams into a standard knockout
bracket (so #1 and #2 can only meet in the final), and writes docs/bracket.json
and docs/schedule.json for the public pages.

Match results are recorded per category in results/<slug>_bracket.csv: the
operator types the winning team's ID in the `winner` column and re-runs this
script, which propagates winners into later rounds (filling the real teams and
names) and refreshes both JSON files. A category whose heats CSV has no scores
yet is marked "pending".

Usage:
  python3 bracket.py
"""

import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

import seed  # reuse load_schedule and the shared SLUG map
from seed import SLUG

ROOT = Path(__file__).parent
DOCS_DIR = ROOT / "docs"
RESULTS_DIR = ROOT / "results"
BRACKET_FILE = DOCS_DIR / "bracket.json"
SCHEDULE_FILE = DOCS_DIR / "schedule.json"
DRAW_FILE = DOCS_DIR / "draw.json"  # solo-run heats (written by app.py on draw)

# Teams advancing from the heats into each knockout (must be a power of two).
# Edit here to change a category's bracket size.
BRACKET_SIZE = {
    "Indigenous Category": 16,
    "Modular School": 32,
    "Ready to Race-School": 16,
    "Ready to Race-University": 16,
    "Modular University": 8,
}

# Round label by number of teams contesting that round.
ROUND_NAMES = {2: "Final", 4: "SF", 8: "QF", 16: "R16", 32: "R32", 64: "R64"}

# Categories that also play a 3rd-place ("2nd runner-up") match between the two
# semi-final losers. Indigenous only, per the organisers.
THIRD_PLACE = {"Indigenous Category"}

# Head-to-head knockout plan, transcribed from
# data/Timing Plan brackets revised.csv.
# Each session is a (day, venue, time-window): the listed categories play the
# listed rounds back-to-back at MATCH_MIN each, starting at `start`. Match counts
# per round (R32=16, R16=8, QF=4, SF=2, Final=1) at 5 min give the CSV's stated
# block lengths (R32 80min, R16 40min, QF 20min, SF 10min). A slot with
# `heats_first` opens with that category's overflow heats (seed.HEATS_OVERFLOW);
# its matches start once those runs are done.
MATCH_MIN = 5  # minutes per head-to-head match
BRACKET_PLAN = [
    {"day": "Day 2 · Fri 12 Jun", "venue": "Central Activity Room",
     "window": "1400-1830", "start": "14:00", "heats_first": "Modular School",
     "events": [
         ("Ready to Race-School", ["R16"]),
         ("Ready to Race-University", ["R16"]),
         ("Modular University", ["QF"]),
     ]},
    {"day": "Day 2 · Fri 12 Jun", "venue": "Auditorium",
     "window": "1400-1830", "start": "14:00", "events": [
         ("Indigenous Category", ["R16"]),
         ("Modular School", ["R32", "R16"]),
     ]},
    {"day": "Day 3 · Sat 13 Jun", "venue": "Auditorium",
     "window": "0800-1300", "start": "10:00", "events": [
         ("Ready to Race-University", ["QF", "SF"]),
         ("Ready to Race-School", ["QF", "SF"]),
         ("Modular University", ["SF"]),
         ("Modular School", ["QF", "SF"]),
         ("Indigenous Category", ["QF"]),
     ]},
    {"day": "Day 3 · Sat 13 Jun", "venue": "Auditorium",
     "window": "1500-1700", "start": "15:00", "events": [
         ("Ready to Race-University", ["Final"]),
         ("Ready to Race-School", ["Final"]),
         ("Modular University", ["Final"]),
         ("Modular School", ["Final"]),
         # Indigenous plays its SF, 3rd-place, and Final in this slot.
         ("Indigenous Category", ["SF", "3rd", "Final"]),
     ]},
]


def parse_score(s):
    s = (s or "").strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_time(s):
    """Seconds as a float, accepting plain seconds (42.1) or mm:ss (1:23.4)."""
    s = (s or "").strip()
    if not s:
        return None
    try:
        if ":" in s:
            m, sec = s.split(":", 1)
            return int(m) * 60 + float(sec)
        return float(s)
    except ValueError:
        return None


def load_results(slug):
    path = RESULTS_DIR / f"{slug}.csv"
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        rows = []
        for r in csv.DictReader(f):
            rows.append({
                "team_no": (r.get("team_no") or "").strip(),
                "team_name": (r.get("team_name") or "").strip(),
                "institution": (r.get("institution") or "").strip(),
                "score": parse_score(r.get("score")),
                "time": parse_time(r.get("time")),
            })
        return rows


def rank(rows):
    """Sort by score desc, time asc; unscored teams sink to the bottom.

    Returns the ranked list with a 1-based `rank` added.
    """
    ordered = sorted(rows, key=lambda r: (
        r["score"] is None,                        # scored teams first
        -(r["score"] or 0),                        # higher score first
        r["time"] is None,                          # timed teams first
        r["time"] or 0,                             # faster time first
    ))
    for i, r in enumerate(ordered, start=1):
        r["rank"] = i
    return ordered


def seed_order(n):
    """Standard single-elim seed slots for a bracket of size n (power of two).

    e.g. n=8 -> [1, 8, 4, 5, 2, 7, 3, 6]. Pairing consecutive slots gives the
    round-1 matches so the two top seeds meet only in the final.
    """
    slots = [1, 2]
    while len(slots) < n:
        m = len(slots) * 2 + 1
        slots = [s for pair in ((x, m - x) for x in slots) for s in pair]
    return slots


def build_matches(ranked, n, seeded, third_place=False):
    """Build the full match list (numbered 1..N) for one category.

    Round 1 holds seeded teams (or byes / pending if heats aren't scored yet);
    each later-round match feeds off the winners of the two matches before it.
    A `third_place` bracket also appends one match fed by the two SF losers.
    Sides are unresolved descriptors that resolve() later turns into teams.
    """
    by_rank = {r["rank"]: r for r in ranked}

    def r1_side(rk):
        if not seeded:
            return {"seed_ref": rk}  # before heats: show "Seed N" placeholders
        r = by_rank.get(rk)
        if r is None:
            return {"bye": True}
        return {"team": {"seed": rk, "team_no": r["team_no"],
                         "team_name": r["team_name"],
                         "institution": r.get("institution", "")}}

    matches, num = [], 0
    order = seed_order(n)
    name = ROUND_NAMES.get(n, f"R{n}")
    prev = []
    for i in range(0, n, 2):
        num += 1
        matches.append({"no": num, "round": name,
                        "a": r1_side(order[i]), "b": r1_side(order[i + 1])})
        prev.append(num)

    sf_nums, size = [], n // 2
    while size >= 2:
        name = ROUND_NAMES.get(size, f"R{size}")
        cur = []
        for j in range(size // 2):
            num += 1
            matches.append({"no": num, "round": name,
                            "a": {"feed": {"match": prev[2 * j], "take": "winner"}},
                            "b": {"feed": {"match": prev[2 * j + 1], "take": "winner"}}})
            cur.append(num)
        if name == "SF":
            sf_nums = cur
        prev, size = cur, size // 2

    if third_place and len(sf_nums) == 2:
        num += 1
        matches.append({"no": num, "round": "3rd",
                        "a": {"feed": {"match": sf_nums[0], "take": "loser"}},
                        "b": {"feed": {"match": sf_nums[1], "take": "loser"}}})
    return matches


def resolve(matches, winners):
    """Resolve every match's two sides and winner, given recorded winners.

    `winners` maps match_no -> winning team_no. Byes auto-advance; an entered
    winner is honoured only if it matches one of the match's resolved teams
    (stale/invalid entries are ignored). Returns serialized matches with
    `a`/`b` side objects (team / bye / tbd / ref) and `winner` (team_no or None).
    """
    res, out = {}, []  # res: no -> {"winner": team|None, "loser": team|None}
    for m in matches:
        a, b = _resolve_side(m["a"], res), _resolve_side(m["b"], res)
        a_team, b_team = a.get("team"), b.get("team")
        win = los = None
        if a_team and "bye" in b:
            win = a_team
        elif b_team and "bye" in a:
            win = b_team
        else:
            wid = winners.get(m["no"])
            if wid and a_team and a_team["team_no"] == wid:
                win, los = a_team, b_team
            elif wid and b_team and b_team["team_no"] == wid:
                win, los = b_team, a_team
        res[m["no"]] = {"winner": win, "loser": los}
        out.append({"no": m["no"], "round": m["round"],
                    "a": _ser(a), "b": _ser(b),
                    "winner": win["team_no"] if win else None})
    return out


def _resolve_side(side, res):
    if "feed" not in side:
        return side  # team / bye / pending
    feed = side["feed"]
    r = res.get(feed["match"])
    team = r and r[feed["take"]]
    if team:
        return {"team": team}
    label = "Winner" if feed["take"] == "winner" else "Loser"
    return {"ref": f"{label} of Match {feed['match']}"}


def _ser(side):
    if "team" in side:
        td = side["team"]
        return {"type": "team", "seed": td["seed"], "team_no": td["team_no"],
                "team_name": td["team_name"], "institution": td.get("institution", "")}
    if "bye" in side:
        return {"type": "bye"}
    if "ref" in side:
        return {"type": "ref", "text": side["ref"]}
    if "seed_ref" in side:
        return {"type": "seed", "seed": side["seed_ref"]}
    return {"type": "tbd"}


def group_rounds(resolved):
    """Group the flat resolved-match list into ordered rounds for bracket.json."""
    rounds = []
    for m in resolved:
        if not rounds or rounds[-1]["name"] != m["round"]:
            rounds.append({"name": m["round"], "matches": []})
        rounds[-1]["matches"].append(
            {"no": m["no"], "a": m["a"], "b": m["b"], "winner": m["winner"]})
    return rounds


def load_bracket_winners(slug):
    """Read {match_no: winner_team_no} from results/<slug>_bracket.csv if present."""
    path = RESULTS_DIR / f"{slug}_bracket.csv"
    if not path.exists():
        return {}
    winners = {}
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        for r in csv.DictReader(f):
            no = (r.get("match_no") or "").strip()
            w = (r.get("winner") or "").strip()
            if no.isdigit() and w:
                winners[int(no)] = w
    return winners


def write_bracket_csv(slug, resolved):
    """Write/refresh results/<slug>_bracket.csv (operator fills only `winner`).

    Auto-fills team IDs + names for every resolved side (blank where a feed isn't
    decided yet) and keeps each match's recorded winner.
    """
    RESULTS_DIR.mkdir(exist_ok=True)
    with open(RESULTS_DIR / f"{slug}_bracket.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["match_no", "round", "team_a", "team_a_name",
                    "team_b", "team_b_name", "winner"])
        for m in resolved:
            a, b = m["a"], m["b"]
            w.writerow([
                m["no"], m["round"],
                a["team_no"] if a["type"] == "team" else "",
                a["team_name"] if a["type"] == "team" else "",
                b["team_no"] if b["type"] == "team" else "",
                b["team_name"] if b["type"] == "team" else "",
                m["winner"] or "",
            ])


def _canon_day(raw):
    for i, label in ((1, "Day 1 · Thu 11 Jun"), (2, "Day 2 · Fri 12 Jun"),
                     (3, "Day 3 · Sat 13 Jun")):
        if f"Day {i}" in raw:
            return label
    return raw


def _canon_venue(raw):
    return "Central Activity Room" if raw.strip().upper() == "CAR" else raw.strip()


def heats_sessions():
    """Solo-run heat schedule, read from docs/draw.json (run order + run times).

    Returns schedule `sessions` (same shape as schedule_brackets) with one
    "Heats" block per category, sorted chronologically; [] if no draw exists.
    """
    if not DRAW_FILE.exists():
        return []
    cats = json.loads(DRAW_FILE.read_text()).get("categories", {})
    groups, order = {}, []
    for event, info in cats.items():
        teams = info.get("teams", [])
        over = info.get("overflow")
        cut = over["from_seed"] - 1 if over else len(teams)
        slots = [(info.get("schedule") or {}, teams[:cut])]
        if over:
            slots.append((over, teams[cut:]))
        for sch, group in slots:
            if not group:
                continue
            key = (_canon_day(sch.get("day", "")), _canon_venue(sch.get("venue", "")),
                   sch.get("time", ""))
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append({"name": event, "solo": True, "matches": [
                {"no": t.get("seed"), "round": "Heats", "time": t.get("run_time", ""),
                 "a": {"type": "team", "seed": t.get("seed"),
                       "team_no": t.get("team_no"), "team_name": t.get("team_name"),
                       "institution": t.get("institution", "")}}
                for t in group]})

    def sort_key(k):
        day, _venue, window = k
        idx = next((i for i in (1, 2, 3) if f"Day {i}" in day), 9)
        start = int(window[:4]) if window[:4].isdigit() else 0
        return (idx, start)

    return [{"day": k[0], "venue": k[1], "window": k[2], "categories": groups[k]}
            for k in sorted(order, key=sort_key)]


def heats_spill():
    """Per-event count of heats that run in the overflow slot (seed.HEATS_OVERFLOW).

    Counts the drawn teams when a draw exists, else the registered teams, so
    the knockout start times stay correct before and after the ceremony.
    """
    if DRAW_FILE.exists():
        cats = json.loads(DRAW_FILE.read_text()).get("categories", {})
        counts = {e: len(i.get("teams", [])) for e, i in cats.items()}
    else:
        counts = Counter(t["Event"].strip() for t in seed.load_teams())
    return {e: seed.overflow_count(e, counts.get(e, 0))
            for e in seed.HEATS_OVERFLOW}


def schedule_brackets(all_matches, spill):
    """Assign a clock time to every head-to-head match, per BRACKET_PLAN.

    Within each session, matches run back-to-back (MATCH_MIN each) from `start`,
    in the configured category + round order; a `heats_first` slot starts after
    that category's overflow heats (`spill`, from heats_spill()). Returns:
      sessions    - list of {day, venue, window, categories:[{name, matches}]}
                    for the schedule page (each match carries its `time`).
      round_sched - {event: {round: {day, venue, time}}} for the bracket page,
                    where `time` is the start time of that round's first match.
    """
    sessions = []
    round_sched = {event: {} for event in all_matches}
    for slot in BRACKET_PLAN:
        clock = _hhmm_to_min(slot["start"])
        clock += spill.get(slot.get("heats_first"), 0) * MATCH_MIN
        blocks = []
        for event, rounds in slot["events"]:
            picked = []
            for rnd in rounds:
                start = f"{clock // 60:02d}:{clock % 60:02d}"
                round_sched[event][rnd] = {
                    "day": slot["day"], "venue": slot["venue"], "time": start,
                }
                for m in (x for x in all_matches[event] if x["round"] == rnd):
                    picked.append(dict(m, time=f"{clock // 60:02d}:{clock % 60:02d}"))
                    clock += MATCH_MIN
            if picked:
                blocks.append({"name": event, "matches": picked})
        sessions.append({"day": slot["day"], "venue": slot["venue"],
                         "window": slot["window"], "categories": blocks})
    return sessions, round_sched


def _hhmm_to_min(s):
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def main():
    schedule = seed.load_schedule()
    categories = {}
    all_matches = {}
    for event, slug in SLUG.items():
        n = BRACKET_SIZE[event]
        ranked = rank(load_results(slug))
        seeded = any(r["score"] is not None for r in ranked)
        matches = build_matches(ranked, n, seeded, event in THIRD_PLACE)
        resolved = resolve(matches, load_bracket_winners(slug))
        write_bracket_csv(slug, resolved)
        all_matches[event] = resolved
        categories[event] = {
            "schedule": schedule.get(event),  # the heats (seeding) slot
            "bracket_size": n,
            "status": "seeded" if seeded else "pending",
            # Rounds are always emitted: before heats they read "Seed N" / "Winner
            # of Match X"; after heats the real teams replace the seed placeholders.
            "rounds": group_rounds(resolved),
        }

    bracket_sessions, round_sched = schedule_brackets(all_matches, heats_spill())
    sessions = heats_sessions() + bracket_sessions  # heats are chronologically first
    for event, entry in categories.items():
        entry["knockout_schedule"] = round_sched.get(event, {})

    DOCS_DIR.mkdir(exist_ok=True)
    BRACKET_FILE.write_text(json.dumps({
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "categories": categories,
    }, indent=2))
    SCHEDULE_FILE.write_text(json.dumps({
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "sessions": sessions,
    }, indent=2))

    print("Brackets generated:")
    for event, entry in categories.items():
        print(f"  {event:<28} size {entry['bracket_size']:>2}  [{entry['status']}]")
    print(f"Wrote {BRACKET_FILE} and {SCHEDULE_FILE}.")


if __name__ == "__main__":
    main()
