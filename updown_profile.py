#!/usr/bin/env python3
"""
Step 3: Deep-profile each candidate wallet.
Fetch ALL positions (resolved + open) to compute true WR, age, clusters, hold behavior.
"""
import urllib.request, json, time, collections, sys

def fetch(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read())
        except Exception as e:
            if i == retries-1:
                return []
            time.sleep(2)

def fetch_activity(wallet, limit=500):
    url = f"https://data-api.polymarket.com/activity?user={wallet}&limit={limit}"
    r = fetch(url)
    return r if isinstance(r, list) else []

def fetch_positions(wallet):
    url = f"https://data-api.polymarket.com/positions?user={wallet}&sizeThreshold=0.001"
    r = fetch(url)
    return r if isinstance(r, list) else []

with open('/tmp/updown_candidates.json') as f:
    candidates = json.load(f)

print(f"Deep-profiling {len(candidates)} candidates...")

NOW = int(time.time())
CUTOFF_48H = NOW - 48*3600
CUTOFF_7D = NOW - 7*86400

results = []

for idx, c in enumerate(candidates[:60]):  # Profile top 60 by initial filter
    wallet = c['wallet']
    sys.stdout.write(f"\r[{idx+1}/{min(len(candidates),60)}] Profiling {wallet[:18]}...")
    sys.stdout.flush()
    
    # Fetch activity
    activity = fetch_activity(wallet, 500)
    buys = [a for a in activity if a.get('type') == 'TRADE' and a.get('side') == 'BUY']
    
    # Fetch positions
    positions = fetch_positions(wallet)
    
    if not buys and not positions:
        continue
    
    # Compute age from first buy
    timestamps = []
    for b in buys:
        ts = int(b.get('timestamp') or 0)
        if ts > 4e12:
            ts //= 1000
        if ts > 0:
            timestamps.append(ts)
    
    age_days = 0
    if timestamps:
        age_days = (NOW - min(timestamps)) / 86400
    
    # Resolved positions: wins + losses
    wins = [p for p in positions if p.get('redeemable') == True]
    # curPrice <= 0.04 = likely loss (unless very recent)
    losses = [p for p in positions if not p.get('redeemable') and 
              float(str(p.get('curPrice') or 1)[:10] or 1) <= 0.04]
    open_pos = [p for p in positions if not p.get('redeemable') and 
                float(str(p.get('curPrice') or 0.5)[:10] or 0.5) > 0.04]
    
    n_wins = len(wins)
    n_losses = len(losses)
    n_resolved = n_wins + n_losses
    wr = n_wins / n_resolved if n_resolved > 0 else 0.0
    
    # Stakes from buys
    stakes = []
    entries = []
    buy_ts = []
    for b in buys:
        size = float(b.get('size') or 0)
        price = float(b.get('price') or 0)
        ts = int(b.get('timestamp') or 0)
        if ts > 4e12:
            ts //= 1000
        if price > 0.02 and price < 0.98 and size > 0.5:
            stake = size * price
            stakes.append(stake)
            entries.append(price)
            buy_ts.append(ts)
    
    avg_stake = sum(stakes) / len(stakes) if stakes else 0
    avg_entry = sum(entries) / len(entries) if entries else 0
    
    # Activity in last 48h
    recent_buys = sum(1 for ts in buy_ts if ts >= CUTOFF_48H)
    recent_7d = sum(1 for ts in buy_ts if ts >= CUTOFF_7D)
    last_buy_ts = max(buy_ts) if buy_ts else 0
    
    # Cluster detection: same-second buys
    ts_counts = collections.Counter(buy_ts)
    same_second = sum(1 for cnt in ts_counts.values() if cnt > 1)
    
    # Hold behavior: check open positions curPrice
    hold_prices = []
    for p in open_pos:
        cp = float(str(p.get('curPrice') or 0)[:10] or 0)
        if cp > 0.05:
            hold_prices.append(cp)
    avg_hold_price = sum(hold_prices) / len(hold_prices) if hold_prices else 0.5
    
    # Up/Down markets from this wallet's activity
    ud_titles = set()
    for b in buys:
        title = b.get('title','') or b.get('market','') or ''
        tl = title.lower()
        ud_kw = ['up or down','closes above','closes below','above $','below $','finish week','finish above','close at']
        stock_kw = ['spy','qqq','nvda','tsla','aapl','msft','meta','amzn','amd','googl','nflx','russell','s&p','nasdaq','dow','spx','ndx']
        if any(kw in tl for kw in ud_kw) and any(kw in tl for kw in stock_kw):
            ud_titles.add(title[:60])
    
    # Crypto check
    crypto_buys = 0
    total_b = 0
    for b in buys:
        title = (b.get('title','') or '').lower()
        total_b += 1
        if any(kw in title for kw in ['bitcoin','ethereum','btc','eth ','xrp','solana','doge','crypto']):
            crypto_buys += 1
    crypto_pct = (crypto_buys / total_b * 100) if total_b > 0 else 0
    
    # Blocked markets
    blocked_kw_list = ['iran','israel','ukraine','russia','trump','election','president','2028','2032']
    blocked_buys = sum(1 for b in buys if any(kw in (b.get('title','') or '').lower() for kw in blocked_kw_list))
    blocked_pct = (blocked_buys / total_b * 100) if total_b > 0 else 0
    
    result = {
        'wallet': wallet,
        'n_wins': n_wins,
        'n_losses': n_losses,
        'n_resolved': n_resolved,
        'wr': round(wr, 3),
        'n_open': len(open_pos),
        'n_buys': len(buys),
        'avg_stake': round(avg_stake, 2),
        'avg_entry': round(avg_entry, 3),
        'age_days': round(age_days, 1),
        'recent_buys_48h': recent_buys,
        'recent_buys_7d': recent_7d,
        'clusters': same_second,
        'avg_hold_price': round(avg_hold_price, 3),
        'ud_markets': list(ud_titles)[:5],
        'n_ud_markets': len(ud_titles),
        'crypto_pct': round(crypto_pct, 1),
        'blocked_pct': round(blocked_pct, 1),
        'last_buy_ts': last_buy_ts,
        'from_mine': c.get('markets', [])[:3],
    }
    results.append(result)
    time.sleep(0.3)  # be gentle

