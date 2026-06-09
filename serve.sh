#!/usr/bin/env bash
# Serve the docs/ directory locally, killing any previous server on the port first.
set -euo pipefail

PORT="${1:-8000}"
DIR="docs"

# Kill any process currently listening on the port.
if pid=$(lsof -ti :"$PORT" -sTCP:LISTEN 2>/dev/null); then
    echo "Killing existing process on port $PORT (PID $pid)..."
    kill "$pid"
    # Wait for the port to be released.
    for _ in $(seq 1 10); do
        lsof -ti :"$PORT" -sTCP:LISTEN >/dev/null 2>&1 || break
        sleep 0.2
    done
fi

echo "Serving $DIR/ at http://localhost:$PORT"
exec python3 -m http.server -d "$DIR" "$PORT"
