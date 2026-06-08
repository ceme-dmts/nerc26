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
templates/, static/   ceremony reveal UI
output/               generated insights.md + insights.json + seeding.*
docs/                 GitHub Pages site (index.html, draws.html, *.json)
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
