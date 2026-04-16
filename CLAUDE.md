# AJ-Copytrader — Session Context & Architecture

> This file preserves the full context from the Claude session that built this bot
> so any new session can pick up exactly where we left off.

---

## 🎯 Goal

Passive income of **$100/day** by autonomously copy-trading the top Polymarket traders
at **$5/trade** stake from an AWS EC2 VPS.

**Current status:** Bot running LIVE on VPS with $98.98 USDC loaded. v5 deployed.

---

## 📁 File Map

| File | Purpose |
|------|---------|
| `copytrade_bot.py` | Main autonomous bot (v5) |
| `test_bot.py` | 42-unit test suite — run before every deploy |
| `.env.template` | Config template — copy to `.env` and fill in |
| `.env` | **NOT committed** — contains PRIVATE_KEY |
| `requirements.txt` | pip dependencies |
| `start.sh` | Screen session launcher for VPS |
| `trade_log.jsonl` | Append-only trade execution log |
| `CLAUDE.md` | This file |

---

## 🏗 Architecture

```
Polymarket Data API (polling every 30s)
         │
         ▼
  fetch_new_since()  ← composite watermark {ts, hashes}
         │
         ▼
  FillAggregator     ← groups micro-fills on same market/side/asset (60s window)
         │
         ▼
  execute_group()
    ├── get_live_price()  ← fetches bid/ask from CLOB order book
    ├── RiskManager.check()  ← slippage, per-market cap, daily loss stop
    ├── place_order()  ← CLOB MarketOrderArgs, OrderType.FOK
    ├── RiskManager.record()
    ├── write_log()  → trade_log.jsonl
    └── send_telegram()  → Telegram bot notification
```

---

## 👥 Trader Watchlist (5 traders)

| Priority | Name | Wallet | ROI | Notes |
|----------|------|--------|-----|-------|
| P1 ⭐ | 0x4815162342 | `0xa0f8b626bf42c179ccfb8abd67aba00f1363b80d` | 60.7% | Crypto directional |
| P1 ⭐ | FeatherLeather | `0xd25c72ac0928385610611c8148803dc717334d20` | 49.6% | Crypto neg-risk |
| P2 | A1d29 | `0x1f1dd8cf3d2c653edbdf319b81079bd753409a6f` | 27.6% | Crypto exits (100% sells) |
| P2 | 0x6a57D2 | `0x6a57d263cd7c8eba88b857edeb7103851f012afa` | 23.9% | NBA Basketball |
| P2 | C.SIN | `0x91654fd592ea5339fc0b1b2f2b30bfffa5e75b98` | 17.4% | Crypto multi-market |

`PRIORITY_LEVEL=1` → copies P1 only (top 2)
`PRIORITY_LEVEL=2` → copies all 5

**Expected EV at $5/trade (all 7 copyable, PRIORITY_LEVEL=2):** ~$108.94/day

---

## 🌐 Polymarket API Schema (verified 2026-02-25)

Activity endpoint: `https://data-api.polymarket.com/activity?user={wallet}&limit=50`

```json
{
  "type": "TRADE",            // "TRADE" | "REDEEM" — only process TRADE
  "side": "BUY",              // "BUY" | "SELL"
  "asset": "71321045...",     // ERC1155 token ID = CLOB token_id  ← NOT asset_id/assetId
  "transactionHash": "0x...", // dedup key  ← NOT id
  "timestamp": 1771248000,    // unix seconds
  "outcomeIndex": 0,          // 0=Yes, 1=No, 999=Redeem
  "outcome": "Yes",           // direct label
  "price": 0.42,              // per-share price
  "usdcSize": 580.0,          // USDC spent  ← use this for weighting
  "size": 580.0,              // shares (may differ from usdcSize)
  "conditionId": "0xdd22...", // market condition ID (used as fill aggregator key)
  "eventSlug": "will-btc-...",// URL: polymarket.com/event/{eventSlug}
  "title": "Will BTC...",     // market title for display
  "proxyWallet": "0xa0f8..."  // trader's wallet
}
```

**REDEEMs** have: `type="REDEEM"`, `asset=""`, `side=""`, `outcomeIndex=999` — easy to filter.

---

## ⚙️ Environment Variables

```bash
PRIVATE_KEY=0x...              # Rabby/MetaMask EOA key — signs CLOB messages (NEVER commit)
POLY_FUNDER_ADDRESS=0x...      # Polymarket proxy wallet — holds your USDC balance
POLY_SIGNATURE_TYPE=0          # 0=EOA (Rabby), 1=Safe, 2=L2
POLY_API_KEY=...               # From polymarket.com → Settings → API
POLY_API_SECRET=...
POLY_API_PASSPHRASE=...
STAKE_USDC=5.0                 # USD per copy trade
POLL_INTERVAL=30               # seconds between polls
PRIORITY_LEVEL=1               # 1 = P1 only, 2 = all traders
SKIP_SELLS=true                # skip SELL activity (exits)
DRY_RUN=true                   # true = log only, false = real orders
MAX_SLIPPAGE=0.05              # 5% max price movement vs signal
MAX_PER_MARKET_USDC=50.0       # max USDC in any single market token
MAX_DAILY_LOSS_USDC=50.0       # daily loss stop
FILL_AGG_WINDOW_SEC=60         # micro-fill aggregation window
CLOB_HOST=https://clob.polymarket.com
CHAIN_ID=137                   # Polygon mainnet
TELEGRAM_BOT_TOKEN=...         # Telegram bot token (optional — rotate if exposed)
TELEGRAM_CHAT_ID=...           # Your Telegram chat ID (optional)
PROXY_URL=...                  # http://user:pass@host:port (SmartProxy for geoblock)
```

