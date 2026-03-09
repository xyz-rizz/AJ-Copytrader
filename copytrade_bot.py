#!/usr/bin/env python3
"""
Polymarket Autonomous Copy-Trade Bot  v7.8.0
==========================================
v7.8.0 (2026-03-10) — COPY_DELAY_SEC=0 (disable broken reactive delay):
  Architecture audit confirmed COPY_DELAY_SEC is reactive-only: execute_group fires
  only on new source activity, so any non-zero delay permanently suppresses
  single-buy-and-hold traders (Signal47, Triangular-Box, Superb-Hyacinth, ~86%
  of Unwieldy-Forage). Setting to 0 disables the guard. Scalper protection is
  fully covered by roster bench (all quick-flip traders at priority=2).
  No roster/cap/stop changes. Backup: copytrade_bot.py.bak_pre780

v7.7.0 (2026-03-09) — EMERGENCY SURVIVAL MODE: roster cut + hard caps + copy delay:
  ROSTER: 9 traders benched (HeisenbergWalt ROI -69.6%, Sharp-c33a ROI -41.0%,
    Veteran-b512 zero-history micro-source, GEM-0x69aee micro-source ,
    SharpEdge-25a1 3-trade noise, jack66666 avg_entry=0.868, bigwhale1337 no edge,
    0x5524f06f Dota2 scalper no PnL, 0xec6604b0 high-freq no edge).
  KEEP: Triangular-Box, Unwieldy-Forage, Signal47-Bets, Superb-Hyacinth (proven +48-94% ROI).
  LEASH: Immense-Gokart max_stake → $15→$10 (+53.9% ROI, CS2 incident history).
  CAPS: Signal47 $30→$8 | Immense $15→$10 | Triangular $20→$8 | Unwieldy $22→$8 | Superb $15→$8.
  GLOBAL_STOP: -$200→-$25 | Signal47: -$30→-$8 | Immense: -$25→-$10 | default: -$15→-$8.
  COPY_DELAY_SEC=120: first copy of any new source position held 120s before execution.
    ⚠️ Architecture flaw — disabled v7.8.0. Reactive-only impl suppresses single-buy traders.
  _source_first_seen: module-level dict tracks first-detection timestamps per (trader, token).
  Backup: copytrade_bot.py.bak_pre770

==========================================
v7.6.17 (2026-03-09) — CLOB balance gate + SELL_MIRROR delayed SELL tracking:
  - CLOB hard gate in execute_group: skip BUY when _live_usdc < effective_stake.
    Prevents order-spam on empty exchange (6 failed API calls per burst when CLOB empty).
  - SELL_MIRROR abandoned-close: delayed SELL orders now added to _pending_claim_orders.
    poll_pending_claims tracks fill/expiry and logs proceeds. Fixes Kings-style silent loss.

v7.6.15 (2026-03-09) — False-orphan grace + 0xec6604b0 risk cut:
  - ORPHAN_GRACE_MIN: 10min → 20min. Jazz/Kings false-orphan cost -$6.93 (10m20s
    positions fired at the exact grace boundary). 20min prevents rapid in-play scalp
    exits from triggering abandon-close on freshly copied positions.
  - 0xec6604b0 max_stake: $15 → $8. High-frequency in-play scalper (Jazz+Kings both
    in/out within 10min). Nuggets+Phillies held — reduce size but keep active.

v7.6.14 (2026-03-08) — Post-incident risk controls:
  - BENCHED 0xc97f6383 (priority=2): -$74.51 realized losses in 1 session (Turkish soccer).
    avg_stake=$2.22 micro-bettor + poor sport selection = confirmed dud. Keep config intact.
  - REDUCED Immense-Gokart max_stake: $25 → $15. CS2 Map 1 specialist but lost both
    active map-1 positions today (-$94.85: FaZe/Monte + paiN/Aurora). Risk floor reduced.
    stake_mult unchanged at 0.9; re-evaluate after 10 further live results.

v7.4 additions (2026-03-05) — Crypto hard-ban + Safe CTF redemption:
  - BANNED crypto markets for ALL traders at hard-stop level (non-bypassable).
    Previously bypass_global_block traders (Triangular-Box, Unwieldy-Forage,
    Helpful-Contention) could still copy crypto markets. Now "crypto" is treated
    as a geopolitical-level hard stop: even bypass_global_block traders cannot
    trade crypto. is_globally_blocked() updated to check both geopolitical AND
    crypto for bypass traders.
  - BENCHED Helpful-Contention (priority=2): its sole category is crypto, so it
    will never trigger under the new hard-ban. Benched rather than removed in
    case policy changes in future.
  - FIXED CTF auto-claim: discovered funder (0xacBcB5) is a Gnosis Safe with
    0x8032 (PRIVATE_KEY) as sole owner (threshold=1). Rewrote _ctf_redeem() to
    call redeemPositions via Safe.execTransaction instead of direct EOA call.
    Manually redeemed 239.8 ETH-Up + 133.33 BTC-Up shares (~$373 USDC) via
    the new Safe-based redemption script.

v7.2 additions (2026-03-05) — Audit fixes: RPC, claims, logging, session P&L:
  - FIXED POLYGON_RPC: polygon-rpc.com had its API key disabled → all CTF win claims
    silently failed. Changed to 1rpc.io/matic (free, no auth, confirmed working).
    Added 2 fallback RPCs in _ctf_get_web3() so if primary fails, bot tries next.
    Impact: previously won positions could not be redeemed. Now auto-claimed on-chain.
  - REMOVED CS2-LoL-Sharp: 0W/5L live (confirmed dead weight). Its wallet actually
    bets NBA games (Hornets, Jazz, Thunder) which were ALL blocked by esports category
    filter — so we never caught any of its real signals. All esports bets placed = losses.
    Triangular-Box (generalist, bypass_global_block) covers all market categories now.
  - FIXED trade log attribution: CLAIM and RESOLVED_LOSS entries now include
    "trader" field. Previously unattributed → impossible to audit per-trader P&L.
  - ADDED session P&L: heartbeat now shows session_net (profit since bot start,
    resets on restart). Separate from global_net (daily realized losses counter).
    Tracks wins collected + losses taken since this process started.

v7.1 additions (2026-03-04) — Leaderboard Expansion + Category Bypass:
  - ADDED 4 new traders from leaderboard deep-scan (human-verified, all categories):
    · Triangular-Box:     99% WR (195W/1L) | avg /bin/zsh.658 | 6.0/d | 44d | sports/esports
    · Unwieldy-Forage:   100% WR (157W/0L) | avg /bin/zsh.473 | 4.2/d | 60d | NHL/soccer
    · Helpful-Contention: 99% WR (139W/2L) | avg /bin/zsh.285 | 21.5/d | 14d | crypto micro
    · Superb-Hyacinth:   100% WR (33W/0L)  | avg /bin/zsh.527 | 1.4/d  | 76d | NBA/NHL (thin)
  - ADDED per-trader bypass_global_block=True flag. Traders with this flag bypass the
    politics/crypto global block but are STILL hard-stopped by geopolitical (war/nuclear).
    Implements user directive: follow high-WR traders across ALL categories.
  - UPDATED is_globally_blocked(title, trader=None): when trader.bypass_global_block=True,
    only the geopolitical hard stop applies; politics/crypto pass through to per-trader filter.
  - UPDATED call site to pass trader= kwarg.
  - Global daily_stop unchanged at 569Xl200 (8 traders now active).

v7.0 additions (2026-03-04) — Capital Reallocation + Sizing Overhaul:
  - REMOVED MultiSport-8f80: 1W/11L (8.3% WR) live — confirmed dead weight, cut.
  - RAISED BASE STAKE: STAKE default $7 → $20, MAX_STAKE_PER_TRADE $20 → $40.
    Previous $2-5 per-trade output was structurally incapable of meaningful growth.
  - RAISED per-trader stake_mult + max_stake for all retained traders:
    · Signal47-Bets:    0.7× $12 → 1.2× $30 (53W/1L, highest conviction — NBA)
    · Immense-Gokart:   0.5× $12 → 0.9× $25 (53W/1L confirmed — CS2 map specialist)
    · GEM-0x69aee:      0.4× $10 → 0.6× $18 (57W/1L confirmed, multi-sport NO-side)
    · Quixotic-Average: 0.3× $8  → 0.4× $12 (432d vet, thin WR — keep conservative)
    · CS2-LoL-Sharp:    0.3× $8  → 0.5× $18 (high volume esports, unproven — watch)
  - FIXED false-positive keyword: removed "elon" from politics CATEGORY_KEYWORDS.
    "elon" is a substring of "barcelona" (b-a-r-c-e-l-o-n-a → positions 4-7 = e,l,o,n).
    Result: every FC Barcelona market was being blocked as "politics". "musk" already
    covers Elon Musk, so "elon" was both redundant and harmful. Now removed.
  - RAISED MAX_PER_MARKET: $40 → $80 to allow full position building on live matches.
  - UPDATED per-trader daily_stop limits to match new sizing (2× bad trades each).

v6.9 additions (2026-03-04):
  - AUDIT: Full post-v6.8 codebase audit — all 10 identified issues fixed.
  - Fix: execute_group SELL now removes orphaned _meta key (positions.json hygiene).
  - Fix: Confluence tracker keys on (conditionId, side, asset) — prevents YES+NO buyers
    from opposite outcomes inflating each other's confluence count.
  - Fix: SellMirror._fetch now uses confirmed API fields (asset→key, size→value in shares).
    Previously used unconfirmed currentValue/tokenId — silently tracked nothing. Now real.
  - Fix: SIZING_STEP now a fraction of price_adj_stake (default 30%) not a flat USDC amount.
    Old flat $5 dominated and defeated price-adjustment logic. New: proportional per-trader.
  - Fix: Added "crypto" to GLOBALLY_BLOCKED_CATEGORIES — generalist traders (MultiSport,
    GEM-0x69aee) can no longer copy crypto markets. Cleaned CATEGORY_KEYWORDS["crypto"]
    of broad false-positive keywords (eth, sol, sec, token removed).
  - Fix: Removed dead PER_TRADER_DAILY variable (was declared but never used in any logic).
  - Fix: Signal47-Bets note updated (was stale "2W/0L thin" — actual 53W/1L confirmed).
  - Raised DAILY_LOSS_STOPS global: -$80 → -$200 (per request, 6-trader operation).

v6.8 additions (2026-03-03):
  - Added 3 new traders:
    · GEM_0x69aee (multi-sport NO-side, 57W/1L trigger hit) stake_mult=0.4
    · Quixotic-Average (NBA underdog 432d vet, 16W/0L) stake_mult=0.3 probationary
    · 0x65b6662c / CS2-LoL-Sharp (CS2/LoL, 21.9/d, 0 bot clusters) stake_mult=0.3
  - Global daily stop $-55 → $-80 to accommodate 6 active traders.

v6.7 additions (2026-03-03):
  - Bug fix: takingAmount empty-string crash in BUY path. When Polymarket returns
    takingAmount:'' (delayed/resting order), estimate shares from stake/price so the
    position is still tracked and can be auto-claimed. Prevents positions falling off
    the radar when orders are not immediately filled.
  - Bug fix: takingAmount empty-string crash in try_claim SELL fallback (or 0 guard).
  - Bug fix: startup balance float(''): or 0 guard on bal.get("balance",0).
  - Raised MAX_SLIPPAGE 5%→8%: was blocking valid live-match signals (CS2/esports
    price moves 6-9% in ~25s latency window are normal and tradeable).

v6.6 additions (2026-03-03):
  - Added MultiSport-8f80 (0x8f80e8c2): deep-scan probationary, stake_mult=0.3,
    max_stake=$8, daily_stop=$-8. Multi-sport generalist (esports/NBA/NHL/tennis),
    12/d stable, 0 same-sec bot clusters, score=60.5.
  - Global daily stop $-40 → $-55 to accommodate 3rd trader.

v6.5 additions (2026-03-03):
  - Latency overhaul: avg latency ~80s → ~25s.
    POLL_INTERVAL 30→10s: 3× faster signal detection.
    FILL_AGG_WINDOW 60→15s: was the primary bottleneck — 45s shaved per trade.
    STALENESS_CUTOFF 300→90s: prevents copying signals older than 90s.
  - Latency logging: trader_ts + signal_age_sec now in every trade_log.jsonl entry.

v6.4 additions (2026-03-03):
  - Mass trader purge: removed 10 traders confirmed as bots or no-edge accounts.
    - Bots (100-360 buys/day, 1-4d account span): HedgeMaster88, Gleeful-Cauliflower,
      Drab-Muscatel, Speedy-Booster.
    - NO-on-impossible-outcomes (avg $0.92-$0.97): BAdiosB, Overjoyed-Mansion, Scared-Cape.
    - Wrong category/crypto: A1d29, 0x6a57D2, C.SIN.
  - Only Signal47-Bets retained (real NBA game-line bets, stake_mult reduced to 0.7).
  - Global daily stop reduced $80→$30 (single-trader mode, bankroll protection).
  - Per-trader stop: Signal47-Bets $-12 (tight until resolved≥10).

v6.3 additions (2026-03-03):
  - Removed White-Leaf from TRADERS list (scatter-shot, primary bleeder).
  - Bug fix: float(bal.get("balance", 0) or 0) — handles empty-string '' from API in
    both execute_group SELL path and try_claim WIN path. Prevents double-loss recording.
  - Bug fix: _meta key now stored on BUY success. try_claim now correctly attributes
    owner_name and stake per-trader → per-trader daily loss stops now function.

v6.2 additions (2026-03-02):
  - CTF on-chain redeemPositions(): auto-claims winners via Polygon web3 (no CLOB needed).
    Falls back to SELL, then Telegram alert. try_claim now runs every 20 polls not every poll.
  - SellMirror class: polls each trader's open positions every 2 polls; when a trader sells
    ≥30% of a position we mirror proportionally. Full exit (≥90%) removes position entirely.
  - Scanner auto-add: wallets scoring >= AUTO_ADD_SCORE injected into TRADERS list via # END_TRADERS marker.

Hotfix 2026-03-01:

  BUG 1 FIXED: Daily loss stop used DEPLOYED capital as a proxy for realized losses.
    White-Leaf deployed $35 in OPEN positions → net showed as -$35 → hit limit → BLOCKED.
    Fix: RiskManager now tracks `realized_losses` separately (only incremented on confirmed
    closed losses via try_claim). Deployed capital in open positions is ignored by loss stop.
    Also fixed off-by-one: changed `<=` to `<` so limit is only triggered when exceeded.

  BUG 2 FIXED: Sizing-up mechanic had no per-market buy cap.
    HedgeMaster88 bought Club León 5× overnight ($40 concentration on one match).
    Fix: Added MAX_BUYS_PER_MARKET = 2. Bot will size up at most once per market per day.

  BUG 3 FIXED: CLAIM detection logged 400+ ERROR lines per day for the same WIN token.
    Club León resolved as WIN but SELL failed (CLOB closed) → bot retried every 30s.
    `_claim_alerted` prevented Telegram spam but NOT the log spam.
    Fix: Skip entire token processing when already in `_claim_alerted`.


Major overhaul 2026-02-28 (edge framework):

  #1  REMOVED Dropper — high-priced political/geopolitical bets (Iran strike at $0.81-0.83)
      have tiny upside and full downside. Empirically confirmed: $16.80 loss.

  #2  Per-trader MAX_STAKE cap — HedgeMaster88 capped at $12/order (was blowing up via
      sizing-up mechanic: NAC Breda ballooned to $50 through repeat buys).

  #3  Per-trader daily loss stop (replaces removed global stop). Each trader has its own
      daily deployment budget. White-Leaf ($35) does NOT get blocked by HedgeMaster88's
      soccer losses. Global hard floor still enforced at $80.

  #4  MAX_RESOLUTION_DAYS = 14 — filters out long-term bets (World Cup outrights, season
      winners). Prevents capital being locked for months. Algeria World Cup bet was $7 tied
      up in a 6-month market with near-zero upside at $1.00 entry.

  #5  Price-adjusted stake sizing — replaces flat base stake with:
        price_factor = (1 - entry_price) × 2
        stake = base_stake × price_factor (capped at trader max_stake)
      Low-price underdog bets (0.16 → factor 1.68×) get MORE capital.
      High-price bets (0.80 → factor 0.40×) get LESS. Automatically fixes the NAC Breda
      problem (0.63 → 0.74×) and would have sized Merrimack up (0.16 → 1.68×).

  #6  GLOBALLY_BLOCKED_CATEGORIES — political and geopolitical markets blocked for ALL
      traders regardless of archetype. Dropper's Iran bets would have been blocked here.

  #7  EdgeTracker — records per-trader W/L and ROI after every resolved position.
      Computes a live Edge Score: (win_rate × avg_roi − loss_rate × avg_loss) × 100.
      Score gates the edge_factor multiplier in stake sizing (capped 0.5×–1.5×).
      Starts at neutral (50 pts) until 5+ resolved positions per trader exist.

v5.9 → kept: price-based win/loss detection, _claim_alerted set, dust cleanup.
v5.7 → kept: sizing-up mechanic, WR-weighted stake_mult, MM filter, confluence boost.
v5.4 → kept: confluence tracker, position-size guard, fill aggregator, category filter.
"""

import os, json, time, sys, traceback, urllib.request
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# v6.2: web3 for CTF on-chain redemption (optional — falls back gracefully if not installed)
try:
    from web3 import Web3
    try:
        from web3.middleware import ExtraDataToPOAMiddleware as _poa_middleware   # web3 v6+
    except ImportError:
        from web3.middleware import geth_poa_middleware as _poa_middleware         # web3 v5
    _WEB3_OK = True
except ImportError:
    _WEB3_OK = False

try:
    import requests as _requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    _REQUESTS_OK = True
except ImportError:
    _REQUESTS_OK = False

load_dotenv(Path(__file__).parent / ".env")

# ── CLOB ──────────────────────────────────────────────────────────────────────
try:
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import MarketOrderArgs, OrderType
    from py_clob_client.order_builder.constants import BUY, SELL as SELL_SIDE
    CLOB_AVAILABLE = True
except ImportError:
    CLOB_AVAILABLE = False
    print("⚠️  py-clob-client not installed — run: pip3 install -r requirements.txt")

