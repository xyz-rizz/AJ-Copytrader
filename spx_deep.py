#!/usr/bin/env python3
"""
spx_deep.py: Find selective directional bettors in SPX/stock UD vertical
- Load /tmp/spx_hist_cands.json
- Apply tight selectivity filter (evts<=40, buys<=120) to strip systematizers
- Deep-profile top 20 with true WR, age, market breakdown
- Separately probe monitor-list wallet 0xf5d07cdbe4dd44d0fe9017a7bf1cf9cb0e1e8fca
"""

import json, time, requests
from datetime import datetime, timezone

BASE = "https://data-api.polymarket.com"

def get_json(url, timeout=15):
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"  ERR {url[:60]}: {e}")
    return None

def get_activity(wallet, limit=500):
    d = get_json(f"{BASE}/activity?user={wallet}&limit={limit}")
    if isinstance(d, list): return d
    if isinstance(d, dict): return d.get('data', d.get('results', []))
    return []

def get_positions(wallet):
    d = get_json(f"{BASE}/positions?user={wallet}&sizeThreshold=0.001&limit=500")
    if isinstance(d, list): return d
    if isinstance(d, dict): return d.get('data', d.get('results', []))
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

def cluster_count(activity):
    buys = [a for a in activity if a.get('type') == 'TRADE' and a.get('side') == 'BUY']
    from collections import Counter
    ts_counts = Counter()
    for b in buys:
        ts = b.get('timestamp', 0) or 0
        if ts > 4e12: ts = int(ts / 1000)
        ts_counts[int(ts)] += 1
    return sum(1 for v in ts_counts.values() if v >= 2)

UD_KEYWORDS = ['up or down', 'opens up or down', 'opens down', 'opens up']
CRYPTO_KEYWORDS = ['bitcoin', 'ethereum', 'btc/', 'eth/', 'crypto', 'btc price', 'eth price']
BLOCKED_TAGS = {'crypto', 'politics', 'elections', 'trump', 'ukraine', 'climate'}

def classify_buy(b):
    title = (b.get('title', '') or b.get('market', '') or '').lower()
    outcome = (b.get('outcome', '') or '').lower()
    if any(k in title for k in CRYPTO_KEYWORDS):
        return 'crypto'
    if any(k in title for k in UD_KEYWORDS):
        return 'ud_stock'
    return 'other'

def deep_profile(wallet):
    activity = get_activity(wallet, 500)
    positions = get_positions(wallet)

    buys = [a for a in activity if a.get('type') == 'TRADE' and a.get('side') == 'BUY']
    age = wallet_age_days(activity)

    wins   = sum(1 for p in positions if p.get('redeemable') == True)
    losses = sum(1 for p in positions if float(p.get('curPrice', 0.5) or 0.5) <= 0.04)
    open_p = len(positions) - wins - losses
    resolved = wins + losses
    wr = wins / resolved if resolved > 0 else 0.0

    type_counts = {'ud_stock': 0, 'crypto': 0, 'other': 0}
    for b in buys:
        type_counts[classify_buy(b)] += 1

    stakes = [float(b.get('usdcSize', 0) or 0) for b in buys if float(b.get('usdcSize', 0) or 0) > 0]
    avg_stake = sum(stakes) / len(stakes) if stakes else 0.0

    entries = [float(b.get('price', 0) or 0) for b in buys if float(b.get('price', 0) or 0) > 0]
    avg_entry = sum(entries) / len(entries) if entries else 0.0

    clust = cluster_count(activity)

    # Last buy timestamp
    buy_ts = []
    for b in buys:
        ts = b.get('timestamp', 0) or 0
        if ts > 4e12: ts /= 1000
        if ts > 1e9: buy_ts.append(float(ts))
    last_buy_h = round((datetime.now(timezone.utc).timestamp() - max(buy_ts)) / 3600, 1) if buy_ts else 999

    return {
        'wallet': wallet,
        'age_days': age,
        'n_buys': len(buys),
        'avg_stake': round(avg_stake, 2),
        'avg_entry': round(avg_entry, 3),
        'clusters': clust,
        'wins': wins, 'losses': losses, 'open': open_p,
        'resolved': resolved,
        'win_rate': round(wr * 100, 1),
        'ud_stock_buys': type_counts['ud_stock'],
        'crypto_buys': type_counts['crypto'],
        'crypto_pct': round(type_counts['crypto'] / max(len(buys), 1) * 100, 1),
        'other_buys': type_counts['other'],
        'last_buy_h_ago': last_buy_h,
        'n_positions': len(positions),
    }

# ─── LOAD CANDIDATES ───────────────────────────────────────────────────────────
with open('/tmp/spx_hist_cands.json') as f:
    raw = json.load(f)

cands = raw.get('candidates', raw) if isinstance(raw, dict) else raw
print(f"Loaded {len(cands)} raw candidates\n")

