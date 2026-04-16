#!/usr/bin/env python3
"""
Mine SPX Opens Up or Down historical markets (past 60 days).
Also profiles the monitor-list wallet 0xf5d07cdbe4...
Also profiles wallets from binary_cands with highest stakes that aren't age=0.
"""
import urllib.request, json, time, collections, sys

def fetch(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read())
        except Exception as e:
            if i == retries-1: return []
            time.sleep(1.5)

BLACKLIST = {
    '0x8f80e8c2','0x65b6662c','0xccbd4bbcc','0x3f5ea0a8','0x14ac84b6',
    '0xdc16718a','0xafaf83a4','0x503f8098','0x0caacf39','0x703200e7',
    '0xc2c1a8c9','0x18fef668','0x4b916c5a',
    '0x77f623734a71c023f9df91011189eaeef891dbd1',
    '0xa83be3f6a49604556f45089799f2b2096e71def4',
    '0xf27e335d2e78a207e802879f72870449836bd69d',
    '0xe85d6567a750b7b15fcb51c01a7c6230f63095d8',
    '0x146703a8a73ae1dff0f84ba44c45d878858a4372',
    '0xa2ed440b6e3b9738a547c5a20f79616b63828808',
}

NOW = int(time.time())

# ── STEP 1: Find all SPX Opens Up or Down markets (past 60 days, closed+active) ──
print("=== STEP 1: SPX Opens Up or Down market participants ===")
spx_events = []
for page in range(5):
    r = fetch(f"https://gamma-api.polymarket.com/events?closed=false&active=true&limit=50&offset={page*50}&order=startDate&ascending=false&tag_slug=finance")
    r += fetch(f"https://gamma-api.polymarket.com/events?closed=true&active=false&limit=50&offset={page*50}&order=startDate&ascending=false&tag_slug=finance")
    for e in r:
        title = e.get('title','').lower()
        if 'opens up or down' in title or ('up or down' in title and ('s&p' in title or 'spx' in title or 'russell' in title or 'nasdaq' in title or 'dow' in title)):
            spx_events.append(e)

# Also check stocks tag
for page in range(5):
    r = fetch(f"https://gamma-api.polymarket.com/events?closed=true&active=false&limit=50&offset={page*50}&order=startDate&ascending=false&tag_slug=stocks")
    for e in r:
        title = e.get('title','').lower()
        if 'opens up or down' in title or ('up or down' in title and ('s&p' in title or 'spx' in title or 'russell' in title or 'nasdaq' in title or 'dow' in title or 'nvda' in title or 'tsla' in title or 'meta' in title or 'msft' in title or 'aapl' in title or 'amzn' in title or 'googl' in title or 'nflx' in title)):
            spx_events.append(e)

# Deduplicate
seen_slugs = set()
uniq_events = []
for e in spx_events:
    slug = e.get('slug','')
    if slug not in seen_slugs:
        seen_slugs.add(slug)
        uniq_events.append(e)

print(f"Found {len(uniq_events)} SPX/index/stock UD events (closed+active)")
for e in uniq_events[:20]:
    print(f"  {e.get('title','')[:70]} vol={e.get('volume24hr',0)}")

# Extract conditionIds
historical_cids = []
cid_event_map = {}
for e in uniq_events:
    markets = e.get('markets', [])
    for m in markets:
        cid = m.get('conditionId','')
        if cid:
            historical_cids.append(cid)
            cid_event_map[cid] = e.get('title','')

print(f"\nTotal historical CIDs: {len(historical_cids)}")

# Mine participants
wallet_data = collections.defaultdict(lambda: {'stakes':[], 'entries':[], 'ts':[], 'events':set()})
print(f"Mining {len(historical_cids)} historical CIDs...")
for i, cid in enumerate(historical_cids):
    trades = fetch(f"https://data-api.polymarket.com/trades?conditionId={cid}&limit=500")
    for t in trades:
        if not isinstance(t, dict): continue
        wallet = t.get('proxyWallet') or t.get('maker') or ''
        if not wallet or len(wallet) < 10: continue
        wl = wallet.lower()
        if any(wl.startswith(b.lower()) for b in BLACKLIST): continue
        if t.get('side') != 'BUY': continue
        size = float(t.get('size') or 0)
        price = float(t.get('price') or 0)
        ts = int(t.get('timestamp') or 0)
        if ts > 4e12: ts //= 1000
        if price <= 0.02 or price >= 0.99: continue
        if size < 0.5: continue
        wallet_data[wallet]['stakes'].append(size*price)
        wallet_data[wallet]['entries'].append(price)
        wallet_data[wallet]['ts'].append(ts)
        wallet_data[wallet]['events'].add(cid_event_map.get(cid,''))
    if (i+1) % 20 == 0:
        print(f"  {i+1}/{len(historical_cids)}, {len(wallet_data)} unique wallets")

print(f"\n{len(wallet_data)} unique wallets in historical SPX/stock UD markets")

