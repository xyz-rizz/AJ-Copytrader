#!/usr/bin/env python3
"""
Fresh broad discovery scan — multi-niche, not just gaming.
Pulls today's scanner gems + live leaderboard + monitor list checks.
Profiles all candidates. Saves to /tmp/fresh_discovery_results.json
"""
import json, urllib.request, time, datetime, re
from collections import defaultdict

# ── Keyword lists ─────────────────────────────────────────────────────────────
CRYPTO_KW = ['bitcoin', 'btc', 'ethereum', 'eth/', 'crypto', 'satoshi',
             'btc price', 'eth price', 'up or down - march', 'up or down - april']
BLOCKED_KW = ['trump', 'tariff', 'epstein', 'ukraine', 'war ', 'nuclear', 'nato',
              'election', 'democrat', 'republican', 'senate', 'congress', 'president',
              'iran', 'russia', 'china tariff', 'trade war', 'musk tweet']
SPORTS_KW   = ['nba', 'nfl', 'mlb', 'nhl', 'tennis', 'atp', 'wta', 'cs2',
               'counter-strike', 'dota', 'valorant', 'league of legends', 'soccer',
               'football match', 'premier league', 'bundesliga', 'ucl', 'champions league',
               'la liga', 'serie a', 'mls', 'baseball', 'hockey', 'lol', 'esport',
               'esports', 'bno', 'wbc', 'wnba', 'boxing', 'mma', 'ufc', 'bnp paribas',
               'open tennis', 'grand slam', 'wimbledon', 'us open', 'french open',
               'australian open', 'world cup', 'euros', 'copa']
WEATHER_KW  = ['temperature', 'rainfall', 'humidity', 'weather', 'precipitation',
               'degrees', 'celsius', 'fahrenheit', '°c', '°f', 'snowfall']
UD_KW       = ['up or down', 'stock up', 'stock down', 'price above', 'price below',
               'close above', 'close below', 'will the price of', 'spx', 'nasdaq',
               'nvda', 'aapl', 'msft', 'tsla', 'meta ', 'amzn', 'googl', 'ndx']
TWEET_KW    = ['tweet', 'post ', 'musk post', 'elon post', 'x post', 'twitter']

def fetch(url, timeout=10):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except:
        return None

def classify_buy(title):
    t = title.lower()
    if any(k in t for k in CRYPTO_KW):   return 'crypto'
    if any(k in t for k in BLOCKED_KW):  return 'blocked'
    if any(k in t for k in WEATHER_KW):  return 'weather'
    if any(k in t for k in TWEET_KW):    return 'tweet'
    if any(k in t for k in UD_KW):       return 'ud_stock'
    if any(k in t for k in SPORTS_KW):   return 'sports'
    return 'other'

def wallet_age_days(buys):
    if not buys: return 0
    ts = [b.get('timestamp', 0) for b in buys]
    ts = [t/1000 if t > 4e12 else t for t in ts]
    if not ts: return 0
    span = max(ts) - min(ts)
    return span / 86400

def cluster_count(buys, window=2):
    ts_list = sorted(b.get('timestamp', 0) for b in buys)
    ts_list = [t/1000 if t > 4e12 else t for t in ts_list]
    clusters = 0
    i = 0
    while i < len(ts_list) - 1:
        if ts_list[i+1] - ts_list[i] <= window:
            clusters += 1
            while i < len(ts_list) - 1 and ts_list[i+1] - ts_list[i] <= window:
                i += 1
        i += 1
    return clusters

