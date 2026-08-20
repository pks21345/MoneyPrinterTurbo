#!/usr/bin/env sh

# MoneyPrinterTurbo Easy launcher for macOS/Linux.
# Keeps the original webui.sh untouched and starts only the Easy entrypoint.

CURRENT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export PYTHONPATH="$CURRENT_DIR${PYTHONPATH:+:$PYTHONPATH}"

MPT_EASY_HOST="${MPT_EASY_HOST:-127.0.0.1}"
MPT_EASY_PORT="${MPT_EASY_PORT:-8501}"
MPT_EASY_OPEN_BROWSER="${MPT_EASY_OPEN_BROWSER:-0}"

if [ -x "$CURRENT_DIR/.venv/bin/python" ]; then
  PORT_CHECK_CMD="$CURRENT_DIR/.venv/bin/python"
  set -- "$CURRENT_DIR/.venv/bin/python" -m streamlit
elif command -v uv >/dev/null 2>&1; then
  PORT_CHECK_CMD="uv run python"
  set -- uv run streamlit
elif command -v streamlit >/dev/null 2>&1; then
  echo "***** Warning: using streamlit from PATH. If dependencies fail, run 'uv sync --frozen' first. *****"
  PORT_CHECK_CMD="python3"
  set -- streamlit
else
  echo "***** MPT Easy could not find project Python, uv, or streamlit. *****"
  echo "***** Install the project dependencies first, then run this launcher again. *****"
  exit 1
fi

find_available_port() {
  EASY_HOST="$MPT_EASY_HOST" EASY_PORT="$MPT_EASY_PORT" "$@" - <<'PY' 2>/dev/null
import os
import socket
import sys

host = os.environ.get("EASY_HOST", "127.0.0.1")
preferred = int(os.environ.get("EASY_PORT", "8501"))
candidates = [preferred] + [port for port in range(8502, 8600) if port != preferred]

for port in candidates:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
        except OSError:
            continue
        print(port)
        sys.exit(0)

sys.exit(1)
PY
}

# shellcheck disable=SC2086
SELECTED_EASY_PORT=$(find_available_port $PORT_CHECK_CMD)

if [ -z "$SELECTED_EASY_PORT" ]; then
  echo "***** MPT Easy could not find an available port in 8501-8599 for $MPT_EASY_HOST. *****"
  exit 1
fi

if [ "$SELECTED_EASY_PORT" != "$MPT_EASY_PORT" ]; then
  echo "***** Port $MPT_EASY_PORT is busy; MPT Easy will use $SELECTED_EASY_PORT. *****"
fi

MPT_EASY_PORT="$SELECTED_EASY_PORT"
EASY_URL="http://$MPT_EASY_HOST:$MPT_EASY_PORT"

echo "***** MPT Easy: $EASY_URL *****"

if [ "$MPT_EASY_OPEN_BROWSER" = "1" ]; then
  if command -v open >/dev/null 2>&1; then
    (sleep 2; open "$EASY_URL" >/dev/null 2>&1 || true) &
  elif command -v xdg-open >/dev/null 2>&1; then
    (sleep 2; xdg-open "$EASY_URL" >/dev/null 2>&1 || true) &
  fi
fi

"$@" run "$CURRENT_DIR/webui/easy/App.py" \
  --server.address="$MPT_EASY_HOST" \
  --server.port="$MPT_EASY_PORT" \
  --browser.serverAddress="$MPT_EASY_HOST" \
  --browser.gatherUsageStats=False \
  --client.toolbarMode=minimal \
  --logger.hideWelcomeMessage=True \
  --server.showEmailPrompt=False \
  --server.enableCORS=True