# ── CREDENTIALS ───────────────────────────────────────────────────────────────
PRIVATE_KEY          = os.getenv("PRIVATE_KEY", "")
FUNDER_PRIVATE_KEY   = os.getenv("FUNDER_PRIVATE_KEY", "")  # v7.3: funder EOA key for CTF redemption
POLY_FUNDER_ADDRESS  = os.getenv("POLY_FUNDER_ADDRESS", "")
POLY_SIGNATURE_TYPE  = int(os.getenv("POLY_SIGNATURE_TYPE", "0"))
POLY_API_KEY         = os.getenv("POLY_API_KEY", "")
POLY_API_SECRET      = os.getenv("POLY_API_SECRET", "")
POLY_API_PASSPHRASE  = os.getenv("POLY_API_PASSPHRASE", "")

# ── CORE CONFIG ───────────────────────────────────────────────────────────────
STAKE              = float(os.getenv("STAKE_USDC",          "20.0"))  # v7.0: $7 → $20 — prior $2-5 output was structurally too small
_live_usdc: float  = STAKE  # v7.4: updated each heartbeat for auto-compound
POLL_INTERVAL      = int(os.getenv("POLL_INTERVAL",         "10"))   # v6.5: 30→10s (3× faster detection)
DRY_RUN            = os.getenv("DRY_RUN", "true").lower() != "false"
PRIORITY_LEVEL     = int(os.getenv("PRIORITY_LEVEL",        "1"))
SKIP_SELLS         = os.getenv("SKIP_SELLS", "true").lower() == "true"
CLOB_HOST          = os.getenv("CLOB_HOST",   "https://clob.polymarket.com")
CHAIN_ID           = int(os.getenv("CHAIN_ID",              "137"))

# ── RISK CONTROLS ─────────────────────────────────────────────────────────────
MAX_SLIPPAGE       = float(os.getenv("MAX_SLIPPAGE",        "0.08"))
MAX_PER_MARKET     = float(os.getenv("MAX_PER_MARKET_USDC", "80.0"))   # v7.0: $40 → $80 — allow full position building
MAX_STAKE_PER_TRADE= float(os.getenv("MAX_STAKE_PER_TRADE", "40.0"))  # v7.0: $20 → $40 — unlocks per-trader max_stake overrides
MAX_CLAIM_ATTEMPTS = 3                                               # v7.5: abandon stuck claim after N tries across restarts
FILL_AGG_WINDOW    = int(os.getenv("FILL_AGG_WINDOW_SEC",   "15"))   # v6.5: 60→15s — was the main latency bottleneck
STALENESS_CUTOFF   = int(os.getenv("STALENESS_CUTOFF_SEC",  "90"))   # v6.5: 300→90s — reject signals >90s old
MAX_SPREAD         = float(os.getenv("MAX_SPREAD",          "0.05"))
MAX_ENTRY_PRICE    = float(os.getenv("MAX_ENTRY_PRICE",     "0.85"))

# v6.0: Resolution days filter — skip markets resolving more than N days from now
MAX_RESOLUTION_DAYS = int(os.getenv("MAX_RESOLUTION_DAYS", "14"))

# v6.0: Per-trader daily loss stops (deployment proxy for loss).
# Keys must match TRADERS[*]["name"]. "default" applies to any trader not listed.
# "global" is the hard floor across all traders combined.
DAILY_LOSS_STOPS = {
    "global":     -25,   # v7.7: survival mode emergency floor | was: -200
    "per_trader": {
        # v7.0: all limits raised to match new sizing (≈ 2 max-stake losses per trader per day)
        "Signal47-Bets":     -8,   # v7.7: survival mode | was: -30
        "Immense-Gokart":    -10,  # v7.7: survival mode leash | was: -25
        "GEM-0x69aee":       -8,   # v7.7: benched | was: -20
        "Quixotic-Average":  -15,  # thin (16W/0L) | 0.4× stake | max $12/trade
        # CS2-LoL-Sharp REMOVED v7.2 | was: -20
        # (0W/5L — see TRADERS removal note above)
        # MultiSport-8f80 REMOVED — 1W/11L (8.3% WR) confirmed bleed
        # v7.1: new leaderboard traders
        "Triangular-Box":    -8,   # v7.7: survival mode | was: -25
        "Unwieldy-Forage":   -8,   # v7.7: survival mode | was: -25
        "Helpful-Contention": -8,  # v7.7: irrelevant (benched-crypto) | was: -15
        "Superb-Hyacinth":   -8,   # v7.7: survival mode | was: -12
                "default":           -8,   # v7.7: survival mode floor
    },
}

# v6.0: Global category block — no trader can copy markets in these categories.
# Applied before trader-specific category filters.
GLOBALLY_BLOCKED_CATEGORIES = ["politics", "geopolitical", "crypto"]  # v6.9: added crypto — generalists cannot copy crypto markets

# v5.7: Sizing-up mechanic
SIZING_STEP        = float(os.getenv("SIZING_STEP", "0.30"))  # v6.9: fraction of price_adj_stake per repeat buy (was flat $5 — dominated price logic)
# v6.1: Cap how many times the bot will buy the same (trader, market) per day.
# Prevents HedgeMaster88-style over-concentration (bought Club León 5× overnight).
MAX_BUYS_PER_MARKET = int(os.getenv("MAX_BUYS_PER_MARKET", "2"))
COPY_DELAY_SEC = 0            # v7.8: disabled — reactive-only impl suppresses single-buy-and-hold traders; scalper protection via roster bench

# v6.9: PER_TRADER_DAILY removed — was dead code, never referenced in any logic.
#        Per-trader limits live exclusively in DAILY_LOSS_STOPS["per_trader"].

# v5.4: Confluence boost
CONFLUENCE_WINDOW_SEC  = int(os.getenv("CONFLUENCE_WINDOW_SEC",  "1800"))
CONFLUENCE_THRESHOLD   = int(os.getenv("CONFLUENCE_THRESHOLD",   "3"))
CONFLUENCE_MULTIPLIER  = float(os.getenv("CONFLUENCE_MULTIPLIER","1.5"))
MAX_WHALE_ORIGINAL     = float(os.getenv("MAX_WHALE_ORIGINAL",   "10000"))

# v5.9: Claim detection
CLAIM_WIN_PRICE_THRESHOLD  = 0.97
CLAIM_LOSS_PRICE_THRESHOLD = 0.03
CLAIM_HOURS_PAST_END       = 2.0
CLAIM_WIN_SELL_FLOOR       = 0.50   # v7.6.6: refuse CLOB SELL on WIN if CLOB price below this (prevents Jazz/Hornets-style premature exit)
_claim_alerted: set = set()
_recon_claimed: set  = set()   # v7.5.1: tokens successfully claimed this session — skip in recon
_neg_risk_tokens: set = set()  # v7.5.3: neg-risk token IDs (manual claim only)
NEG_RISK_FILE = "/home/ubuntu/copytrade/neg_risk_pending.json"  # persists across restarts
_session_wins:   float = 0.0   # v7.2: USDC won since bot start
_session_losses: float = 0.0   # v7.2: USDC lost since bot start
_pending_claim_orders: dict = {}   # v7.6.0: {order_id -> {owner, stake, token_id, shares, ts}}
_source_first_seen:   dict = {}   # v7.7: {(trader_name, token_id): first_seen_ts} — copy delay tracking
_PENDING_CLAIMS_FILE = "/home/ubuntu/copytrade/pending_claims.json"  # persists across restarts

# v6.2: CTF on-chain redemption (Polygon)
POLYGON_RPC    = "https://1rpc.io/matic"                   # v7.5.1: benchmarked fastest (50ms from IE)
POLYGON_RPC_FALLBACKS = [                          # v7.5.1: ordered by measured latency
    "https://polygon-bor-rpc.publicnode.com",      # PublicNode — 77ms, proven reliable
    "https://rpc.ankr.com/polygon",                # Ankr — 91ms
    "https://polygon.drpc.org",                    # dRPC — 95ms
]
CTF_ADDRESS    = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
USDC_ADDRESS   = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
_ctf_w3        = None
_ctf_contract  = None
NEG_RISK_ADAPTER_ADDR = "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296"  # v7.5.4
NEG_RISK_ADAPTER_ABI  = json.loads('[{"inputs":[{"name":"_conditionId","type":"bytes32"},{"name":"_amounts","type":"uint256[]"}],"name":"redeemPositions","outputs":[],"stateMutability":"nonpayable","type":"function"}]')

CTF_REDEEM_ABI = json.loads('[{"inputs":[{"name":"collateralToken","type":"address"},{"name":"parentCollectionId","type":"bytes32"},{"name":"conditionId","type":"bytes32"},{"name":"indexSets","type":"uint256[]"}],"name":"redeemPositions","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"name":"owner","type":"address"},{"name":"id","type":"uint256"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]')  # v7.5.2: added balanceOf

SAFE_ABI = [
    {"inputs": [], "name": "nonce",
     "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "to",            "type": "address"},
                {"name": "value",         "type": "uint256"},
                {"name": "data",          "type": "bytes"},
                {"name": "operation",     "type": "uint8"},
                {"name": "safeTxGas",     "type": "uint256"},
                {"name": "baseGas",       "type": "uint256"},
                {"name": "gasPrice",      "type": "uint256"},
                {"name": "gasToken",      "type": "address"},
                {"name": "refundReceiver","type": "address"},
                {"name": "_nonce",        "type": "uint256"}],
     "name": "getTransactionHash", "outputs": [{"type": "bytes32"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "to",            "type": "address"},
                {"name": "value",         "type": "uint256"},
                {"name": "data",          "type": "bytes"},
                {"name": "operation",     "type": "uint8"},
                {"name": "safeTxGas",     "type": "uint256"},
                {"name": "baseGas",       "type": "uint256"},
                {"name": "gasPrice",      "type": "uint256"},
                {"name": "gasToken",      "type": "address"},
                {"name": "refundReceiver","type": "address"},
                {"name": "signatures",    "type": "bytes"}],
     "name": "execTransaction", "outputs": [{"type": "bool"}],
     "stateMutability": "payable", "type": "function"},
]  # v7.6.10: module-level Safe ABI for _neg_risk_redeem() (was undefined -> NameError)

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")

# Proxy
PROXY_URL = os.getenv("PROXY_URL", "")
if PROXY_URL:
    os.environ["HTTP_PROXY"]  = PROXY_URL
    os.environ["HTTPS_PROXY"] = PROXY_URL
    os.environ["http_proxy"]  = PROXY_URL
    os.environ["https_proxy"] = PROXY_URL
    try:
        import httpx as _httpx
        import py_clob_client.http_helpers.helpers as _clob_http
        _clob_http._http_client = _httpx.Client(proxy=PROXY_URL)
    except Exception:
        pass

LOG_FILE        = Path(__file__).parent / "trade_log.jsonl"
POSITIONS_FILE  = Path(__file__).parent / "positions.json"
EDGE_SCORE_FILE = Path(__file__).parent / "edge_scores.json"

DATA_API  = "https://data-api.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"
POLY_BASE = "https://polymarket.com/event"

_PROXIES = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None

# ── WATCHLIST ─────────────────────────────────────────────────────────────────
# archetype: "value" | "generalist" | "specialist"
# max_stake:  per-order cap in USDC (overrides global MAX_STAKE_PER_TRADE)
# categories: specialist filter — copy ONLY these category keys
# stake_mult: WR-weighted base multiplier on STAKE
#
TRADERS = [
    # ── ACTIVE: verified human traders with honest entry prices ───────────────
    {
        "name": "Signal47-Bets", "wallet": "0xa83be3f6a49604556f45089799f2b2096e71def4",
        "roi": None, "priority": 1, "archetype": "specialist",
        "stake_mult": 1.2, "max_stake": 8.0,    # v7.7: survival mode cap | was: 30.0 v7.0
        "categories": ["nba"],
        "note": "NBA game-lines at real prices ($0.30-$0.99) | 53W/1L confirmed | HIGHEST CONVICTION",
    },

    # ── v1.7 scan results (2026-03-03) ────────────────────────────────────────
    {
        "name": "Immense-Gokart",
        "wallet": "0xf27e335d2e78a207e802879f72870449836bd69d",
        "roi": None, "priority": 1,
        "archetype": "specialist",
        "stake_mult": 0.9, "max_stake": 10.0,   # v7.7: survival mode leash | was: 15.0 v7.6.14
        "categories": ["esports"],
        "note": "CS2 map specialist | 53W/1L confirmed | avg $0.319 | 1.3/d | 97d",
    },
    # Phony-Mantel  0xbdf2db48 — REJECTED: crypto market participation (Ethereum Up/Down)
    # New-Browser   0x89cdac7b — BLACKLISTED: confirmed ladder bot (same-second repeat fills)

    # ── MultiSport-8f80 REMOVED v7.0 — 1W/11L (8.3% WR) live confirmed, bleeding $31+ ──

    # ── v6.8 manual adds (2026-03-03) ─────────────────────────────────────────
    {
        "name": "GEM-0x69aee",
        "wallet": "0x69aee04532c679ecd4060d9e31af19d6af319f18",
        "roi": None, "priority": 2,  # v7.7: BENCHED micro-bettor source ($2 avg) | was: priority=1
        "archetype": "generalist",
        "stake_mult": 0.6, "max_stake": 8.0,    # v7.6.13: micro-bettor avg_stake=$2.65 - capped from $18
        "categories": [],   # multi-sport NO-side: CS2/LoL/NBA match markets
        "note": "multi-sport NO-side bettor | 57W/1L trigger hit | avg $0.483 | 2.2/d | 60d",
    },
    {
        "name": "Quixotic-Average",
        "wallet": "0xbbef15091aee07f8310d7314761d3a3063749838",
        "roi": None, "priority": 2,  # v7.5: BENCHED
        "archetype": "specialist",
        "stake_mult": 0.4, "max_stake": 12.0,   # v7.0: 0.3×$8 → 0.4×$12 | 432d vet but thin WR
        "categories": ["nba"],
        "note": "NBA underdog specialist | 432d vet | 16W/0L (thin — probationary) | avg $0.418 | median $0.320",
    },
    # CS2-LoL-Sharp REMOVED v7.2 — 0W/5L live. Wallet bets NBA games (blocked by esports filter)
    # so we never captured its real signals. All esports bets placed = losses. Dead weight.

    # ── v7.1 leaderboard scan results (2026-03-04) ──────────────────────────────
    {
        "name": "Triangular-Box",
        "wallet": "0xe85d6567a750b7b15fcb51c01a7c6230f63095d8",
        "roi": None, "priority": 1,
        "archetype": "generalist",
        "bypass_global_block": True,    # v7.1: 99% WR across all niches — unrestricted
        "stake_mult": 0.6, "max_stake": 8.0,    # v7.7: survival mode cap | was: 20.0
        "categories": [],   # sports 57% + other 41% (NBA/CS2/LoL + misc)
        "note": "99% WR (195W/1L verified) | avg /bin/zsh.658 | freq=6.0/d | age=44d | sports/esports/other",
    },
    {
        "name": "Unwieldy-Forage",
        "wallet": "0x146703a8a73ae1dff0f84ba44c45d878858a4372",
        "roi": None, "priority": 1,
        "archetype": "generalist",
        "bypass_global_block": True,    # v7.1: 100% WR — unrestricted
        "stake_mult": 0.7, "max_stake": 8.0,    # v7.7: survival mode cap | was: 22.0
        "categories": [],   # NHL/soccer (keyword mismatch — generalist catches all)
        "note": "100% WR (157W/0L verified) | 0 bot clusters | avg /bin/zsh.473 | freq=4.2/d | age=60d | NHL/soccer",
    },
    {
        "name": "Helpful-Contention",
        "wallet": "0x14f742820b9c71f4221ee948ed4aba20cd7e232c",
        "roi": None, "priority": 2,  # v7.4: BENCHED — crypto hard-banned
        "archetype": "specialist",
        "bypass_global_block": True,    # v7.1: crypto micro-market specialist — crypto block bypassed
        "stake_mult": 0.4, "max_stake": 12.0,
        "categories": ["crypto"],   # Bitcoin/Ethereum Up-or-Down 15-min windows only
        "note": "99% WR (139W/2L verified) | avg $0.285 | freq=21.5/d | age=14d | crypto micro-markets | BENCHED v7.4",
    },
    {
        "name": "Superb-Hyacinth",
        "wallet": "0x419be42e6a9899d6ce2b443d17052a990b3f0944",
        "roi": None, "priority": 1,  # v7.6.0: activated — 33W/0L confirmed in edge_scores, 76d age
        "archetype": "generalist",
        "bypass_global_block": True,    # v7.1: unrestricted
        "stake_mult": 0.5, "max_stake": 8.0,   # v7.7: survival mode cap | was: 15.0 v7.6.0
        "categories": [],   # NBA/NHL (generalist catches all)
        "note": "100% WR (33W/0L) | freq=1.4/d | age=76d | NBA/NHL | ACTIVATED v7.6.0",
    },

    # ── v7.5 deep-scan gems (2026-03-05) ──────────────────────────────────────
    {
        "name": "SharpEdge-25a1",
        "wallet": "0x25a1a36e671aa52180be2e5ad498dc2013d9ddf8",
        "roi": None, "priority": 2,  # v7.7: BENCHED — 3-trade sample, unproven | was: priority=1
        "archetype": "generalist",
        "stake_mult": 0.7, "max_stake": 8.0,   # v7.6.12: micro-bettor avg_stake=$1.30 - capped
        "categories": [],
        "note": "98.5% WR (66W/1L) | avg $0.496 | freq=3.3/d | age=49d | sports=86% | score=76.4",
    },
    {
        "name": "kkap8897",
        "wallet": "0xbb15969cb69d5b430d40870aabdf2a1d91820f02",
        "roi": None, "priority": 2,  # BENCHED v7.5.3: W1/L4 live (20%WR vs scan 56W/0L — dud)
        "archetype": "generalist",
        "stake_mult": 0.5, "max_stake": 15.0,
        "categories": [],
        "note": "95% WR capped (56W/0L) | avg $0.475 | freq=5.8/d | age=24d | sports=73% | 30dPnL=$6431",
    },
    {
        "name": "Sharp-c33a",
        "wallet": "0xc33a100b8362bc732e78cce28c99739f173b3da3",
        "roi": None, "priority": 2,  # v7.7: BENCHED ROI -41% (7W/2L $160→$95) | was: priority=1
        "archetype": "generalist",
        "stake_mult": 0.6, "max_stake": 18.0,
        "categories": [],
        "note": "95% WR capped (30W/0L) | avg $0.434 | freq=3.2/d | age=31d | sports=68% | 30dPnL=$8263",
    },
    {
        "name": "Veteran-b512",
        "wallet": "0xb5124dae83419944bb000ebe28607560de9144a5",
        "roi": None, "priority": 2,  # v7.7: BENCHED zero history, micro-source $2 | was: priority=1
        "archetype": "generalist",
        "stake_mult": 0.8, "max_stake": 22.0,
        "categories": [],
        "note": "95% WR capped (100W/0L) | avg $0.427 | freq=1.2/d | age=204d | sports=61% | score=84.7",
    },

    {
        "name": "RawrRawr",
        "wallet": "0x71971342cb4c2555f60366ac62abdcdd1a1d14c8",
        "roi": None, "priority": 2,  # BENCHED v7.6.4: 1W/18L live (5.3%WR) | -$220 PnL | dud
        "archetype": "generalist",
        "stake_mult": 1.0, "max_stake": 27.0,   # v7.5.5: 95.9% WR | 98 resolved | EPL/football | freq=16.7+/d
        "categories": [],
        "note": "BENCHED v7.6.4 | scan 95.9%WR was hot-streak | live: 1W/18L (5.3%WR) | -$220.74 | ROI=-75.4% | 100% delayed | double-bet pattern",
    },
    {
        "name": "jack66666",
        "wallet": "0x05b21f43e056cdf3f26ae5f28dc0238495e2a469",
        "roi": None, "priority": 2,  # v7.7: BENCHED avg_entry=0.868>0.80, no edge history | was: priority=1
        "archetype": "generalist",
        "stake_mult": 0.9, "max_stake": 25.0,   # v7.5.5: 91.7% WR | 24 resolved | NBA | freq=16.7+/d
        "categories": [],
        "note": "91.7% WR (22W/2L) | 22.9d age | NBA | freq=16.7+/d | $2296/30d | scout_wide2",
    },
    {
        "name": "HeisenbergWalt",
        "wallet": "0x4042a8ef98b5abf2a1cf2423f8475c91ee150bda",
        "roi": None, "priority": 2,  # v7.7: BENCHED ROI -69.6% (2W/1L $289→$88) | was: priority=1
        "archetype": "generalist",
        "stake_mult": 0.75, "max_stake": 22.0,  # v7.5.5: 85.4% WR | 96 resolved | WTA tennis | freq=16.7+/d
        "categories": [],
        "note": "85.4% WR (82W/14L) | 11.5d age | WTA tennis | freq=16.7+/d | $2057/30d | scout_wide2",
    },
    {
        "name": "bigwhale1337",
        "wallet": "0x77f623734a71c023f9df91011189eaeef891dbd1",
        "roi": None, "priority": 2,  # v7.7: BENCHED no edge_scores history, emergency | was: priority=1
        "archetype": "generalist",
        "stake_mult": 0.65, "max_stake": 20.0,  # v7.5.5: 81.8% WR | 82d age | ATP tennis | freq=5.0/d
        "categories": [],
        "note": "81.8% WR (27W/6L) | 82d age | ATP tennis | freq=5.0/d | $3360/30d | scout_wide2",
    },

    
    {
        "name": "0xc97f6383",
        "wallet": "0xc97f63836ef3b8f373da5588713cd9ecd0ffb793",
        "roi": None, "priority": 2,  # BENCHED v7.6.14 2026-03-08
        "archetype": "generalist",
        "stake_mult": 0.7, "max_stake": 8.0,   # v7.6.13: micro-bettor avg_stake=$2.22 - capped from $15
        "note": "Auto-added by scanner v1.6 | score=88.5 | 81r 100%WR | sports=43% | BENCHED v7.6.14 2026-03-08: -$74.51 Turkish soccer losses in 1 session",
    },
    
    {
        "name": "0x5524f06f",
        "wallet": "0x5524f06fc1c49a5199fe2c781e42473c24282f3c",
        "roi": None, "priority": 2,  # v7.7: BENCHED in-play Dota2/CS2 scalper, no PnL | was: priority=1
        "archetype": "generalist",
        "stake_mult": 0.7, "max_stake": 15.0,
        "note": "Auto-added by scanner v1.6 | score=85.2 | 99r 100%WR | sports=82%",
    },
    
    {
        "name": "0xec6604b0",
        "wallet": "0xec6604b010557c6fbf054643c93ec1245ebde58f",
        "roi": None, "priority": 2,  # v7.7: BENCHED high-freq multi-sport, no edge history | was: priority=1
        "archetype": "generalist",
        "stake_mult": 0.7, "max_stake": 8.0,
        "note": "Auto-added by scanner v1.6 | score=85.6 | 100r 99%WR | sports=66%",
    },
    # END_TRADERS  ← scanner auto-add injects new entries here

    # ── REMOVED v6.4 ──────────────────────────────────────────────────────────
    # BAdiosB          — geopolitical specialist, avg $0.925, 0% sports. No copy edge.
    # Overjoyed-Mansion — NO-on-impossible-outcomes bot, avg $0.958.
    # Scared-Cape       — same pattern, avg $0.974, fake sports% via World Cup NO bets.
    # HedgeMaster88     — 359 buys/day, acct span 1d. Confirmed bot.
    # Gleeful-Cauliflower — 202/d, acct span 2d. Confirmed bot.
    # Drab-Muscatel     — 107/d, acct span 4d. Confirmed bot.
    # Speedy-Booster    — 249/d, acct span 2d. Confirmed bot.
    # A1d29             — crypto-only markets (7 total buys). Wrong category.
    # 0x6a57D2          — 28.3/d (exceeds MAX_FREQ_PER_DAY), bot concentration.
    # C.SIN             — 33.2/d, 0 resolved positions, crypto markets.
]

