#!/usr/bin/env python3
"""
Whale Scout v1.0 — Find high-conviction directional bettors
Criteria: WR > 80% + avg_stake > $100 + not a hedge bettor + sports-dominant
Scans top-500 leaderboard by 30d PnL, checks positions for each.
"""
import json, urllib.request, time, re, sys
from datetime import datetime, timezone

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'

def fetch(url, timeout=12):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())

def score_trader(wallet, name='?'):
    """Return a score dict for a wallet. None if disqualified early."""
    try:
        pos_data = fetch(f'https://data-api.polymarket.com/positions?user={wallet}&limit=500&sizeThreshold=0.01')
    except Exception as e:
        return None

    if not pos_data or not isinstance(pos_data, list):
        return None

    wins = losses = open_pos = 0
    categories = {}
    amounts_by_market = {}  # market → list of positions (detect hedging)
    invested_total = 0.0
    proceeds_total = 0.0

    for p in pos_data:
        cur = float(p.get('curPrice') or 0)
        redeemable = p.get('redeemable', False)
        pnl = float(p.get('percentPnl') or 0)
        cur_val = float(p.get('currentValue') or 0)
        title = (p.get('title') or p.get('market') or '').strip()
        size_usdc = float(p.get('cashProfitLoss') or 0)

        # Normalize title to detect same-market hedging
        # Remove O/U suffix patterns, keep base game title
        base_title = re.sub(r':\s*(O/U|Spread|ML|Moneyline).*', '', title, flags=re.I).strip()
        amounts_by_market.setdefault(base_title, []).append(p)

        # Category
        tl = title.lower()
        for cat, kws in [
            ('sports', ['nba','nfl','nhl','mlb','ufc','tennis','football','soccer','epl',
                       'basketball','baseball','hockey','spread','o/u','moneyline','winner',
                       'will ','match','game','vs','playoff','championship','cup']),
            ('crypto', ['bitcoin','btc','eth','crypto','solana','price','pump','dump']),
            ('politics', ['president','election','congress','senate','trump','biden']),
            ('weather', ['temperature','hurricane','storm','rainfall'])
        ]:
            if any(k in tl for k in kws):
                categories[cat] = categories.get(cat, 0) + 1
                break
        else:
            categories['other'] = categories.get('other', 0) + 1

        # Classify
        if redeemable and cur_val > 0:
            wins += 1
            proceeds_total += cur_val
        elif redeemable and cur_val == 0 and pnl <= -50:
            losses += 1
        elif cur <= 0.04 and not redeemable:
            losses += 1
        elif not redeemable and cur > 0.04:
            open_pos += 1

    resolved = wins + losses
    if resolved < 15:
        return None  # not enough data

    wr = wins / resolved * 100

    # Crypto check — hard ban
    crypto_pct = categories.get('crypto', 0) / max(sum(categories.values()), 1) * 100
    if crypto_pct > 20:
        return None

    # Hedge detection: count markets where both YES and NO sides appear
    hedge_markets = 0
    for base, positions in amounts_by_market.items():
        if len(positions) >= 2:
            # Check if they have both YES and NO in same market
            outcomes = set()
            for pos in positions:
                outcome = (pos.get('outcome') or pos.get('side') or '').lower()
                if outcome in ('yes', 'no', 'buy', 'sell'):
                    outcomes.add(outcome)
            if ('yes' in outcomes and 'no' in outcomes) or ('buy' in outcomes and 'sell' in outcomes):
                hedge_markets += 1

    hedge_ratio = hedge_markets / max(len(amounts_by_market), 1)

    return {
        'wallet': wallet,
        'name': name,
        'wr': wr,
        'wins': wins,
        'losses': losses,
        'resolved': resolved,
        'open': open_pos,
        'categories': categories,
        'crypto_pct': crypto_pct,
        'hedge_markets': hedge_markets,
        'hedge_ratio': hedge_ratio,
        'proceeds': proceeds_total,
    }

def get_avg_stake(wallet):
    try:
        act = fetch(f'https://data-api.polymarket.com/activity?user={wallet}&limit=200')
        if not act or not isinstance(act, list):
            return 0, 0, 0
        buys = [d for d in act if (d.get('side') or d.get('type') or '').upper() in ('BUY',)]
        if not buys:
            buys = act
        amounts = [float(d.get('usdcSize') or d.get('amount') or 0) for d in buys]
        avg = sum(amounts) / len(amounts) if amounts else 0
        now = datetime.now(timezone.utc).timestamp()
        recent = [d for d in buys if abs(now - int(str(d.get('timestamp','0'))[:10])) < 30*86400]
        freq = len(recent) / 30.0
        # v7.5.6: avg_entry_price — exclude near-certainty bettors (buy at 0.97-0.99)
        prices = [float(d.get('price') or 0) for d in buys if d.get('price')]
        avg_entry = sum(prices) / len(prices) if prices else 0
        return avg, freq, avg_entry
    except:
        return 0, 0, 0

