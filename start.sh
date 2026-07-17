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
    if [ -n "${POT_PID:-}" ] && kill -0 "$POT_PID" 2>/dev/null; then
        kill "$POT_PID"
        wait "$POT_PID" 2>/dev/null || true
    fi
}
trap cleanup SIGTERM SIGINT EXIT

if [[ ! -f "$POT_SERVER_DIR/build/main.js" ]]; then
    echo "[start.sh] Missing POT server build at $POT_SERVER_DIR/build/main.js"
    exit 1
fi

echo "[start.sh] Starting bgutil POT server on port $POT_PORT..."
"$NODE_PATH" "$POT_SERVER_DIR/build/main.js" --port "$POT_PORT" \
    > "$POT_LOG" 2>&1 &
POT_PID=$!

echo "[start.sh] Waiting for POT server to be ready..."
for i in $(seq 1 30); do
    if curl -s "http://127.0.0.1:${POT_PORT}/ping" > /dev/null 2>&1; then
        echo "[start.sh] POT server ready after ${i}s"
        break
    fi
    if ! kill -0 "$POT_PID" 2>/dev/null; then
        echo "[start.sh] ERROR: POT server exited prematurely. Logs:"
        cat "$POT_LOG"
        exit 1
    fi
    sleep 1
done

if ! curl -s "http://127.0.0.1:${POT_PORT}/ping" > /dev/null 2>&1; then
    echo "[start.sh] POT server not responding after 30s"
    echo "[start.sh] POT server logs:"
    cat "$POT_LOG"
    exit 1
fi

echo "[start.sh] Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8080
