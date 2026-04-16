#!/usr/bin/env python3
"""
Targeted deep-dive on 4 specific candidates.
For each: full trade history breakdown by market type, cluster analysis,
hold behavior, true WR verification.
"""
import urllib.request, json, time, collections

def fetch(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read())
        except Exception as e:
            if i == retries-1: return []
            time.sleep(1.5)

TARGET_WALLETS = {
    '0x40344cc4ba1a39648399b2d97d0d31c27122f52c': 'primary_gem',
    '0x3c345994037eacd37a73980f7a65657dd5842055': 'old_100pct_wr',
    '0x00fbfc48c79aecb65ebc04bccf9f4120ec344442': 'low_hold_100pct',
    '0x0f5c37e3d248ed29e2f0a0913b2a3a0d8021cc27': 'deep_scan_gem',  # from deep_scan 83.8 score
    '0x118b00b4fcf14c1d35d1795a0d4034c83a3fd58f': 'whale_209avg',
    '0xdbdd45150249e229eb4ca8aa48a30dca21faa5de': 'whale_88avg',
    '0xa42f127d7e8df9f168818938c7d4e3e7b8b46af6': 'binary_whale_42avg',
}

NOW = int(time.time())
CUTOFF_48H = NOW - 48*3600

for wallet, label in TARGET_WALLETS.items():
    print(f"\n{'='*70}")
    print(f"WALLET: {wallet}")
    print(f"LABEL:  {label}")
    print(f"{'='*70}")

    # Fetch full activity
    activity = fetch(f"https://data-api.polymarket.com/activity?user={wallet}&limit=500")
    positions = fetch(f"https://data-api.polymarket.com/positions?user={wallet}&sizeThreshold=0.001")

    buys = [a for a in activity if isinstance(a, dict) and a.get('type') == 'TRADE' and a.get('side') == 'BUY']
    if not buys and not positions:
        print("  NO DATA")
        continue

    # Categorize buys by market type
    market_types = collections.Counter()
    ud_stock_buys = []
    price_ladder_buys = []
    crypto_buys = []
    blocked_buys = []
    other_buys = []

    buy_ts = []
    stakes = []
    entries = []

    for b in buys:
        title = (b.get('title') or b.get('market') or '').lower()
        price = float(b.get('price') or 0)
        size = float(b.get('size') or 0)
        ts = int(b.get('timestamp') or 0)
        if ts > 4e12: ts //= 1000

        stake = size * price
        if price > 0.01 and price < 0.99 and size > 0.1:
            stakes.append(stake)
            entries.append(price)
            buy_ts.append(ts)

        # Classify
        is_crypto = any(kw in title for kw in ['bitcoin','ethereum','btc','eth ','xrp','solana','doge','crypto'])
        is_blocked = any(kw in title for kw in ['iran','israel','ukraine','russia','trump','election','president'])
        is_ud_stock = any(kw in title for kw in ['up or down','opens up or down']) and any(kw in title for kw in ['spy','qqq','nvda','tsla','aapl','msft','meta','amzn','googl','nflx','pltr','russell','s&p','nasdaq','dow','hood','open','rbr','djia','rut','spx','ndx','nya','dax','ftse','nyse','nflx'])
        is_ladder = any(kw in title for kw in ['closes above','closes week','finish week','close at','finish above','above ___','what will']) and any(kw in title for kw in ['nvda','tsla','aapl','msft','meta','amzn','googl','nflx','pltr','open'])

        if is_crypto: crypto_buys.append(b)
        elif is_blocked: blocked_buys.append(b)
        elif is_ud_stock: ud_stock_buys.append(b)
        elif is_ladder: price_ladder_buys.append(b)
        else: other_buys.append(b)

    print(f"TOTAL BUYS: {len(buys)}")
    print(f"  UD stock binary : {len(ud_stock_buys)} buys")
    print(f"  Price ladder     : {len(price_ladder_buys)} buys")
    print(f"  Crypto           : {len(crypto_buys)} buys ({100*len(crypto_buys)/max(len(buys),1):.0f}%)")
    print(f"  Blocked          : {len(blocked_buys)} buys ({100*len(blocked_buys)/max(len(buys),1):.0f}%)")
    print(f"  Other            : {len(other_buys)} buys")

    if stakes:
        avg_s = sum(stakes)/len(stakes)
        avg_e = sum(entries)/len(entries)
        print(f"  avg_stake: ${avg_s:.2f}  avg_entry: {avg_e:.3f}")

    # Age
    if buy_ts:
        first_ts = min(buy_ts)
        last_ts = max(buy_ts)
        age_d = (NOW - first_ts) / 86400
        days_since_last = (NOW - last_ts) / 3600
        print(f"  age: {age_d:.1f}d  last_buy: {days_since_last:.1f}h ago")

    # Cluster check
    if buy_ts:
        ts_counts = collections.Counter(buy_ts)
        clusters = sum(1 for cnt in ts_counts.values() if cnt > 1)
        max_cluster = max(ts_counts.values())
        print(f"  clusters: {clusters}  max_same_second: {max_cluster}")

    # Wins / losses from positions
    wins = [p for p in positions if p.get('redeemable')]
    losses = [p for p in positions if not p.get('redeemable') and float(str(p.get('curPrice') or 1)[:10] or 1) <= 0.04]
    open_pos = [p for p in positions if not p.get('redeemable') and float(str(p.get('curPrice') or 0.5)[:10] or 0.5) > 0.04]
    n_wins, n_losses = len(wins), len(losses)
    n_resolved = n_wins + n_losses
    wr = n_wins / n_resolved if n_resolved else 0
    print(f"  POSITIONS: {n_wins}W/{n_losses}L ({wr:.1%} WR, {n_resolved} resolved) | {len(open_pos)} open")

    # What UD stock markets do they trade?
    ud_titles = collections.Counter()
    for b in ud_stock_buys:
        t = (b.get('title') or '').split('?')[0][:60]
        ud_titles[t] += 1
    print(f"  TOP UD-STOCK MARKETS:")
    for t, cnt in ud_titles.most_common(8):
        print(f"    [{cnt:2d}x] {t}")

    # Price ladder markets
    ladder_titles = collections.Counter()
    for b in price_ladder_buys:
        t = (b.get('title') or '').split('?')[0][:60]
        ladder_titles[t] += 1
    if ladder_titles:
        print(f"  TOP PRICE-LADDER MARKETS:")
        for t, cnt in ladder_titles.most_common(5):
            print(f"    [{cnt:2d}x] {t}")

    # Open positions analysis
    if open_pos:
        hold_prices = [float(str(p.get('curPrice') or 0.5)[:10] or 0.5) for p in open_pos]
        avg_hold = sum(hold_prices) / len(hold_prices)
        print(f"  OPEN {len(open_pos)} positions: avg_curPrice={avg_hold:.3f}")
        for p in open_pos[:3]:
            title = (p.get('title') or p.get('market') or '')[:55]
            cp = p.get('curPrice')
            sz = p.get('size')
            print(f"    curP={cp} sz={sz} | {title}")

    time.sleep(0.5)

print("\nDone.")
