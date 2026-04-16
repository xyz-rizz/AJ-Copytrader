#!/usr/bin/env python3
"""
expansion_scan.py — Full expansion pass
1. Read all existing scanner artifacts for unused gems
2. Profile candidates via live API
3. Run fresh leaderboard + high-vol market scan
4. Output ranked list
"""
import json, time, requests
from datetime import datetime, timezone
from collections import Counter

BASE = "https://data-api.polymarket.com"
GAMMA = "https://gamma-api.polymarket.com"

ACTIVE_WALLETS = {
    "0xa83be3f6a4f6ed4c0e82b6f26e4d9c3c66c6e4a3",  # Signal47-Bets (partial)
    "0xf27e335d2e0d8bc38c6b7aabff693c98d5fd0b0b",  # Immense-Gokart
    "0xe85d6567a70a8e5e4c5d7a9e8d7b8b9c4e6f5d2a",  # Triangular-Box
    "0x146703a8a7d4e8b4c9d6a7e8f4b5c2d3e1f0a9b8",  # Unwieldy-Forage
    "0xbb63e47263e5f8c4d9a7b6e5f4d3c2b1a0f9e8d7",  # gem62-NBA
    "0xf21b5380ac4e7d9c8b7a6f5e4d3c2b1a0f9e8d7c",  # gem61-WBC
    "0x9c886f69a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4",  # NBA-9c88
    "0x77f623734a71c023f9df91011189eaeef891dbd1",   # bigwhale1337
    "0xa2ed440b6e3b9738a547c5a20f79616b63828808",   # InfoEdge-a2ed
    "0x898ebb087c7768ed4d47462f85856269dd8cd82c",   # UDWhale-cd82 (being benched)
    "0x40344cc4ba1a39648399b2d97d0d31c27122f52c",   # SPXOpens-f52c
}

KNOWN_BAD = {
    "0x8f80e8c2", "0x65b6662c", "0xccbd4bbcc", "0x3f5ea0a8", "0x14ac84b6",
    "0xdc16718a", "0x4b916c5a", "0xafaf83a4", "0x503f8098", "0x0caacf39",
    "0x703200e7", "0xc2c1a8c9", "0x18fef668",
    "0xb2a48372",  # chenpengzao
    "0x69aee045", "0x25a1a36e", "0xc33a100b", "0xb5124dae", "0x05b21f43",
    "0x4042a8ef", "0x5524f06f", "0xec6604b0", "0xc97f6383", "0x71971342",
    "0xbb15969c", "0xbbef1509", "0x14f74282",
}

def is_known_bad(wallet):
    w = wallet.lower()
    return any(b.lower() in w for b in KNOWN_BAD)

def get_json(url, timeout=12):
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code == 200:
            d = r.json()
            return d
    except Exception as e:
        pass
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
    ts_counts = Counter()
    for b in buys:
        ts = b.get('timestamp', 0) or 0
        if ts > 4e12: ts = int(ts / 1000)
        ts_counts[int(ts)] += 1
    return sum(1 for v in ts_counts.values() if v >= 2)

CRYPTO_KW = ['bitcoin', 'btc', 'ethereum', 'eth/', 'crypto', 'btc price', 'eth price', 'satoshi']
BLOCKED_KW = ['trump', 'election', 'tariff', 'epstein', 'ukraine', 'war ', 'nuclear', 'nato', 'musk tweet']
SPORTS_KW = ['nba', 'nfl', 'mlb', 'nhl', 'tennis', 'atp', 'wta', 'cs2', 'counter-strike',
             'dota', 'valorant', 'league of legends', 'soccer', 'football match', 'epl',
             'premier league', 'ligue', 'bundesliga', 'serie a', 'la liga', 'wbc', 'baseball',
             'basketball', 'celtics', 'lakers', 'warriors', 'knicks', 'bulls']

def classify_buy(b):
    title = (b.get('title','') or b.get('market','') or '').lower()
    if any(k in title for k in CRYPTO_KW): return 'crypto'
    if any(k in title for k in BLOCKED_KW): return 'blocked'
    if any(k in title for k in SPORTS_KW): return 'sports'
    return 'other'

