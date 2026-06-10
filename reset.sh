#!/usr/bin/env bash
# Reset — wipe all test draw + bracket data back to the clean pre-ceremony state.
#
# Run this after a test ceremony to clear the random draw and any entered heat
# scores / match winners, so the website shows no solo-run heats and every
# bracket reads "pending" again.
#
# Removes:
#   * docs/draw.json   -> the solo-run draw (so heats vanish from the schedule)
#   * results/*.csv    -> heat seeding CSVs + bracket winner CSVs (test scores)
# Then regenerates docs/schedule.json and docs/bracket.json (all categories
# pending, head-to-head matches showing "Seed N" placeholders).
#
# This does NOT push. Run ./update-website.sh afterwards to publish the reset.
# A fresh DRAW in app.py recreates everything, so testing can resume any time.

set -euo pipefail
cd "$(dirname "$0")"          # always run from the repo root (where this lives)

echo "==> Removing draw + results (test data)"
rm -f docs/draw.json
rm -f results/*.csv

echo "==> Regenerating brackets + schedule (bracket.py)"
python3 bracket.py

echo
echo "Reset complete — schedule has no heats and every bracket is 'pending'."
echo "Run ./update-website.sh to publish this reset."
