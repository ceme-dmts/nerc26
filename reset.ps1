# Reset - wipe all test draw + bracket data back to the clean pre-ceremony state.
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
# This does NOT push. Run .\update-website.ps1 afterwards to publish the reset.
# A fresh DRAW in app.py recreates everything, so testing can resume any time.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "==> Removing draw + results (test data)"
Remove-Item -Force "docs\draw.json" -ErrorAction SilentlyContinue
Remove-Item -Force "results\*.csv" -ErrorAction SilentlyContinue

Write-Host "==> Regenerating brackets + schedule (bracket.py)"
py bracket.py

Write-Host ""
Write-Host "Reset complete - schedule has no heats and every bracket is 'pending'."
Write-Host "Run .\update-website.ps1 to publish this reset."