# ── CATEGORY KEYWORDS ─────────────────────────────────────────────────────────
CATEGORY_KEYWORDS = {
    "soccer": [
        "fc ", " fc", "united", "city fc", "atletico", "madrid", "barcelona", "paris saint",
        "liverpool", "chelsea", "arsenal", "ucl", "champions league", "premier league",
        "bundesliga", "serie a", "ligue 1", "la liga", "laliga", "copa", "eredivisie",
        "championship", "santos", "flamengo", "boca juniors", "river plate", "benfica",
        "porto", "ajax", "milan", "inter milan", "juventus", "napoli", "roma", "sevilla",
        "villarreal", "dortmund", "borussia", "psg", "marseille", "lyon", "mls",
        "brasileirao", "primera división", "superliga", "ekstraklasa", "eliteserien",
        "allsvenskan", "btts", "both teams", "over 2.5", "under 2.5", "win on 202",
        "soccer", "football match", "efl", "fa cup", "carabao", "league cup",
    ],
    "nba": [
        "nba", "celtics", "lakers", "warriors", "knicks", "heat", "bucks", "spurs",
        "bulls", "sixers", "suns", "nuggets", "clippers", "mavericks", "mavs",
        "rockets", "nets", "pacers", "hawks", "hornets", "magic", "pistons",
        "cavaliers", "cavs", "raptors", "jazz", "thunder", "trail blazers", "timberwolves",
        "grizzlies", "pelicans", "kings", "wizards", "basketball",
    ],
    # v6.1: esports category added for Speedy-Booster (CS) + Unripe-Duster (LoL)
    "esports": [
        "counter-strike", "cs:", "lol:", "league of legends", "valorant",
        "dota", "map winner", "map handicap", "lec", "lcs", "lck", "lpl",
        "esports", "esl", "blast", "faceit", "cct europe", "a1 gaming",
        "iem", "major", "pgl", "navi", "team liquid", "faze", "g2 esports",
        "astralis", "nip", "vitality", "heroic", "natus vincere",
    ],
    "politics": [
        "trump", "election", "president", "democrat", "republican", "senate", "congress",
        "ballot", "vote", "white house", "supreme court", "epstein", "classified files",
        "tariff", "executive order", "cabinet", "filibuster", "doge", "musk",
        "prime minister", "chancellor", "parliament", "referendum", "inauguration",
        "impeach", "resign", "appoint", "nominate", "rfk", "vivek",
        # v7.0: removed "elon" — false-positive substring of "barcelona" (b-a-r-c-e-l-o-n-a).
        # "musk" (line above) already covers Elon Musk markets. "elon" alone was redundant + harmful.
    ],
    "geopolitical": [
        "strikes iran", "strike iran", "iran by", "attack iran", "bombs iran",
        "invades", "invade", "nuclear strike", "military action", "air strike",
        "us troops", "nato invok", "world war", "armed conflict",
        "will us bomb", "will russia", "sanctions imposed", "blockade",
        "military strike", "geopolitical", "war between",
    ],
    "crypto": [
        # v6.9: removed "eth" (false-pos: "whether"), "sol" (dup/broad), "sec" (false-pos:
        # "secure","second"), "token" (broad) — safe unambiguous identifiers only
        "bitcoin", "btc", "ethereum", "solana", "xrp", "ripple",
        "crypto", "defi", "nft", "blockchain", "binance", "coinbase",
        "pump.fun", "axiom", "bybit", "hyperliquid",
    ],
    # v6.6: added nhl + tennis for multi-sport specialist support
    "nhl": [
        "nhl", "stanley cup", "hockey", "penguins", "bruins", "canadiens", "maple leafs",
        "rangers", "blackhawks", "red wings", "oilers", "flames", "canucks", "stars",
        "blues", "lightning", "panthers", "avalanche", "golden knights", "ducks",
        "sharks", "coyotes", "senators", "sabres", "devils", "islanders", "flyers",
        "predators", "wild", "jets", "hurricanes", "blue jackets", "capitals",
    ],
    "tennis": [
        "tennis", "atp", "wta", "wimbledon", "us open", "french open", "australian open",
        "djokovic", "nadal", "federer", "alcaraz", "medvedev", "swiatek", "sabalenka",
        "gauff", "rybakina", "set winner", "match winner", "grand slam", "aces",
        "first set", "second set", "winner:", "vs ", " v ",
    ],
}


def is_globally_blocked(title, trader=None):
    """
    v6.0: Returns (True, category_name) if market falls in a globally blocked category.
    Applied before trader-specific filters — blocks ALL traders from these markets.
    v7.4: bypass_global_block traders hard-stopped by BOTH geopolitical AND crypto.
    Only politics can be bypassed. Crypto is permanently banned for all traders.
    """
    t = title.lower()
    if trader and trader.get("bypass_global_block"):
        # v7.4: Hard-stop for BOTH geopolitical AND crypto — neither is bypassable.
        # bypass_global_block only allows politics through; crypto is permanently banned.
        for hard_cat in ["geopolitical", "crypto"]:
            kws = CATEGORY_KEYWORDS.get(hard_cat, [])
            if any(kw in t for kw in kws):
                return True, hard_cat
        return False, None
    for cat in GLOBALLY_BLOCKED_CATEGORIES:
        kws = CATEGORY_KEYWORDS.get(cat, [cat])
        if any(kw in t for kw in kws):
            return True, cat
    return False, None


def is_in_trader_category(act, trader):
    """Returns True if this trade falls within the trader's specialty (or trader has no filter)."""
    cats = trader.get("categories")
    if not cats:
        return True
    title = (act.get("title") or "").lower()
    for cat in cats:
        kws = CATEGORY_KEYWORDS.get(cat, [cat])
        if any(kw in title for kw in kws):
            return True
    return False

# ── CONFLUENCE TRACKER ────────────────────────────────────────────────────────
_confluence_tracker = defaultdict(list)

# ── HELPERS ───────────────────────────────────────────────────────────────────

def ts():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

def now_unix():
    return int(datetime.now(timezone.utc).timestamp())

def log(msg, level="INFO"):
    print(f"[{ts()}] [{level}] {msg}", flush=True)

def send_telegram(msg, parse_mode="HTML"):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    if not _REQUESTS_OK:
        return
    try:
        _requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": parse_mode},
            timeout=5,
        )
    except Exception:
        pass

def portfolio_line(client):
    """
    v7.5.8: One-line portfolio snapshot appended to key Telegram alerts.
    Returns: '\n💵 Cash: $X | 📊 Open: $Y | 🏦 Total: $Z'
    Fails silently (returns '') so alerts are never blocked.
    """
    try:
        from py_clob_client.clob_types import AssetType, BalanceAllowanceParams
        _bal = client.get_balance_allowance(
            params=BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
        )
        cash = float(_bal.get("balance", 0) or 0) / 1e6
    except Exception:
        cash = 0.0
    try:
        _wallet = os.environ.get("POLY_FUNDER_ADDRESS", "")
        _resp = _requests.get(
            f"https://data-api.polymarket.com/positions?user={_wallet}&sizeThreshold=0.01&limit=500",
            timeout=8
        )
        open_val = sum(float(p.get("currentValue") or 0) for p in _resp.json() if isinstance(p, dict))
    except Exception:
        open_val = 0.0
    total = cash + open_val
    return (f"\n💵 Cash: <b>${cash:.2f}</b> | "
            f"📊 Open: <b>${open_val:.2f}</b> | "
            f"🏦 Total: <b>${total:.2f}</b>")

def fetch_json(url, retries=3):
    for attempt in range(retries):
        try:
            r = _requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=12,
                proxies=_PROXIES,
                verify=False,
            )
            r.raise_for_status()
            return r.json()
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)

def fetch_activity(wallet, limit=50, offset=0):
    try:
        url  = f"{DATA_API}/activity?user={wallet}&limit={limit}&offset={offset}"
        data = fetch_json(url)
        return data if isinstance(data, list) else data.get("data", [])
    except Exception as e:
        log(f"fetch_activity error {wallet[:10]}...: {e}", "WARN")
        return None

def fetch_new_since(wallet, watermark, max_pages=3):
    since_ts    = watermark["ts"]
    seen_hashes = watermark["hashes"]
    all_new     = []
    page_cap_hit = False
    for page in range(max_pages):
        acts = fetch_activity(wallet, limit=50, offset=page * 50)
        if not acts:
            break
        page_exhausted = True
        for act in acts:
            if act["timestamp"] < since_ts:
                page_exhausted = False
                break
            if act["timestamp"] == since_ts and act["transactionHash"] in seen_hashes:
                page_exhausted = False
                break
            all_new.append(act)
        if not page_exhausted:
            break
        if len(acts) < 50:
            break
        if page == max_pages - 1:
            page_cap_hit = True
    if page_cap_hit:
        log(f"⚠️  Page cap hit for {wallet[:10]}... — some trades may have been missed.", "WARN")
        send_telegram(f"⚠️ <b>Page cap hit</b> for <code>{wallet[:10]}...</code>")
    return all_new

def write_log(entry):
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

def load_positions():
    try:
        if POSITIONS_FILE.exists():
            with open(POSITIONS_FILE) as f:
                data = json.load(f)
            if data:
                log(f"  ✓ Loaded {len(data)} persisted position(s) from {POSITIONS_FILE.name}")
            return data
    except Exception as e:
        log(f"  ⚠️ Could not load positions file: {e}", "WARN")
    return {}

def save_positions(positions):
    try:
        with open(POSITIONS_FILE, "w") as f:
            json.dump(positions, f, indent=2)
    except Exception as e:
        log(f"  ⚠️ Could not save positions: {e}", "WARN")

def get_market_end_days(token_id):
    """
    v6.0: Returns days until market resolution, or None if unknown / already ended.
    Used to filter out long-term capital traps (MAX_RESOLUTION_DAYS).
    """
    try:
        data = fetch_json(f"{GAMMA_API}/markets?clob_token_ids={token_id}")
        mkts = data if isinstance(data, list) else data.get("markets", [data])
        if not mkts:
            return None
        end_str = mkts[0].get("endDate", "")
        if not end_str:
            return None
        end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
        days   = (end_dt - datetime.now(timezone.utc)).total_seconds() / 86400
        return max(0.0, days)
    except Exception:
        return None

# ── EDGE TRACKER ──────────────────────────────────────────────────────────────

class EdgeTracker:
    """
    v6.0: Records per-trader resolved position outcomes and computes a live Edge Score.

    Edge Score = (win_rate × avg_roi  −  loss_rate × avg_loss%) × 100
    Range: 0–100. Starts at 50 (neutral) until a trader has 5+ resolved positions.

    Score drives the edge_factor multiplier in calculate_stake():
      score >= 70  →  edge_factor 1.5× (proven edge, size up)
      score 50-69  →  edge_factor 1.0× (neutral — no boost)
      score < 50   →  edge_factor 0.7× (losing — reduce exposure)
    """
    def __init__(self, score_file):
        self.score_file = Path(score_file)
        self.data = self._load()

    def _load(self):
        try:
            if self.score_file.exists():
                return json.loads(self.score_file.read_text())
        except Exception:
            pass
        return {}

    def _save(self):
        try:
            self.score_file.write_text(json.dumps(self.data, indent=2))
        except Exception as e:
            log(f"  ⚠️ EdgeTracker save failed: {e}", "WARN")

    def record(self, trader_name, stake, proceeds, won):
        """Call after each position resolves (win or loss)."""
        if trader_name not in self.data:
            self.data[trader_name] = {
                "wins": 0, "losses": 0,
                "total_staked": 0.0, "total_proceeds": 0.0,
            }
        d = self.data[trader_name]
        d.setdefault("total_staked",   0.0)   # v7.5.1: guard missing keys
        d.setdefault("total_proceeds", 0.0)
        d["total_staked"]   += stake
        d["total_proceeds"] += proceeds
        if won:
            d["wins"] += 1
        else:
            d["losses"] += 1
        self._save()
        score = self.get_score(trader_name)
        log(f"  📊 EdgeTracker [{trader_name}]: {'WIN' if won else 'LOSS'} "
            f"(stake=${stake:.2f} → ${proceeds:.2f}) | "
            f"W{d['wins']}/L{d['losses']} | score={score:.0f}")

    def get_score(self, trader_name):
        """Returns 0–100 edge score. 50 = neutral (not enough data)."""
        d = self.data.get(trader_name, {})
        wins   = d.get("wins",   0)
        losses = d.get("losses", 0)
        total  = wins + losses
        if total < 5:
            return 50.0   # not enough data — neutral
        staked   = d.get("total_staked",   1.0)
        proceeds = d.get("total_proceeds", 0.0)
        win_rate  = wins / total
        loss_rate = 1.0 - win_rate
        avg_roi   = (proceeds - staked) / staked   # e.g. 0.45 = 45% avg return
        avg_loss  = abs(min(avg_roi, 0))            # only counts if avg_roi is negative
        score = 50.0 + (win_rate * avg_roi * 100) - (loss_rate * avg_loss * 100)
        return max(0.0, min(100.0, score))

    def get_edge_factor(self, trader_name):
        """Returns the stake multiplier based on edge score."""
        score = self.get_score(trader_name)
        if score >= 70:
            return 1.5
        elif score >= 50:
            return 1.0
        else:
            return 0.7

    def summary(self):
        lines = []
        for trader, d in sorted(self.data.items()):
            w = d.get("wins", 0)
            l = d.get("losses", 0)
            total = w + l
            wr = w / total * 100 if total else 0
            score = self.get_score(trader)
            lines.append(f"  {trader:<22} W{w}/L{l} ({wr:.0f}%WR) score={score:.0f}")
        return "\n".join(lines) if lines else "  (no resolved positions yet)"


