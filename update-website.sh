#!/usr/bin/env bash
# Update Website — regenerate the published data and push it to GitHub Pages.
#
# Safe to run at any stage; it just regenerates everything and commits whatever
# changed:
#   * after the DRAW              -> publishes docs/draw.json, brackets reset to "pending"
#   * after entering heat scores  -> seeds the knockout round 1
#   * after entering match winners-> advances the bracket + schedule
#
# Edit results/<category>.csv (heat score/time) or results/<category>_bracket.csv
# (winner) first, then run this.

set -euo pipefail
cd "$(dirname "$0")"          # always run from the repo root (where this lives)

echo "==> Regenerating insights        (process.py)"
python3 process.py

echo "==> Regenerating brackets + schedule (bracket.py)"
python3 bracket.py

echo "==> Staging changes"
git add -A                    # docs/ + results/ are tracked; data/ + output/ are gitignored

if git diff --cached --quiet; then
  echo "Nothing changed — website is already up to date."
  exit 0
fi

echo "----- changes to publish -----"
git status --short
echo "------------------------------"

git commit -m "Update website: $(date '+%Y-%m-%d %H:%M')"

branch="$(git rev-parse --abbrev-ref HEAD)"
echo "==> Pushing to origin/$branch"
git push

echo "Done. GitHub Pages will refresh in a minute or two."
