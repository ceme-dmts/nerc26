# Serve the docs/ directory locally, killing any previous server on the port first.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$PORT = if ($args[0]) { $args[0] } else { 8000 }
$DIR = "docs"

# Kill any process currently listening on the port.
$conn = Get-NetTCPConnection -LocalPort $PORT -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    $pid_ = $conn.OwningProcess | Select-Object -First 1
    Write-Host "Killing existing process on port $PORT (PID $pid_)..."
    Stop-Process -Id $pid_ -Force -ErrorAction SilentlyContinue
    # Wait for the port to be released.
    for ($i = 0; $i -lt 10; $i++) {
        Start-Sleep -Milliseconds 200
        if (-not (Get-NetTCPConnection -LocalPort $PORT -State Listen -ErrorAction SilentlyContinue)) { break }
    }
}

Write-Host "Serving $DIR/ at http://localhost:$PORT"
py -m http.server -d $DIR $PORT