def get_dynamic_stake(usdc_balance: float) -> float:
    """v7.4: Auto-compound — base stake scales with USDC balance."""
    if usdc_balance >= 3000: return 80.0
    if usdc_balance >= 2000: return 60.0
    if usdc_balance >= 1500: return 50.0
    if usdc_balance >= 1000: return 40.0
    if usdc_balance >=  750: return 32.0
    if usdc_balance >=  500: return 26.0
    if usdc_balance >=  400: return 22.0
    if usdc_balance >=  350: return 20.0
    return 15.0

def calculate_stake(base_stake, signal_price, trader, edge_tracker):
    """
    v6.0: Price-adjusted dynamic stake sizing.

    price_factor: low entries deserve more capital (higher upside).
      entry 0.16 → factor 1.68×  (big upside, size up)
      entry 0.50 → factor 1.00×  (neutral)
      entry 0.80 → factor 0.40×  (small upside, size down)

    edge_factor: scales with proven performance.
      score ≥ 70 → 1.5×  |  50-69 → 1.0×  |  < 50 → 0.7×

    Result is capped by:
      1. trader['max_stake']  (per-trader hard cap, e.g. HedgeMaster88=$12)
      2. MAX_STAKE_PER_TRADE  (global hard cap, default $20)
    """
    price_factor = (1.0 - signal_price) * 2.0   # 0→2.0, 0.5→1.0, 0.85→0.30
    price_factor = max(0.1, min(price_factor, 2.0))  # clamp to [0.1, 2.0]

    edge_factor  = edge_tracker.get_edge_factor(trader["name"])

    result = round(base_stake * price_factor * edge_factor, 2)

    # Per-trader cap (e.g. HedgeMaster88 max_stake=12)
    trader_cap = trader.get("max_stake", MAX_STAKE_PER_TRADE)
    result = min(result, trader_cap, MAX_STAKE_PER_TRADE)
    return max(result, 0.50)   # never less than $0.50


# ── RISK MANAGER ──────────────────────────────────────────────────────────────

class RiskManager:
    """
    v6.0: Per-trader daily loss stops + global hard floor.

    Enforcement:
    - Per-trader: if net_deployed (deployed − credits) > |trader limit| → block
    - Global: if total net across all traders > |global limit| → block all

    Credits (wins) reduce the loss counter when a position is claimed successfully.
    """
    def __init__(self):
        self.daily_deployed  = 0.0
        self.trader_daily    = defaultdict(float)   # deployed per trader today
        self.trader_credits  = defaultdict(float)   # wins credited back per trader today
        self.realized_losses = defaultdict(float)   # v6.1: ONLY confirmed closed losses
        self.market_exposure = defaultdict(float)
        self._sizing_count   = defaultdict(int)
        self.day_start       = now_unix() // 86400

    def _check_day_reset(self):
        today = now_unix() // 86400
        if today != self.day_start:
            log(
                f"New day — resetting risk counters. Yesterday: ${self.daily_deployed:.2f} deployed  "
                + "  ".join(f"{t}=${v:.1f}" for t, v in sorted(self.trader_daily.items()))
            )
            send_telegram(
                f"🔄 <b>Daily reset</b>\nYesterday deployed: <b>${self.daily_deployed:.2f}</b>\n"
                + "\n".join(f"  {t}: ${v:.1f}" for t, v in sorted(self.trader_daily.items()))
            )
            self.daily_deployed  = 0.0
            self.trader_daily    = defaultdict(float)
            self.trader_credits  = defaultdict(float)
            self.realized_losses = defaultdict(float)   # v6.1
            self.market_exposure = defaultdict(float)
            self._sizing_count   = defaultdict(int)
            self.day_start       = today

    def get_sizing_count(self, trader_name, token_id):
        return self._sizing_count[(trader_name, token_id)]

    def get_trader_net_loss(self, trader_name):
        """
        v6.1 FIX: Net loss for trader today based on CONFIRMED CLOSED losses only.
        Deployed capital in OPEN positions is NOT counted as a loss — only actual
        resolved-against positions (recorded via record_realized_loss) count.
        """
        return self.trader_credits[trader_name] - self.realized_losses[trader_name]

    def get_global_net_loss(self):
        """
        v6.1 FIX: Net loss across all traders today, based on REALIZED losses only.
        Open deployed positions are NOT counted as losses.
        """
        total_credits = sum(self.trader_credits.values())
        total_realized = sum(self.realized_losses.values())
        return total_credits - total_realized

    def check(self, token_id, stake, signal_price, live_price, trader_name=""):
        self._check_day_reset()

        # 1. Near-resolved price ceiling
        if signal_price >= MAX_ENTRY_PRICE:
            return False, f"Price ceiling: signal ${signal_price:.3f} ≥ ${MAX_ENTRY_PRICE}"

        # 2. Slippage check
        if signal_price > 0 and live_price > 0:
            slip = (live_price - signal_price) / signal_price
            if slip > MAX_SLIPPAGE:
                return False, (f"Slippage too high: signal=${signal_price:.4f} now=${live_price:.4f} "
                               f"({slip:.1%} > {MAX_SLIPPAGE:.0%})")

        # 3. Per-market cap
        already = self.market_exposure[token_id]
        if already + stake > MAX_PER_MARKET:
            return False, f"Per-market cap: already ${already:.2f} + ${stake:.2f} > ${MAX_PER_MARKET}"

        # 4. v6.1: Per-trader daily loss stop (realized losses only — NOT open deployed capital)
        if trader_name:
            per_trader_limits = DAILY_LOSS_STOPS.get("per_trader", {})
            limit = per_trader_limits.get(trader_name, per_trader_limits.get("default", -15))
            net   = self.get_trader_net_loss(trader_name)
            if net < limit:   # v6.1 FIX: was <= (boundary off-by-one blocked at exactly limit)
                return False, (f"Daily loss stop [{trader_name}]: net ${net:.2f} < ${limit} limit "
                               f"(realized_losses ${self.realized_losses[trader_name]:.2f}, "
                               f"credited ${self.trader_credits[trader_name]:.2f})")

        # 5. v6.1: Global daily hard floor (realized losses only)
        global_net = self.get_global_net_loss()
        global_limit = DAILY_LOSS_STOPS.get("global", -80)
        if global_net < global_limit:   # v6.1 FIX: was <=
            return False, (f"Global daily floor: net ${global_net:.2f} < ${global_limit} "
                           "— bot suspended for rest of day")

        return True, "ok"

    def record(self, token_id, stake, success, side="BUY", trader_name=""):
        self._check_day_reset()
        if success and side == "BUY":
            self.market_exposure[token_id] += stake
            self.daily_deployed             += stake
            if trader_name:
                self.trader_daily[trader_name]              += stake
                self._sizing_count[(trader_name, token_id)] += 1

    def record_win_credit(self, trader_name, usdc):
        """Call when a position is successfully claimed — reduces effective daily loss."""
        self._check_day_reset()
        self.trader_credits[trader_name] += usdc
        log(f"  💳 Win credit: +${usdc:.2f} → {trader_name} net loss now "
            f"${self.get_trader_net_loss(trader_name):.2f}")

    def record_realized_loss(self, trader_name, stake):
        """
        v6.1: Call ONLY when a position is confirmed closed as a LOSS.
        This is what actually feeds the daily loss stop — NOT deployed capital.
        """
        self._check_day_reset()
        self.realized_losses[trader_name] += stake
        log(f"  📉 Realized loss: −${stake:.2f} → {trader_name} net loss now "
            f"${self.get_trader_net_loss(trader_name):.2f}")


risk = RiskManager()

# ── FILL AGGREGATOR ───────────────────────────────────────────────────────────

class FillAggregator:
    """Groups rapid micro-fills on the same (conditionId, side, asset) into one copy order."""
    def __init__(self):
        self.buckets   = {}
        self._mm_track = defaultdict(lambda: defaultdict(list))

    def add(self, trader_name, act):
        key = (trader_name, act["conditionId"], act["side"], act["asset"])
        now = time.time()

        if act["side"] == "BUY":
            cid     = act["conditionId"]
            out_idx = act.get("outcomeIndex", -1)
            cutoff  = now - FILL_AGG_WINDOW * 20
            self._mm_track[trader_name][cid].append((out_idx, now))
            self._mm_track[trader_name][cid] = [
                (i, t) for (i, t) in self._mm_track[trader_name][cid] if t > cutoff
            ]
            distinct = {i for (i, t) in self._mm_track[trader_name][cid] if i >= 0}
            if len(distinct) > 1:
                log(
                    f"  🚫 MM-filter: {trader_name} bought outcomes {sorted(distinct)} on "
                    f"{cid[:22]}... — likely market-making, skip", "WARN",
                )
                return "MM_FILTERED"

        if key not in self.buckets:
            self.buckets[key] = {"acts": [], "last_ts": now}
        self.buckets[key]["acts"].append(act)
        self.buckets[key]["last_ts"] = now
        return None

    def flush_ready(self):
        now    = time.time()
        ready  = []
        remove = []
        for key, bucket in self.buckets.items():
            if now - bucket["last_ts"] >= FILL_AGG_WINDOW:
                ready.append((key, bucket["acts"]))
                remove.append(key)
        for k in remove:
            del self.buckets[k]
        return ready


aggregator = FillAggregator()

# ── CLOB CLIENT ───────────────────────────────────────────────────────────────

def init_clob():
    if not CLOB_AVAILABLE:
        return None
    if not PRIVATE_KEY or "YOUR_PRIVATE_KEY" in PRIVATE_KEY:
        log("PRIVATE_KEY not configured — forcing DRY_RUN", "WARN")
        return None
    try:
        client = ClobClient(
            CLOB_HOST,
            key            = PRIVATE_KEY,
            chain_id       = CHAIN_ID,
            signature_type = POLY_SIGNATURE_TYPE,
            funder         = POLY_FUNDER_ADDRESS if POLY_FUNDER_ADDRESS else None,
        )
        if POLY_API_KEY and POLY_API_SECRET and POLY_API_PASSPHRASE:
            from py_clob_client.clob_types import ApiCreds
            client.set_api_creds(ApiCreds(
                api_key        = POLY_API_KEY,
                api_secret     = POLY_API_SECRET,
                api_passphrase = POLY_API_PASSPHRASE,
            ))
            log("CLOB client ready (explicit API creds)")
        else:
            client.set_api_creds(client.create_or_derive_api_creds())
            log("CLOB client ready (derived API creds)")
        try:
            signer_addr    = client.get_address()
            funder_display = POLY_FUNDER_ADDRESS if POLY_FUNDER_ADDRESS else signer_addr
            log(f"CLOB signer  : {signer_addr}")
            log(f"CLOB funder  : {funder_display}")
            from py_clob_client.clob_types import AssetType, BalanceAllowanceParams
            bal     = client.get_balance_allowance(
                params=BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
            )
            balance = float(bal.get("balance", 0) or 0) / 1e6
            log(f"CLOB balance : ${balance:.2f} USDC")
            if balance < STAKE:
                log(f"⚠️  CLOB balance ${balance:.2f} < stake ${STAKE} — orders will fail!", "WARN")
                send_telegram(f"⚠️ <b>Low CLOB balance</b>: ${balance:.2f} USDC\nNeeded per trade: ${STAKE}")
        except Exception as be:
            log(f"Balance check skipped: {be}", "WARN")
        return client
    except Exception as e:
        log(f"CLOB init failed: {e}", "ERROR")
        return None

def get_book_info(client, token_id):
    try:
        book     = client.get_order_book(token_id)
        asks     = [float(a.price) for a in (book.asks if hasattr(book, "asks") else [])]
        bids     = [float(b.price) for b in (book.bids if hasattr(book, "bids") else [])]
        best_ask = min(asks) if asks else None
        best_bid = max(bids) if bids else None
        spread   = round(best_ask - best_bid, 6) if (best_ask and best_bid) else None
        return {"best_ask": best_ask, "best_bid": best_bid, "spread": spread}
    except Exception:
        pass
    return {"best_ask": None, "best_bid": None, "spread": None}

def _rotate_clob_proxy(direct=False):
    try:
        import httpx as _hx
        import py_clob_client.http_helpers.helpers as _ch
        _ch._http_client = _hx.Client() if (direct or not PROXY_URL) else _hx.Client(proxy=PROXY_URL)
    except Exception:
        pass

def place_order(client, token_id, side_str, stake, label):
    """Place one market order with proxy-rotation retry on 403 geoblock."""
    side = BUY if side_str == "BUY" else SELL_SIDE
    if DRY_RUN or client is None:
        log(f"  [DRY RUN] {side_str} ${stake:.2f} — {label}", "DRY")
        return True, {"dry_run": True, "token_id": token_id, "side": side_str, "stake": stake}
    for attempt in range(1, 6):
        try:
            signed = client.create_market_order(
                MarketOrderArgs(token_id=token_id, amount=stake, side=side)
            )
            resp = client.post_order(signed, OrderType.FOK)
            log(f"  ✅ {side_str} ${stake:.2f} placed | {resp}")
            if PROXY_URL: _rotate_clob_proxy()
            return True, resp
        except Exception as e:
            err    = str(e)
            is_geo = any(k in err.lower() for k in ("regional", "restricted", "geoblock", "403"))
            is_net = any(k in err      for k in ("Request exception", "socket", "timeout", "TLS"))
            if (is_geo or is_net) and attempt < 5:
                if attempt == 4 and PROXY_URL:
                    log(f"  ⚠️  Proxy geo-blocked {attempt}× — attempt {attempt+1} direct", "WARN")
                    _rotate_clob_proxy(direct=True)
                else:
                    log(f"  ⚠️  {'Geo-block' if is_geo else 'Net error'} attempt {attempt} — rotating", "WARN")
                    if PROXY_URL: _rotate_clob_proxy()
                time.sleep(1)
                continue
            log(f"  ❌ Order failed — {side_str} ${stake:.2f}: {e}", "ERROR")
            if PROXY_URL: _rotate_clob_proxy()
            return False, {"error": str(e)}
    log(f"  ❌ Order failed after 5 attempts — {side_str} ${stake:.2f}", "ERROR")
    if PROXY_URL: _rotate_clob_proxy()
    return False, {"error": "Max retries exceeded"}

# ── EXECUTE AGGREGATED GROUP ──────────────────────────────────────────────────

