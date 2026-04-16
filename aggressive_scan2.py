#!/usr/bin/env python3
"""aggressive_scan2.py — New-source aggressive discovery
Sources: top-600 leaderboard (30d) + recently-resolved sports markets (last 14d) + hot 12h
Thresholds: age>=5d, resolved>=8, stake>=$4, entry<=0.82, clusters<12, blocked<40%, WR>=65%
"""
import urllib.request, json, time, sys
from collections import Counter

# ── KNOWN / BLACKLISTED ─────────────────────────────────────────────────────
KNOWN = {
    "0xa83be3f6a49604556f45089799f2b2096e71def4","0xf27e335d2e78a207e802879f72870449836bd69d",
    "0xe85d6567a750b7b15fcb51c01a7c6230f63095d8","0x146703a8a73ae1dff0f84ba44c45d878858a4372",
    "0xbb63e47263321b67d7535f3909f2ec3c10a0bea4","0xf21b5380ac186a254422e046a97b0e80c8a8894e",
    "0x9c886f69a9e2e5dfcf53f5ef6058925865f16871","0xb2a48372404e6a0bfb6c2f23d715d3acc5a8cf8a",
    "0x419be42e6a04adcd6b1e76c45ade4006c4c3cb2c",  # Superb-Hyacinth benched
    "0x69aee04532e2064b23f03b9fde0ec1ada1a1db44",  # GEM-0x69aee micro
}
BLACKLIST = {
    "0x0caacf3919c50a4d59c784f7496116a809fdb2bd",
    "0x703200e7df059638f4dc338e5e11ab2c7e8d1cc9",
    "0xc2c1a8c92e4c6dcb6a8c90a3b0c7d3f9e2a5b1d4",
    "0x18fef6681893aba51c01fac570a245a5844da4a0",
    "0x4b916c5ad935c58652dc1d5eb234a1f789ceb1fb",  # gem68 clone
    "0xafaf83a457ceb6d6778839f67038bd103708572d",  # weather flipper
    "0x503f8098201ff4c9d5ec1f325b71a2f36a5fec57",  # crypto scalper
    "0xccbd4bbcc445e7f4b98abf3061aa2b9e0130f1b7",  # HFT bot
    "0x3f5ea0a8053e81ce2f59814118869322c35fe7db",  # piggyery 137 clusters
    "0x14ac84b66a27fc30e56ed620ebfa61cd8105cb21",  # BrokeMaxxing 158 clusters
    "0xdc16718af9f04590b38a8e8aa32dedcd034740a5",  # ELESTUDIO freq=193/d
    "0x58f8f1138be2192696378629fc9aa23c7910dc70",  # bloodmaster 14 clusters
    "0x71971342cb4c2555f60366ac62abdcdd1a1d14c8",  # RawrRawr 1W/18L live
    "0x65b6662c2cb28e3018cbb6a4983c5b83b2842108",  # 0W/446L
    "0x8c68a36a884a2fa808996b40c70eb9ff9349570c",  # WR 7.7%
    "0x0684013902f5d899f4621e2c48c7af5407e9d593",  # 0W/12L
    "0x2ff8631ea9a348e1f7e0620933397532a49167e2",  # 0W/13L
    "0xbb15969cb69d5b430d40870aabdf2a1d91820f02",  # kkap8897 1W/4L live
    "0xc33a100b8362bc732e78cce28c99739f173b3da3",  # Sharp-c33a -41% ROI
    "0x4042a8ef98b5abf2a1cf2423f8475c91ee150bda",  # HeisenbergWalt -69.6% ROI
    "0x0b9cae2b0dfe7a71c413e0604eaac1c352f87e44",  # geniusMC 1d
    "0x05b21f43e056cdf3f26ae5f28dc0238495e2a469",  # jack66666 entry=0.868
    "0x25a1a36e671aa52180be2e5ad498dc2013d9ddf8",  # SharpEdge micro $1
    "0xb5124dae83419944bb000ebe28607560de9144a5",  # Veteran micro $2
    "0x0f5c37e3d248ed29e2f0a0913b2a3a0d8021cc27",  # micro $2
    "0xe2c2ad73fe56a6f3786eac98a957753611f262e4",  # dsfarwe — handled by deep_check_3.py
    "0x77f623734a71c023f9df91011189eaeef891dbd1",  # bigwhale1337 — handled by deep_check_3.py
    "0x894fcbd7c3563e5472cfa6ff336f1189f2f8e372",  # John5 — handled by deep_check_3.py
}
SKIP = KNOWN | BLACKLIST