# Filter and score
CUTOFF_30D = NOW - 30*86400
CUTOFF_48H = NOW - 48*3600
hist_cands = []
for wallet, data in wallet_data.items():
    stakes = data['stakes']
    entries = data['entries']
    ts_list = data['ts']
    events = data['events']
    if len(stakes) < 5: continue
    avg_s = sum(stakes)/len(stakes)
    avg_e = sum(entries)/len(entries)
    last_ts = max(ts_list) if ts_list else 0
    first_ts = min(ts_list) if ts_list else 0
    if avg_s < 4: continue
    if avg_e > 0.87: continue
    if last_ts < CUTOFF_30D: continue
    ts_counts = collections.Counter(ts_list)
    clusters = sum(1 for cnt in ts_counts.values() if cnt > 1)
    if clusters > 20: continue
    age_d = (last_ts - first_ts) / 86400
    hist_cands.append({
        'wallet': wallet,
        'n_buys': len(stakes),
        'avg_stake': round(avg_s, 2),
        'avg_entry': round(avg_e, 3),
        'age_d_in_market': round(age_d, 1),
        'clusters': clusters,
        'n_events': len(events),
        'active_48h': last_ts >= CUTOFF_48H,
        'events': list(events)[:4],
    })

hist_cands.sort(key=lambda x: (x['active_48h'], x['n_buys'], x['avg_stake']), reverse=True)
print(f"Filtered historical SPX/stock-UD candidates: {len(hist_cands)}")
print("\nTop 25:")
for c in hist_cands[:25]:
    print(f"  {c['wallet'][:22]} buys={c['n_buys']:3d} avg_s=${c['avg_stake']:7.2f} entry={c['avg_entry']:.3f} clust={c['clusters']:2d} evts={c['n_events']} 48h={c['active_48h']}")
    print(f"    market_age={c['age_d_in_market']:.0f}d | {list(c['events'])[:1]}")

# ── STEP 2: Profile monitor-list whale ──
print("\n=== STEP 2: Monitor-list wallet 0xf5d07cdbe4 ===")
mon_wallet = '0xf5d07cdbe4dd44d0fe9017a7bf1cf9cb0e1e8fca'

activity = fetch(f"https://data-api.polymarket.com/activity?user={mon_wallet}&limit=500")
positions = fetch(f"https://data-api.polymarket.com/positions?user={mon_wallet}&sizeThreshold=0.001")

buys = [a for a in activity if isinstance(a,dict) and a.get('type')=='TRADE' and a.get('side')=='BUY']
wins = [p for p in positions if p.get('redeemable')]
losses = [p for p in positions if not p.get('redeemable') and float(str(p.get('curPrice') or 1)[:10] or 1) <= 0.04]
open_p = [p for p in positions if not p.get('redeemable') and float(str(p.get('curPrice') or 0.5)[:10] or 0.5) > 0.04]

stakes = []
entries = []
buy_ts = []
ud_stock = []
for b in buys:
    price = float(b.get('price') or 0)
    size = float(b.get('size') or 0)
    ts = int(b.get('timestamp') or 0)
    if ts > 4e12: ts //= 1000
    title = (b.get('title') or '').lower()
    if price > 0.01 and price < 0.99 and size > 0.1:
        stakes.append(size*price)
        entries.append(price)
        buy_ts.append(ts)
    if any(kw in title for kw in ['up or down','opens up or down','closes above']):
        if any(kw in title for kw in ['nvda','tsla','aapl','msft','meta','amzn','googl','nflx','pltr','open','s&p','spx','russell','nasdaq','dow','rut','ndx']):
            ud_stock.append(b)

if stakes:
    avg_s = sum(stakes)/len(stakes)
    avg_e = sum(entries)/len(entries)
    age_d = (NOW - min(buy_ts)) / 86400 if buy_ts else 0
    last_buy = (NOW - max(buy_ts)) / 3600 if buy_ts else 999
    ts_counts = collections.Counter(buy_ts)
    clusters = sum(1 for cnt in ts_counts.values() if cnt > 1)
    n_res = len(wins) + len(losses)
    wr = len(wins)/n_res if n_res else 0
    print(f"  buys={len(buys)} avg_stake=${avg_s:.2f} avg_entry={avg_e:.3f}")
    print(f"  age={age_d:.1f}d last_buy={last_buy:.1f}h ago clusters={clusters}")
    print(f"  WR={wr:.1%} ({len(wins)}W/{len(losses)}L, {n_res} resolved) | {len(open_p)} open")
    print(f"  UD stock buys: {len(ud_stock)}")
    for b in ud_stock[:5]:
        print(f"    {(b.get('title') or '')[:70]}")
else:
    print("  NO DATA")

with open('/tmp/spx_hist_cands.json','w') as f:
    json.dump(hist_cands, f, indent=2)
print(f"\nSaved {len(hist_cands)} historical cands to /tmp/spx_hist_cands.json")