def execute_group(trader, acts, client, positions, edge_tracker):
    """Fire one copy trade for an aggregated fill group. v6.0 overhaul."""
    first      = acts[0]
    side       = first["side"]
    token_id   = first["asset"]
    outcome    = first["outcome"]
    title      = first["title"]
    event_slug = first.get("eventSlug", "")
    n_fills    = len(acts)

    total_usdc = sum(float(a["usdcSize"]) for a in acts)
    total_size = sum(float(a["size"])     for a in acts)
    if total_usdc > 0:
        sig_price = sum(float(a["price"]) * float(a["usdcSize"]) for a in acts) / total_usdc
    else:
        sig_price = float(first["price"])

    market_url = f"{POLY_BASE}/{event_slug}" if event_slug else POLY_BASE
    label      = f"{outcome} — {title[:40]}"

    log(f"🔔 {trader['name']} | {side} {outcome} @ ${sig_price:.4f} | "
        f"${total_usdc:,.0f} USDC ({n_fills} fills) | {title[:45]}")

    # ── Staleness check ────────────────────────────────────────────────────────
    last_ts        = max(a["timestamp"] for a in acts)
    signal_age_sec = now_unix() - last_ts
    if signal_age_sec > STALENESS_CUTOFF:
        log(f"  ⏰ Signal {signal_age_sec}s old (>{STALENESS_CUTOFF}s) — stale, skip", "WARN")
        write_log({
            "ts": datetime.now(timezone.utc).isoformat(), "trader": trader["name"],
            "action": "SKIPPED", "reason": f"Stale signal {signal_age_sec}s > {STALENESS_CUTOFF}s",
            "token_id": token_id, "side": side, "signal_price": sig_price,
        })
        return

    # ── EXIT: mirror trader's sell ─────────────────────────────────────────────
    if side == "SELL":
        shares = positions.get(token_id, 0)
        if shares <= 0:
            log(f"  ↩️  {trader['name']} exited {outcome} — not in our positions, skip")
            return
        if client and not DRY_RUN:
            try:
                from py_clob_client.clob_types import AssetType, BalanceAllowanceParams
                bal = client.get_balance_allowance(
                    params=BalanceAllowanceParams(asset_type=AssetType.CONDITIONAL, token_id=token_id)
                )
                live_shares = float(bal.get("balance", 0) or 0) / 1e6
                if live_shares > 0:
                    shares = live_shares
                else:
                    # v7.5: ghost position — 0 CLOB balance, purge & skip
                    log(f"  🧹 Ghost pos {token_id[:20]}… 0 CLOB balance — purging & skip")
                    positions.pop(token_id, None)
                    positions.pop(f"{token_id}_meta", None)
                    save_positions(positions)
                    return
            except Exception as be:
                log(f"  ⚠️  Balance query failed: {be}", "WARN")

        log(f"🚪 {trader['name']} EXIT {outcome} — selling {shares:.4f} shares | {title[:45]}")
        ok, resp = place_order(client, token_id, "SELL", shares, f"EXIT {label}")
        if ok:
            positions.pop(token_id, None)
            positions.pop(f"{token_id}_meta", None)   # v6.9: clean up orphaned meta key
            save_positions(positions)
            send_telegram(
                f"🚪 <b>Exit mirrored</b>\n"
                f"Trader: <b>{trader['name']}</b>\nMarket: {title[:60]}\n"
                f"Sold: <b>{shares:.4f} shares</b>\n<a href='{market_url}'>View market</a>"
            )
        else:
            err = resp.get("error", "?") if isinstance(resp, dict) else str(resp)
            log(f"  ❌ Exit FAILED: {err[:120]}", "ERROR")
            send_telegram(f"❌ <b>Exit FAILED</b>\n{trader['name']} | {title[:50]}\n<code>{err[:200]}</code>")
        write_log({
            "ts": datetime.now(timezone.utc).isoformat(), "trader": trader["name"],
            "wallet": trader["wallet"], "action": "EXIT", "side": "SELL",
            "outcome": outcome, "token_id": token_id, "title": title,
            "shares_sold": shares, "dry_run": DRY_RUN, "success": ok,
            "response": resp if isinstance(resp, dict) else {"raw": str(resp)},
            "url": market_url,
        })
        return

    # ── BUY path ───────────────────────────────────────────────────────────────

    # v6.0: Global category block — checked BEFORE trader filter
    blocked, blocked_cat = is_globally_blocked(title, trader=trader)
    if blocked:
        log(f"  🚫 Globally blocked category '{blocked_cat}': {title[:55]}", "WARN")
        write_log({
            "ts": datetime.now(timezone.utc).isoformat(), "trader": trader["name"],
            "action": "SKIPPED", "reason": f"Globally blocked category: {blocked_cat}",
            "token_id": token_id, "side": side, "signal_price": sig_price,
        })
        return

    # v6.0: Resolution days filter — skip long-term capital traps
    if MAX_RESOLUTION_DAYS > 0:
        days_to_end = get_market_end_days(token_id)
        if days_to_end is not None and days_to_end > MAX_RESOLUTION_DAYS:
            reason = f"Market resolves in {days_to_end:.0f}d > {MAX_RESOLUTION_DAYS}d cap (capital trap)"
            log(f"  📅 {reason}", "WARN")
            write_log({
                "ts": datetime.now(timezone.utc).isoformat(), "trader": trader["name"],
                "action": "SKIPPED", "reason": reason,
                "token_id": token_id, "side": side, "signal_price": sig_price,
            })
            return

    # v5.4: Confluence counter
    conf_key = (first["conditionId"], side, first["asset"])   # v6.9: asset prevents YES+NO buyers from conflating confluence
    now_t    = now_unix()
    _confluence_tracker[conf_key] = [
        (n, t) for (n, t) in _confluence_tracker[conf_key]
        if now_t - t <= CONFLUENCE_WINDOW_SEC
    ]
    active_names = {n for (n, t) in _confluence_tracker[conf_key]}
    if trader["name"] not in active_names:
        _confluence_tracker[conf_key].append((trader["name"], now_t))
        active_names.add(trader["name"])
    n_confluent = len(active_names)

    # v6.0: Price-adjusted + edge-weighted stake (replaces flat base_stake)
    base_stake      = round(get_dynamic_stake(_live_usdc) * trader.get("stake_mult", 1.0), 2)  # v7.4: auto-compound
    price_adj_stake = calculate_stake(base_stake, sig_price, trader, edge_tracker)

    # v5.7: Sizing-up mechanic (repeat buys on same token)
    sizing_count = risk.get_sizing_count(trader["name"], token_id)

    # v7.7: survival mode copy delay — hold off first entry on any new token for COPY_DELAY_SEC
    if sizing_count == 0:
        _sfirst = _source_first_seen.setdefault((trader["name"], token_id), time.time())
        _age    = time.time() - _sfirst
        if _age < COPY_DELAY_SEC:
            log(f"  ⏳ COPY_DELAY {trader['name']} | {token_id[:16]}… age={_age:.0f}s < {COPY_DELAY_SEC}s — holding")
            return

    # v6.1: Per-market buy cap — prevents unlimited sizing-up concentration
    if sizing_count >= MAX_BUYS_PER_MARKET:
        reason = (f"Max buys per market reached ({sizing_count}/{MAX_BUYS_PER_MARKET}) "
                  f"for {trader['name']} on {token_id[:20]}...")
        log(f"  🔒 {reason}", "RISK")
        write_log({
            "ts": datetime.now(timezone.utc).isoformat(), "trader": trader["name"],
            "action": "SKIPPED", "reason": reason,
            "token_id": token_id, "side": side, "signal_price": sig_price,
        })
        return

    sizing_bonus = round(sizing_count * price_adj_stake * SIZING_STEP, 2)   # v6.9: proportional (30% of price-adj stake per repeat)

    # Cap sizing bonus so total doesn't exceed trader max_stake
    trader_cap    = trader.get("max_stake", MAX_STAKE_PER_TRADE)
    effective_stake = min(round(price_adj_stake + sizing_bonus, 2), trader_cap, MAX_STAKE_PER_TRADE)

    if sizing_count > 0:
        log(
            f"  📈 Sizing up ×{sizing_count+1}: ${price_adj_stake:.2f} price-adj "
            f"+ ${sizing_bonus:.2f} bonus = ${effective_stake:.2f}"
        )

    # v5.4: Confluence boost (on top of everything, still capped by trader max)
    if n_confluent >= CONFLUENCE_THRESHOLD:
        boosted = min(round(effective_stake * CONFLUENCE_MULTIPLIER, 2), trader_cap, MAX_STAKE_PER_TRADE)
        log(
            f"  🔥 CONFLUENCE: {n_confluent} traders → ${effective_stake:.2f} "
            f"× {CONFLUENCE_MULTIPLIER} = ${boosted:.2f}",
        )
        effective_stake = boosted
    elif n_confluent == 2:
        log(f"  📶 2-trader alignment ({', '.join(sorted(active_names))}) — watching for 3rd")

    # Whale guard
    if total_usdc > MAX_WHALE_ORIGINAL and effective_stake > price_adj_stake:
        log(f"  🐋 Whale trade (${total_usdc:,.0f}) — suppressing boost to ${price_adj_stake:.2f}")
        effective_stake = price_adj_stake

    # Order book: live price + spread check
    live_price = sig_price
    if client and not DRY_RUN:
        book_info = get_book_info(client, token_id)
        lp = book_info["best_ask"] if side == "BUY" else book_info["best_bid"]
        if lp is not None:
            live_price = lp
        if book_info["spread"] is not None and book_info["spread"] > MAX_SPREAD:
            msg = (f"Wide spread ${book_info['spread']:.3f} > ${MAX_SPREAD:.3f} "
                   f"(ask={book_info['best_ask']}, bid={book_info['best_bid']}) — illiquid, skip")
            log(f"  💸 {msg}", "WARN")
            write_log({
                "ts": datetime.now(timezone.utc).isoformat(), "trader": trader["name"],
                "action": "SKIPPED", "reason": msg, "token_id": token_id, "side": side,
                "signal_price": sig_price, "spread": book_info["spread"],
            })
            return

    allowed, reason = risk.check(token_id, effective_stake, sig_price, live_price,
                                 trader_name=trader["name"])
    if not allowed:
        log(f"  ⛔ Skipped — {reason}", "RISK")
        send_telegram(
            f"⛔ <b>Trade skipped</b>\nTrader: <b>{trader['name']}</b>\n"
            f"Market: {title[:50]}\nReason: <code>{reason}</code>"
        )
        write_log({
            "ts": datetime.now(timezone.utc).isoformat(), "trader": trader["name"],
            "action": "SKIPPED", "reason": reason, "token_id": token_id,
            "side": side, "signal_price": sig_price, "live_price": live_price,
        })
        return

    # v7.6.17: CLOB balance hard gate — skip BUY if exchange cash < stake (prevents order spam)
    if side == "BUY" and _live_usdc < effective_stake:
        log(f"  ⛔ CLOB dry (${_live_usdc:.2f} < ${effective_stake:.2f}) — skip buy until funded", "WARN")
        return

    shares = 0.0  # v7.6.0: init so fill_price available in write_log regardless of fill path
    ok, resp = place_order(client, token_id, side, effective_stake, label)
    risk.record(token_id, effective_stake, ok, side=side, trader_name=trader["name"])

    if ok and side == "BUY" and isinstance(resp, dict):
        if resp.get("dry_run"):
            shares = effective_stake / live_price if live_price > 0 else effective_stake / sig_price
        else:
            raw_taking = resp.get("takingAmount") or ""
            if raw_taking:
                shares = float(raw_taking)
            else:
                # delayed/resting limit order — takingAmount is '' until filled
                # estimate shares so we can still track and auto-claim the position
                shares = effective_stake / live_price if live_price > 0 else effective_stake / sig_price
                log(f"  ⚠️  takingAmount empty (delayed order) — tracking ~{shares:.4f} est. shares", "WARN")
        if shares > 0:
            positions[token_id] = positions.get(token_id, 0) + shares
            # v7.5.2: schedule token_id verification on next claim cycle via balanceOf pre-check
            meta = positions.get(f"{token_id}_meta", {})
            meta["trader"]        = trader["name"]
            meta["trader_wallet"] = trader["wallet"]   # v7.5.5: for abandoned-pos detection
            meta["stake"]         = meta.get("stake", 0) + effective_stake
            if "opened_ts" not in meta:
                meta["opened_ts"] = datetime.now(timezone.utc).isoformat()
            positions[f"{token_id}_meta"] = meta
            log(f"  📦 Position: +{shares:.4f} shares → {positions[token_id]:.4f} total | {token_id[:20]}...")
            save_positions(positions)

    edge_score = edge_tracker.get_score(trader["name"])
    price_fac  = (1 - sig_price) * 2
    confluent_tag = f" 🔥×{n_confluent}" if n_confluent >= CONFLUENCE_THRESHOLD else ""
    mode_tag = "🔶 DRY RUN" if DRY_RUN else "✅ LIVE"
    if ok:
        send_telegram(
            f"{mode_tag} <b>Copy trade placed</b>{confluent_tag}\n"
            f"Trader: <b>{trader['name']}</b> (edge={edge_score:.0f}/100)\n"
            f"Side: <b>{side}</b> {outcome}\nMarket: {title[:60]}\n"
            f"Signal: ${sig_price:.4f} | Live: ${live_price:.4f} | price_factor={price_fac:.2f}×\n"
            f"Stake: <b>${effective_stake}</b> | Fills: {n_fills}\n"
            f"Confluent traders: {n_confluent} | Deployed today: ${risk.daily_deployed:.2f}\n"
            f"<a href='{market_url}'>View market</a>"
            f"{portfolio_line(client)}"
        )
    else:
        err = resp.get("error", "unknown error") if isinstance(resp, dict) else str(resp)
        send_telegram(
            f"❌ <b>Order FAILED</b>\nTrader: {trader['name']} | {side} {outcome}\n"
            f"Market: {title[:50]}\nError: <code>{err[:200]}</code>"
        )

    _now_ts = time.time()
    write_log({
        "ts":             datetime.now(timezone.utc).isoformat(),
        "action":         "BUY",                               # v7.6.0: was missing (all showed action=None)
        "trader":         trader["name"],
        "wallet":         trader["wallet"],
        "archetype":      trader.get("archetype", "unknown"),
        "n_fills":        n_fills,
        "side":           side,
        "outcome":        outcome,
        "token_id":       token_id,
        "title":          title,
        "signal_price":   sig_price,
        "live_price":     live_price,
        "fill_price":     round(effective_stake / shares, 4) if shares > 0 else None,  # v7.6.0: actual fill cost-per-share
        "remaining_edge": round((1 - live_price) / (1 - sig_price), 3) if (0 < sig_price < 0.99) else None,  # v7.6.0: our upside vs trader's upside
        "order_status":   resp.get("status", "unknown") if isinstance(resp, dict) else "unknown",  # v7.6.0: matched vs delayed
        "trader_ts":      last_ts,                              # v6.5: trader's original trade timestamp
        "signal_age_sec": round(_now_ts - last_ts, 1),         # v6.5: latency = now - trader's trade time
        "price_factor":   round(price_fac, 3),
        "edge_score":     round(edge_score, 1),
        "orig_usdc":      total_usdc,
        "orig_size":      total_size,
        "copy_stake":     effective_stake,
        "n_confluent":    n_confluent,
        "confluence_boost": effective_stake > price_adj_stake,
        "dry_run":        DRY_RUN,
        "success":        ok,
        "response":       resp,
        "url":            market_url,
    })

# ── AUTO-CLAIM ────────────────────────────────────────────────────────────────

def check_market_resolution(token_id):
    """
    Returns (is_resolved, we_hold_winner).
    v5.9 two-path detection kept unchanged.
    Path 1: Official Gamma closed+winner.
    Path 2: Price-based after CLAIM_HOURS_PAST_END hours past endDate.
    """
    try:
        data = fetch_json(f"{GAMMA_API}/markets?clob_token_ids={token_id}")
        mkts = data if isinstance(data, list) else data.get("markets", [data])
        if not mkts:
            return False, False
        mkt = mkts[0]

        # Path 1: Official
        if mkt.get("closed"):
            winner = mkt.get("winner", "")
            if not winner:
                pass  # v7.5: empty winner — fall through to price/API check below
            raw_ids      = mkt.get("clobTokenIds", "[]")
            raw_outcomes = mkt.get("outcomes",     "[]")
            try:
                ids      = json.loads(raw_ids)      if isinstance(raw_ids,      str) else raw_ids
                outcomes = json.loads(raw_outcomes) if isinstance(raw_outcomes, str) else raw_outcomes
            except Exception:
                return True, False
            winner_lower = winner.lower()
            for i, outcome in enumerate(outcomes):
                if outcome.lower() == winner_lower and i < len(ids):
                    return True, (ids[i] == token_id)
            # v7.5: no matching outcome found — fall through to price/API check

        # Path 2: Price-based
        end_date_str = mkt.get("endDate", "")
        if end_date_str:
            try:
                end_dt     = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                hours_past = (datetime.now(timezone.utc) - end_dt).total_seconds() / 3600
                if hours_past >= CLAIM_HOURS_PAST_END:
                    price = float(mkt.get("lastTradePrice") or 0)
                    if price >= CLAIM_WIN_PRICE_THRESHOLD:
                        log(f"  🕐 {token_id[:22]}... {hours_past:.1f}h past end, "
                            f"price={price:.3f} ≥ {CLAIM_WIN_PRICE_THRESHOLD} → WIN (price-based)")
                        return True, True
                    elif price <= CLAIM_LOSS_PRICE_THRESHOLD:
                        log(f"  🕐 {token_id[:22]}... {hours_past:.1f}h past end, "
                            f"price={price:.3f} ≤ {CLAIM_LOSS_PRICE_THRESHOLD} → LOSS (price-based)")
                        return True, False
            except Exception:
                pass
        return False, False
    except Exception as e:
        log(f"  ⚠️ Resolution check failed: {e}", "WARN")
        return False, False


def _ctf_get_web3():
    """Lazy-init web3 + CTF contract singleton. v7.2: tries fallback RPCs."""
    global _ctf_w3, _ctf_contract
    if not _WEB3_OK:
        return None, None
    if _ctf_w3 is not None:
        return _ctf_w3, _ctf_contract
    for rpc in [POLYGON_RPC] + POLYGON_RPC_FALLBACKS:
        try:
            w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 10}))
            _ = w3.eth.block_number   # confirm live
            # v7.6.9: verify contract calls decode (catches RPCs that pass block_number but return b'')
            _chk = w3.eth.contract(address=Web3.to_checksum_address(CTF_ADDRESS), abi=CTF_REDEEM_ABI)
            _chk.functions.balanceOf(Web3.to_checksum_address(POLY_FUNDER_ADDRESS), 1).call()
            w3.middleware_onion.inject(_poa_middleware, layer=0)
            _ctf_w3 = w3
            _ctf_contract = _chk
            log(f"  [CTF] web3 connected via {rpc}")
            return _ctf_w3, _ctf_contract
        except Exception as e:
            log(f"  [CTF] RPC {rpc} failed: {e}", "WARN")
    log("  [CTF] All Polygon RPCs failed — CTF redemption unavailable", "ERROR")
    return None, None


def _save_neg_risk_file(token_id: str):
    """v7.5.3: persist neg-risk token so bot does not re-alert after restart."""
    try:
        data = {}
        if os.path.exists(NEG_RISK_FILE):
            with open(NEG_RISK_FILE) as _f:
                data = json.load(_f)
        toks = set(data.get("tokens", []))
        toks.add(token_id)
        with open(NEG_RISK_FILE, "w") as _f:
            json.dump({"tokens": list(toks), "updated": datetime.now(timezone.utc).isoformat()}, _f)
        _neg_risk_tokens.add(token_id)
    except Exception as _e:
        log(f"  [NEG-RISK] Save failed: {_e}", "WARN")

def _load_neg_risk_file():
    """v7.5.3: on startup pre-populate _recon_claimed from neg_risk_pending.json."""
    global _neg_risk_tokens
    try:
        if not os.path.exists(NEG_RISK_FILE):
            return
        with open(NEG_RISK_FILE) as _f:
            data = json.load(_f)
        loaded = set(str(t) for t in data.get("tokens", []))
        _neg_risk_tokens.update(loaded)
        _recon_claimed.update(loaded)
        if loaded:
            log(f"  [NEG-RISK] Loaded {len(loaded)} pending neg-risk tokens — recon blocked ✓")
    except Exception as _e:
        log(f"  [NEG-RISK] Load failed: {_e}", "WARN")

def _cleanup_neg_risk_file(still_redeemable: set):
    """v7.5.3: remove tokens no longer redeemable (user claimed via UI) from file."""
    global _neg_risk_tokens
    try:
        if not os.path.exists(NEG_RISK_FILE):
            return
        with open(NEG_RISK_FILE) as _f:
            data = json.load(_f)
        toks = set(data.get("tokens", []))
        gone = toks - still_redeemable
        if not gone:
            return
        toks -= gone
        with open(NEG_RISK_FILE, "w") as _f:
            json.dump({"tokens": list(toks), "updated": datetime.now(timezone.utc).isoformat()}, _f)
        _neg_risk_tokens -= gone
        for t in gone:
            log(f"  [NEG-RISK] {t[:22]}… no longer redeemable — cleared from pending file ✓")
    except Exception as _e:
        log(f"  [NEG-RISK] Cleanup failed: {_e}", "WARN")

def _save_pending_claims():
    """v7.6.0: persist _pending_claim_orders to JSON so poll survives restarts."""
    try:
        with open(_PENDING_CLAIMS_FILE, "w") as _f:
            json.dump({"orders": _pending_claim_orders,
                       "updated": datetime.now(timezone.utc).isoformat()}, _f)
    except Exception as _e:
        log(f"  [PENDING-CLAIMS] Save failed: {_e}", "WARN")


def _load_pending_claims():
    """v7.6.0: on startup reload any pending delayed SELL claim orders."""
    global _pending_claim_orders
    try:
        if not os.path.exists(_PENDING_CLAIMS_FILE):
            return
        with open(_PENDING_CLAIMS_FILE) as _f:
            data = json.load(_f)
        loaded = data.get("orders", {})
        if loaded:
            _pending_claim_orders.update(loaded)
            log(f"  [PENDING-CLAIMS] Loaded {len(loaded)} pending delayed SELL orders ✓")
    except Exception as _e:
        log(f"  [PENDING-CLAIMS] Load failed: {_e}", "WARN")


