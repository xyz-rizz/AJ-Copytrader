#!/usr/bin/env python3
"""
Unit tests for copytrade_bot.py  (v5 fixes)
Run: python3 -u test_bot.py
"""
import os, time, json, sys
os.environ["DRY_RUN"]             = "true"
os.environ["PRIVATE_KEY"]         = "0xFAKE"
os.environ["STAKE_USDC"]          = "5.0"
os.environ["MAX_SLIPPAGE"]        = "0.05"
os.environ["MAX_PER_MARKET_USDC"] = "20.0"
os.environ["MAX_DAILY_LOSS_USDC"] = "50.0"
os.environ["FILL_AGG_WINDOW_SEC"] = "2"
os.environ["POLL_INTERVAL"]       = "999"

from unittest.mock import patch
with patch("dotenv.load_dotenv"):
    import copytrade_bot as bot

PASS = "✅ PASS"
FAIL = "❌ FAIL"
results = []

def check(name, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((status, name, detail))
    print(f"  {status}  {name}" + (f"  [{detail}]" if detail else ""))

print("\n" + "="*60)
print("  COPYTRADE BOT v5 — UNIT TESTS")
print("="*60)

# ── Verified live API shape ───────────────────────────────────────────────────
TOKEN = "71321045679252212594626385532706912750332728571942532289631379312455583992563"
REAL_TRADE = {
    "proxyWallet": "0xa0f8b626bf42c179ccfb8abd67aba00f1363b80d",
    "timestamp": 1771248000, "conditionId": "0xdd22472e552119702021d3030c348427c1e1d4b2",
    "type": "TRADE", "size": 580.0, "usdcSize": 580.0,
    "transactionHash": "0xabc123", "price": 0.42, "asset": TOKEN,
    "side": "BUY", "outcomeIndex": 0, "outcome": "Yes",
    "title": "Will BTC hit $100k before April 2026?",
    "slug": "will-btc-hit-100k-before-april-2026",
    "eventSlug": "will-btc-hit-100k-before-april-2026",
    "icon": "", "name": "0x4815162342", "pseudonym": "",
    "bio": "", "profileImage": "", "profileImageOptimized": "",
}
REAL_REDEEM = {**REAL_TRADE, "type": "REDEEM", "side": "", "asset": "",
               "outcomeIndex": 999, "outcome": "", "price": 0,
               "transactionHash": "0xredeem1"}
TRADER = bot.TRADERS[0]

# ── 1. Schema ─────────────────────────────────────────────────────────────────
print("\n── Schema ──")
check("asset field present",         "asset" in REAL_TRADE)
check("asset NOT asset_id",          "asset_id" not in REAL_TRADE)
check("asset NOT assetId",           "assetId" not in REAL_TRADE)
check("dedup key is transactionHash","transactionHash" in REAL_TRADE)
check("type is TRADE not BUY",       REAL_TRADE["type"] == "TRADE")
check("side is BUY string",          REAL_TRADE["side"] == "BUY")
check("outcome populated",           REAL_TRADE["outcome"] == "Yes")
check("outcomeIndex is int",         isinstance(REAL_TRADE["outcomeIndex"], int))
check("usdcSize field present",      "usdcSize" in REAL_TRADE)
check("eventSlug present",           REAL_TRADE["eventSlug"] != "")
check("REDEEM has empty asset",      REAL_REDEEM["asset"] == "")
check("REDEEM outcomeIndex=999",     REAL_REDEEM["outcomeIndex"] == 999)

# ── 2. execute_group — field access + weighted price ─────────────────────────
print("\n── execute_group ──")
captured = {}
orig_place = bot.place_order
bot.place_order = lambda client, token_id, side_str, stake, label: (
    captured.update({"token_id": token_id, "side": side_str, "stake": stake}),
    (True, {"dry_run": True})
)[1]
orig_write = bot.write_log
bot.write_log = lambda e: captured.update({"logged": e})

# Single fill
bot.execute_group(TRADER, [REAL_TRADE], client=None)
check("token_id from 'asset'",       captured.get("token_id") == TOKEN,     captured.get("token_id","?")[:20])
check("side correctly passed",       captured.get("side") == "BUY")
check("stake is configured amount",  captured.get("stake") == 5.0)
check("log written",                 "logged" in captured)
check("log outcome=Yes",             captured.get("logged",{}).get("outcome") == "Yes")
check("log signal_price correct",    captured.get("logged",{}).get("signal_price") == 0.42)
check("log dry_run=True",            captured.get("logged",{}).get("dry_run") == True)
url = captured.get("logged",{}).get("url","")
check("URL uses eventSlug",          "will-btc-hit-100k" in url, url)
check("log has orig_usdc not orig_total",
      "orig_usdc" in captured.get("logged",{}) and "orig_total" not in captured.get("logged",{}))

# Weighted average price: 3 fills at different prices/usdcSizes
fill_a = {**REAL_TRADE, "transactionHash": "0xa", "price": 0.40, "usdcSize": 100.0, "size": 100.0}
fill_b = {**REAL_TRADE, "transactionHash": "0xb", "price": 0.45, "usdcSize": 400.0, "size": 400.0}
captured2 = {}
bot.write_log = lambda e: captured2.update({"logged": e})
bot.execute_group(TRADER, [fill_a, fill_b], client=None)
expected_wavg = (0.40 * 100 + 0.45 * 400) / 500  # = 0.44
actual_sig = captured2.get("logged", {}).get("signal_price", 0)
check("Weighted avg price correct",  abs(actual_sig - expected_wavg) < 0.0001,
      f"expected={expected_wavg:.4f} got={actual_sig:.4f}")

bot.place_order = orig_place
bot.write_log   = orig_write

# ── 3. Filtering ──────────────────────────────────────────────────────────────
print("\n── REDEEM / SELL filtering ──")
def should_process(act, skip_sells=True):
    if act["type"] != "TRADE":             return False, "not TRADE"
    if not act["asset"]:                   return False, "empty asset"
    if act["side"] == "SELL" and skip_sells: return False, "SELL skipped"
    return True, "ok"

check("REDEEM filtered",             not should_process(REAL_REDEEM)[0])
check("Empty asset filtered",        not should_process({**REAL_TRADE, "asset": ""})[0])
check("SELL blocked when SKIP_SELLS",not should_process({**REAL_TRADE, "side": "SELL"})[0])
check("SELL passes when not skipping",   should_process({**REAL_TRADE, "side": "SELL"}, False)[0])
check("Valid TRADE passes",              should_process(REAL_TRADE)[0])

# ── 4. Composite watermark ────────────────────────────────────────────────────
print("\n── Composite watermark (fix #1) ──")

def make_act(ts, tx):
    return {**REAL_TRADE, "timestamp": ts, "transactionHash": tx}

def run_fetch_new(acts_on_wire, watermark):
    """Simulate fetch_new_since using a mock fetch_activity."""
    call_count = [0]
    def mock_fetch(wallet, limit=50, offset=0):
        call_count[0] += 1
        start = offset
        end   = offset + limit
        return acts_on_wire[start:end]
    orig = bot.fetch_activity
    bot.fetch_activity = mock_fetch
    result = bot.fetch_new_since("0xwallet", watermark, max_pages=3)
    bot.fetch_activity = orig
    return result

# Scenario: two trades at same timestamp — old watermark would drop one
wm_ts   = 1000
wm_hash = "0xOLD"
acts    = [make_act(1001, "0xNEW2"), make_act(1001, "0xNEW1"), make_act(1000, wm_hash)]
watermark = {"ts": wm_ts, "hashes": {wm_hash}}
new = run_fetch_new(acts, watermark)
check("Both trades at ts=1001 captured", len(new) == 2, f"got {len(new)}")

# Same-second dedup: one of the new trades has same ts AND hash as watermark
acts2   = [make_act(1000, "0xNEW_SAME_SEC"), make_act(1000, wm_hash)]
watermark2 = {"ts": 1000, "hashes": {wm_hash}}
new2 = run_fetch_new(acts2, watermark2)
check("Only new hash at same second returned", len(new2) == 1 and new2[0]["transactionHash"] == "0xNEW_SAME_SEC",
      f"got {len(new2)}: {[a['transactionHash'] for a in new2]}")

# Strictly older activity is excluded
acts3     = [make_act(999, "0xOLD2"), make_act(998, "0xOLD3")]
watermark3 = {"ts": 1000, "hashes": {"0xWM"}}
new3 = run_fetch_new(acts3, watermark3)
check("Older trades excluded",       len(new3) == 0, f"got {len(new3)}")

# ── 5. FillAggregator ─────────────────────────────────────────────────────────
print("\n── FillAggregator ──")
agg = bot.FillAggregator()
f1 = {**REAL_TRADE, "transactionHash": "0x1", "usdcSize": 100.0}
f2 = {**REAL_TRADE, "transactionHash": "0x2", "usdcSize": 200.0}
f3 = {**REAL_TRADE, "transactionHash": "0x3", "usdcSize":  50.0}

agg.add("0x4815162342", f1); agg.add("0x4815162342", f2); agg.add("0x4815162342", f3)
check("No flush before window",      len(agg.flush_ready()) == 0)
time.sleep(3)
ready = agg.flush_ready()
check("Flushes after window",        len(ready) == 1,  f"got {len(ready)}")
_, group = ready[0]
check("Group has all 3 fills",       len(group) == 3,  f"got {len(group)}")
total_usdc = sum(float(a["usdcSize"]) for a in group)
check("Total usdcSize correct",      total_usdc == 350.0, f"got {total_usdc}")

# Different markets → different buckets
f_other = {**REAL_TRADE, "conditionId": "0xOTHER", "asset": "9999", "transactionHash": "0x4"}
agg.add("0x4815162342", f1); agg.add("0x4815162342", f_other)
time.sleep(3)
check("Two markets → 2 buckets",     len(agg.flush_ready()) == 2)

# ── 6. RiskManager ────────────────────────────────────────────────────────────
print("\n── RiskManager ──")
rm = bot.RiskManager()

ok, r = rm.check(TOKEN, 5.0, 0.42, 0.42)
check("Normal BUY allowed",                ok, r)

ok, r = rm.check(TOKEN, 5.0, 0.42, 0.45)
check("7.1% slippage blocked",             not ok and "Slippage" in r, r)

ok, r = rm.check(TOKEN, 5.0, 0.42, 0.44)
check("4.8% slippage allowed",             ok, r)

# Per-market cap (BUY side only)
rm.record(TOKEN, 5.0, True, side="BUY")
rm.record(TOKEN, 5.0, True, side="BUY")
rm.record(TOKEN, 5.0, True, side="BUY")
rm.record(TOKEN, 5.0, True, side="BUY")   # $20 total
ok, r = rm.check(TOKEN, 5.0, 0.42, 0.42)
check("Per-market cap blocks at $20",      not ok and "cap" in r, r)

# SELL does NOT decrement daily_pnl or increment market_exposure
rm2 = bot.RiskManager()
rm2.record(TOKEN, 5.0, True, side="BUY")   # pnl = -5
rm2.record(TOKEN, 5.0, True, side="SELL")  # pnl should stay -5
check("SELL doesn't affect daily_pnl",     rm2.daily_pnl == -5.0, f"got {rm2.daily_pnl}")
check("SELL doesn't increment exposure",   rm2.market_exposure[TOKEN] == 5.0,
      f"got {rm2.market_exposure[TOKEN]}")

# Daily loss stop
rm3 = bot.RiskManager()
rm3.daily_pnl = -51.0
ok, r = rm3.check(TOKEN, 5.0, 0.42, 0.42)
check("Daily loss stop at -$51",           not ok and "Daily loss" in r, r)

# ── Summary ───────────────────────────────────────────────────────────────────
passed = sum(1 for s,*_ in results if s == PASS)
failed = sum(1 for s,*_ in results if s == FAIL)
print(f"\n{'='*60}")
print(f"  {passed} passed   {failed} failed   ({len(results)} total)")
print(f"{'='*60}\n")
sys.exit(0 if failed == 0 else 1)
