# NERC26

Simple structure for processing the **National Engineering Robotics Contest 2026**
team registration data and presenting some insights.

> This is intentionally minimal — a starting point to build on once requirements are clear.

## Layout

```
data/                 Teams_NERC_26.csv  (source data)
process.py            reads the CSV, computes insights
seed.py               offline solo-run seeding CLI (dry-run / audit)
app.py                live seeding-ceremony web app (Flask)
bracket.py            ranks heats -> brackets (docs/bracket.json) + Day-2 schedule (docs/schedule.json)
templates/, static/   ceremony reveal UI
results/              per-category heat results (score/time) — filled by operators
output/               generated insights.md + insights.json + seeding.*
docs/                 GitHub Pages site (index.html, draws.html, bracket.html, schedule.html, *.json)
```

## Usage

```bash
python3 process.py
```

This regenerates `output/insights.md`, `output/insights.json`, and `docs/data.json`.
No dependencies — standard library only.

## Live seeding ceremony

Copy the final team list to `data/Teams_NERC_26.csv`, then:

```bash
pip install -r requirements.txt
python3 app.py            # open http://localhost:5000 (fullscreen on the big screen)
```

Press **DRAW THE SEEDING** once — it randomly orders all five scheduled
categories, reveals them with animation, and writes `docs/draw.json`. To publish
the result on the website:

```bash
git add docs/draw.json && git commit -m "Publish NERC26 seeding" && git push
```

The public page `docs/draws.html` then shows the same order. The draw is
reproducible: `python3 seed.py --seed <seed shown on screen>` recreates it.

## Brackets

Each of the five scheduled categories runs as timed solo **heats**; the top
finishers then advance into a single-elimination **knockout bracket**.

Pressing **DRAW** also writes one `results/<slug>.csv` per category (e.g.
`results/modular_uni.csv`) listing every team with blank `score` and `time`
columns. During the heats, fill those in:

- `score` — a number (higher is better)
- `time` — seconds (`42.1`) or `mm:ss` (`1:23.4`); used only to break score ties

Then regenerate and publish the brackets:

```bash
python3 bracket.py    # ranks each category (score desc, time tiebreak) and
                      # seeds the top-N into docs/bracket.json
git add results docs/bracket.json
git commit -m "Publish NERC26 brackets" && git push
```

`bracket.py` also writes `docs/schedule.json`, rendered by `docs/schedule.html`
as the **Day-2 head-to-head match schedule** — matches grouped by venue
(Auditorium, then Central Activity Room) and category, with estimated start
times. Round-1 matches show the seeded teams; later same-day rounds show
"Winner of Match X vs Winner of Match Y". The Day-2 layout (venues, categories,
rounds) is defined in `DAY2` in `bracket.py`, mirroring
`data/Timing Plan brackets.csv`. (Day-3 finals and live winner scoring come later.)

The public page `docs/bracket.html` shows each bracket. Round 1 is seeded from
the heat ranking (#1 vs lowest qualifier, etc.); later rounds show **TBD** until
winners are recorded. A category with no scores yet shows as *pending*.

Bracket sizes are set per category in `BRACKET_SIZE` at the top of `bracket.py`
(top 32 for Indigenous and Modular School, top 16 for the Ready-to-Race events,
top 8 for Modular University).

## Website

The site under `docs/` reads `docs/data.json` and shows headline numbers plus
breakdowns by event and city. To publish:

1. Push this repo to GitHub.
2. **Settings → Pages → Source:** deploy from `main` branch, `/docs` folder.

Then open it locally any time with:

```bash
python3 -m http.server -d docs 8000   # http://localhost:8000
```

## Insights currently produced

- Total teams and participants
- Fees paid vs unpaid, and amount collected
- In-station vs out-station teams
- Breakdown by event, city, institution, and gender
- Team-size distribution