def poll_pending_claims(client, edge_tracker):
    """
    v7.6.0: Poll get_order() for each pending delayed SELL claim order.
    Called at the start of each try_claim() cycle.
    On MATCHED  → record real proceeds in EdgeTracker + send Telegram.
    On CANCELLED/EXPIRED/404/timeout(>1h) → log, remove, no fake proceeds.
    """
    global _pending_claim_orders, _session_wins
    if not _pending_claim_orders:
        return
    now_ts   = time.time()
    resolved = []

    for order_id, meta in list(_pending_claim_orders.items()):
        owner     = meta.get("owner", "unknown")
        stake     = float(meta.get("stake", 0))
        token_id  = meta.get("token_id", "")
        shares    = float(meta.get("shares", 0))
        stored_ts = float(meta.get("ts", now_ts))
        age_sec   = now_ts - stored_ts

        # ── Timeout: >1 h without matching ────────────────────────────────
        if age_sec > 3600:
            log(f"  [PENDING-CLAIMS] {order_id[:16]}… TIMEOUT >1h — no proceeds recorded", "WARN")
            write_log({
                "ts":       datetime.now(timezone.utc).isoformat(),
                "action":   "CLAIM_EXPIRED",
                "trader":   owner,
                "order_id": order_id,
                "token_id": token_id,
                "shares":   shares,
                "stake":    stake,
                "note":     "poll_pending_claims: delayed SELL timed out >1h, no proceeds (v7.6.8)",
            })
            send_telegram(
                f"⚠️ <b>Delayed SELL EXPIRED (>1h)</b>\n"
                f"Trader: <b>{owner}</b>\n"
                f"Shares: <b>{shares:.4f}</b> — no proceeds recorded\n"
                f"Order: <code>{order_id[:30]}…</code>\n"
                f"Manual verification recommended."
            )
            resolved.append(order_id)
            continue

        try:
            order_data = client.get_order(order_id)
        except Exception as _e:
            err_str = str(_e)
            if "404" in err_str or "not found" in err_str.lower():
                log(f"  [PENDING-CLAIMS] {order_id[:16]}… 404 (expired/pruned) — no proceeds recorded", "WARN")
                resolved.append(order_id)
            else:
                log(f"  [PENDING-CLAIMS] {order_id[:16]}… get_order error: {_e} — will retry", "WARN")
            continue

        if order_data is None:
            log(f"  [PENDING-CLAIMS] {order_id[:16]}… get_order returned None — will retry", "WARN")
            continue

        status       = str(order_data.get("status", "")).upper()
        size_matched = float(order_data.get("size_matched", 0) or 0)
        price        = float(order_data.get("price", 0) or 0)

        if status == "MATCHED":
            if size_matched == 0:
                log(f"  [PENDING-CLAIMS] {order_id[:16]}… MATCHED but size_matched=0 (API lag?) — will retry", "WARN")
                continue  # v7.6.8: retry next cycle, do not record zero proceeds
            proceeds = round(size_matched * price, 4)
            log(f"  [PENDING-CLAIMS] {order_id[:16]}… MATCHED ✓ | {size_matched:.4f}sh × {price:.4f} = ${proceeds:.4f} USDC (owner={owner})")
            edge_tracker.record(owner, stake, proceeds, won=True)
            risk.record_win_credit(owner, proceeds)
            _session_wins += proceeds
            write_log({
                "ts":       datetime.now(timezone.utc).isoformat(),
                "action":   "CLAIM_SETTLED",
                "trader":   owner,
                "order_id": order_id,
                "token_id": token_id,
                "shares":   shares,
                "proceeds": proceeds,
                "stake":    stake,
            })
            send_telegram(
                f"💰 <b>Delayed SELL settled!</b>\n"
                f"Trader: <b>{owner}</b>\n"
                f"Shares: <b>{shares:.4f}</b> × price <b>{price:.4f}</b> → <b>${proceeds:.4f} USDC</b>\n"
                f"Order: <code>{order_id[:30]}…</code>\n"
                f"Age: {int(age_sec)}s"
            )
            resolved.append(order_id)

        elif status in ("CANCELLED", "EXPIRED"):
            log(f"  [PENDING-CLAIMS] {order_id[:16]}… {status} — no proceeds recorded", "WARN")
            resolved.append(order_id)

        else:
            # Still OPEN/LIVE/DELAYED — retry next cycle
            log(f"  [PENDING-CLAIMS] {order_id[:16]}… still {status} (age={int(age_sec)}s) — will retry")

    if resolved:
        for oid in resolved:
            _pending_claim_orders.pop(oid, None)
        _save_pending_claims()


def _ctf_get_condition_and_index(token_id: str):
    """
    Returns (conditionId_hex, index_sets_list) for a token_id via Gamma API.
    index_sets: [1] for YES (bit 0), [2] for NO (bit 1).
    Returns (None, None) on failure OR if market is neg-risk (v7.5.2).
    v7.5.2: neg-risk markets use a different redemption architecture — standard
    redeemPositions() is a no-op for them. Return (None, None) to skip CTF and
    fall through to manual claim alert instead.
    """
    try:
        r = fetch_json(f"{GAMMA_API}/markets?clob_token_ids={token_id}")
        mkt = r[0] if isinstance(r, list) and r else (r if isinstance(r, dict) else None)
        if not mkt:
            return None, None
        # v7.5.2: skip CTF for neg-risk markets — redeemPositions is always a no-op
        cid = mkt.get("conditionId") or mkt.get("condition_id")
        if not cid:
            return None, None
        # v7.5.4: neg-risk — return (cid, None) so _ctf_redeem() uses NegRiskAdapter path
        if mkt.get("negRisk"):
            _neg_risk_tokens.add(token_id)
            log(f"  [CTF] negRisk=True for {token_id[:22]}… — routing to NegRiskAdapter")
            return cid, None
        tokens = mkt.get("clobTokenIds", "[]")
        if isinstance(tokens, str):
            tokens = json.loads(tokens)
        for idx, tid in enumerate(tokens):
            if str(tid) == str(token_id):   # v7.5.2: str() cast — JSON parses big ints, token_id is str
                return cid, [1 << idx]   # 1=YES, 2=NO
        return cid, [1]  # default to YES index if token not found in list
    except Exception as e:
        log(f"  [CTF] condition/index lookup failed: {e}", "WARN")
        return None, None


def _neg_risk_redeem(token_id: str, shares: float, condition_id: str) -> bool:
    """
    v7.5.4: Claim neg-risk position via NegRiskAdapter.redeemPositions() through Safe.
    Confirmed: Safe isApprovedForAll=True for NegRiskAdapter. Proven live 2026-03-06 (+$20.15).
    """
    try:
        _w3, _ctf = _ctf_get_web3()
        if not _w3 or not _ctf:
            log("  [CTF-NR] no web3", "WARN")
            return False
        SAFE = Web3.to_checksum_address(POLY_FUNDER_ADDRESS)
        NRA  = Web3.to_checksum_address(NEG_RISK_ADAPTER_ADDR)
        ZERO = "0x0000000000000000000000000000000000000000"

        raw_bal = _ctf.functions.balanceOf(SAFE, int(token_id)).call()
        if raw_bal == 0:
            log(f"  [CTF-NR] balanceOf=0 for {token_id[:22]}… — nothing to redeem", "WARN")
            return False
        log(f"  [CTF-NR] Safe holds {raw_bal/1e6:.4f} — determining YES/NO index…")

        # Determine YES/NO index from Gamma API clobTokenIds
        token_idx = 0
        try:
            _gr  = fetch_json(f"{GAMMA_API}/markets?clob_token_ids={token_id}")
            _mkt = _gr[0] if isinstance(_gr, list) and _gr else _gr
            _tok = _mkt.get("clobTokenIds", "[]")
            if isinstance(_tok, str):
                _tok = json.loads(_tok)
            for _i, _t in enumerate(_tok):
                if str(_t) == str(token_id):
                    token_idx = _i
                    break
        except Exception as _ge:
            log(f"  [CTF-NR] clobTokenIds lookup failed ({_ge}) — defaulting idx=0", "WARN")

        amounts = [0, 0]
        amounts[token_idx] = raw_bal
        log(f"  [CTF-NR] idx={token_idx} ({'YES' if token_idx==0 else 'NO'}), amounts={amounts}")

        _nra = _w3.eth.contract(address=NRA, abi=NEG_RISK_ADAPTER_ABI)
        _cid_b = bytes.fromhex(condition_id[2:] if condition_id.startswith("0x") else condition_id)
        _rcd   = _nra.encode_abi("redeemPositions", args=[_cid_b, amounts])
        _cd    = bytes.fromhex(_rcd[2:]) if isinstance(_rcd, str) else _rcd

        _safe  = _w3.eth.contract(address=SAFE, abi=SAFE_ABI)
        _nc    = _safe.functions.nonce().call()
        _gp    = max(int(_w3.eth.gas_price * 1.4), _w3.to_wei("120", "gwei"))
        _th    = _safe.functions.getTransactionHash(NRA, 0, _cd, 0, 0, 0, 0, ZERO, ZERO, _nc).call()
        _sig   = Account._sign_hash(_th, PRIVATE_KEY)
        log(f"  [CTF-NR] nonce={_nc} gp={_gp/1e9:.1f}gwei hash={_th.hex()[:16]}…")

        if DRY_RUN:
            log("  [CTF-NR] DRY RUN — skip execTransaction")
            return False

        _acc = Account.from_key(PRIVATE_KEY)
        _tx  = _safe.functions.execTransaction(
            NRA, 0, _cd, 0, 0, 0, 0, ZERO, ZERO, _sig.signature
        ).build_transaction({
            "from": _acc.address,
            "nonce": _w3.eth.get_transaction_count(_acc.address),
            "gas": 400000, "gasPrice": _gp, "chainId": 137,
        })
        _s   = _w3.eth.account.sign_transaction(_tx, PRIVATE_KEY)
        _txh = _w3.eth.send_raw_transaction(_s.raw_transaction)
        log(f"  [CTF-NR] TX: {_txh.hex()[:20]}… waiting…")
        _rcpt = _w3.eth.wait_for_transaction_receipt(_txh, timeout=30)
        if _rcpt.status == 1:
            log(f"  [CTF-NR] ✅ {raw_bal/1e6:.4f} USDC redeemed via NegRiskAdapter!")
            return True
        log(f"  [CTF-NR] execTransaction reverted: {_txh.hex()}", "WARN")
        log(  # v7.6.12: full revert context
            f"  [CTF-NR] REVERT DETAIL"
            f" | cond={condition_id[:22]}…"
            f" | token_idx={token_idx}"
            f" | amounts={amounts}"
            f" | safe_nonce={_nc}"
            f" | calldata={_cd.hex()[:80]}…", "WARN")
        write_log({  # v7.6.11
            "ts":             datetime.now(timezone.utc).isoformat(),
            "action":         "CLAIM_REVERTED",
            "path":           "NegRiskAdapter",
            "token_id":       token_id,
            "condition_id":   condition_id,
            "token_idx":      token_idx,
            "amounts":        amounts,
            "shares":         shares,
            "safe_nonce":     _nc,
            "calldata_hex":   _cd.hex() if isinstance(_cd, bytes) else str(_cd),
            "tx_hash":        _txh.hex(),
            "gas_price_gwei": round(_gp / 1e9, 2),
            "nra_address":    NEG_RISK_ADAPTER_ADDR,
        })
        return False
    except Exception as _e:
        log(f"  [CTF-NR] error: {_e}", "WARN")
        log(  # v7.6.11: always-in-scope context for exception path
            f"  [CTF-NR] EXCEPTION CONTEXT"
            f" | cond={condition_id[:22]}…"
            f" | shares={shares:.4f}", "WARN")
        return False

def _ctf_redeem(token_id: str, shares: float, condition_id: str, index_sets: list) -> bool:
    """
    Call CTF.redeemPositions() via Gnosis Safe.execTransaction().
    v7.4: CTF tokens are held by the Gnosis Safe (POLY_FUNDER_ADDRESS).
    PRIVATE_KEY (0x8032) is the sole Safe owner (threshold=1).
    No FUNDER_PRIVATE_KEY needed — PRIVATE_KEY signs the Safe tx directly.
    Returns True on success.
    """
    global _ctf_w3, _ctf_contract
    if DRY_RUN or not _WEB3_OK or not PRIVATE_KEY or not POLY_FUNDER_ADDRESS:
        return False

    # v7.5.2: balanceOf pre-check — prevents no-op CTF calls when Safe has 0 tokens.
    # Root cause: neg-risk markets use different token IDs in activity API vs positions API.
    # If balanceOf(Safe, token_id) == 0, the Safe doesn't hold these tokens — skip CTF.
    try:
        _w3_tmp, _ctf_tmp = _ctf_get_web3()
        if _w3_tmp and _ctf_tmp:
            _raw_bal = _ctf_tmp.functions.balanceOf(
                Web3.to_checksum_address(POLY_FUNDER_ADDRESS), int(token_id)
            ).call()
            if _raw_bal == 0:
                log(f"  [CTF] balanceOf=0 for {token_id[:22]}… — Safe holds no tokens, skipping CTF", "WARN")
                return False
            log(f"  [CTF] balanceOf={_raw_bal/1e6:.4f} — Safe has tokens ✓")
    except Exception as _e:
        log(f"  [CTF] balanceOf pre-check failed: {_e} — proceeding anyway", "WARN")

    # v7.5.4: neg-risk path — index_sets=None signals NegRiskAdapter instead of CTF
    if index_sets is None:
        return _neg_risk_redeem(token_id, shares, condition_id)

    ZERO_ADDR = "0x0000000000000000000000000000000000000000"
    # v7.6.10: SAFE_ABI_MINI -> module-level SAFE_ABI

    all_rpcs = [POLYGON_RPC] + POLYGON_RPC_FALLBACKS
    for attempt, _rpc in enumerate(all_rpcs):
        try:
            w3, ctf = _ctf_get_web3()
            if not w3 or not ctf:
                return False

            account   = w3.eth.account.from_key(PRIVATE_KEY)
            safe_addr = Web3.to_checksum_address(POLY_FUNDER_ADDRESS)
            safe      = w3.eth.contract(address=safe_addr, abi=SAFE_ABI)

            cid_bytes = bytes.fromhex(condition_id.replace("0x", "").zfill(64))
            call_data = ctf.encode_abi("redeemPositions", args=[
                Web3.to_checksum_address(USDC_ADDRESS),
                bytes(32),
                cid_bytes,
                index_sets,
            ])

            safe_nonce = safe.functions.nonce().call()
            tx_hash_b  = safe.functions.getTransactionHash(
                Web3.to_checksum_address(CTF_ADDRESS), 0, call_data,
                0, 0, 0, 0, ZERO_ADDR, ZERO_ADDR, safe_nonce
            ).call()

            signed_msg = w3.eth.account._sign_hash(tx_hash_b, PRIVATE_KEY)
            sig_bytes  = (signed_msg.r.to_bytes(32, "big") +
                          signed_msg.s.to_bytes(32, "big") +
                          bytes([signed_msg.v]))

            signer_nonce = w3.eth.get_transaction_count(account.address, "latest")
            outer = safe.functions.execTransaction(
                Web3.to_checksum_address(CTF_ADDRESS), 0, call_data,
                0, 0, 0, 0, ZERO_ADDR, ZERO_ADDR, sig_bytes
            ).build_transaction({
                "from":     account.address,
                "nonce":    signer_nonce,
                "gas":      350_000,
                "gasPrice": max(int(w3.eth.gas_price * 1.4), w3.to_wei("120", "gwei")),  # v7.5: dynamic
            })

            signed  = w3.eth.account.sign_transaction(outer, PRIVATE_KEY)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)  # v7.5.1: 90→30s, retry via MAX_CLAIM_ATTEMPTS

            if receipt.status == 1:
                log(f"  [CTF] ✅ Safe.execTransaction OK | tx={tx_hash.hex()[:18]}…")
                return True
            else:
                log(f"  [CTF] execTransaction reverted: {tx_hash.hex()}", "WARN")
                log(  # v7.6.11: full revert context
                    f"  [CTF] REVERT DETAIL | rpc={_rpc}"
                    f" | cond={condition_id[:22]}…"
                    f" | idx_sets={index_sets}"
                    f" | shares={shares:.4f}"
                    f" | safe_nonce={safe_nonce}"
                    f" | signer_nonce={signer_nonce}"
                    f" | calldata={call_data.hex()[:80]}…", "WARN")
                write_log({  # v7.6.11
                    "ts":             datetime.now(timezone.utc).isoformat(),
                    "action":         "CLAIM_REVERTED",
                    "path":           "CTF",
                    "token_id":       token_id,
                    "condition_id":   condition_id,
                    "index_sets":     index_sets,
                    "shares":         shares,
                    "rpc":            _rpc,
                    "safe_nonce":     safe_nonce,
                    "signer_nonce":   signer_nonce,
                    "calldata_hex":   call_data.hex(),
                    "tx_hash":        tx_hash.hex(),
                    "gas_price_gwei": round(outer["gasPrice"] / 1e9, 2),
                    "ctf_address":    CTF_ADDRESS,
                    "usdc_address":   USDC_ADDRESS,
                })
                return False

        except Exception as e:
            err = str(e)
            if "429" in err or "Too Many Requests" in err or "rate" in err.lower():
                log(f"  [CTF] RPC rate-limited (attempt {attempt+1}/{len(all_rpcs)}) — switching RPC", "WARN")
                _ctf_w3     = None
                _ctf_contract = None
                time.sleep(3)
                continue
            if "return data: b''" in err or ("return data" in err and "b''" in err):
                log(f"  [CTF] RPC empty response (attempt {attempt+1}/{len(all_rpcs)}) — trying next", "WARN")
                _ctf_w3 = None
                _ctf_contract = None
                continue  # v7.6.9: retry with next RPC via _ctf_get_web3() re-init
            log(f"  [CTF] Safe redemption exception: {e}", "WARN")
            log(  # v7.6.11: always-in-scope context for exception path
                f"  [CTF] EXCEPTION CONTEXT | rpc={_rpc}"
                f" | cond={condition_id[:22]}…"
                f" | idx_sets={index_sets}"
                f" | shares={shares:.4f}", "WARN")
            return False

    log("  [CTF] All RPCs exhausted — CTF redemption failed this cycle", "WARN")
    return False


