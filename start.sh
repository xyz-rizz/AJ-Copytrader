#!/bin/bash
# ─────────────────────────────────────────────────────────────────
#  Start / Restart the Copy-Trade Bot  (Ireland server)
# ─────────────────────────────────────────────────────────────────

BOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BOT_SCRIPT="$BOT_DIR/copytrade_bot.py"
LOGFILE="$BOT_DIR/bot.log"
PIDFILE="$BOT_DIR/bot.pid"

if [ ! -f "$BOT_DIR/.env" ]; then
    echo "❌  .env not found."
    exit 1
fi

# Kill existing instance if running
if [ -f "$PIDFILE" ]; then
    OLD_PID=$(cat "$PIDFILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "  Stopping existing bot (PID $OLD_PID)..."
        kill "$OLD_PID"
        sleep 2
    fi
    rm -f "$PIDFILE"
fi

# Resolve python
if   [ -f "$HOME/venv/bin/python3"     ]; then PYTHON="$HOME/venv/bin/python3"
elif [ -f "$BOT_DIR/venv/bin/python3"  ]; then PYTHON="$BOT_DIR/venv/bin/python3"
else PYTHON="python3"
fi

echo "  Using Python: $PYTHON"
echo "  Log file    : $LOGFILE"

# Launch with nohup — works reliably over SSH without a PTY
nohup "$PYTHON" -u "$BOT_SCRIPT" >> "$LOGFILE" 2>&1 &
BOT_PID=$!
echo $BOT_PID > "$PIDFILE"

sleep 3

if kill -0 "$BOT_PID" 2>/dev/null; then
    echo "✅  Bot started (PID $BOT_PID)"
    echo ""
    echo "  Tail log:    tail -f $LOGFILE"
    echo "  Stop bot:    kill \$(cat $PIDFILE)"
    echo ""
    tail -20 "$LOGFILE"
else
    echo "❌  Bot failed to start. Check bot.log:"
    tail -20 "$LOGFILE"
    exit 1
fi