---

## 🤖 Telegram Setup

1. **Get your chat_id:**
   - Message your bot on Telegram (find it by searching its username)
   - Visit: `https://api.telegram.org/bot{TOKEN}/getUpdates`
   - Find `"chat":{"id": YOUR_CHAT_ID}` in the response

2. **Add to VPS `.env`:**
   ```bash
   TELEGRAM_BOT_TOKEN=<your_bot_token_from_BotFather>
   TELEGRAM_CHAT_ID=YOUR_CHAT_ID_HERE
   ```

3. **Notifications sent for:**
   - Bot startup (mode, traders, config)
   - Every copy trade placed (market, side, price, stake, P&L)
   - Trade skipped by risk manager (with reason)
   - Page cap warning (may have missed trades)
   - Heartbeat every 10 polls (~5 min)
   - Bot shutdown
   - Main loop errors / execute_group errors
   - Daily reset with yesterday's P&L

---

## 🖥 VPS Details

| | |
|--|--|
| **Host** | `ec2-100-48-53-78.compute-1.amazonaws.com` |
| **User** | `ubuntu` |
| **OS** | Ubuntu 24.04 LTS |
| **SSH key** | `~/.ssh/copytrade-vps.pem` |
| **Bot dir** | `~/copytrade/` |
| **Python venv** | `~/venv/` |
| **Screen session** | `bot` |

### VPS Commands

```bash
# SSH in
ssh -i ~/.ssh/copytrade-vps.pem ubuntu@ec2-100-48-53-78.compute-1.amazonaws.com

# Watch live logs
tail -f ~/copytrade/bot.log

# Check trade history
cat ~/copytrade/trade_log.jsonl | python3 -m json.tool | tail -100

# Stop bot
screen -S bot -X quit

# Start bot
cd ~/copytrade && screen -dmS bot bash -c '~/venv/bin/python3 -u copytrade_bot.py 2>&1 | tee -a bot.log'

# Attach to running session
screen -r bot
# Detach: Ctrl+A then D

# Run tests
cd ~/copytrade && ~/venv/bin/python3 -u test_bot.py
```

---

## 🔧 CLOB Client (py-clob-client)

### Account binding (EOA signer + proxy funder wallet)

Polymarket creates a **proxy wallet** (funder) for each user — this holds the USDC.
The **EOA signer** (Rabby/MetaMask key) signs CLOB messages on behalf of the funder.

```python
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import MarketOrderArgs, OrderType, ApiCreds
from py_clob_client.order_builder.constants import BUY, SELL

# EOA signer key = Rabby wallet private key
# funder         = Polymarket proxy wallet address (0xacBcB5...)
# signature_type = 0 for standard EOA (MetaMask/Rabby)
client = ClobClient(
    "https://clob.polymarket.com",
    key            = PRIVATE_KEY,           # Rabby EOA — signs messages
    chain_id       = 137,
    signature_type = POLY_SIGNATURE_TYPE,   # 0 = EOA, 1 = Safe, 2 = L2
    funder         = POLY_FUNDER_ADDRESS,   # funded proxy wallet
)
client.set_api_creds(ApiCreds(
    api_key        = POLY_API_KEY,
    api_secret     = POLY_API_SECRET,
    api_passphrase = POLY_API_PASSPHRASE,
))

# Place market order
signed = client.create_market_order(MarketOrderArgs(token_id=token_id, amount=5.0, side=BUY))
resp   = client.post_order(signed, OrderType.FOK)

# Get order book for slippage check
book = client.get_order_book(token_id)
best_ask = min(float(a.price) for a in book.asks)  # BUY: use asks
best_bid = max(float(b.price) for b in book.bids)  # SELL: use bids
```

---

## 🐛 Bugs Fixed (Full History)

### Schema Bugs (discovered by fetching live API)
- ❌ Used `asset_id` / `assetId` → ✅ field is `asset`
- ❌ Used `id` as dedup key → ✅ field is `transactionHash`
- ❌ Filtered `type in ("BUY", "PURCHASE")` → ✅ `type == "TRADE"` and check `side`
- ❌ Tried to copy both sides of neg-risk markets → ✅ removed; activity only shows one side