SPORT_TAGS = {"nba","nfl","nhl","mlb","soccer","football","basketball","baseball","tennis",
              "mma","ufc","cricket","rugby","golf","esports","cs2","lol","dota2","dota","sports",
              "wbc","ncaa","atp","wta","boxing","f1","formula","hockey","league"}
CRYPTO_TAGS = {"bitcoin","ethereum","btc","eth","crypto","solana","defi","nft","xrp","doge","bnb"}
BLOCKED_TAGS = {"bitcoin","ethereum","btc","eth","crypto","solana","xrp","weather","iran",
                "ukraine","geopolitics","ai-","pope","election","mayor","senate","congress",
                "president","inflation","gdp","fed "}

# ── Thresholds ───────────────────────────────────────────────────────────────
P_MIN_AGE      = 5
P_MIN_RESOLVED = 8
P_MIN_STAKE    = 4.0
P_MAX_ENTRY    = 0.82
P_MAX_CLUSTERS = 12
P_MAX_BLOCKED  = 0.40
P_MIN_WR       = 0.65
P_MAX_CRYPTO   = 0.35
P_MAX_FREQ     = 40.0

def fetch(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read())
        except:
            if i < retries-1: time.sleep(1.5)
    return None

def classify_market(title, slug=""):
    combined = ((title or "") + " " + (slug or "")).lower()
    blk = any(t in combined for t in BLOCKED_TAGS)
    cry = any(t in combined for t in CRYPTO_TAGS)
    spt = any(t in combined for t in SPORT_TAGS)
    return blk, cry, spt

def get_activity(wallet, limit=500):
    d = fetch(f"https://data-api.polymarket.com/activity?user={wallet}&limit={limit}")
    return d if isinstance(d, list) else []

def get_positions(wallet):
    d = fetch(f"https://data-api.polymarket.com/positions?user={wallet}&sizeThreshold=0.01")
    return d if isinstance(d, list) else []