def profile_wallet(wallet):
    url = f'https://data-api.polymarket.com/activity?user={wallet}&limit=500'
    data = fetch(url)
    if not data: return None
    buys = [x for x in data if x.get('type') == 'TRADE' and x.get('side') == 'BUY']
    if not buys: return None

    age = wallet_age_days(buys)
    clust = cluster_count(buys)
    stakes = [float(b.get('size', b.get('amount', 0)) or 0) *
              float(b.get('price', b.get('avgPrice', 1)) or 1) for b in buys]
    avg_stake = sum(stakes) / len(stakes) if stakes else 0
    entries = [float(b.get('price', b.get('avgPrice', 0)) or 0) for b in buys]
    avg_entry = sum(entries) / len(entries) if entries else 0
    titles = [b.get('title', '') for b in buys]
    cats = [classify_buy(t) for t in titles]
    crypto_pct = cats.count('crypto') / len(cats) * 100 if cats else 0
    blocked_pct = cats.count('blocked') / len(cats) * 100 if cats else 0
    sports_pct = cats.count('sports') / len(cats) * 100 if cats else 0
    weather_pct = cats.count('weather') / len(cats) * 100 if cats else 0
    tweet_pct = cats.count('tweet') / len(cats) * 100 if cats else 0
    ud_pct = cats.count('ud_stock') / len(cats) * 100 if cats else 0

    now = time.time()
    recent_ts = [b.get('timestamp', 0) for b in buys]
    recent_ts = [t/1000 if t > 4e12 else t for t in recent_ts]
    last_buy_h = (now - max(recent_ts)) / 3600 if recent_ts else 9999
    buys_24h = sum(1 for t in recent_ts if now - t < 86400)
    buys_48h = sum(1 for t in recent_ts if now - t < 172800)

    # Get positions
    pos_url = f'https://data-api.polymarket.com/positions?user={wallet}&sizeThreshold=0.001&limit=500'
    pos_data = fetch(pos_url, timeout=12)
    wins = losses = open_pos = 0
    if pos_data:
        for p in pos_data:
            cur = float(p.get('curPrice', 0) or 0)
            if p.get('redeemable'): wins += 1
            elif cur <= 0.04: losses += 1
            else: open_pos += 1
    resolved = wins + losses

    if resolved == 0: return None
    wr = wins / resolved * 100 if resolved > 0 else 0

    return {
        'wallet': wallet,
        'age_days': round(age, 1),
        'n_buys': len(buys),
        'avg_stake': round(avg_stake, 1),
        'avg_entry': round(avg_entry, 3),
        'clusters': clust,
        'wins': wins, 'losses': losses, 'open': open_pos,
        'resolved': resolved,
        'win_rate': round(wr, 1),
        'crypto_pct': round(crypto_pct, 1),
        'blocked_pct': round(blocked_pct, 1),
        'sports_pct': round(sports_pct, 1),
        'weather_pct': round(weather_pct, 1),
        'tweet_pct': round(tweet_pct, 1),
        'ud_pct': round(ud_pct, 1),
        'last_buy_h': round(last_buy_h, 1),
        'buys_24h': buys_24h,
        'buys_48h': buys_48h,
        'freq_per_day': round(len(buys) / max(age, 1), 1),
        'recent_titles': [b.get('title', '')[:50] for b in sorted(buys,
                           key=lambda x: -x.get('timestamp', 0))[:4]],
    }

# ── Step 1: Known sources ────────────────────────────────────────────────────
print("=== FRESH DISCOVERY SCAN ===")
candidates = {}

# Today's scanner results
try:
    with open('/home/ubuntu/copytrade/scanner_results.json') as f:
        scan = json.load(f)
    print(f"Scanner ({scan.get('timestamp','?')}): {len(scan.get('gems',[]))} gems")
    for g in scan.get('gems', []):
        w = g.get('wallet', '')
        if w and g.get('win_rate', 0) >= 80:
            candidates[w] = {'source': 'scanner_today', 'artifact_score': g.get('score', 0)}
except Exception as e:
    print(f"Scanner load error: {e}")

# Monitor list
MONITOR = [
    '0xe3084ecc131468c9e12bffc99e024a5a4b2e4eb1',   # melonaire1
    '0x0799daf859e32ec813845a58249172daee889452',    # 0x0799 watchlist
]
for w in MONITOR:
    candidates[w] = {'source': 'monitor_list', 'artifact_score': 0}

# Scout wide2 candidates not already in bot
try:
    with open('/home/ubuntu/copytrade/scout_wide2_results.json') as f:
        sw = json.load(f)
    for g in sw.get('gems', sw if isinstance(sw, list) else []):
        w = g.get('wallet', '')
        if w and g.get('win_rate', 0) >= 85 and w not in candidates:
            candidates[w] = {'source': 'scout_wide2', 'artifact_score': g.get('score', 0)}
except Exception as e:
    print(f"scout_wide2 load error: {e}")

# Live leaderboard
print("\nScanning leaderboard...")
lb_wallets = set()
for window in ['1m']:
    for offset in [0, 100, 200]:
        url = f'https://data-api.polymarket.com/profiles/leaderboard?window={window}&limit=100&offset={offset}'
        data = fetch(url, timeout=10)
        if not data: continue
        entries = data if isinstance(data, list) else data.get('data', [])
        for e in entries:
            w = e.get('address', e.get('wallet', ''))
            pnl = float(e.get('pnl', e.get('profit', 0)) or 0)
            if w and pnl > 0:
                lb_wallets.add(w)
        time.sleep(0.3)
