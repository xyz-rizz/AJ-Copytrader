#!/usr/bin/env python3
"""
Deep Probe v1.0 — Comprehensive evaluation of 4 top discovery candidates.
Checks: recent activity (24h/72h), open book quality, sell-price breakdown,
entry-price distribution, market category detail, clone risk vs active roster.
"""
import json, urllib.request, time, re, collections
from datetime import datetime, timezone

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
NOW = int(time.time())

def fetch(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read())
        except Exception as e:
            if i == retries-1:
                return []
            time.sleep(1.5)

# ── Candidates to probe ───────────────────────────────────────────────────────
CANDIDATES = [
    {'name': '0x3ad-Sports',  'wallet': '0x3ad91bd36f4fb04b907eddfeeaa85ac95fd53cb4'},
    {'name': '0x233-Mixed',   'wallet': '0x233d939faca6d417b6490c1dad00de2dc7e0f8c8'},
    {'name': '0x65f-Weather', 'wallet': '0x65f93c0f054db935ed6a254c0ce0e9b3ca624425'},
    {'name': '0xcbc-Sports',  'wallet': '0xcbcd9c1223a0125d6cfc16fee86aaec47f733218'},
]

# ── Active roster — check clone risk (recent 48h buys) ───────────────────────
ROSTER = {
    'Signal47':   '0xa83be3f6a49604556f45089799f2b2096e71def4',
    'Immense':    '0xf27e335d2e78a207e802879f72870449836bd69d',
    'Triangular': '0xe85d6567a750b7b15fcb51c01a7c6230f63095d8',
    'Unwieldy':   '0x146703a8a73ae1dff0f84ba44c45d878858a4372',
    'bigwhale':   '0x77f623734a71c023f9df91011189eaeef891dbd1',
    'NBAEdge':    '0xaeab8222e0caee3e949fed38de2b9d31e22c41a4',
    'SoccerSharp':'0xf23ca65397ee8060ddd8e4a2b5c0f1b8f1dc54c0',
    'Sport-dd57': '0xdd57cbe710a86b88e54b1898ccc6c88bde9a8f55',
}

def classify_title(title):
    tl = title.lower()
    if any(k in tl for k in ['bitcoin','btc','eth','solana','crypto','xrp','price above','price below',
                               'will btc','will eth','pump','dump','defi','nft','blockchain']):
        return 'CRYPTO'
    if any(k in tl for k in ['up or down','opens up or down','closes above','closes below',
                               's&p','spx','nasdaq','ndx','russell','rut','dow','djia',
                               'nvda','tsla','aapl','msft','meta','amzn','googl','nflx',
                               'pltr','spy','qqq','stock','etf']):
        return 'SPX/STOCK-UD'
    if any(k in tl for k in ['temperature','hurricane','storm','rainfall','snow','flood',
                               'weather','celsius','fahrenheit','cyclone','tornado','drought',
                               'will it rain','precipitation']):
        return 'WEATHER'
    if any(k in tl for k in ['nba','nfl','nhl','mlb','ufc','mma','tennis','atp','wta',
                               'football','soccer','epl','premier league','la liga','bundesliga',
                               'champions league','basketball','baseball','hockey','spread',
                               'o/u','moneyline','match result','cs2','counter-strike','csgo',
                               'dota','league of legends','valorant','esport','boxing','cricket',
                               'golf','super bowl','playoffs','championship','ncaa','college']):
        return 'SPORTS'
    if any(k in tl for k in ['trump','biden','president','election','congress','senate',
                               'fed rate','interest rate','gdp','inflation','cpi','recession',
                               'iran','ceasefire','war','nato','tariff','trade deal',
                               'will the fed','federal reserve']):
        return 'POLITICS/MACRO'
    return 'OTHER'

