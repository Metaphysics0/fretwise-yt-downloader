#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="$(cd "$(dirname "$0")" && pwd)"
POT_SERVER_DIR="${POT_SERVER_DIR:-/opt/pot-server/server}"
if [[ ! -f "$POT_SERVER_DIR/build/main.js" ]]; then
    POT_SERVER_DIR="$APP_ROOT/.pot-server/server"
fi
POT_LOG="/tmp/pot-server.log"
POT_PORT="${POT_PORT:-4416}"
NODE_PATH="${NODE_PATH:-$(command -v node)}"

cleanup() {
    echo "[start.sh] Shutting down..."
    for pid in "${UVICORN_PID:-}" "${POT_PID:-}"; do
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid"
            wait "$pid" 2>/dev/null || true
        fi
    done
}
trap cleanup SIGTERM SIGINT EXIT

if [[ ! -f "$POT_SERVER_DIR/build/main.js" ]]; then
    echo "[start.sh] Missing POT server build at $POT_SERVER_DIR/build/main.js"
    exit 1
fi

echo "[start.sh] Starting uvicorn..."
uvicorn app.main:app --host 0.0.0.0 --port 8080 &
UVICORN_PID=$!

for _ in $(seq 1 30); do
    if curl --silent --output /dev/null http://127.0.0.1:8080/openapi.json; then
        break
    fi
    if ! kill -0 "$UVICORN_PID" 2>/dev/null; then
        wait "$UVICORN_PID" 2>/dev/null || true
        exit 1
    fi
    sleep 1
done

if ! curl --silent --output /dev/null http://127.0.0.1:8080/openapi.json; then
    echo "[start.sh] Uvicorn did not bind port 8080"
    exit 1
fi

echo "[start.sh] Starting bgutil POT server on port $POT_PORT..."
"$NODE_PATH" "$POT_SERVER_DIR/build/main.js" --port "$POT_PORT" \
    > "$POT_LOG" 2>&1 &
POT_PID=$!

wait "$UVICORN_PID"
