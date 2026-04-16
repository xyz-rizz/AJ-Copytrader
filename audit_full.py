#!/usr/bin/env python3
"""Full audit: trade log, capital, per-trader PnL"""
import json, urllib.request, os
from collections import defaultdict

# ── Trade Log ────────────────────────────────────────────────────────────────
log = '/home/ubuntu/copytrade/trade_log.jsonl'
traders = defaultdict(lambda: {'buys': 0, 'stake': 0, 'wins': 0, 'losses': 0,
                                 'pnl': 0, 'worst': [], 'stakes': []})
total_stake = 0; total_wins = 0; total_losses = 0; total_pnl = 0
skips = defaultdict(int)
all_entries = []

with open(log) as f:
    for line in f:
        try:
            e = json.loads(line.strip())
        except:
            continue
        all_entries.append(e)
        a = e.get('action', '')
        trader = e.get('trader', 'unknown')
        if a == 'BUY':
            st = float(e.get('stake', 0) or 0)
            traders[trader]['buys'] += 1
            traders[trader]['stake'] += st
            traders[trader]['stakes'].append(st)
            total_stake += st
        elif a in ('CLAIM', 'RESOLVED_WIN'):
            pnl = float(e.get('pnl', 0) or e.get('profit', 0) or 0)
            traders[trader]['wins'] += 1
            traders[trader]['pnl'] += pnl
            total_wins += 1
            total_pnl += pnl
        elif a == 'RESOLVED_LOSS':
            pnl = float(e.get('pnl', 0) or e.get('loss', 0) or 0)
            traders[trader]['losses'] += 1
            traders[trader]['pnl'] += pnl
            traders[trader]['worst'].append(pnl)
            total_losses += 1
            total_pnl += pnl
        elif a == 'SKIPPED':
            reason = e.get('reason', '?')[:50]
            skips[reason] += 1

print('=' * 70)
print('TRADE LOG SUMMARY')
print('=' * 70)
print(f'Total BUY entries : {sum(t["buys"] for t in traders.values())}')
print(f'Total BUY stake   : ${total_stake:.2f}')
print(f'Resolved wins     : {total_wins}')
print(f'Resolved losses   : {total_losses}')
print(f'Realized PnL      : ${total_pnl:.2f}')
print()

# Active traders only (known in v7.8.12)
ACTIVE = ['Signal47-Bets', 'Immense-Gokart', 'Triangular-Box', 'Unwieldy-Forage',
          'gem62-NBA', 'gem61-WBC', 'NBA-9c88', 'bigwhale1337', 'InfoEdge-a2ed',
          'SPXOpens-f52c', 'NBAEdge-aeab', 'SoccerSharp-f23c', 'Sport-dd57']

print('=' * 70)
print('PER-TRADER BOT-SIDE PnL (active roster + recent benched)')
print(f'{"Trader":<22} {"Buys":>5} {"W":>4} {"L":>4} {"PnL":>9} {"AvgStake":>9} {"Worst":>30}')
print('-' * 70)
for name, d in sorted(traders.items(), key=lambda x: -x[1]['pnl']):
    if d['buys'] == 0 and d['wins'] == 0 and d['losses'] == 0:
        continue
    avg = d['stake'] / d['buys'] if d['buys'] else 0
    worst_str = str(sorted(d['worst'])[:2])
    print(f'{name:<22} {d["buys"]:>5} {d["wins"]:>4} {d["losses"]:>4} ${d["pnl"]:>8.2f} ${avg:>8.1f} {worst_str:>30}')

print()
print('=' * 70)
print('TOP SKIP REASONS')
print('=' * 70)
for r, c in sorted(skips.items(), key=lambda x: -x[1])[:15]:
    print(f'  {c:>6}x  {r}')

# ── Positions (SAFE wallet) ──────────────────────────────────────────────────
print()
print('=' * 70)
print('SAFE WALLET POSITIONS')
print('=' * 70)
safe = '0xacBcB5edEC9cdDF2d1CE72dD8A2E734E849AF6bf'
url = f'https://data-api.polymarket.com/positions?user={safe}&sizeThreshold=0.001&limit=500'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        pos = json.load(r)
except Exception as ex:
    print(f'ERROR: {ex}')
    pos = []

redeemable_size = 0
redeemable_count = 0
open_mtm = 0
open_count = 0
loss_count = 0
loss_val = 0

for p in pos:
    cur = float(p.get('curPrice', 0) or 0)
    size = float(p.get('size', 0) or 0)
    if p.get('redeemable'):
        redeemable_size += size
        redeemable_count += 1
    elif cur <= 0.04:
        loss_count += 1
        loss_val += size * cur
    else:
        open_mtm += size * cur
        open_count += 1

print(f'Total tokens      : {len(pos)}')
print(f'Redeemable (wins) : {redeemable_count} tokens, redemption_value=${redeemable_size:.2f}')
print(f'Open (live)       : {open_count} tokens, MTM=${open_mtm:.2f}')
print(f'Near-loss (≤0.04) : {loss_count} tokens, residual=${loss_val:.2f}')
print()
print('Open positions detail:')
open_list = [(p.get('title','?')[:60], float(p.get('curPrice',0) or 0),
              float(p.get('size',0) or 0)) for p in pos
             if not p.get('redeemable') and float(p.get('curPrice',0) or 0) > 0.04]
open_list.sort(key=lambda x: -x[1]*x[2])
for t, c, s in open_list:
    print(f'  {t:<60} cur={c:.3f} size={s:.1f} val=${s*c:.2f}')

print()
print('Redeemable (top 15 by size):')
red_list = [(p.get('title','?')[:60], float(p.get('size',0) or 0))
             for p in pos if p.get('redeemable')]
red_list.sort(key=lambda x: -x[1])
for t, s in red_list[:15]:
    print(f'  {t:<60} size={s:.1f}')

# ── Read bot.log for today's copies ─────────────────────────────────────────
print()
print('=' * 70)
print('TODAY\'s BUY/LOSS from bot.log (last 24h)')
print('=' * 70)
import subprocess, time
result = subprocess.run(['grep', '-E', '\\[BUY\\]|🔔|RESOLVED_LOSS|RESOLVED_WIN|CLAIM|daily_stop',
                         '/home/ubuntu/copytrade/bot.log'],
                        capture_output=True, text=True)
lines = result.stdout.strip().split('\n')
# Filter to today (2026-03-12 or yesterday Mar 11 after 13:39)
today_lines = [l for l in lines if '2026-03-12' in l or ('2026-03-11' in l and '1[3-9]:' in l)]
print(f'Matching lines today: {len(today_lines)}')
for l in today_lines[-40:]:
    print(l[:140])