def try_claim(client, positions, trader_map, edge_tracker):
    """
    v6.2: Auto-claim resolved positions.
      1. Try CTF on-chain redeemPositions() first (works even when CLOB is closed)
      2. Fall back to CLOB SELL
      3. Alert Telegram once if both fail (manual claim needed)
    Records outcomes to EdgeTracker + RiskManager.
    Called every 20 polls (~10 min) to reduce API load.
    """
    global _session_wins, _session_losses  # v7.4 fix: declare globals before += assignment

    poll_pending_claims(client, edge_tracker)   # v7.6.0: settle any delayed SELL orders

    if not positions:
        return

    to_remove    = []
    claimed_usdc = 0.0

    # v7.5: Batch-fetch funder positions from Polymarket API (one call, most accurate)
    # Handles CLOB-closed markets where curPrice=0 even for winning tokens.
    # Also reconciles untracked wins (positions on-chain but missing from positions.json).
    _api_resolved = {}  # token_id -> {win: bool, value: float}
    try:
        _url = ("https://data-api.polymarket.com/positions"
                "?user=%s&sizeThreshold=0.001" % POLY_FUNDER_ADDRESS)
        _req = urllib.request.Request(_url, headers={"User-Agent": "copytrade-bot/7.5"})
        _api_pos = json.loads(urllib.request.urlopen(_req, timeout=10).read())
        for _ap in _api_pos:
            _tid = str(_ap.get("asset", ""))
            _val = float(_ap.get("currentValue", 0) or 0)
            _red = bool(_ap.get("redeemable", False))
            _cur_p = float(_ap.get("curPrice") or 0)   # v7.6.6: SELL floor guard
            if _red and (_tid in positions or _val >= 0.05):
                _api_resolved[_tid] = {"win": _val > 0, "value": _val, "cur_price": _cur_p}
            # Reconcile: untracked win on-chain -> inject into positions.json
            # v7.5.1: skip tokens already claimed this session (API cache lag)
            if _tid in _recon_claimed:
                continue
            if _red and _val > 0.05 and _tid not in positions:
                _sz = float(_ap.get("size", _val) or _val)
                log(f"  🔍 Recon: untracked win {_tid[:20]}… ${_val:.2f} — injecting")
                positions[_tid] = _sz
                positions[_tid + "_meta"] = {
                    "trader": "recon-recovery", "stake": _val,
                    "claim_attempts": 0, "note": "auto-recon v7.5",
                }
                save_positions(positions)
        _wins = sum(1 for v in _api_resolved.values() if v["win"])
        if _api_resolved:
            log(f"  [CLAIM] API: {len(_api_resolved)} resolved ({_wins} wins)")
        # v7.5.3: cleanup neg-risk file for tokens user already claimed via Polymarket UI
        _still_red = {tid for tid, info in _api_resolved.items() if info.get("win")}
        _cleanup_neg_risk_file(_still_red)
    except Exception as _e:
        log(f"  [CLAIM] API pre-fetch failed: {_e} — using price-based fallback", "WARN")


    for token_id, shares in list(positions.items()):
        if token_id.endswith("_meta"):
            continue
        if shares <= 0:
            to_remove.append(token_id)
            continue

        # Already alerted — user knows, skip until resolved
        if token_id in _claim_alerted:
            continue

        # v7.5: API-first resolution (accurate for CLOB-closed markets)
        if token_id in _api_resolved:
            is_resolved = True
            we_win      = _api_resolved[token_id]["win"]
        else:
            is_resolved, we_win = check_market_resolution(token_id)
        if not is_resolved:
            continue

        # Resolve live share count via CLOB balance
        live_shares = shares
        if client and not DRY_RUN:
            try:
                from py_clob_client.clob_types import AssetType, BalanceAllowanceParams
                bal = client.get_balance_allowance(
                    params=BalanceAllowanceParams(asset_type=AssetType.CONDITIONAL, token_id=token_id)
                )
                live_shares = float(bal.get("balance", 0) or 0) / 1e6
                if live_shares < 0.01:
                    log(f"  🧹 {token_id[:22]}... on-chain balance 0 — removing")
                    _claim_alerted.discard(token_id)
                    to_remove.append(token_id)
                    to_remove.append(f"{token_id}_meta")
                    continue
            except Exception as be:
                log(f"  ⚠️  Balance query skipped: {be}", "WARN")

        trader_info = positions.get(f"{token_id}_meta", {})
        owner_name  = trader_info.get("trader", "unknown")
        entry_stake = trader_info.get("stake", live_shares)

        if we_win:
            log(f"  🏆 WIN: {token_id[:22]}... ({live_shares:.4f} shares) — trying CTF redeem…")
            usdc_value       = live_shares  # approx 1:1 for resolved YES positions
            claimed_ok       = False
            _delayed_claim   = False   # v7.6.1: True when CLOB SELL goes delayed
            _queued_order_id = ""      # v7.6.1: orderID for CLAIM_QUEUED log

            # ── Path 1: CTF on-chain redeem ─────────────────────────────────
            condition_id, index_sets = _ctf_get_condition_and_index(token_id)
            if condition_id:   # v7.5.4: index_sets may be None for neg-risk (handled in _ctf_redeem)
                claimed_ok = _ctf_redeem(token_id, live_shares, condition_id, index_sets)
                if claimed_ok:
                    claimed_usdc += usdc_value
                    _claim_alerted.discard(token_id)
                    edge_tracker.record(owner_name, entry_stake, usdc_value, won=True)
                    risk.record_win_credit(owner_name, usdc_value)
                    send_telegram(
                        f"💰 <b>CTF auto-claimed!</b>\n"
                        f"Shares: <b>{live_shares:.2f}</b> → ~<b>${usdc_value:.2f} USDC</b>\n"
                        f"Token: <code>{token_id[:30]}...</code>"
                        f"{portfolio_line(client)}"
                    )

            # ── v7.6.6: CLOB SELL price floor guard ──────────────────────────
            # Refuse to SELL a resolved WIN if CLOB price is near-zero.
            # CLOB can lag behind on-chain resolution by minutes — this was the
            # Sharp-c33a Jazz/Hornets failure: sold 142sh @$0.005 on a market
            # that resolved YES seconds later (lost ~$141 per position).
            if not claimed_ok and token_id in _api_resolved:
                _clob_floor_p = _api_resolved[token_id].get("cur_price", 1.0)
                if _clob_floor_p < CLAIM_WIN_SELL_FLOOR:
                    log(f"  [CTF] ⛔ CLOB cur_price={_clob_floor_p:.4f} < floor {CLAIM_WIN_SELL_FLOOR}"
                        f" — resolved WIN, CLOB lag detected. Deferring SELL (v7.6.6, no attempt counted).")
                    continue   # skip this cycle; do NOT place order; do NOT penalise claim_attempts

            # ── Path 2: CLOB SELL fallback ───────────────────────────────────
            if not claimed_ok:
                log(f"  [CTF] CTF failed/skipped — trying CLOB SELL fallback")
                ok, resp = place_order(client, token_id, "SELL", live_shares, f"CLAIM {token_id[:22]}")
                _order_status = resp.get("status", "") if (ok and isinstance(resp, dict)) else ""
                _order_id     = resp.get("orderID", "") if (ok and isinstance(resp, dict)) else ""
                usdc = float(resp.get("takingAmount", 0) or 0) if (ok and isinstance(resp, dict)) else 0.0
                if ok:
                    claimed_ok = True
                    _claim_alerted.discard(token_id)
                    if _order_status.lower() == "matched" and usdc > 0:
                        # Immediate fill — record proceeds now
                        claimed_usdc += usdc
                        edge_tracker.record(owner_name, entry_stake, usdc, won=True)
                        risk.record_win_credit(owner_name, usdc)
                        log(f"  [CTF] CLOB SELL MATCHED immediately — ${usdc:.4f} USDC ✓")
                        send_telegram(
                            f"💰 <b>Position claimed (SELL)!</b>\n"
                            f"Shares: <b>{live_shares:.2f}</b> → <b>${usdc:.2f} USDC</b>\n"
                            f"Token: <code>{token_id[:30]}...</code>"
                            f"{portfolio_line(client)}"
                        )
                        usdc_value = usdc
                    else:
                        # Delayed order — queue for settlement via poll_pending_claims()
                        _delayed_claim   = True       # v7.6.1: suppress provisional accounting
                        _queued_order_id = _order_id  # v7.6.1: captured for CLAIM_QUEUED log
                        log(f"  [CTF] CLOB SELL delayed (status={_order_status!r}) — order {_order_id[:16]}… queued for polling")
                        if _order_id:
                            _pending_claim_orders[_order_id] = {
                                "owner":    owner_name,
                                "stake":    entry_stake,
                                "token_id": token_id,
                                "shares":   live_shares,
                                "ts":       time.time(),
                            }
                            _save_pending_claims()
                            send_telegram(
                                f"⏳ <b>Claim SELL queued (delayed)</b>\n"
                                f"Trader: <b>{owner_name}</b>\n"
                                f"Shares: <b>{live_shares:.4f}</b> → polling for proceeds\n"
                                f"Order: <code>{_order_id[:30]}…</code>"
                            )
                        else:
                            log(f"  [CTF] CLOB SELL delayed but no orderID in response — cannot poll", "WARN")

            # ── Path 3: Retry-limited alert — abandon after MAX_CLAIM_ATTEMPTS ─────
            if not claimed_ok:
                # v7.5: persist claim_attempts to _meta so counter survives restarts
                _cmeta = positions.get(f"{token_id}_meta", {})
                _attempts = _cmeta.get("claim_attempts", 0) + 1
                _cmeta["claim_attempts"] = _attempts
                positions[f"{token_id}_meta"] = _cmeta
                save_positions(positions)

                # v7.5.3: neg-risk — block recon immediately + persist across restarts
                # Without this, ABANDONED pos gets re-injected by recon (API cache lag)
                if token_id in _neg_risk_tokens:
                    _recon_claimed.add(token_id)   # blocks recon THIS session
                    _save_neg_risk_file(token_id)  # blocks recon AFTER restart

                if _attempts >= MAX_CLAIM_ATTEMPTS:
                    log(f"  🔴 {token_id[:22]}… ABANDONED after {_attempts} attempts — removing from tracker", "ERROR")
                    send_telegram(
                        f"🔴 <b>Claim ABANDONED ({_attempts}/{MAX_CLAIM_ATTEMPTS} attempts)</b>\n"
                        f"Shares: <b>{live_shares:.2f}</b> (~<b>${usdc_value:.2f} USDC</b>)\n"
                        f"CTF + SELL failed {_attempts}× — bot will NOT retry.\n"
                        f"<b>→ Claim manually: polymarket.com/portfolio</b>\n"
                        f"Token: <code>{token_id[:30]}...</code>"
                    )
                    to_remove.append(token_id)
                    to_remove.append(f"{token_id}_meta")
                    _claim_alerted.discard(token_id)
                    _recon_claimed.add(token_id)   # v7.6.9: block recon re-inject after final abandonment
                else:
                    log(f"  ❌ Both CTF and SELL failed (attempt {_attempts}/{MAX_CLAIM_ATTEMPTS}) — alerting", "ERROR")
                    _claim_alerted.add(token_id)
                    send_telegram(
                        f"🏆 <b>WIN — manual claim needed!</b>\n"
                        f"Shares: <b>{live_shares:.2f}</b> (~<b>${usdc_value:.2f} USDC</b>)\n"
                        f"CTF redeem + CLOB SELL both failed (attempt {_attempts}/{MAX_CLAIM_ATTEMPTS}).\n"
                        f"<b>→ Claim at polymarket.com/portfolio</b>\n"
                        f"Token: <code>{token_id[:30]}...</code>"
                    )

            if claimed_ok:
                to_remove.append(token_id)
                to_remove.append(f"{token_id}_meta")
                _recon_claimed.add(token_id)   # v7.5.1: prevent recon re-inject
                if _delayed_claim:
                    # v7.6.1: SELL is in-flight — real proceeds arrive via poll_pending_claims()
                    # Do NOT add to _session_wins here; poll_pending_claims() will when settled
                    write_log({
                        "ts":       datetime.now(timezone.utc).isoformat(),
                        "action":   "CLAIM_QUEUED",
                        "trader":   owner_name,
                        "token_id": token_id,
                        "shares":   live_shares,
                        "order_id": _queued_order_id,
                    })
                else:
                    _session_wins += usdc_value   # v7.2 session tracker
                    write_log({
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "action": "CLAIM", "trader": owner_name, "token_id": token_id,
                        "shares": live_shares, "usdc_received": usdc_value, "success": True,
                    })

        else:
            _session_losses += entry_stake   # v7.2 session tracker
            log(f"  💀 {token_id[:22]}... resolved AGAINST us ({live_shares:.4f} shares → $0)")
            edge_tracker.record(owner_name, entry_stake, 0.0, won=False)
            risk.record_realized_loss(owner_name, entry_stake)
            send_telegram(
                f"💀 <b>Position resolved as loss</b>\n"
                f"Token: <code>{token_id[:30]}...</code>\nShares: {live_shares:.2f} → $0"
            )
            write_log({
                "ts": datetime.now(timezone.utc).isoformat(),
                "action": "RESOLVED_LOSS", "trader": owner_name, "token_id": token_id,
                "shares": live_shares, "stake": entry_stake, "usdc_received": 0.0, "success": False,
            })
            to_remove.append(token_id)
            to_remove.append(f"{token_id}_meta")

    if to_remove:
        for tid in set(to_remove):
            positions.pop(tid, None)
        save_positions(positions)
        if claimed_usdc > 0:
            log(f"  ✓ Claim run: ${claimed_usdc:.2f} USDC reclaimed, "
                f"{len(set(to_remove))} position(s) closed")
        else:
            log(f"  ✓ Claim run: {len(set(to_remove))} stale/resolved position(s) removed")


# ── SELL MIRROR ───────────────────────────────────────────────────────────────

class SellMirror:
    """
    v6.2: Background position monitor. Polls each trader's open positions via
    data-api every 2 polls. When a trader sells ≥30% of a position we hold,
    mirror the exit proportionally. Full exit (≥90% drop) removes position.
    """
    def __init__(self):
        self._last: dict[str, dict[str, float]] = {}
        # { trader_wallet: { token_id: share_count } }

    def _fetch(self, wallet: str) -> dict[str, float]:
        try:
            r = _requests.get(
                f"https://data-api.polymarket.com/positions?user={wallet}&sizeThreshold=0.01",
                timeout=10
            )
            data = r.json()
            if isinstance(data, dict) and "data" in data:
                data = data["data"]
            # v6.9: confirmed API fields — asset=token_id, size=shares (not price-affected)
            # Using size not currentValue so price moves don't trigger false exit signals
            return {
                str(p.get("asset") or p.get("conditionId") or ""):
                float(p.get("size") or 0)
                for p in (data or [])
                if float(p.get("size") or 0) > 0
            }
        except Exception as e:
            log(f"  [SELL_MIRROR] fetch failed {wallet[:12]}…: {e}", "WARN")
            return {}

    def check_exits(self, client, traders: list, our_positions: dict) -> None:
        for t in traders:
            wallet = t.get("wallet", "")
            if not wallet:
                continue
            current  = self._fetch(wallet)
            previous = self._last.get(wallet, {})

            for tid, prev_val in previous.items():
                if prev_val <= 0 or tid not in our_positions:
                    continue
                curr_val  = current.get(tid, 0.0)
                drop_pct  = (prev_val - curr_val) / prev_val

                if drop_pct < 0.20:   # v7.5.5: 30%→20% for faster mirror response
                    continue

                our_shares  = our_positions[tid]
                sell_shares = our_shares * drop_pct
                if sell_shares < 0.1:
                    continue

                # v7.5: ghost position guard — verify CLOB balance before SELL
                if client and not DRY_RUN:
                    try:
                        from py_clob_client.clob_types import AssetType, BalanceAllowanceParams
                        _b = client.get_balance_allowance(
                            params=BalanceAllowanceParams(asset_type=AssetType.CONDITIONAL, token_id=tid)
                        )
                        _live = float(_b.get("balance", 0) or 0) / 1e6
                        if _live < 0.01:
                            log(f"  [SELL_MIRROR] Ghost {tid[:12]}… 0 live balance — purging & skip", "WARN")
                            our_positions.pop(tid, None)
                            our_positions.pop(f"{tid}_meta", None)
                            save_positions(our_positions)
                            continue
                        sell_shares = min(sell_shares, _live)
                    except Exception:
                        pass  # fail-open: if check fails, proceed normally

                log(f"  [SELL_MIRROR] {t['name']} sold {drop_pct:.0%} of {tid[:12]}… "
                    f"— mirroring {sell_shares:.2f} shares")
                try:
                    ok, _ = place_order(client, tid, "SELL", sell_shares,
                                        f"MIRROR EXIT {t['name']} {tid[:12]}")
                    if ok:
                        if drop_pct >= 0.80:   # v7.5.7: 0.90→0.80 (prevents dust-stub on full exits)
                            our_positions.pop(tid, None)
                            our_positions.pop(f"{tid}_meta", None)
                        else:
                            remaining = our_shares - sell_shares
                            if remaining < 0.5:  # v7.5.7: cascade stub cleanup — too small to track
                                log(f"  [SELL_MIRROR] Stub {remaining:.2f}sh < 0.5 — full exit ✓", "INFO")
                                our_positions.pop(tid, None)
                                our_positions.pop(f"{tid}_meta", None)
                            else:
                                our_positions[tid] = remaining
                        save_positions(our_positions)
                        send_telegram(
                            f"📤 <b>Sell mirror</b>\n"
                            f"Trader: {t['name']} exited {drop_pct:.0%}\n"
                            f"Sold {sell_shares:.2f} shares of {tid[:16]}…"
                            f"{portfolio_line(client)}"
                        )
                except Exception as e:
                    log(f"  [SELL_MIRROR] sell failed: {e}", "WARN")

            self._last[wallet] = current

        # v7.5.5: Abandoned position check — if NO tracked trader holds a token we own, close it.
        # Catches positions where we restarted and the trader had already exited before first fetch.
        if len(self._last) > 0:
            _all_held = set()
            for _pd in self._last.values():
                _all_held.update(_pd.keys())
            _now = datetime.now(timezone.utc)
            for _tid in list(our_positions.keys()):
                if _tid.endswith("_meta") or our_positions.get(_tid, 0) <= 0:
                    continue
                if _tid in _all_held:
                    continue  # at least one tracked trader still holds it
                _meta2 = our_positions.get(f"{_tid}_meta", {})
                if _meta2.get("trader") in ("recon-recovery",):
                    continue  # let try_claim handle resolved positions
                _ots = _meta2.get("opened_ts", "")
                if _ots:
                    try:
                        _age_min = (_now - datetime.fromisoformat(_ots)).total_seconds() / 60
                        if _age_min < 20:
                            continue  # grace: ignore positions opened in last 10 min
                    except Exception:
                        pass
                elif not _ots:  # v7.6.3: fall through — no-TS = old pos, _all_held already protects
                    pass  # v7.6.3: allow abandoned-close (definitionally old, >10 min)
                if _tid in _claim_alerted:
                    continue  # v7.6.9: try_claim owns this token — sell_mirror must not interfere
                _sh = our_positions.get(_tid, 0)
                if _sh <= 0:
                    continue
                log(f"  [SELL_MIRROR] 🏃 Abandoned {_tid[:16]}… no trader holds it — closing {_sh:.4f} sh", "WARN")
                try:
                    if client and not DRY_RUN:
                        try:
                            from py_clob_client.clob_types import AssetType, BalanceAllowanceParams
                            _b2 = client.get_balance_allowance(
                                params=BalanceAllowanceParams(asset_type=AssetType.CONDITIONAL, token_id=_tid))
                            _live2 = float(_b2.get("balance", 0) or 0) / 1e6
                            if _live2 < 0.01:
                                our_positions.pop(_tid, None); our_positions.pop(f"{_tid}_meta", None)
                                save_positions(our_positions); continue
                            _sh = _live2
                        except Exception:
                            pass
                        _ok2, _resp2 = place_order(client, _tid, "SELL", _sh, f"ABANDONED {_tid[:12]}")
                        if _ok2:
                            our_positions.pop(_tid, None); our_positions.pop(f"{_tid}_meta", None)
                            save_positions(our_positions)
                            # v7.6.17: track delayed abandoned-close SELL in poll_pending_claims
                            _sell_status2 = _resp2.get("status", "") if isinstance(_resp2, dict) else ""
                            _sell_oid2    = _resp2.get("orderID", "") if isinstance(_resp2, dict) else ""
                            if _sell_status2 == "delayed" and _sell_oid2:
                                _pending_claim_orders[_sell_oid2] = {
                                    "owner":    (_meta2 or {}).get("trader", "unknown"),
                                    "stake":    (_meta2 or {}).get("stake", _sh),
                                    "token_id": _tid,
                                    "shares":   _sh,
                                    "ts":       time.time(),
                                }
                                _save_pending_claims()
                                log(f"  [SELL_MIRROR] Abandoned SELL delayed — order {_sell_oid2[:16]}… queued for poll", "WARN")
                            send_telegram(f"🏃 <b>Abandoned pos closed</b>\n"
                                          f"<code>{_tid[:30]}…</code>\n{_sh:.4f} sh — no tracked trader holds it")
                            # v7.6.12: SELL failed - resolved/dead market. Defer to try_claim; block retry loop.
                            _claim_alerted.add(_tid)
                            log(f"  [SELL_MIRROR] Abandoned SELL failed {_tid[:16]} - deferred to claim, retry blocked", "WARN")
                except Exception as _ae:
                    log(f"  [SELL_MIRROR] abandoned close err: {_ae}", "WARN")