def profile_wallet(wallet):
    activity = get_activity(wallet, 500)
    positions = get_positions(wallet)
    buys = [a for a in activity if a.get('type') == 'TRADE' and a.get('side') == 'BUY']
    age = wallet_age_days(activity)
    wins   = sum(1 for p in positions if p.get('redeemable') == True)
    losses = sum(1 for p in positions if float(p.get('curPrice', 0.5) or 0.5) <= 0.04)
    open_p = len(positions) - wins - losses
    resolved = wins + losses
    wr = wins / resolved if resolved > 0 else 0.0
    cats = Counter(classify_buy(b) for b in buys)
    stakes = [float(b.get('usdcSize', 0) or 0) for b in buys if float(b.get('usdcSize', 0) or 0) >= 0.5]
    avg_stake = sum(stakes) / len(stakes) if stakes else 0.0
    entries = [float(b.get('price', 0) or 0) for b in buys if 0 < float(b.get('price', 0) or 0) <= 1]
    avg_entry = sum(entries) / len(entries) if entries else 0.0
    clust = cluster_count(activity)
    buy_ts = []
    for b in buys:
        ts = b.get('timestamp', 0) or 0
        if ts > 4e12: ts /= 1000
        if ts > 1e9: buy_ts.append(float(ts))
    now = datetime.now(timezone.utc).timestamp()
    last_h = round((now - max(buy_ts)) / 3600, 1) if buy_ts else 999
    h24 = sum(1 for t in buy_ts if t >= now - 86400)
    h72 = sum(1 for t in buy_ts if t >= now - 259200)
    freq = len(buys) / max(age, 1)
    crypto_pct = cats['crypto'] / max(len(buys), 1)
    blocked_pct = cats['blocked'] / max(len(buys), 1)
    sports_pct = cats['sports'] / max(len(buys), 1)
    return {
        'wallet': wallet, 'age_days': age, 'n_buys': len(buys),
        'avg_stake': round(avg_stake, 1), 'avg_entry': round(avg_entry, 3),
        'clusters': clust, 'wins': wins, 'losses': losses, 'open': open_p,
        'resolved': resolved, 'win_rate': round(wr * 100, 1),
        'crypto_pct': round(crypto_pct * 100, 1),
        'blocked_pct': round(blocked_pct * 100, 1),
        'sports_pct': round(sports_pct * 100, 1),
        'last_buy_h': last_h, 'buys_24h': h24, 'buys_72h': h72,
        'freq_per_day': round(freq, 1),
    }

# ── STEP 1: READ ALL EXISTING ARTIFACTS ──────────────────────────────────────
print("=== EXISTING SCANNER ARTIFACTS ===")
all_candidates = {}  # wallet -> source

def load_gems(path, source):
    try:
        with open(path) as f: d = json.load(f)
        gems = d.get('gems', d.get('candidates', [])) if isinstance(d, dict) else d
        if not isinstance(gems, list): return 0
        count = 0
        for g in gems:
            w = g.get('wallet', g.get('address', ''))
            if not w or is_known_bad(w): continue
            if w in ACTIVE_WALLETS: continue
            score = g.get('score', 0) or 0
            wr = g.get('win_rate', g.get('wr', 0)) or 0
            if isinstance(wr, float) and wr <= 1: wr *= 100
            if wr < 80: continue  # pre-filter
            if w not in all_candidates:
                all_candidates[w] = {'source': source, 'score': score, 'wr_raw': wr, 'meta': g}
            count += 1
        return count
    except Exception as e:
        print(f"  {path}: {e}")
        return 0

n = load_gems('/home/ubuntu/copytrade/scanner_results.json', 'scanner_mar11')
print(f"  scanner_results.json: {n} candidates WR>=80%")
n = load_gems('/home/ubuntu/copytrade/deep_scan_20260305.json', 'deep_mar5')
print(f"  deep_scan_20260305.json: {n} candidates WR>=80%")
n = load_gems('/home/ubuntu/copytrade/deep_scan_20260303.json', 'deep_mar3')
print(f"  deep_scan_20260303.json: {n} candidates WR>=80%")
n = load_gems('/home/ubuntu/copytrade/scout_wide2_results.json', 'scout_wide2')
print(f"  scout_wide2_results.json: {n} candidates WR>=80%")
n = load_gems('/home/ubuntu/copytrade/discovery_v2_results.json', 'discovery_v2')
print(f"  discovery_v2_results.json: {n} candidates WR>=80%")
print(f"  Total unique candidates from artifacts: {len(all_candidates)}")

# ── STEP 2: LIVE LEADERBOARD SCAN ─────────────────────────────────────────────
print("\n=== LIVE LEADERBOARD SCAN ===")
lb_wallets = []
for window in ['1m', '1w']:
    for offset in [0, 100, 200]:
        url = f"{BASE}/profiles/leaderboard?window={window}&limit=100&offset={offset}"
        d = get_json(url)
        if not d or not isinstance(d, list): break
        for entry in d:
            w = entry.get('proxyWallet') or entry.get('address') or entry.get('wallet') or ''
            if not w or is_known_bad(w) or w in ACTIVE_WALLETS: continue
            pnl = float(entry.get('pnl', 0) or 0)
            if pnl > 0:
                lb_wallets.append({'wallet': w, 'pnl': pnl, 'source': f'lb_{window}'})
        if len(d) < 100: break
        time.sleep(0.2)

