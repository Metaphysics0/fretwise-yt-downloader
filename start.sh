#!/bin/bash
set -euo pipefail

POT_SERVER_DIR="/opt/pot-server/server"
POT_LOG="/tmp/pot-server.log"
POT_PORT=4416

# Clean shutdown: kill POT server when this script exits
cleanup() {
    echo "[start.sh] Shutting down..."
    if [ -n "${POT_PID:-}" ] && kill -0 "$POT_PID" 2>/dev/null; then
        kill "$POT_PID"
        wait "$POT_PID" 2>/dev/null || true
    fi
}
trap cleanup SIGTERM SIGINT EXIT

# Start POT server in background
echo "[start.sh] Starting bgutil POT server on port $POT_PORT..."
node "$POT_SERVER_DIR/build/main.js" --port "$POT_PORT" \
    > "$POT_LOG" 2>&1 &
POT_PID=$!

# Wait for POT server to be ready (up to 30s)
echo "[start.sh] Waiting for POT server to be ready..."
for i in $(seq 1 30); do
    if curl -s "http://127.0.0.1:${POT_PORT}/ping" > /dev/null 2>&1; then
        echo "[start.sh] POT server ready after ${i}s"
        break
    fi
    if ! kill -0 "$POT_PID" 2>/dev/null; then
        echo "[start.sh] ERROR: POT server exited prematurely. Logs:"
        cat "$POT_LOG"
        echo "[start.sh] Continuing without POT server..."
        break
    fi
    sleep 1
done

# Check if we timed out
if ! curl -s "http://127.0.0.1:${POT_PORT}/ping" > /dev/null 2>&1; then
    echo "[start.sh] WARNING: POT server not responding after 30s. Continuing anyway..."
    echo "[start.sh] POT server logs:"
    cat "$POT_LOG"
fi

# Start uvicorn in foreground (replaces this shell process for signal handling)
echo "[start.sh] Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8080