def probe_wallet(name, wallet):
    print(f"\n{'='*70}")
    print(f"  DEEP PROBE: {name}")
    print(f"  wallet: {wallet}")
    print(f"{'='*70}")

    # ── 1. Activity (last 500 trades) ────────────────────────────────────────
    act = fetch(f'https://data-api.polymarket.com/activity?user={wallet}&limit=500')
    if not act:
        act = []

    buys  = [a for a in act if isinstance(a, dict) and a.get('side') == 'BUY']
    sells = [a for a in act if isinstance(a, dict) and a.get('side') == 'SELL']

    CUT_24H = NOW - 86400
    CUT_72H = NOW - 3*86400
    CUT_7D  = NOW - 7*86400

    def get_ts(d):
        ts = int(d.get('timestamp') or d.get('updatedAt') or 0)
        if ts > 4e12: ts //= 1000
        return ts

    buys_24h = [b for b in buys if get_ts(b) >= CUT_24H]
    buys_72h = [b for b in buys if get_ts(b) >= CUT_72H]
    buys_7d  = [b for b in buys if get_ts(b) >= CUT_7D]

    print(f"\n  ACTIVITY: total={len(act)} buys={len(buys)} sells={len(sells)}")
    print(f"  Recency: buys_24h={len(buys_24h)} buys_72h={len(buys_72h)} buys_7d={len(buys_7d)}")

    # Buy entry price distribution
    buy_prices = [float(b.get('price') or 0) for b in buys if b.get('price')]
    buy_prices = [p for p in buy_prices if 0.02 < p < 0.99]
    if buy_prices:
        buckets = {'≤0.50':0, '0.51-0.60':0, '0.61-0.70':0, '0.71-0.80':0,
                   '0.81-0.85':0, '0.86-0.90':0, '0.91-0.95':0, '>0.95':0}
        for p in buy_prices:
            if p <= 0.50:   buckets['≤0.50'] += 1
            elif p <= 0.60: buckets['0.51-0.60'] += 1
            elif p <= 0.70: buckets['0.61-0.70'] += 1
            elif p <= 0.80: buckets['0.71-0.80'] += 1
            elif p <= 0.85: buckets['0.81-0.85'] += 1
            elif p <= 0.90: buckets['0.86-0.90'] += 1
            elif p <= 0.95: buckets['0.91-0.95'] += 1
            else:            buckets['>0.95'] += 1
        pct_copyable = sum(v for k,v in buckets.items() if k not in ['0.86-0.90','0.91-0.95','>0.95']) / len(buy_prices) * 100
        avg_entry = sum(buy_prices)/len(buy_prices)
        print(f"\n  ENTRY PRICE DISTRIBUTION (n={len(buy_prices)}, avg={avg_entry:.3f}, copyable≤0.85={pct_copyable:.0f}%):")
        for k, v in buckets.items():
            bar = '█' * (v * 30 // max(max(buckets.values()),1))
            flag = '  ← BOT CEILING' if k in ['0.86-0.90','0.91-0.95','>0.95'] else ''
            print(f"    {k:12s}: {v:4d} {bar}{flag}")

    # Sell price distribution (flip risk analysis)
    sell_prices = [float(s.get('price') or 0) for s in sells if s.get('price')]
    sell_prices = [p for p in sell_prices if p > 0]
    if sell_prices:
        high_exits = sum(1 for p in sell_prices if p >= 0.95)
        mid_exits  = sum(1 for p in sell_prices if 0.50 <= p < 0.95)
        low_exits  = sum(1 for p in sell_prices if p < 0.50)
        print(f"\n  SELL PRICE BREAKDOWN (n={len(sell_prices)}, sell_ratio={len(sells)/(len(buys)+1):.0%}):")
        print(f"    high exits ≥0.95 (CLOB-exit/wins): {high_exits} ({high_exits/len(sell_prices)*100:.0f}%)")
        print(f"    mid  exits 0.50-0.95 (suspicious):  {mid_exits} ({mid_exits/len(sell_prices)*100:.0f}%)")
        print(f"    low  exits <0.50 (dump/flipper):    {low_exits} ({low_exits/len(sell_prices)*100:.0f}%)")
        # Show mid/low exits with titles
        mid_low = [s for s in sells if float(s.get('price') or 0) < 0.95]
        if mid_low:
            print(f"    Mid/low exits (flip suspects):")
            for s in sorted(mid_low, key=lambda x: float(x.get('price') or 0))[:10]:
                p = float(s.get('price') or 0)
                title = (s.get('title') or s.get('market') or 'unknown')[:60]
                ts_diff = (NOW - get_ts(s)) / 3600
                print(f"      price={p:.3f} | {ts_diff:.0f}h ago | {title}")

    # ── 2. Category breakdown from recent buys ───────────────────────────────
    cat_counts = collections.Counter()
    recent_titles = []
    for b in buys[:200]:
        title = b.get('title') or b.get('market') or ''
        cat = classify_title(title)
        cat_counts[cat] += 1
        if len(recent_titles) < 30:
            recent_titles.append((get_ts(b), title, float(b.get('price') or 0),
                                   float(b.get('size') or 0) * float(b.get('price') or 0)))

    total_cat = sum(cat_counts.values())
    print(f"\n  CATEGORY BREAKDOWN (last 200 buys):")
    for cat, cnt in cat_counts.most_common():
        print(f"    {cat:20s}: {cnt:4d} ({cnt/total_cat*100:.0f}%)")

    # Recent 24h/72h activity titles
    print(f"\n  RECENT 24H BUYS ({len(buys_24h)}):")
    for b in sorted(buys_24h, key=get_ts, reverse=True)[:10]:
        p = float(b.get('price') or 0)
        sz = float(b.get('size') or 0)
        stake = sz * p
        title = (b.get('title') or b.get('market') or 'unknown')[:65]
        print(f"    entry={p:.3f} stake=${stake:.2f} | {title}")

    if not buys_24h:
        print(f"\n  RECENT 72H BUYS ({len(buys_72h)}):")
        for b in sorted(buys_72h, key=get_ts, reverse=True)[:10]:
            p = float(b.get('price') or 0)
            sz = float(b.get('size') or 0)
            stake = sz * p
            title = (b.get('title') or b.get('market') or 'unknown')[:65]
            print(f"    entry={p:.3f} stake=${stake:.2f} | {title}")

    # ── 3. Open positions ────────────────────────────────────────────────────
    time.sleep(0.3)
    pos = fetch(f'https://data-api.polymarket.com/positions?user={wallet}&sizeThreshold=0.001')
    if not pos: pos = []

    open_pos = [p for p in pos if not p.get('redeemable') and
                float(str(p.get('curPrice') or '0.5')[:10] or 0.5) > 0.04]
    wins_pos  = [p for p in pos if p.get('redeemable')]
    loss_pos  = [p for p in pos if not p.get('redeemable') and
                 float(str(p.get('curPrice') or '1')[:10] or 1) <= 0.04]

    print(f"\n  POSITIONS: total={len(pos)} wins={len(wins_pos)} losses={len(loss_pos)} open={len(open_pos)}")

    # Classify open positions
    dirty_open = []
    clean_open = []
    for p in open_pos:
        title = (p.get('title') or p.get('market') or '')
        cat = classify_title(title)
        cp = float(str(p.get('curPrice') or '0.5')[:10] or 0.5)
        val = float(p.get('currentValue') or 0)
        if cat in ('CRYPTO', 'POLITICS/MACRO'):
            dirty_open.append((cat, cp, val, title))
        else:
            clean_open.append((cat, cp, val, title))

    print(f"  Open: clean={len(clean_open)} dirty={len(dirty_open)}")
    if dirty_open:
        print(f"  DIRTY OPEN POSITIONS:")
        for cat, cp, val, title in dirty_open[:10]:
            print(f"    [{cat}] price={cp:.3f} val=${val:.2f} | {title[:65]}")
    if clean_open:
        print(f"  Sample clean open:")
        for cat, cp, val, title in sorted(clean_open, key=lambda x: -x[2])[:8]:
            print(f"    [{cat}] price={cp:.3f} val=${val:.2f} | {title[:65]}")

    # ── 4. Clone risk vs active roster ───────────────────────────────────────
    time.sleep(0.3)
    # Get candidate's recent 72h market set
    cand_markets_72h = set()
    for b in buys_72h:
        title = (b.get('title') or b.get('market') or '').strip()
        if title:
            cand_markets_72h.add(title[:60])

    if cand_markets_72h:
        print(f"\n  CLONE RISK CHECK (candidate 72h markets vs roster):")
        for rname, rwallet in ROSTER.items():
            r_act = fetch(f'https://data-api.polymarket.com/activity?user={rwallet}&limit=100')
            r_buys_72h = [a for a in (r_act or [])
                          if isinstance(a, dict) and a.get('side') == 'BUY'
                          and get_ts(a) >= CUT_72H]
            r_markets = set((a.get('title') or a.get('market') or '')[:60] for a in r_buys_72h)
            overlap = cand_markets_72h & r_markets
            if overlap:
                print(f"    vs {rname}: {len(overlap)} overlap markets")
                for m in list(overlap)[:3]:
                    print(f"      >> {m}")
            time.sleep(0.2)
    else:
        print(f"\n  CLONE RISK: No 72h buys (inactive) — cannot check")

    # ── 5. Summary verdict ───────────────────────────────────────────────────
    print(f"\n  ── SUMMARY ──────────────────────────────────────────────────────────")
    print(f"  24h_active: {len(buys_24h)>0} | 72h_active: {len(buys_72h)>0}")
    if buy_prices:
        pct_above_ceiling = sum(1 for p in buy_prices if p > 0.85) / len(buy_prices) * 100
        print(f"  Entries above bot ceiling (>0.85): {pct_above_ceiling:.0f}% of trades")
        print(f"  Copyable trades (≤0.85): {100-pct_above_ceiling:.0f}%")
    print(f"  Dirty open positions: {len(dirty_open)}")
    print(f"  Total open positions: {len(open_pos)}")
    print()

    time.sleep(0.5)

# ── Pull roster recent markets for clone check (shared across all probes) ────
print("Running deep probe on 4 candidates...")
print(f"Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")

for cand in CANDIDATES:
    probe_wallet(cand['name'], cand['wallet'])
    time.sleep(0.5)

print("\n\nDone.")
