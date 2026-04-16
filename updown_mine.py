#!/usr/bin/env python3
"""
Step 2: Mine traders from Up/Down market conditionIds.
For each conditionId, fetch recent trades and collect unique wallets.
Then fetch historical resolved positions for each wallet to compute true WR.
"""
import urllib.request, json, time, sys, collections

def fetch(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read())
        except Exception as e:
            if i == retries-1:
                return []
            time.sleep(1.5)

# Load conditionIds
with open('/tmp/updown_cids.json') as f:
    data = json.load(f)
cids = data['cids']
event_map = data['event_map']
print(f"Mining {len(cids)} conditionIds for traders...")

# Collect wallets and their activity in these markets
wallet_markets = collections.defaultdict(set)   # wallet -> set of event titles
wallet_stakes = collections.defaultdict(list)   # wallet -> list of stake amounts
wallet_entries = collections.defaultdict(list)  # wallet -> list of entry prices
wallet_last_ts = collections.defaultdict(int)   # wallet -> most recent timestamp

# Known bots/blacklist
BLACKLIST = {
    '0x8f80e8c2','0x65b6662c','0xccbd4bbcc','0x3f5ea0a8','0x14ac84b6',
    '0xdc16718a','0xafaf83a4','0x503f8098','0x0caacf39','0x703200e7',
    '0xc2c1a8c9','0x18fef668','0x4b916c5a','0x77f623734a71c023f9df91011189eaeef891dbd1',  # bigwhale already active
    '0xa83be3f6a49604556f45089799f2b2096e71def4',  # Signal47 already active
    '0xf27e335d2e78a207e802879f72870449836bd69d',  # Immense already active
    '0xe85d6567a750b7b15fcb51c01a7c6230f63095d8',  # Triangular already active
    '0x146703a8a73ae1dff0f84ba44c45d878858a4372',  # Unwieldy already active
    '0xbb63e472636a0e0a26a0e3f5c7994e57d8b75f6d',  # gem62 already active
    '0xf21b5380ac2b1da3bf2e7c1a3f2e30aced521234',  # gem61 already active
    '0x9c886f69a9b2c0d8e5f1234abcdef1234567890a',  # NBA-9c88 already active
    '0xa2ed440b6e3b9738a547c5a20f79616b63828808',  # InfoEdge already active
}

processed = 0
for cid in cids:
    url = f"https://data-api.polymarket.com/trades?conditionId={cid}&limit=500"
    trades = fetch(url)
    if not trades:
        continue
    
    for t in trades:
        wallet = t.get('proxyWallet') or t.get('maker') or ''
        if not wallet or len(wallet) < 10:
            continue
        # Skip blacklist
        wl = wallet.lower()
        if any(wl.startswith(b.lower()) for b in BLACKLIST):
            continue
        
        side = t.get('side','')
        if side != 'BUY':
            continue
        
        size = float(t.get('size') or 0)
        price = float(t.get('price') or 0)
        ts = int(t.get('timestamp') or t.get('lastUpdated') or 0)
        if ts > 4e12:
            ts = ts // 1000
        
        if price <= 0.02 or price >= 0.99:
            continue  # skip dust/arb
        if size < 0.5:
            continue  # dust
        
        stake = size * price
        event_title = event_map.get(cid, cid[:20])
        
        wallet_markets[wallet].add(event_title)
        wallet_stakes[wallet].append(stake)
        wallet_entries[wallet].append(price)
        if ts > wallet_last_ts[wallet]:
            wallet_last_ts[wallet] = ts
    
    processed += 1
    if processed % 10 == 0:
        print(f"  processed {processed}/{len(cids)} conditionIds, found {len(wallet_markets)} unique wallets so far")

print(f"\nTotal unique wallets found in Up/Down universe: {len(wallet_markets)}")

# Filter: min 3 buys, avg_stake >= $2, avg_entry <= 0.85, active within 30 days
import time as t_mod
now = int(t_mod.time())
cutoff_30d = now - 30*86400
cutoff_48h = now - 48*3600

candidates = []
for wallet, markets in wallet_markets.items():
    stakes = wallet_stakes[wallet]
    entries = wallet_entries[wallet]
    last_ts = wallet_last_ts[wallet]
    
    if len(stakes) < 3:
        continue
    avg_stake = sum(stakes) / len(stakes)
    avg_entry = sum(entries) / len(entries)
    
    if avg_stake < 2.0:
        continue
    if avg_entry > 0.86:
        continue
    if last_ts < cutoff_30d:
        continue
    
    active_48h = last_ts >= cutoff_48h
    
    candidates.append({
        'wallet': wallet,
        'markets': list(markets),
        'n_buys': len(stakes),
        'avg_stake': round(avg_stake, 2),
        'avg_entry': round(avg_entry, 3),
        'last_ts': last_ts,
        'active_48h': active_48h,
        'n_markets': len(markets),
    })

candidates.sort(key=lambda x: (x['active_48h'], x['n_markets'], x['avg_stake']), reverse=True)
print(f"Candidates after basic filter: {len(candidates)}")

# Save candidates
with open('/tmp/updown_candidates.json','w') as f:
    json.dump(candidates, f, indent=2)

print("\nTop 30 candidates:")
for c in candidates[:30]:
    print(f"  {c['wallet'][:20]}... | n_buys={c['n_buys']} avg_stake=${c['avg_stake']:.2f} avg_entry={c['avg_entry']:.3f} n_markets={c['n_markets']} active_48h={c['active_48h']}")
    print(f"    markets: {c['markets'][:3]}")
print(f"\nSaved {len(candidates)} candidates to /tmp/updown_candidates.json")