### Codex Review Bugs (v4 → v5)
1. **Same-second watermark** — timestamp-only watermark dropped same-second trades
   - Fix: composite `{"ts": int, "hashes": set}` watermark
2. **Page cap silent miss** — `max_pages=3` could silently miss burst activity
   - Fix: explicit WARN log + Telegram alert when page cap hit
3. **Wrong order book side for slippage** — always used ask even for SELL
   - Fix: `get_live_price()` returns bid for SELL, ask for BUY
4. **First-fill price + wrong size field** — used first fill's price and `size` not `usdcSize`
   - Fix: weighted average price by `usdcSize`; log both `orig_usdc` and `orig_size`
5. **Daily loss counts SELLs** — `record()` decremented P&L for SELL orders
   - Fix: only BUY side decrements `daily_pnl` and increments `market_exposure`

### Proxy / CLOB Bugs (v5 → v5.1, Feb 2026)
6. **httpx singleton not proxied** — `py-clob-client` uses `httpx.Client(http2=True)` created
   at module-level import time. `os.environ["HTTPS_PROXY"]` set after import has no effect,
   and `http2=True` + proxy breaks SSL tunnelling. Fix: monkey-patch the singleton directly:
   ```python
   import httpx as _hx; import py_clob_client.http_helpers.helpers as _ch
   _ch._http_client = _hx.Client(proxy=PROXY_URL)   # no http2, explicit proxy
   ```
   This must run **after** `PROXY_URL` is read from env and **before** any CLOB calls.

7. **No retry on 403 geoblock** — SmartProxy pools have mixed geo exit IPs (US + non-US).
   A single attempt that hits a Turkish/blocked IP fails permanently. Fix: `_rotate_clob_proxy()`
   recreates the httpx singleton on each 403 (new connection = new exit IP from pool). Up to
   5 attempts; attempt 4 tries direct (no proxy) as fallback. Same pattern as the reference
   JS bot (`openclaw-workspace/polymarket-bot-v4/executor.js`).
   ```python
   def _rotate_clob_proxy(direct=False):
       import httpx as _hx; import py_clob_client.http_helpers.helpers as _ch
       _ch._http_client = _hx.Client() if (direct or not PROXY_URL) else _hx.Client(proxy=PROXY_URL)
   ```

---

## 📊 Analysis Results (Feb 2026)

Source: Polymarket top-50 monthly leaderboard, `orderBy=PNL`

**7 copyable traders** (≤20 trades/day, ROI ≥10%):

| Trader | ROI | Avg stake | EV/trade |
|--------|-----|-----------|----------|
| 0x4815162342 | 60.7% | $5 | $3.04 |
| FeatherLeather | 49.6% | $5 | $2.48 |
| A1d29 | 27.6% | $5 | $1.38 |
| 0x6a57D2 | 23.9% | $5 | $1.20 |
| C.SIN | 17.4% | $5 | $0.87 |

All 5 at $5/trade ≈ **$108.94/day EV** (hits $100 goal).
Top 2 only (P1) ≈ **~$55/day EV**.

Analysis JSON: `/Users/rizz/Documents/Research on CopyTrade/copytrade (codex)/analysis_output/polymarket_top50_monthly_analysis_20260225.json`

---

## 🚀 Deploy Checklist

```bash
# 1. Run tests locally first
python3 -u test_bot.py   # must be 42/42 PASS

# 2. SCP to VPS
scp -i ~/.ssh/copytrade-vps.pem \
    copytrade_bot.py test_bot.py requirements.txt start.sh \
    ubuntu@ec2-100-48-53-78.compute-1.amazonaws.com:~/copytrade/

# 3. On VPS: install any new deps
ssh -i ~/.ssh/copytrade-vps.pem ubuntu@ec2-100-48-53-78.compute-1.amazonaws.com \
    "~/venv/bin/pip install -r ~/copytrade/requirements.txt -q"

# 4. On VPS: run tests
ssh -i ~/.ssh/copytrade-vps.pem ubuntu@ec2-100-48-53-78.compute-1.amazonaws.com \
    "cd ~/copytrade && ~/venv/bin/python3 -u test_bot.py"

# 5. Restart bot
ssh -i ~/.ssh/copytrade-vps.pem ubuntu@ec2-100-48-53-78.compute-1.amazonaws.com "
  screen -S bot -X quit 2>/dev/null || true
  sleep 1
  cd ~/copytrade
  screen -dmS bot bash -c '~/venv/bin/python3 -u copytrade_bot.py 2>&1 | tee -a bot.log'
  sleep 8
  tail -30 bot.log
"
```

---

## 🔮 Future Improvements

- [ ] Position tracking (know when a market resolves, track actual P&L)
- [ ] Trailing stop on losing positions
- [ ] Auto-scale stake based on trader ROI confidence
- [ ] Weekly performance report via Telegram
- [ ] Add more traders from leaderboard refresh (check monthly)
- [ ] SELL copy for A1d29 (who is 100% sells — could mirror exits)
- [ ] Web dashboard for trade history