def loss_sweeper(client, positions: dict, edge_tracker=None) -> None:
    """
    v7.5.6: Sweep confirmed-loss positions out of positions.json.
    Runs every 10 polls. Detects redeemable=True + currentValue=0 (confirmed loss)
    or curPrice<=0.01 (near-zero = effectively lost) and purges them.
    v7.6.5: Records confirmed/near-zero losses in EdgeTracker for accurate per-trader accounting.
    Stale purges (not in API) are NOT recorded (could be filled SELLs — ambiguous).
    """
    try:
        our_wallet = os.environ.get("POLY_FUNDER_ADDRESS", "")
        if not our_wallet:
            return
        import requests as _req
        resp = _req.get(
            f"https://data-api.polymarket.com/positions?user={our_wallet}&sizeThreshold=0.001&limit=500",
            timeout=10
        )
        if resp.status_code != 200:
            return
        live_pos = resp.json()
        if not isinstance(live_pos, list):
            return

        live_map = {str(p.get("asset") or ""): p for p in live_pos}
        changed = False

        for tid in list(positions.keys()):
            if tid.endswith("_meta"):
                continue
            p = live_map.get(tid)
            if p is None:
                # Not in API at all — stale (already sold/expired)
                meta = positions.get(f"{tid}_meta", {})
                ots = meta.get("opened_ts", "")
                if ots:
                    try:
                        age_min = (datetime.now(timezone.utc) - datetime.fromisoformat(ots)).total_seconds() / 60
                        if age_min < 30:
                            continue  # young position — give it time to appear in API
                    except Exception:
                        pass
                log(f"  [LOSS_SWEEP] Stale (not in API) — purging {tid[:18]}…", "INFO")
                positions.pop(tid, None)
                positions.pop(f"{tid}_meta", None)
                changed = True
                continue

            cur_val = float(p.get("currentValue") or 0)
            cur_price = float(p.get("curPrice") or 0)
            redeemable = p.get("redeemable", False)
            title = (p.get("title") or "")[:50]

            if redeemable and cur_val == 0 and cur_price <= 0.01:
                log(f"  [LOSS_SWEEP] Confirmed loss — purging {tid[:18]}… {title}", "INFO")
                # v7.6.5: record in EdgeTracker for accurate per-trader accounting
                _lsmeta = positions.get(f"{tid}_meta", {})
                _ls_trader = _lsmeta.get("trader", "")
                _ls_stake  = float(_lsmeta.get("stake") or 0)
                if edge_tracker and _ls_trader and _ls_stake > 0:
                    edge_tracker.record(_ls_trader, _ls_stake, 0.0, won=False)
                    risk.record_realized_loss(_ls_trader, _ls_stake)
                    write_log({"ts": datetime.now(timezone.utc).isoformat(),
                               "action": "RESOLVED_LOSS", "trader": _ls_trader,
                               "token_id": tid, "stake": _ls_stake,
                               "usdc_received": 0.0, "success": False,
                               "note": "loss_sweeper confirmed"})
                else:
                    log(f"  [LOSS_SWEEP] No trader/stake meta for {tid[:18]} — loss not recorded in EdgeTracker", "WARN")
                positions.pop(tid, None)
                positions.pop(f"{tid}_meta", None)
                changed = True
            elif cur_price <= 0.01 and not redeemable:
                # v7.6.7: market NOT yet resolved — tracking cleanup only.
                # In-play price collapses (live underdog etc.) must NOT poison EdgeTracker.
                # Only redeemable=True positions are confirmed losses.
                log(f"  [LOSS_SWEEP] Near-zero cur={cur_price:.4f}, unresolved — "
                    f"tracking cleanup only (v7.6.7): {tid[:18]}… {title}", "INFO")
                write_log({"ts": datetime.now(timezone.utc).isoformat(),
                           "action": "NEAR_ZERO_PURGE", "token_id": tid,
                           "cur_price": cur_price, "title": title,
                           "note": "loss_sweeper near-zero unresolved (v7.6.7: no financial accounting)"})
                positions.pop(tid, None)
                positions.pop(f"{tid}_meta", None)
                changed = True

        if changed:
            save_positions(positions)

    except Exception as e:
        log(f"  [LOSS_SWEEP] error: {e}", "WARN")

sell_mirror = SellMirror()

# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    mode    = "DRY RUN 🔶" if DRY_RUN else "LIVE 🟢"
    traders = [t for t in TRADERS if t["priority"] <= PRIORITY_LEVEL]
    trader_map = {t["name"]: t for t in traders}

    edge_tracker = EdgeTracker(EDGE_SCORE_FILE)

    value_traders      = [t for t in traders if t.get("archetype") == "value"]
    generalist_traders = [t for t in traders if t.get("archetype") == "generalist"]
    specialist_traders = [t for t in traders if t.get("archetype") == "specialist"]

    _load_neg_risk_file()   # v7.5.3: pre-populate _recon_claimed from neg_risk_pending.json
    _load_pending_claims()  # v7.6.0: reload any pending delayed SELL claim orders
    log("=" * 72)
    log(f"  POLYMARKET COPY-TRADE BOT v7.0  |  {mode}")
    log("=" * 72)
    log(f"  Base stake         : ${STAKE} × trader stake_mult × price_factor × edge_factor")
    log(f"  Price adjustment   : factor = (1 − entry_price) × 2  (0.16→1.68×, 0.80→0.40×)")
    log(f"  Max stake/order    : ${MAX_STAKE_PER_TRADE} (global) | per-trader see roster")
    log(f"  Sizing-up step     : +{SIZING_STEP:.0%} of price-adj stake per repeat buy (proportional)")
    log(f"  Max buys/market    : {MAX_BUYS_PER_MARKET} (v6.1: prevents León-style over-concentration)")
    log(f"  Poll interval      : {POLL_INTERVAL}s")
    log(f"  Traders active     : {len(traders)}  "
        f"({len(value_traders)} value, {len(generalist_traders)} generalist, {len(specialist_traders)} specialist)")
    log(f"  Max slippage       : {MAX_SLIPPAGE:.0%}")
    log(f"  Staleness cutoff   : {STALENESS_CUTOFF}s")
    log(f"  Max spread         : ${MAX_SPREAD:.3f}")
    log(f"  Max entry price    : ${MAX_ENTRY_PRICE:.2f}  (fee kills margin above this)")
    log(f"  Max per market     : ${MAX_PER_MARKET}")
    log(f"  Max resolution     : {MAX_RESOLUTION_DAYS}d  (v6.0: skip long-term capital traps)")
    log(f"  Blocked categories : {', '.join(GLOBALLY_BLOCKED_CATEGORIES)}  (all traders)")
    log(f"  Confluence boost   : {CONFLUENCE_THRESHOLD}+ traders → ×{CONFLUENCE_MULTIPLIER}  ({CONFLUENCE_WINDOW_SEC}s window)")
    log(f"  Whale guard        : original >${MAX_WHALE_ORIGINAL:,.0f} → suppress boosts")
    log(f"  MM filter          : ✅ skip offsetting YES+NO buys")
    log(f"  Category filter    : ✅ specialists copy niche-only")
    log(f"  Auto-claim         : ✅ price-based detection v5.9 "
        f"(win≥{CLAIM_WIN_PRICE_THRESHOLD}, loss≤{CLAIM_LOSS_PRICE_THRESHOLD}, "
        f"{CLAIM_HOURS_PAST_END}h past endDate)")
    log(f"  Edge tracker       : ✅ {EDGE_SCORE_FILE.name} — scores update on every resolved position")
    log(f"  Daily loss stops   : global=${DAILY_LOSS_STOPS['global']} | "
        + " | ".join(f"{k}=${v}" for k, v in DAILY_LOSS_STOPS["per_trader"].items()))
    log(f"  Telegram alerts    : {'✅ enabled' if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID else '❌ not configured'}")
    if PROXY_URL:
        proxy_display = "✅ " + PROXY_URL.split("@")[-1]
    else:
        proxy_display = "✅ EU direct (Ireland eu-west-1)"
    log(f"  Proxy              : {proxy_display}")
    log("=" * 72)
    log("  ROSTER:")
    for t in traders:
        cats       = ", ".join(t.get("categories") or ["all markets"])
        arch       = t.get("archetype", "?")
        sm         = t.get("stake_mult", 1.0)
        max_st     = t.get("max_stake", MAX_STAKE_PER_TRADE)
        escore     = edge_tracker.get_score(t["name"])
        efactor    = edge_tracker.get_edge_factor(t["name"])
        limit      = DAILY_LOSS_STOPS["per_trader"].get(t["name"],
                     DAILY_LOSS_STOPS["per_trader"].get("default", -15))
        log(f"  {'⭐' if t['priority']==1 else '  '} {t['name']:<22} [{arch:<10}] "
            f"×{sm:<4}= base ${STAKE*sm:<5.2f}  cap=${max_st:<5.1f}  "
            f"edge={escore:.0f}/100({efactor:.1f}×)  daily_stop=${limit}")
    log("")
    if edge_tracker.data:
        log("  EDGE SCORES (from resolved positions):")
        log(edge_tracker.summary())
        log("")
    log("=" * 72)

    if DRY_RUN:
        log("🔶 DRY RUN — no real orders. Set DRY_RUN=false in .env to go live.")
    else:
        log("🟢 LIVE MODE — real orders will be placed!")

    client = None if DRY_RUN else init_clob()
    if not DRY_RUN and client is None:
        log("Cannot start LIVE without valid CLOB client.", "ERROR")
        sys.exit(1)

    log("\n  Seeding baselines...")
    watermarks = {}
    for t in traders:
        acts = fetch_activity(t["wallet"], limit=10)
        if acts:
            seed_ts     = acts[0]["timestamp"]
            seed_hashes = {a["transactionHash"] for a in acts if a["timestamp"] == seed_ts}
            watermarks[t["wallet"]] = {"ts": seed_ts, "hashes": seed_hashes}
            log(f"  ✓  {t['name']}  (ts={seed_ts}, {len(seed_hashes)} hash(es))")
        else:
            watermarks[t["wallet"]] = {"ts": now_unix(), "hashes": set()}
            log(f"  ✗  {t['name']}  (no data — seeding to now)")

    trader_names = ", ".join(t["name"] for t in traders)
    mode_emoji   = "🔶 DRY RUN" if DRY_RUN else "🟢 LIVE"
    send_telegram(
        f"{mode_emoji} <b>CopyTrade Bot v7.0 started</b>\n"
        f"Traders ({len(traders)}): {trader_names}\n"
        f"Stake: base ${STAKE} × price_factor × edge_factor | max ${MAX_STAKE_PER_TRADE}/order\n"
        f"Filters: slippage {MAX_SLIPPAGE:.0%} | spread ${MAX_SPREAD:.3f} | price ≤${MAX_ENTRY_PRICE} "
        f"| max_res {MAX_RESOLUTION_DAYS}d | blocked: {', '.join(GLOBALLY_BLOCKED_CATEGORIES)}\n"
        f"Daily stops: global=${DAILY_LOSS_STOPS['global']} | per-trader independent"
    )

    log("\n  ✅ Bot running. Ctrl+C to stop.\n")

    poll_count  = 0
    trade_count = 0
    error_count = 0
    positions   = load_positions()

    while True:
        try:
            time.sleep(POLL_INTERVAL)
            poll_count += 1

            # ── 1. Fetch new activity — PARALLEL (v7.5.1) ────────────────────
            # Poll all traders simultaneously; collapse 9×~100ms → ~100ms total
            with ThreadPoolExecutor(max_workers=len(traders)) as _pool:
                _poll_results = list(_pool.map(
                    lambda t: (t, fetch_new_since(t["wallet"], watermarks[t["wallet"]], max_pages=3)),
                    traders
                ))

            for t, new_acts in _poll_results:
                wallet = t["wallet"]
                if new_acts:
                    new_ts     = new_acts[0]["timestamp"]
                    new_hashes = {a["transactionHash"] for a in new_acts if a["timestamp"] == new_ts}
                    watermarks[wallet] = {"ts": new_ts, "hashes": new_hashes}

                    for act in reversed(new_acts):
                        if act["type"] != "TRADE":
                            continue
                        if not act["asset"]:
                            continue
                        if act["side"] == "SELL" and SKIP_SELLS:
                            continue
                        if not is_in_trader_category(act, t):
                            log(
                                f"  🔕 {t['name']} | cat-filter: "
                                f"'{act.get('title','?')[:55]}' ∉ {t.get('categories',[])}",
                                "INFO",
                            )
                            continue
                        result = aggregator.add(t["name"], act)
                        if result == "MM_FILTERED":
                            continue

            # ── 2. Fire aggregated groups ──────────────────────────────────────
            for (trader_name, cond_id, side, asset), acts in aggregator.flush_ready():
                trader = next((t for t in traders if t["name"] == trader_name), None)
                if not trader:
                    continue
                try:
                    execute_group(trader, acts, client, positions, edge_tracker)
                    trade_count += 1
                except Exception as e:
                    error_count += 1
                    log(f"execute_group error: {e}", "ERROR")
                    traceback.print_exc()
                    send_telegram(f"❌ <b>execute_group error</b>\n<code>{str(e)[:300]}</code>")

            # ── 3. Heartbeat every 10 polls ────────────────────────────────────
            if poll_count % 10 == 0:
                # v7.4: Refresh live USDC for auto-compound stake sizing
                global _live_usdc  # must declare global before assignment in main()
                try:
                    from py_clob_client.clob_types import AssetType, BalanceAllowanceParams
                    _u = client.get_balance_allowance(
                        params=BalanceAllowanceParams(asset_type=AssetType.USDC)
                    ) if client else {}
                    _bal = float(_u.get("balance", 0) or 0) / 1e6
                    if _bal > 0:
                        _live_usdc = _bal
                except Exception:
                    pass  # keep last known value
                trader_loss_summary = " | ".join(
                    f"{n}=${risk.get_trader_net_loss(n):.1f}"
                    for n in sorted(risk.trader_daily.keys())
                ) or "none"
                log(
                    f"heartbeat | poll={poll_count} fired={trade_count} errors={error_count} "
                    f"deployed=${risk.daily_deployed:.2f} "
                    f"today_net=${risk.get_global_net_loss():.2f} "
                    f"session=+${_session_wins:.2f}/-${_session_losses:.2f} "
                    f"dyn_stake=${get_dynamic_stake(_live_usdc):.0f} "
                    f"open={len(positions)} | {trader_loss_summary}"
                )

            # ── 3.5. Sell mirror (every 2 polls — mirrors trader exits) ──────────
            if poll_count % 2 == 0:
                try:
                    sell_mirror.check_exits(client, traders, positions)
                    if poll_count % 10 == 0:  # v7.5.6: sweep dead positions
                        loss_sweeper(client, positions, edge_tracker)  # v7.6.5: pass edge_tracker
                except Exception as sme:
                    log(f"sell_mirror error: {sme}", "ERROR")

            # ── 4. Auto-claim (every 20 polls ~10 min — CTF + SELL fallback) ─────
            if poll_count % 20 == 0:
                try:
                    try_claim(client, positions, trader_map, edge_tracker)
                except Exception as ce:
                    log(f"try_claim error: {ce}", "ERROR")

        except KeyboardInterrupt:
            log(f"\nStopped. polls={poll_count} fired={trade_count} errors={error_count}")
            send_telegram(
                f"🛑 <b>Bot stopped</b> (Ctrl+C)\n"
                f"Polls: {poll_count} | Trades: {trade_count} | Errors: {error_count}\n"
                f"Deployed today: ${risk.daily_deployed:.2f}"
            )
            break
        except Exception as e:
            error_count += 1
            log(f"Main loop error: {e}", "ERROR")
            traceback.print_exc()
            send_telegram(f"❌ <b>Main loop error</b>\n<code>{str(e)[:300]}</code>")
            time.sleep(10)


if __name__ == "__main__":
    main()
