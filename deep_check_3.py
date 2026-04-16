#!/usr/bin/env python3
"""deep_check_3.py — Full profile on bigwhale1337, dsfarwe, John5"""
import urllib.request, json, time, sys

WALLETS = [
    ("0x77f623734a71c023f9df91011189eaeef891dbd1", "bigwhale1337"),
    ("0xe2c2ad73fe56a6f3786eac98a957753611f262e4", "dsfarwe"),
    ("0x894fcbd7c3563e5472cfa6ff336f1189f2f8e372", "John5"),
]

KNOWN = {
    "0xa83be3f6a49604556f45089799f2b2096e71def4","0xf27e335d2e78a207e802879f72870449836bd69d",
    "0xe85d6567a750b7b15fcb51c01a7c6230f63095d8","0x146703a8a73ae1dff0f84ba44c45d878858a4372",
    "0xbb63e47263321b67d7535f3909f2ec3c10a0bea4","0xf21b5380ac186a254422e046a97b0e80c8a8894e",
    "0x9c886f69a9e2e5dfcf53f5ef6058925865f16871","0xb2a48372404e6a0bfb6c2f23d715d3acc5a8cf8a",
}

SPORT_TAGS = {"nba","nfl","nhl","mlb","soccer","football","basketball","baseball","tennis",
              "mma","ufc","cricket","rugby","golf","esports","cs2","lol","dota","sports",
              "wbc","ncaa","atp","wta","boxing","cycling","olympics"}
CRYPTO_TAGS = {"bitcoin","ethereum","crypto","btc","eth","solana","defi","web3","nft","xrp","doge"}
BLOCKED_TAGS = {"crypto","bitcoin","ethereum","btc","eth","solana","xrp","weather","politics",
                "iran","ukraine","geopolitics","science","ai","pope","election","mayor"}

def fetch(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read())
        except Exception as e:
            if i == retries-1: return None
            time.sleep(1.5)

def get_activity(wallet, limit=500):
    d = fetch(f"https://data-api.polymarket.com/activity?user={wallet}&limit={limit}")
    return d if isinstance(d, list) else []

def get_positions(wallet):
    d = fetch(f"https://data-api.polymarket.com/positions?user={wallet}&sizeThreshold=0.01")
    return d if isinstance(d, list) else []

def classify_market(title, slug):
    t = (title or "").lower(); s = (slug or "").lower()
    combined = t + " " + s
    is_blocked = any(tag in combined for tag in BLOCKED_TAGS)
    is_crypto  = any(tag in combined for tag in CRYPTO_TAGS)
    is_sports  = any(tag in combined for tag in SPORT_TAGS)
    return is_blocked, is_crypto, is_sports