print(f"\n\nProfiled {len(results)} wallets with data")
with open('/tmp/updown_profiles.json','w') as f:
    json.dump(results, f, indent=2)

# Score and print
def score(r):
    s = 0
    if r['n_resolved'] >= 8: s += 20
    elif r['n_resolved'] >= 5: s += 10
    if r['wr'] >= 0.75: s += 30
    elif r['wr'] >= 0.65: s += 15
    if r['avg_stake'] >= 20: s += 20
    elif r['avg_stake'] >= 8: s += 10
    elif r['avg_stake'] >= 4: s += 5
    if r['avg_entry'] <= 0.65: s += 10
    elif r['avg_entry'] <= 0.75: s += 5
    if r['recent_buys_48h'] >= 2: s += 10
    if r['clusters'] <= 2: s += 5
    elif r['clusters'] > 10: s -= 20
    if r['n_ud_markets'] >= 3: s += 10
    elif r['n_ud_markets'] >= 1: s += 5
    if r['crypto_pct'] > 80: s -= 30  # crypto-dominant
    return s

for r in results:
    r['score'] = score(r)

results.sort(key=lambda x: x['score'], reverse=True)

print("\n=== TOP PROFILES (sorted by score) ===")
for r in results[:30]:
    print(f"\n  {r['wallet']}")
    print(f"  Score={r['score']} | WR={r['wr']:.1%} ({r['n_wins']}W/{r['n_losses']}L, {r['n_resolved']} resolved)")
    print(f"  avg_stake=${r['avg_stake']:.2f} avg_entry={r['avg_entry']:.3f} age={r['age_days']:.0f}d clusters={r['clusters']}")
    print(f"  buys={r['n_buys']} recent48h={r['recent_buys_48h']} crypto_pct={r['crypto_pct']:.0f}% blocked_pct={r['blocked_pct']:.0f}%")
    print(f"  ud_markets: {r['ud_markets'][:2]}")

with open('/tmp/updown_profiles.json','w') as f:
    json.dump(results, f, indent=2)
print(f"\nSaved to /tmp/updown_profiles.json")