def score_wallet(wallet):
    activity = get_activity(wallet, 500)
    if not activity: return None
    buys = [a for a in activity if a.get("type")=="TRADE" and a.get("side")=="BUY"]
    sells = [a for a in activity if a.get("type")=="TRADE" and a.get("side")=="SELL"]
    if len(buys) < 5: return None

    # Stakes + entries
    stakes = []
    for b in buys:
        try: stakes.append(float(b.get("usdcSize") or b.get("size") or 0))
        except: pass
    entries = []
    for b in buys:
        try:
            e = float(b.get("price") or b.get("outcomeIndex") or 0)
            if 0.01 < e < 0.99: entries.append(e)
        except: pass

    avg_stake = sum(stakes)/len(stakes) if stakes else 0
    if avg_stake < P_MIN_STAKE: return {"reject": "micro_stake"}

    avg_entry = sum(entries)/len(entries) if entries else 0
    if avg_entry > P_MAX_ENTRY and avg_entry > 0: return {"reject": "high_entry"}

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
    if not ts_vals: return None
    ts_vals.sort(reverse=True)

    age_days = (now - min(ts_vals)) / 86400
    if age_days < P_MIN_AGE: return {"reject": "too_young"}
    last_buy_h = (now - ts_vals[0]) / 3600
    if last_buy_h > 72: return {"reject": "stale"}
    recent_24h = sum(1 for t in ts_vals if now - t < 86400)
    freq = len(buys) / age_days
    if freq > P_MAX_FREQ: return {"reject": "high_freq"}

    # Clusters
    sec_counts = Counter(int(t) for t in ts_vals)
    clusters = sum(1 for c in sec_counts.values() if c >= 2)
    if clusters >= P_MAX_CLUSTERS: return {"reject": "clusters"}

    # Market classification
    blk_n = cry_n = spt_n = 0
    for b in buys:
        title = b.get("title") or b.get("market") or ""
        if isinstance(title, dict): title = title.get("question") or ""
        blk, cry, spt = classify_market(str(title))
        if blk: blk_n += 1
        if cry: cry_n += 1
        if spt: spt_n += 1

    total_b = len(buys)
    blocked_pct = blk_n / total_b
    crypto_pct  = cry_n / total_b
    sports_pct  = spt_n / total_b

    if blocked_pct >= P_MAX_BLOCKED: return {"reject": "blocked_heavy"}
    if crypto_pct  >= P_MAX_CRYPTO:  return {"reject": "crypto_heavy"}

    # W/L from positions
    positions = get_positions(wallet)
    wins = losses = open_pos = 0
    for p in positions:
        cp_raw = p.get("curPrice") if p.get("curPrice") is not None else p.get("currentPrice")
        try: cp = float(cp_raw) if cp_raw is not None else 0.5
        except: cp = 0.5
        if p.get("redeemable"): wins += 1
        elif cp <= 0.04: losses += 1
        elif 0.05 < cp < 0.95: open_pos += 1

    resolved = wins + losses
    if resolved < P_MIN_RESOLVED: return {"reject": "few_resolved"}
    wr = wins / resolved
    if wr < P_MIN_WR: return {"reject": "low_wr"}

    hold_score = 1.0 - min(len(sells)/len(buys), 1.0)

    # Edge score (0-100 style)
    edge = (wr * 40) + (min(resolved, 50) / 50 * 20) + (min(avg_stake, 200) / 200 * 20) + ((1 - avg_entry) * 20)
    copy = (hold_score * 30) + ((1 - clusters / 12) * 20) + ((1 - blocked_pct) * 20) + (min(recent_24h, 5) / 5 * 15) + (sports_pct * 15)

    return {
        "wallet": wallet, "wr": wr, "wins": wins, "losses": losses, "resolved": resolved,
        "open": open_pos, "avg_stake": avg_stake, "avg_entry": avg_entry,
        "age_days": age_days, "freq": freq, "clusters": clusters,
        "blocked_pct": blocked_pct, "crypto_pct": crypto_pct, "sports_pct": sports_pct,
        "hold_score": hold_score, "recent_24h": recent_24h, "last_buy_h": last_buy_h,
        "edge": round(edge, 1), "copy": round(copy, 1),
    }

# ── SOURCE 1: Leaderboard top-600 (30d PnL) ─────────────────────────────────
def get_leaderboard_wallets():
    wallets = set()
    for offset in [0, 100, 200, 300, 400, 500]:
        url = f"https://data-api.polymarket.com/profiles/leaderboard?window=1m&limit=100&offset={offset}&sortBy=profitAndLoss"
        d = fetch(url)
        if not d: break
        items = d if isinstance(d, list) else d.get("data", []) if isinstance(d, dict) else []
        for item in items:
            w = item.get("address") or item.get("proxyWallet") or item.get("wallet")
            if w: wallets.add(w.lower())
        time.sleep(0.3)
    print(f"[LEADERBOARD] Got {len(wallets)} wallets")
    return wallets

# ── SOURCE 2: Recently-resolved sports markets (last 14d) ───────────────────
def get_resolved_sports_wallets():
    wallets = set()
    # Try multiple sport tags on gamma closed markets
    tags = ["sports","nba","nfl","nhl","soccer","tennis","esports","baseball"]
    for tag in tags:
        url = f"https://gamma-api.polymarket.com/markets?closed=true&tag_slug={tag}&limit=50&order=closeTime&ascending=false"
        d = fetch(url)
        if not d: continue
        markets = d if isinstance(d, list) else d.get("data", []) if isinstance(d, dict) else []
        for m in markets[:20]:
            cid = m.get("conditionId")
            if not cid: continue
            # Get trades for this market
            url2 = f"https://data-api.polymarket.com/trades?conditionId={cid}&limit=50"
            trades = fetch(url2)
            if isinstance(trades, list):
                for t in trades:
                    w = t.get("maker") or t.get("taker") or t.get("user")
                    if w and len(w) == 42: wallets.add(w.lower())
        time.sleep(0.4)
    print(f"[RESOLVED SPORTS] Got {len(wallets)} wallets from closed markets")
    return wallets