# ─── APPLY SELECTIVE FILTER ────────────────────────────────────────────────────
# Systematizers have evts=80-261. Real directional bettors: evts<=40, buys<=150
# Also require decent stake and not-too-high entry
selective = [c for c in cands if
    c.get('n_events', 999) <= 40
    and c.get('n_buys', 0) <= 150
    and c.get('avg_stake', 0) >= 5
    and c.get('avg_entry', 1.0) <= 0.82
    and c.get('n_clusters', 999) <= 8
    and c.get('active_48h', False)
]

print(f"After selective filter (evts<=40, buys<=150, stake>=$5, entry<=0.82, clust<=8): {len(selective)}")
selective.sort(key=lambda x: -x.get('avg_stake', 0))

print("\nTop 30 selective candidates:")
for c in selective[:30]:
    print(f"  {c['wallet'][:22]} buys={c.get('n_buys',0):4d} avg_s=${c.get('avg_stake',0):7.2f} "
          f"entry={c.get('avg_entry',0):.3f} clust={c.get('n_clusters',0):2d} evts={c.get('n_events',0):3d}")

# ─── DEEP PROFILE TOP 20 + KNOWN GOOD ──────────────────────────────────────────
to_profile_wallets = [c['wallet'] for c in selective[:20]]

# Always include our known good candidate
known = '0x40344cc4ba1a39648399b2d97d0d31c27122f52c'
if known not in to_profile_wallets:
    to_profile_wallets.append(known)

print(f"\n=== DEEP PROFILING {len(to_profile_wallets)} CANDIDATES ===")
profiles = []
for wallet in to_profile_wallets:
    print(f"  {wallet[:24]}... ", end='', flush=True)
    try:
        p = deep_profile(wallet)
        profiles.append(p)
        ud_flag = f" ud={p['ud_stock_buys']}" if p['ud_stock_buys'] > 0 else ""
        print(f"age={p['age_days']}d WR={p['win_rate']}%({p['wins']}W/{p['losses']}L/{p['open']}o) "
              f"stake=${p['avg_stake']:.0f} entry={p['avg_entry']:.3f} clust={p['clusters']}{ud_flag} "
              f"crypto={p['crypto_pct']:.0f}% last={p['last_buy_h_ago']}h")
    except Exception as e:
        print(f"ERROR: {e}")
    time.sleep(0.4)

# ─── MONITOR-LIST WALLET ───────────────────────────────────────────────────────
print("\n=== MONITOR-LIST WALLET (full address) ===")
mon_wallet = '0xf5d07cdbe4dd44d0fe9017a7bf1cf9cb0e1e8fca'
print(f"  Profiling {mon_wallet}...")
try:
    p = deep_profile(mon_wallet)
    profiles.append(p)
    print(f"  age={p['age_days']}d WR={p['win_rate']}%({p['wins']}W/{p['losses']}L/{p['open']}o) "
          f"n_buys={p['n_buys']} stake=${p['avg_stake']:.0f} entry={p['avg_entry']:.3f} "
          f"clust={p['clusters']} ud={p['ud_stock_buys']} crypto={p['crypto_pct']:.0f}% last={p['last_buy_h_ago']}h")
except Exception as e:
    print(f"  ERROR: {e}")

# Also try updown_profiles.json for this wallet
print("\n  Checking updown_profiles.json for monitor wallet...")
try:
    with open('/tmp/updown_profiles.json') as f:
        up = json.load(f)
    for p in (up if isinstance(up, list) else up.get('profiles', [])):
        if mon_wallet[:10].lower() in p.get('wallet','').lower():
            print(f"  Found in updown_profiles: {json.dumps(p, indent=2)[:400]}")
except Exception as e:
    print(f"  Could not check updown_profiles: {e}")

# ─── SAVE + SUMMARY ────────────────────────────────────────────────────────────
with open('/tmp/spx_deep.json', 'w') as f:
    json.dump(profiles, f, indent=2)
print(f"\nSaved {len(profiles)} deep profiles to /tmp/spx_deep.json")

# Final ranked summary
print("\n=== RANKED SUMMARY (viable candidates only) ===")
viable = [p for p in profiles if
    p.get('age_days', 0) >= 5
    and p.get('resolved', 0) >= 5
    and p.get('crypto_pct', 100) < 60
    and p.get('avg_stake', 0) >= 4
    and p.get('clusters', 999) <= 6
]
viable.sort(key=lambda x: (-(x.get('win_rate',0)), -x.get('resolved',0)))
for p in viable:
    print(f"  {p['wallet'][:22]} age={p['age_days']}d WR={p['win_rate']}% "
          f"({p['wins']}W/{p['losses']}L) stake=${p['avg_stake']:.0f} "
          f"entry={p['avg_entry']:.3f} ud={p['ud_stock_buys']} clust={p['clusters']}")
print(f"Total viable: {len(viable)}")
