#!/usr/bin/env python3
"""
ud_verdict.py: Final Up/Down vertical pipeline verdict
- Show distribution of selectivity (evts, buys) to understand the landscape
- Probe monitor wallet with multiple API paths
- Load updown_profiles.json for any missed candidates
- Build ranked 10-item output
"""

import json, time, requests
from datetime import datetime, timezone

BASE = "https://data-api.polymarket.com"

def get_json(url, timeout=15):
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code == 200:
            return r.json()
        return {'status': r.status_code, 'text': r.text[:200]}
    except Exception as e:
        return {'error': str(e)}

# ─── LOAD CANDIDATES & SHOW DISTRIBUTION ──────────────────────────────────────
with open('/tmp/spx_hist_cands.json') as f:
    raw = json.load(f)
cands = raw.get('candidates', raw) if isinstance(raw, dict) else raw
print(f"Loaded {len(cands)} spx_hist_cands\n")

# Distribution of evts (events covered)
print("=== EVENT COVERAGE DISTRIBUTION (how many UD markets each wallet bets in) ===")
buckets = {
    '1-10': 0, '11-20': 0, '21-40': 0, '41-80': 0, '81-150': 0, '151+': 0
}
for c in cands:
    e = c.get('n_events', 0)
    if e <= 10: buckets['1-10'] += 1
    elif e <= 20: buckets['11-20'] += 1
    elif e <= 40: buckets['21-40'] += 1
    elif e <= 80: buckets['41-80'] += 1
    elif e <= 150: buckets['81-150'] += 1
    else: buckets['151+'] += 1
