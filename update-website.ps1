# Update Website - regenerate the published data and push it to GitHub Pages.
#
# Safe to run at any stage; it just regenerates everything and commits whatever
# changed:
#   * after the DRAW              -> publishes docs/draw.json, brackets reset to "pending"
#   * after entering heat scores  -> seeds the knockout round 1
#   * after entering match winners-> advances the bracket + schedule
#
# Edit results/<category>.csv (heat score/time) or results/<category>_bracket.csv
# (winner) first, then run this.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "==> Regenerating insights        (process.py)"
py process.py

Write-Host "==> Regenerating brackets + schedule (bracket.py)"
py bracket.py

Write-Host "==> Staging changes"
git add -A

git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "Nothing changed - website is already up to date."
    exit 0
}

Write-Host "----- changes to publish -----"
git status --short
Write-Host "------------------------------"

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"
git commit -m "Update website: $timestamp"

$branch = git rev-parse --abbrev-ref HEAD
Write-Host "==> Pushing to origin/$branch"
git push

Write-Host "Done. GitHub Pages will refresh in a minute or two."
