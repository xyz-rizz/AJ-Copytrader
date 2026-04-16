#!/usr/bin/env python3
"""
Focused: mine ONLY from pure binary Up/Down markets (not closes-above price ladders).
These are cleaner directional bets - better for copytrading.
Also deep-profiles the top high-stake candidates from the raw mine.
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

# Load full universe
with open('/tmp/updown_cids.json') as f:
    data = json.load(f)
cids = data['cids']
event_map = data['event_map']

# Filter to ONLY pure binary Up/Down markets
# These have specific event titles like "Meta Up or Down on March 11"
binary_ud_keywords = ['up or down', 'opens up or down']
# Exclude price-ladder events
ladder_keywords = ['closes above', 'closes week', 'closes at', 'finish week', 'finish above',
                   'above ___', 'close above', 'hit high', 'hit low', 'price at',
                   'what will', 'all time high']

binary_cids = []
for cid in cids:
    title = event_map.get(cid, '').lower()
    is_binary = any(kw in title for kw in binary_ud_keywords)
    is_ladder = any(kw in title for kw in ladder_keywords)
    if is_binary and not is_ladder:
        binary_cids.append(cid)

print(f"Binary Up/Down CIDs: {len(binary_cids)} of {len(cids)} total")
# Show unique events
binary_events = set()
for cid in binary_cids:
    binary_events.add(event_map.get(cid,''))
print("Binary events:")
for e in sorted(binary_events):
    print(f"  {e}")

# Mine these binary markets
wallet_stakes = collections.defaultdict(list)
wallet_entries = collections.defaultdict(list)
wallet_events = collections.defaultdict(set)
wallet_last_ts = collections.defaultdict(int)
wallet_buy_ts = collections.defaultdict(list)

print(f"\nMining {len(binary_cids)} binary conditionIds...")
for i, cid in enumerate(binary_cids):
    trades = fetch(f"https://data-api.polymarket.com/trades?conditionId={cid}&limit=500")
    if not trades:
        continue
    for t in trades:
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
        stake = size * price
        evt = event_map.get(cid, '')
        wallet_stakes[wallet].append(stake)
        wallet_entries[wallet].append(price)
        wallet_events[wallet].add(evt)
        wallet_buy_ts[wallet].append(ts)
        if ts > wallet_last_ts[wallet]:
            wallet_last_ts[wallet] = ts
    if (i+1) % 20 == 0:
        print(f"  {i+1}/{len(binary_cids)} done, {len(wallet_stakes)} wallets")

print(f"\nTotal wallets in binary Up/Down markets: {len(wallet_stakes)}")
NOW = int(time.time())
CUTOFF_48H = NOW - 48*3600
CUTOFF_30D = NOW - 30*86400

# Filter and score candidates
binary_cands = []
for wallet, stakes in wallet_stakes.items():
    if len(stakes) < 3: continue
    avg_stake = sum(stakes)/len(stakes)
    avg_entry = sum(wallet_entries[wallet])/len(wallet_entries[wallet])
    last_ts = wallet_last_ts[wallet]
    buy_ts_list = wallet_buy_ts[wallet]
    if avg_stake < 3.0: continue
    if avg_entry > 0.86: continue
    if last_ts < CUTOFF_30D: continue
    active_48h = last_ts >= CUTOFF_48H
    n_events = len(wallet_events[wallet])
    # Cluster check
    ts_counts = collections.Counter(buy_ts_list)
    clusters = sum(1 for cnt in ts_counts.values() if cnt > 1)
    if clusters > 15: continue  # skip HFT
    binary_cands.append({
        'wallet': wallet,
        'n_buys': len(stakes),
        'avg_stake': round(avg_stake, 2),
        'avg_entry': round(avg_entry, 3),
        'last_ts': last_ts,
        'active_48h': active_48h,
        'n_events': n_events,
        'clusters': clusters,
        'events': list(wallet_events[wallet])[:5],
    })

binary_cands.sort(key=lambda x: (x['active_48h'], x['n_events'], x['avg_stake']), reverse=True)
print(f"Filtered binary candidates: {len(binary_cands)}")
with open('/tmp/binary_cands.json','w') as f:
    json.dump(binary_cands, f, indent=2)

print("\nTop 30 binary Up/Down candidates:")
for c in binary_cands[:30]:
    print(f"  {c['wallet'][:22]} buys={c['n_buys']:3d} avg_s=${c['avg_stake']:7.2f} entry={c['avg_entry']:.3f} evts={c['n_events']} clust={c['clusters']} 48h={c['active_48h']}")
    print(f"    events: {list(c['events'])[:2]}")
print(f"\nSaved {len(binary_cands)} to /tmp/binary_cands.json")