for k, v in buckets.items():
    bar = '█' * (v // 3)
    print(f"  evts {k:6s}: {v:4d} {bar}")

# Also show stake distribution
print("\n=== AVG STAKE DISTRIBUTION ===")
stake_buckets = {'<$5': 0, '$5-10': 0, '$10-25': 0, '$25-50': 0, '$50+': 0}
for c in cands:
    s = c.get('avg_stake', 0)
    if s < 5: stake_buckets['<$5'] += 1
    elif s < 10: stake_buckets['$5-10'] += 1
    elif s < 25: stake_buckets['$10-25'] += 1
    elif s < 50: stake_buckets['$25-50'] += 1
    else: stake_buckets['$50+'] += 1
for k, v in stake_buckets.items():
    bar = '█' * (v // 5)
    print(f"  {k:6s}: {v:4d} {bar}")

# Top 15 by avg_stake (stake-weighted quality)
print("\n=== TOP 15 BY AVG STAKE (stake-weighted) ===")
by_stake = sorted(cands, key=lambda x: -x.get('avg_stake', 0))
for c in by_stake[:15]:
    print(f"  {c['wallet'][:22]} avg_s=${c.get('avg_stake',0):7.2f} buys={c.get('n_buys',0):4d} "
          f"entry={c.get('avg_entry',0):.3f} clust={c.get('n_clusters',0):2d} evts={c.get('n_events',0):3d}")

# Top 15 by lowest event coverage (most selective)
print("\n=== TOP 15 BY LOWEST EVENT COVERAGE (most selective) ===")
by_evts = sorted(cands, key=lambda x: x.get('n_events', 999))
for c in by_evts[:15]:
    print(f"  {c['wallet'][:22]} evts={c.get('n_events',0):3d} buys={c.get('n_buys',0):4d} "
          f"avg_s=${c.get('avg_stake',0):7.2f} entry={c.get('avg_entry',0):.3f} clust={c.get('n_clusters',0):2d}")

# ─── LOAD UPDOWN_PROFILES.JSON (60 earlier-profiled wallets) ──────────────────
print("\n=== FROM UPDOWN_PROFILES.JSON (prev session, 60 profiled) ===")
try:
    with open('/tmp/updown_profiles.json') as f:
        up_raw = json.load(f)
    up_list = up_raw if isinstance(up_raw, list) else up_raw.get('profiles', [])
    print(f"Loaded {len(up_list)} updown profiles")
    # Show all with reasonable stats
    up_list.sort(key=lambda x: -x.get('score', 0))
    for p in up_list:
        wallet = p.get('wallet', '')[:22]
        score = p.get('score', 0)
        wr = p.get('win_rate', 0) or p.get('wr', 0)
        resolved = p.get('resolved', 0) or p.get('total_resolved', 0)
        age = p.get('age_days', 0) or p.get('age', 0)
        clust = p.get('clusters', 0) or p.get('n_clusters', 0)
        crypto = p.get('crypto_pct', 0)
        avg_s = p.get('avg_stake', 0)
        ud = p.get('ud_stock_buys', 0) or p.get('n_ud_markets', 0)
        print(f"  {wallet} sc={score} WR={wr:.0f}%({resolved}r) age={age}d "
              f"stake=${avg_s:.0f} clust={clust} crypto={crypto:.0f}% ud={ud}")
except Exception as e:
    print(f"ERROR: {e}")

# ─── MONITOR WALLET MULTI-PATH PROBE ──────────────────────────────────────────
print("\n=== MONITOR WALLET: 0xf5d07cdbe4dd44d0fe9017a7bf1cf9cb0e1e8fca ===")
mon = '0xf5d07cdbe4dd44d0fe9017a7bf1cf9cb0e1e8fca'

# Path 1: activity
r1 = get_json(f"{BASE}/activity?user={mon}&limit=20")
if isinstance(r1, list):
    print(f"  activity: {len(r1)} items, first: {json.dumps(r1[0])[:200] if r1 else 'empty'}")
else:
    print(f"  activity: {r1}")

# Path 2: positions
r2 = get_json(f"{BASE}/positions?user={mon}&sizeThreshold=0.001")
if isinstance(r2, list):
    print(f"  positions: {len(r2)} items")
    if r2: print(f"    first: {json.dumps(r2[0])[:200]}")
else:
    print(f"  positions: {r2}")

# Path 3: trades (general)
r3 = get_json(f"{BASE}/trades?user={mon}&limit=5")
print(f"  trades: {str(r3)[:200]}")

# Path 4: profile
r4 = get_json(f"{BASE}/profiles?address={mon}")
print(f"  profiles: {str(r4)[:200]}")

# Path 5: leaderboard profile
r5 = get_json(f"https://gamma-api.polymarket.com/profiles?address={mon}")
print(f"  gamma profiles: {str(r5)[:200]}")

# ─── PROBE BEST LOW-EVTS CANDIDATES ───────────────────────────────────────────
print("\n=== DEEP PROBE: 5 most-selective + 5 highest-stake from spx_hist ===")
# Most selective (low evts, reasonable stake)
selective_low = [c for c in cands if c.get('n_events',999) <= 15 and c.get('avg_stake',0) >= 8]
selective_low.sort(key=lambda x: -x.get('avg_stake',0))
# Highest stake regardless
high_stake = [c for c in cands if c.get('avg_stake',0) >= 30 and c.get('n_clusters',999) <= 5]
high_stake.sort(key=lambda x: -x.get('avg_stake',0))

print(f"Low-evts (<=15) + stake>=$8: {len(selective_low)} candidates")
for c in selective_low[:5]:
    print(f"  {c['wallet'][:22]} evts={c.get('n_events',0):3d} buys={c.get('n_buys',0):4d} "
          f"avg_s=${c.get('avg_stake',0):7.2f} entry={c.get('avg_entry',0):.3f} clust={c.get('n_clusters',0):2d}")

print(f"High-stake (>=$30) + clust<=5: {len(high_stake)} candidates")
for c in high_stake[:5]:
    print(f"  {c['wallet'][:22]} avg_s=${c.get('avg_stake',0):7.2f} evts={c.get('n_events',0):3d} "
          f"buys={c.get('n_buys',0):4d} entry={c.get('avg_entry',0):.3f} clust={c.get('n_clusters',0):2d}")

to_probe = []
seen = set()
for c in selective_low[:5] + high_stake[:5]:
    w = c['wallet']
    if w not in seen:
        seen.add(w)
        to_probe.append(c)

if to_probe:
    def get_activity(wallet, limit=300):
        d = get_json(f"{BASE}/activity?user={wallet}&limit={limit}")
        if isinstance(d, list): return d
        if isinstance(d, dict): return d.get('data', [])
        return []

    def get_positions(wallet):
        d = get_json(f"{BASE}/positions?user={wallet}&sizeThreshold=0.001&limit=500")
        if isinstance(d, list): return d
        if isinstance(d, dict): return d.get('data', [])
        return []

    def wallet_age_days(activity):
        ts_list = []
        for a in activity:
            ts = a.get('timestamp', 0) or 0
            if ts > 4e12: ts /= 1000
            if ts > 1e9: ts_list.append(float(ts))
        if not ts_list: return 0.0
        now = datetime.now(timezone.utc).timestamp()
        return round((now - min(ts_list)) / 86400, 1)

    print("\nDeep profiling...")
    for c in to_probe:
        wallet = c['wallet']
        print(f"  {wallet[:22]}...", end=' ', flush=True)
        act = get_activity(wallet, 300)
        pos = get_positions(wallet)
        buys = [a for a in act if a.get('type')=='TRADE' and a.get('side')=='BUY']
        age = wallet_age_days(act)
        wins = sum(1 for p in pos if p.get('redeemable')==True)
        losses = sum(1 for p in pos if float(p.get('curPrice',0.5) or 0.5) <= 0.04)
        wr = wins/(wins+losses) if (wins+losses)>0 else 0
        # classify
        ud=0; crypto=0
        for b in buys:
            t = (b.get('title','') or '').lower()
            if any(k in t for k in ['up or down','opens up']): ud+=1
            elif any(k in t for k in ['bitcoin','ethereum','btc','eth']): crypto+=1
        stakes = [float(b.get('usdcSize',0) or 0) for b in buys]
        avg_s = sum(stakes)/len(stakes) if stakes else 0
        print(f"age={age}d WR={wr:.0%}({wins}W/{losses}L) n_buys={len(buys)} avg_s=${avg_s:.0f} ud={ud} crypto_pct={crypto/max(len(buys),1):.0%}")
        time.sleep(0.4)