# ── Main scan ────────────────────────────────────────────────────────────────
# Already in our bot — skip these
ALREADY_TRACKING = {
    '0xa83be3f6a4', '0xf27e335d2e', '0x69aee04532', '0xe85d6567',
    '0x146703a8', '0x25a1a36e67', '0xbb15969c', '0xc33a100b', '0xb5124dae',
    '0x71971342cb', '0x05b21f43e0', '0x4042a8ef98', '0x77f623734a'
}

print("=" * 70)
print(f"WHALE SCOUT — {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC")
print("Criteria: WR≥80% | resolved≥15 | avg_stake≥$100 | hedge_ratio<30% | no-crypto")
print("=" * 70)

gems = []
scanned = 0

for offset in range(0, 500, 50):
    try:
        lb = fetch(f'https://data-api.polymarket.com/v1/leaderboard?limit=50&offset={offset}&window=30d')
        entries = lb if isinstance(lb, list) else lb.get('data', [])
    except Exception as e:
        print(f"Leaderboard fetch failed at offset {offset}: {e}")
        continue

    for entry in entries:
        wallet = (entry.get('proxyWallet') or entry.get('address') or '').lower()
        name = entry.get('name') or entry.get('pseudonym') or wallet[:10]
        pnl_30d = float(entry.get('profit') or entry.get('pnl') or 0)

        if not wallet or len(wallet) < 20:
            continue

        # Skip already tracking
        if any(wallet.startswith(t.lower()) for t in ALREADY_TRACKING):
            continue

        scanned += 1
        sys.stdout.write(f"\r  Scanning {scanned}: {name[:20]:20s} | 30d_pnl=${pnl_30d:,.0f}   ")
        sys.stdout.flush()

        result = score_trader(wallet, name)
        time.sleep(0.3)

        if result is None:
            continue

        wr = result['wr']
        resolved = result['resolved']

        if wr < 80:
            continue

        avg_stake, freq, avg_entry = get_avg_stake(wallet)
        time.sleep(0.3)

        result['avg_stake'] = avg_stake
        result['freq'] = freq
        result['avg_entry'] = avg_entry   # v7.5.6
        result['pnl_30d'] = pnl_30d

        if avg_stake < 100:
            print(f"\n  ⚡ {name}: WR={wr:.1f}% but avg_stake=${avg_stake:.0f} (too small)")
            continue

        if avg_entry > 0.80:   # v7.5.6: exclude near-certainty bettors (enter at 0.97-0.99)
            print(f"\n  🎯 {name}: WR={wr:.1f}% but avg_entry={avg_entry:.2f} (near-certainty, no copy edge)")
            continue

        if result['hedge_ratio'] > 0.30:
            print(f"\n  🔀 {name}: WR={wr:.1f}% but hedge_ratio={result['hedge_ratio']:.0%} (hedger)")
            continue

        crypto_pct = result['crypto_pct']
        if crypto_pct > 20:
            print(f"\n  ₿  {name}: WR={wr:.1f}% but crypto={crypto_pct:.0f}% (hard-ban)")
            continue

        gems.append(result)
        cats = result['categories']
        print(f"\n  🔥 GEM: {name} | WR={wr:.1f}% ({result['wins']}W/{result['losses']}L) "
              f"| avg_stake=${avg_stake:.0f} | freq={freq:.1f}/d "
              f"| hedge={result['hedge_ratio']:.0%} | cats={cats} "
              f"| wallet={wallet}")

    time.sleep(0.5)

print(f"\n\nScanned {scanned} wallets. Found {len(gems)} whale gems.")
print()
if gems:
    print("=" * 70)
    print("WHALE GEMS SUMMARY")
    print("=" * 70)
    print(f"{'Name':20s} {'WR%':>6} {'Res':>5} {'Avg$':>7} {'Freq':>6} {'Hedge':>6} {'30d PnL':>10}")
    print("-" * 70)
    for g in sorted(gems, key=lambda x: -x['wr']):
        print(f"{g['name']:20s} {g['wr']:>6.1f} {g['resolved']:>5d} "
              f"{g['avg_stake']:>7.0f} {g['freq']:>6.1f} "
              f"{g['hedge_ratio']:>6.0%} {g.get('avg_entry',0):>7.2f} ${g['pnl_30d']:>9,.0f}")
        print(f"  wallet: {g['wallet']}")
else:
    print("No gems found in this scan window. Try expanding to 7d leaderboard or more offsets.")

print("\nDone.")
