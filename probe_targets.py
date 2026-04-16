#!/usr/bin/env python3
import json, urllib.request, time

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            return json.load(r)
    except Exception as e:
        return None

# Scanner results
with open('/home/ubuntu/copytrade/scanner_results.json') as f:
    scan = json.load(f)
print(f"Scanner keys: {list(scan.keys())[:6]}")
print(f"Scanner ts: {scan.get('ts', scan.get('timestamp', '?'))}")
gems = scan.get('gems', [])
print(f"Scanner gems ({len(gems)}):")
for g in gems:
    print(f"  {g.get('wallet','')[:22]} WR={g.get('win_rate',0):.1f}% {g.get('wins',0)}W/{g.get('losses',0)}L"
          f" res={g.get('resolved',0)} stake=${g.get('avg_stake',0):.0f} age={g.get('age_days',0):.0f}d score={g.get('score',0):.0f}")

# UDHighFreq-9868 age check
print()
wallet_ud = '0xaf32d3df3a83eed06b759e52da83088faf709868'
data = fetch(f'https://data-api.polymarket.com/activity?user={wallet_ud}&limit=200')
if data:
    buys = [x for x in data if x.get('type') == 'TRADE' and x.get('side') == 'BUY']
    buys.sort(key=lambda x: -x.get('timestamp', 0))
    if buys:
        ts_list = [b.get('timestamp', 0) for b in buys]
        ts_list = [t/1000 if t > 4e12 else t for t in ts_list]
        age = (max(ts_list) - min(ts_list)) / 86400
        last = (time.time() - max(ts_list)) / 3600
        print(f"UDHighFreq-9868: {len(buys)} buys, age={age:.1f}d, last={last:.1f}h")
        for b in buys[:4]:
            print(f"  {b.get('title','')[:60]}")

# 0x0799 positions
print()
wallet_99 = '0x0799daf859e32ec813845a58249172daee889452'
pos = fetch(f'https://data-api.polymarket.com/positions?user={wallet_99}&sizeThreshold=0.001')
if pos:
    wins = sum(1 for p in pos if p.get('redeemable'))
    losses = sum(1 for p in pos if float(p.get('curPrice', 0) or 0) <= 0.04)
    open_p = [p for p in pos if not p.get('redeemable') and float(p.get('curPrice', 0) or 0) > 0.04]
    print(f"0x0799: {wins}W/{losses}L/{len(open_p)}open (resolved={wins+losses})")
    for p in open_p:
        cur = float(p.get('curPrice', 0) or 0)
        print(f"  OPEN: {p.get('title','')[:55]} cur={cur:.3f}")

# Also try to read UDHighFreq positions
pos_ud = fetch(f'https://data-api.polymarket.com/positions?user={wallet_ud}&sizeThreshold=0.001')
if pos_ud:
    wins_ud = sum(1 for p in pos_ud if p.get('redeemable'))
    losses_ud = sum(1 for p in pos_ud if float(p.get('curPrice', 0) or 0) <= 0.04)
    open_ud = sum(1 for p in pos_ud if not p.get('redeemable') and float(p.get('curPrice', 0) or 0) > 0.04)
    print(f"\nUDHighFreq-9868 positions: {wins_ud}W/{losses_ud}L/{open_ud}open (resolved={wins_ud+losses_ud})")