print(f"Leaderboard: {len(lb_wallets)} profitable wallets")

# Add top leaderboard to candidates (sample 30)
for w in list(lb_wallets)[:30]:
    if w not in candidates:
        candidates[w] = {'source': 'leaderboard_1m', 'artifact_score': 0}

# Also add expansion_results viable wallets not in current roster
CURRENT_ROSTER = {
    '0xa83be3f6a49604556f45089799f2b2096e71def4',  # Signal47-Bets
    '0xf27e335d2e7f4d0b39b42a5b67f2a5b2b5c3abc',  # Immense-Gokart (approx)
    '0x146703a8a73ae1dff0f84ba44c45d878858a4372',  # Unwieldy-Forage
    '0xaeab8222e044ab64b7253a3c10c16ba75096a2ed',  # NBAEdge-aeab
    '0xf23ca65324b789016acaffb6c2dccae48657555d',  # SoccerSharp-f23c
    '0xdd57cbe710edcb13a0e315003ec68c00c18e530f',  # Sport-dd57
    '0x40344cc4ba1a39648399b2d97d0d31c27122f52c',  # SPXOpens-f52c
    '0x77f623734a71c023f9df91011189eaeef891dbd1',  # bigwhale1337
    '0xa2ed440b6e3b9738a547c5a20f79616b63828808',  # InfoEdge-a2ed
}

print(f"\nTotal candidates to profile: {len(candidates)}")

# ── Step 2: Profile ──────────────────────────────────────────────────────────
viable = []
borderline = []
done = 0
for wallet, meta in candidates.items():
    if wallet in CURRENT_ROSTER:
        done += 1
        continue
    profile = profile_wallet(wallet)
    done += 1
    if done % 10 == 0:
        print(f"  [{done}/{len(candidates)}] profiled...")
    if not profile:
        continue
    profile.update(meta)

    # Hard filters
    issues = []
    if profile['win_rate'] < 85: issues.append(f"wr={profile['win_rate']:.0f}%<85")
    if profile['resolved'] < 8: issues.append(f"res={profile['resolved']}<8")
    if profile['age_days'] < 5: issues.append(f"age={profile['age_days']:.1f}d<5")
    if profile['clusters'] > 8: issues.append(f"clust={profile['clusters']}>8")
    if profile['crypto_pct'] >= 50: issues.append(f"crypto={profile['crypto_pct']:.0f}%>=50")

    if not issues:
        viable.append(profile)
    elif profile['win_rate'] >= 85 and profile['resolved'] >= 5:
        profile['issues'] = issues
        borderline.append(profile)
    time.sleep(0.05)

# ── Step 3: Output ────────────────────────────────────────────────────────────
print(f"\n=== VIABLE ({len(viable)}) ===")
viable.sort(key=lambda x: (-x['win_rate'], -x['resolved']))
for p in viable:
    print(f"\n{p['wallet'][:20]}")
    print(f"  WR={p['win_rate']}% {p['wins']}W/{p['losses']}L/{p['open']}o res={p['resolved']}")
    print(f"  age={p['age_days']}d stake=${p['avg_stake']} entry={p['avg_entry']}")
    print(f"  clust={p['clusters']} crypto={p['crypto_pct']}% blk={p['blocked_pct']}% spt={p['sports_pct']}% wx={p['weather_pct']}% tw={p['tweet_pct']}% ud={p['ud_pct']}%")
    print(f"  last={p['last_buy_h']:.1f}h 24h={p['buys_24h']} 48h={p['buys_48h']} freq={p['freq_per_day']}/d source={p['source']}")
    print(f"  recent: {p['recent_titles'][:2]}")

print(f"\n=== BORDERLINE ({len(borderline)}) ===")
for p in sorted(borderline, key=lambda x: -x['win_rate'])[:10]:
    print(f"  {p['wallet'][:20]} WR={p['win_rate']}% {p['wins']}W/{p['losses']}L res={p['resolved']} age={p['age_days']}d 24h={p['buys_24h']} | issues: {','.join(p.get('issues',[]))}")

out = {'viable': viable, 'borderline': borderline, 'ts': str(datetime.datetime.utcnow())}
with open('/tmp/fresh_discovery_results.json', 'w') as f:
    json.dump(out, f, indent=2)
print(f"\nSaved to /tmp/fresh_discovery_results.json")