def analyze(wallet, name):
    print(f"\n{'='*60}")
    print(f"  {name}  |  {wallet[:16]}...")
    print(f"{'='*60}")

    activity = get_activity(wallet, 500)
    positions = get_positions(wallet)

    if not activity:
        print("  ❌ No activity data"); return

    # --- Activity stats ---
    buys = [a for a in activity if a.get("type")=="TRADE" and a.get("side")=="BUY"]
    sells = [a for a in activity if a.get("type")=="TRADE" and a.get("side")=="SELL"]

    if not buys:
        print("  ❌ No BUY activity"); return

    stakes = []
    for b in buys:
        try: stakes.append(float(b.get("usdcSize") or b.get("size") or 0))
        except: pass
    entries = []
    for b in buys:
        try: entries.append(float(b.get("price") or b.get("outcomeIndex") or 0))
        except: pass
    entries = [e for e in entries if 0.01 < e < 0.99]

    avg_stake = sum(stakes)/len(stakes) if stakes else 0
    avg_entry = sum(entries)/len(entries) if entries else 0

    # Timestamps
    now = time.time()
    ts_vals = []
    for b in buys:
        ts = b.get("timestamp") or b.get("createdAt") or 0
        try:
            ts = float(ts)
            if ts > 4e12: ts /= 1000
            ts_vals.append(ts)
        except: pass

    ts_vals.sort(reverse=True)
    age_days = (now - min(ts_vals)) / 86400 if ts_vals else 0
    last_buy_h = (now - ts_vals[0]) / 3600 if ts_vals else 999
    recent_24h = sum(1 for t in ts_vals if now - t < 86400)
    freq = len(buys) / age_days if age_days > 0 else 0

    # Clusters (same-second buys)
    from collections import Counter
    sec_counts = Counter(int(t) for t in ts_vals)
    clusters = sum(1 for c in sec_counts.values() if c >= 2)

    # Market classification
    blocked_n = 0; crypto_n = 0; sports_n = 0
    cats_seen = set()
    for b in buys:
        title = b.get("title") or b.get("market") or b.get("conditionId") or ""
        slug  = b.get("slug") or b.get("category") or b.get("conditionId") or ""
        # try to get category from nested
        if isinstance(b.get("market"), dict):
            title = b["market"].get("question") or title
            slug  = b["market"].get("slug") or slug
        blk, cry, spt = classify_market(title, slug)
        if blk: blocked_n += 1
        if cry: crypto_n += 1
        if spt: sports_n += 1
        # top category guess from slug
        for tag in SPORT_TAGS:
            if tag in (slug or "").lower():
                cats_seen.add(tag); break

    total = len(buys)
    sports_pct = sports_n / total if total else 0
    crypto_pct = crypto_n / total if total else 0
    blocked_pct = blocked_n / total if total else 0

    # Hold behavior
    sell_ratio = len(sells) / len(buys) if buys else 0
    hold_score = 1.0 - min(sell_ratio, 1.0)

    # W/L from positions
    wins = losses = open_pos = 0
    for p in positions:
        cp_raw = p.get("curPrice") if p.get("curPrice") is not None else p.get("currentPrice")
        try: cp = float(cp_raw) if cp_raw is not None else 0.5
        except: cp = 0.5
        redeemable = p.get("redeemable", False)
        if redeemable:
            wins += 1
        elif cp <= 0.04:
            losses += 1
        elif 0.05 < cp < 0.95:
            open_pos += 1

    resolved = wins + losses
    wr = wins / resolved if resolved > 0 else 0

    # Recent buys detail (last 8)
    print(f"  Age: {age_days:.1f}d | Last buy: {last_buy_h:.1f}h ago | Freq: {freq:.1f}/d | Recent 24h: {recent_24h}")
    print(f"  Buys: {len(buys)} | Sells: {len(sells)} | sell_ratio={sell_ratio:.2f} | hold_score={hold_score:.2f}")
    print(f"  avg_stake: ${avg_stake:.2f} | avg_entry: {avg_entry:.3f}")
    print(f"  WR: {wr:.1%} ({wins}W/{losses}L, {open_pos} open, {resolved} resolved)")
    print(f"  sports: {sports_pct:.0%} | crypto: {crypto_pct:.0%} | blocked: {blocked_pct:.0%}")
    print(f"  clusters: {clusters} | categories seen: {sorted(cats_seen)[:8]}")

    # Last 8 buy titles
    print(f"  --- LAST 8 BUYS ---")
    for b in buys[:8]:
        try:
            ts = float(b.get("timestamp") or b.get("createdAt") or 0)
            if ts > 4e12: ts /= 1000
            import datetime
            dt = datetime.datetime.utcfromtimestamp(ts).strftime("%m-%d %H:%M")
        except: dt = "??"
        title = (b.get("title") or b.get("market") or "")
        if isinstance(title, dict): title = title.get("question") or str(title)
        price = b.get("price") or b.get("outcomeIndex") or "?"
        stake_v = b.get("usdcSize") or b.get("size") or "?"
        try: stake_v = f"${float(stake_v):.0f}"
        except: stake_v = str(stake_v)
        blk, cry, spt = classify_market(str(title), "")
        tag = "🚫CRYPTO" if cry else ("🚫BLOCK" if blk else ("⚽" if spt else "❓non-sport"))
        print(f"    {dt} | {str(price)[:5]} | {stake_v:>8} | {str(title)[:55]} [{tag}]")

    # Filter evaluation
    print(f"  --- FILTER CHECK (age>=5d, res>=8, stake>=$4, entry<=0.82, clust<12, blocked<40%, WR>=65%) ---")
    checks = [
        ("age>=5d",          age_days >= 5),
        ("resolved>=8",      resolved >= 8),
        ("stake>=$4",        avg_stake >= 4.0),
        ("entry<=0.82",      avg_entry <= 0.82 or avg_entry == 0),
        ("clusters<12",      clusters < 12),
        ("blocked<40%",      blocked_pct < 0.40),
        ("WR>=65%",          wr >= 0.65),
        ("recent_activity",  last_buy_h < 48),
    ]
    all_pass = True
    for label, result in checks:
        s = "✅" if result else "❌"
        print(f"    {s} {label}")
        if not result: all_pass = False

    verdict = "✅ PASS — candidate for bucket A/B" if all_pass else "❌ REJECT"
    print(f"  VERDICT: {verdict}")

for wallet, name in WALLETS:
    analyze(wallet, name)
    time.sleep(0.5)

print("\n=== DONE ===")