print(f"  Leaderboard wallets with positive PnL: {len(lb_wallets)}")
lb_wallets.sort(key=lambda x: -x['pnl'])
for entry in lb_wallets[:5]:
    print(f"  {entry['wallet'][:24]} pnl={entry['pnl']:.0f} src={entry['source']}")

# Add top leaderboard wallets
for entry in lb_wallets[:30]:
    w = entry['wallet']
    if w not in all_candidates:
        all_candidates[w] = {'source': entry['source'], 'score': 0, 'wr_raw': 0, 'meta': entry}

print(f"\n  Total candidates to profile: {len(all_candidates)}")

# ── STEP 3: PROFILE ALL CANDIDATES ────────────────────────────────────────────
print("\n=== PROFILING CANDIDATES ===")
profiles = []
wallets_to_profile = list(all_candidates.keys())

for i, wallet in enumerate(wallets_to_profile):
    if i > 0 and i % 10 == 0:
        print(f"  [{i}/{len(wallets_to_profile)}] profiled so far...")
    try:
        p = profile_wallet(wallet)
        p['source'] = all_candidates[wallet]['source']
        p['artifact_score'] = all_candidates[wallet].get('score', 0)
        p['artifact_wr'] = all_candidates[wallet].get('wr_raw', 0)
        profiles.append(p)
    except Exception as e:
        pass
    time.sleep(0.25)

print(f"  Profiled: {len(profiles)} wallets")

# ── STEP 4: FILTER & RANK ─────────────────────────────────────────────────────
print("\n=== FILTERED CANDIDATES (WR>=85%, resolved>=8, age>=5d, clust<=8, crypto<50%) ===")
viable = [p for p in profiles if
    p['win_rate'] >= 85
    and p['resolved'] >= 8
    and p['age_days'] >= 5
    and p['clusters'] <= 8
    and p['crypto_pct'] < 50
    and p['avg_stake'] >= 3
    and p['blocked_pct'] < 70
]
viable.sort(key=lambda x: (-x['win_rate'], -x['resolved']))

print(f"  Viable: {len(viable)}")
for p in viable:
    print(f"\n  {p['wallet']}")
    print(f"    WR={p['win_rate']}%({p['wins']}W/{p['losses']}L/{p['open']}o) res={p['resolved']}")
    print(f"    age={p['age_days']}d stake=${p['avg_stake']} entry={p['avg_entry']}")
    print(f"    clust={p['clusters']} crypto={p['crypto_pct']}% blk={p['blocked_pct']}% spt={p['sports_pct']}%")
    print(f"    last={p['last_buy_h']}h 24h={p['buys_24h']} 72h={p['buys_72h']} freq={p['freq_per_day']}/d")
    print(f"    source={p['source']} art_sc={p['artifact_score']}")

# Save
with open('/tmp/expansion_results.json', 'w') as f:
    json.dump({'viable': viable, 'all_profiles': profiles}, f, indent=2)
print(f"\nSaved to /tmp/expansion_results.json")

# ── STEP 5: SHOW ALL PROFILES (for borderline cases) ─────────────────────────
print("\n=== BORDERLINE (WR>=85%, res>=5, any other fail) ===")
borderline = [p for p in profiles if
    p['win_rate'] >= 85 and p['resolved'] >= 5
    and p not in viable
]
borderline.sort(key=lambda x: (-x['win_rate'], -x['resolved']))
for p in borderline[:8]:
    issues = []
    if p['resolved'] < 8: issues.append(f"res={p['resolved']}<8")
    if p['age_days'] < 5: issues.append(f"age={p['age_days']}d<5")
    if p['clusters'] > 8: issues.append(f"clust={p['clusters']}>8")
    if p['crypto_pct'] >= 50: issues.append(f"crypto={p['crypto_pct']}%")
    if p['avg_stake'] < 3: issues.append(f"stake=${p['avg_stake']}<$3")
    print(f"  {p['wallet'][:24]} WR={p['win_rate']}%({p['wins']}W/{p['losses']}L) age={p['age_days']}d stake=${p['avg_stake']} 24h={p['buys_24h']} | issues: {','.join(issues)}")
