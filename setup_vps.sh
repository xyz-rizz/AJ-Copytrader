#!/bin/bash
# ─────────────────────────────────────────────────────────────────
#  VPS Setup Script — Polymarket Copy-Trade Bot
#  Run this ONCE on a fresh Ubuntu 22.04 VPS
#  $ bash setup_vps.sh
# ─────────────────────────────────────────────────────────────────

set -e
echo "=== Installing system deps ==="
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv screen curl

echo "=== Creating venv ==="
python3 -m venv /opt/copytrade_venv
source /opt/copytrade_venv/bin/activate

echo "=== Installing Python deps ==="
pip install -q py-clob-client python-dotenv

echo "=== Copying bot files ==="
mkdir -p /opt/copytrade
cp copytrade_bot.py  /opt/copytrade/
cp .env.template     /opt/copytrade/.env.template
cp start.sh          /opt/copytrade/
cp requirements.txt  /opt/copytrade/
chmod +x /opt/copytrade/start.sh

echo ""
echo "✅  Done! Next steps:"
echo ""
echo "  1.  cd /opt/copytrade"
echo "  2.  cp .env.template .env"
echo "  3.  nano .env           # add your PRIVATE_KEY, set DRY_RUN=true"
echo "  4.  bash start.sh       # starts bot in a persistent screen session"
echo ""
