#!/usr/bin/env bash
# Start or stop the editor so it keeps running after the shell exits.
# Frontend listens on 0.0.0.0:5173; backend stays on 127.0.0.1:8000.
# ./serve.sh start  — starts fresh; if anything is already up, restarts first.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$ROOT/.run"
mkdir -p "$RUN_DIR"

BACKEND_PID="$RUN_DIR/backend.pid"
FRONTEND_PID="$RUN_DIR/frontend.pid"
BACKEND_LOG="$RUN_DIR/backend.log"
FRONTEND_LOG="$RUN_DIR/frontend.log"

alive() {
  local pidfile="$1"
  [[ -f "$pidfile" ]] || return 1
  local pid
  pid="$(cat "$pidfile")"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

port_busy() {
  local port="$1"
  ss -ltn "sport = :$port" 2>/dev/null | grep -q LISTEN
}

free_port() {
  local port="$1"
  if command -v fuser >/dev/null 2>&1; then
    fuser -k "${port}/tcp" >/dev/null 2>&1 || true
  else
    local p
    while read -r p; do
      [[ -n "$p" ]] && kill "$p" 2>/dev/null || true
    done < <(ss -ltnp "sport = :$port" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | sort -u)
  fi
  sleep 0.5
  if port_busy "$port"; then
    if command -v fuser >/dev/null 2>&1; then
      fuser -k -KILL "${port}/tcp" >/dev/null 2>&1 || true
    fi
  fi
}

stop_one() {
  local name="$1" pidfile="$2"
  if alive "$pidfile"; then
    kill "$(cat "$pidfile")" 2>/dev/null || true
    sleep 0.5
    if alive "$pidfile"; then
      kill -9 "$(cat "$pidfile")" 2>/dev/null || true
    fi
    echo "stopped $name"
  fi
  rm -f "$pidfile"
}

stop_all() {
  stop_one frontend "$FRONTEND_PID"
  stop_one backend "$BACKEND_PID"
  free_port 5173
  free_port 8000
}

needs_restart() {
  alive "$BACKEND_PID" || alive "$FRONTEND_PID" || port_busy 8000 || port_busy 5173
}

start() {
  if needs_restart; then
    echo "restarting..."
    stop_all
  fi

  if [[ ! -x "$ROOT/backend/.venv/bin/uvicorn" ]]; then
    echo "missing backend venv: $ROOT/backend/.venv" >&2
    exit 1
  fi
  if [[ ! -d "$ROOT/frontend/node_modules" ]]; then
    echo "missing frontend deps, run: cd frontend && npm install" >&2
    exit 1
  fi

  if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q "Status: active"; then
    ufw allow 5173/tcp >/dev/null || echo "could not open 5173 (try: sudo ufw allow 5173/tcp)"
  fi

  (
    cd "$ROOT/backend"
    nohup .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 \
      >>"$BACKEND_LOG" 2>&1 &
    echo $! >"$BACKEND_PID"
  )

  (
    cd "$ROOT/frontend"
    nohup npm run dev -- --host 0.0.0.0 --port 5173 \
      >>"$FRONTEND_LOG" 2>&1 &
    echo $! >"$FRONTEND_PID"
  )

  sleep 1
  status
  echo "logs: $BACKEND_LOG  $FRONTEND_LOG"
}

status() {
  if alive "$BACKEND_PID"; then
    echo "backend  pid $(cat "$BACKEND_PID")  http://127.0.0.1:8000"
  elif port_busy 8000; then
    echo "backend  port 8000 in use (no pid file)"
  else
    echo "backend  stopped"
  fi
  if alive "$FRONTEND_PID"; then
    echo "frontend pid $(cat "$FRONTEND_PID")  http://0.0.0.0:5173"
  elif port_busy 5173; then
    echo "frontend port 5173 in use (no pid file)"
  else
    echo "frontend stopped"
  fi
}

case "${1:-start}" in
  start) start ;;
  stop)
    stop_all
    echo "stopped"
    ;;
  status) status ;;
  restart)
    stop_all
    start
    ;;
  *)
    echo "usage: $0 {start|stop|status|restart}" >&2
    exit 1
    ;;
esac
