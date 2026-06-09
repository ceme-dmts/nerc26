#!/usr/bin/env python3
"""Process the NERC26 teams CSV and produce simple insights.

Reads data/Teams_NERC_26.csv, computes a handful of summaries, and writes:
  - output/insights.json   (machine-readable)
  - output/insights.md     (human-readable summary)
  - docs/data.json         (consumed by the GitHub Pages site)

Stdlib only. Run:  python3 process.py
"""

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent
CSV_PATH = ROOT / "data" / "Teams_NERC_26.csv"
OUT_DIR = ROOT / "output"
DOCS_DIR = ROOT / "docs"

# Columns holding each member's name; used to estimate team size.
MEMBER_NAME_COLS = [
    "Team Leader Name",
    "2nd Member Name",
    "3rd Member Name",
    "4th Member Name",
    "5th Member Name",
    "6th Member Name",
]
MEMBER_GENDER_COLS = [
    "Team Leader Gender",
    "2nd Member Gender",
    "3rd Member Gender",
    "4th Member Gender",
    "5th Member Gender",
    "6th Member Gender",
]


def load_rows():
    with open(CSV_PATH, newline="", encoding="utf-8", errors="replace") as f:
        return list(csv.DictReader(f))


def team_size(row):
    return sum(1 for c in MEMBER_NAME_COLS if row.get(c, "").strip())


def to_int(value, default=0):
    try:
        return int(float(str(value).strip()))
    except (ValueError, TypeError):
        return default


# Institution values that aren't a real institution — bucketed as "Private Teams".
PRIVATE_LABELS = {"", "(private)", "private", "n/a", "na", "none", "-"}


def norm_inst(s):
    """Collapse whitespace in an institution name (e.g. 'CEME  NUST' -> 'CEME NUST')."""
    return " ".join((s or "").split())


def city_institution_detail(rows):
    """Per city, a breakdown of teams by institution (most teams first).

    Private / unspecified institutions are merged into a single "Private Teams"
    entry shown last. Cities are ordered by total team count, descending.
    """
    city_totals = Counter(r["City"].strip() for r in rows)
    by_city = {}
    for r in rows:
        city = r["City"].strip()
        inst = norm_inst(r.get("institution", ""))
        bucket = by_city.setdefault(city, Counter())
        bucket["\0private" if inst.lower() in PRIVATE_LABELS else inst] += 1

    detail = {}
    for city, total in city_totals.most_common():
        counts = by_city[city]
        private = counts.pop("\0private", 0)
        insts = [{"name": name, "count": n} for name, n in counts.most_common()]
        if private:
            insts.append({"name": "Private Teams", "count": private})
        detail[city] = {"total": total, "institutions": insts}
    return detail


def compute(rows):
    participants = 0
    gender = Counter()
    for row in rows:
        participants += team_size(row)
        for c in MEMBER_GENDER_COLS:
            g = row.get(c, "").strip().title()
            if g in ("Male", "Female"):
                gender[g] += 1

    fees_paid = sum(1 for r in rows if to_int(r.get("FeesPaid")) == 1)
    instation = sum(1 for r in rows if to_int(r.get("InStation")) == 1)
    fees_due = sum(to_int(r.get("Total Fees")) for r in rows)
    fees_collected = sum(
        to_int(r.get("Total Fees")) for r in rows if to_int(r.get("FeesPaid")) == 1
    )

    return {
        "total_teams": len(rows),
        "total_participants": participants,
        "teams_paid": fees_paid,
        "teams_unpaid": len(rows) - fees_paid,
        "fees_due_rs": fees_due,
        "fees_collected_rs": fees_collected,
        "instation_teams": instation,
        "outstation_teams": len(rows) - instation,
        "by_event": dict(Counter(r["Event"].strip() for r in rows).most_common()),
        "by_city": dict(Counter(r["City"].strip() for r in rows).most_common()),
        "by_city_detail": city_institution_detail(rows),
        "by_institution": dict(
            Counter(r["institution"].strip() for r in rows).most_common()
        ),
        "by_gender": dict(gender),
        "team_size_distribution": dict(
            sorted(Counter(team_size(r) for r in rows).items())
        ),
    }


def write_json(stats):
    OUT_DIR.mkdir(exist_ok=True)
    DOCS_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "insights.json").write_text(json.dumps(stats, indent=2))
    (DOCS_DIR / "data.json").write_text(json.dumps(stats, indent=2))


def write_markdown(stats):
    lines = ["# NERC26 — Insights", ""]
    lines += [
        f"- **Total teams:** {stats['total_teams']}",
        f"- **Total participants:** {stats['total_participants']}",
        f"- **Teams that paid:** {stats['teams_paid']} "
        f"(unpaid: {stats['teams_unpaid']})",
        f"- **Fees collected:** Rs {stats['fees_collected_rs']:,} "
        f"of Rs {stats['fees_due_rs']:,}",
        f"- **In-station / out-station:** "
        f"{stats['instation_teams']} / {stats['outstation_teams']}",
        "",
    ]

    def table(title, mapping, key_header):
        out = [f"## {title}", "", f"| {key_header} | Teams |", "| --- | --- |"]
        out += [f"| {k or '(blank)'} | {v} |" for k, v in mapping.items()]
        out.append("")
        return out

    lines += table("Teams by event", stats["by_event"], "Event")
    lines += table("Teams by city", stats["by_city"], "City")
    lines += table("Gender split (members)", stats["by_gender"], "Gender")
    lines += table(
        "Top institutions",
        dict(list(stats["by_institution"].items())[:15]),
        "Institution",
    )

    (OUT_DIR / "insights.md").write_text("\n".join(lines))


def main():
    rows = load_rows()
    stats = compute(rows)
    write_json(stats)
    write_markdown(stats)
    print(f"Processed {stats['total_teams']} teams "
          f"({stats['total_participants']} participants).")
    print(f"Wrote {OUT_DIR/'insights.md'}, {OUT_DIR/'insights.json'}, "
          f"{DOCS_DIR/'data.json'}.")


if __name__ == "__main__":
    main()