# ── SOURCE 3: Hot markets (last 12h) ────────────────────────────────────────
def get_hot_market_wallets():
    wallets = set()
    # Get currently active sports markets, scan recent traders
    url = "https://gamma-api.polymarket.com/markets?active=true&tag_slug=sports&limit=50&order=volume&ascending=false"
    d = fetch(url)
    markets = d if isinstance(d, list) else (d.get("data",[]) if isinstance(d,dict) else [])
    for m in markets[:30]:
        cid = m.get("conditionId")
        if not cid: continue
        url2 = f"https://data-api.polymarket.com/trades?conditionId={cid}&limit=30"
        trades = fetch(url2)
        if isinstance(trades, list):
            for t in trades:
                # Only if recent (last 12h)
                ts = t.get("timestamp") or t.get("createdAt") or 0
                try:
                    ts = float(ts)
                    if ts > 4e12: ts /= 1000
                    if time.time() - ts < 43200:  # 12h
                        w = t.get("maker") or t.get("taker") or t.get("user")
                        if w and len(w) == 42: wallets.add(w.lower())
                except: pass
        time.sleep(0.3)
    print(f"[HOT MARKETS 12h] Got {len(wallets)} wallets")
    return wallets

# ── MAIN ─────────────────────────────────────────────────────────────────────
print("=== aggressive_scan2.py — New-source aggressive discovery ===")
print("Collecting wallets from 3 sources...")

lb_wallets = get_leaderboard_wallets()
resolved_wallets = get_resolved_sports_wallets()
hot_wallets = get_hot_market_wallets()

all_wallets = (lb_wallets | resolved_wallets | hot_wallets) - SKIP
print(f"[COMBINED] {len(all_wallets)} unique novel candidates to score")

results = []
rejects = Counter()
for i, wallet in enumerate(all_wallets, 1):
    if i % 50 == 0:
        print(f"  {i}/{len(all_wallets)} | pass={len(results)}", flush=True)
    r = score_wallet(wallet)
    if r is None:
        rejects["no_data"] += 1
    elif "reject" in r:
        rejects[r["reject"]] += 1
    else:
        results.append(r)
    time.sleep(0.12)

# Sort by edge score
results.sort(key=lambda x: x["edge"] + x["copy"], reverse=True)

print(f"\n{'='*65}")
print(f"RESULTS: {len(results)} PASSED | Rejects: {dict(rejects)}")
print(f"{'='*65}")
for r in results[:20]:
    bucket = "A" if (r["wr"]>=0.82 and r["resolved"]>=15 and r["avg_stake"]>=10 and r["avg_entry"]<=0.75) else "B"
    print(f"  [{bucket}] {r['wallet'][:16]}... WR={r['wr']:.0%}({r['wins']}W/{r['losses']}L) "
          f"res={r['resolved']} age={r['age_days']:.0f}d stk=${r['avg_stake']:.0f} "
          f"ent={r['avg_entry']:.3f} spt={r['sports_pct']:.0%} clst={r['clusters']} "
          f"blk={r['blocked_pct']:.0%} hold={r['hold_score']:.2f} 24h={r['recent_24h']} "
          f"edge={r['edge']} copy={r['copy']}")

out = {"run_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "sources": {"leaderboard": len(lb_wallets), "resolved_markets": len(resolved_wallets), "hot_12h": len(hot_wallets)},
       "total_candidates": len(all_wallets), "reject_counts": dict(rejects), "results": results[:30]}
with open("/home/ubuntu/copytrade/aggressive_scan2_results.json", "w") as f:
    json.dump(out, f, indent=2)
print(f"\nResults → /home/ubuntu/copytrade/aggressive_scan2_results.json")
print("DONE.")
