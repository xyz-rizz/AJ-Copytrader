#!/usr/bin/env python3
"""
poly_discovery_v3.py — Open-minded multi-category copytrade discovery engine.

Philosophy: Real edge = real WR + real depth + real stake + real flow + copyable behaviour.
NOT WR alone. Covers SPX/NDX UD, stock UD, weather, finance, sports, other.

Key fixes vs all prior scripts:
1. No leaderboard dependency — tries 4 windows, works without any of them
2. 8 market categories mined (not just sports tags)
3. Sell-ratio is a HARD FILTER, not just a scoring penalty
   - Exception: in-game CLOB exits at >=0.97 are NOT flipping
4. Dollar flow ($/7d) as primary flow signal, not just trade count
5. Sports bias removed from copyability scoring
6. 120h staleness window (covers weekends for SPX specialists)
7. Open-book quality scored (blocked/crypto open positions = penalty)
8. Composite score: EDGE + FLOW - COPYABILITY_PENALTIES

v3.0  2026-03-13
"""
import urllib.request, json, time, datetime, collections, sys

# ── Hard filter thresholds ────────────────────────────────────────────────────
HARD_MIN_AGE_DAYS    = 7       # wallet must have been active for >= 7 days
HARD_MIN_RESOLVED    = 10      # minimum resolved positions
HARD_MIN_STAKE       = 5.0     # minimum avg stake USDC
HARD_MAX_CLUSTERS    = 12      # max same-second cluster pairs
HARD_MAX_CRYPTO_PCT  = 0.40    # crypto buys fraction
HARD_MAX_SELL_RATIO  = 0.35    # sells/buys — above = flipper (unless CLOB exits)
HARD_MIN_WR          = 0.80    # minimum win rate

# Soft filter thresholds (show but flag)
SOFT_MAX_ENTRY_PRICE = 0.86    # avg entry above this = very late bettors
SOFT_MAX_STALENESS_H = 120     # last buy more than 5 days ago = stale
SOFT_MAX_OPEN_DIRTY  = 3       # open positions in crypto/blocked categories

# ── Known active roster (skip these) ──────────────────────────────────────────
ACTIVE_ROSTER = {
    '0xa83be3f6a49604556f45089799f2b2096e71def4',  # Signal47-Bets
    '0xf27e335d2e78a207e802879f72870449836bd69d',  # Immense-Gokart
    '0xe85d6567a750b7b15fcb51c01a7c6230f63095d8',  # Triangular-Box
    '0x146703a8a73ae1dff0f84ba44c45d878858a4372',  # Unwieldy-Forage (also primary wallet)
    '0x77f623734a71c023f9df91011189eaeef891dbd1',  # bigwhale1337
    '0xaeab8222e044ab64b7253a3c10c16ba75096a2ed',  # NBAEdge-aeab
    '0xf23ca65324b789016acaffb6c2dccae48657555d',  # SoccerSharp-f23c
    '0xdd57cbe710edcb13a0e315003ec68c00c18e530f',  # Sport-dd57
}

BLACKLIST = {
    '0x0caacf3919c50a4d59c784f7496116a809fdb2bd',  # false gem (curPrice=0 bug)
    '0x703200e7df059638f4dc338e5e11ab2c7e8d1cc9',  # 7.8%WR
    '0x4b916c5ad935c58652dc1d5eb234a1f789ceb1fb',  # gem68 clone
    '0xafaf83a457ceb6d6778839f67038bd103708572d',  # weather multi-leg flipper
    '0x503f8098201ff4c9d5ec1f325b71a2f36a5fec57',  # XRP UD bot
    '0xccbd4bbcc445e7f4b98abf3061aa2b9e0130f1b7',  # NBA Whale 87 clusters
    '0x3f5ea0a8053e81ce2f59814118869322c35fe7db',  # piggyery 137 clusters
    '0x14ac84b66a27fc30e56ed620ebfa61cd8105cb21',  # BrokeMaxxing 158 clusters
    '0xdc16718af9f04590b38a8e8aa32dedcd034740a5',  # ELESTUDIO 193/d flipper
    '0x71971342cb4c2555f60366ac62abdcdd1a1d14c8',  # RawrRawr 1W/18L
    '0x65b6662c2cb28e3018cbb6a4983c5b83b2842108',  # CS2-LoL-Sharp 0W/5L
    '0xc2c1a8c92e4c6dcb6a8c90a3b0c7d3f9e2a5b1d4',  # 0%WR 0W/32L
    '0x18fef6681893aba51c01fac570a245a5844da4a0',  # 0%WR 0W/32L
    # Benched traders
    '0x40344cc4ba1a39648399b2d97d0d31c27122f52c',  # SPXOpens (Trump speech bettor)
    '0xa2ed440b6e3b9738a547c5a20f79616b63828808',  # InfoEdge (52% flipper)
    '0xbb63e47263321b67d7535f3909f2ec3c10a0bea4',  # gem62 benched
    '0xf21b5380ac186a254422e046a97b0e80c8a8894e',  # gem61 benched
    '0x9c886f69a9e2e5dfcf53f5ef6058925865f16871',  # NBA-9c88 benched
    '0xb2a48372404e6a0bfb6c2f23d715d3acc5a8cf8a',  # chenpengzao (order splitter)
    '0x898ebb087c7768ed4d47462f85856269dd8cd82c',  # UDWhale-cd82 (BTC scalper)
}

BLACKLIST_PREFIXES = {'0x8f80e8c2', '0x146703a8a73ae1'}  # prefix-match blacklist

def should_skip(wallet):
    w = wallet.lower()
    if w in ACTIVE_ROSTER or w in BLACKLIST:
        return True
    return any(w.startswith(p.lower()) for p in BLACKLIST_PREFIXES)

# ── Category classifier ────────────────────────────────────────────────────────
CRYPTO_KW  = ['bitcoin',' btc','ethereum','eth/','crypto','satoshi','defi','solana',
               ' sol/',' xrp','dogecoin','nft','web3','blockchain','token launch',
               'fdv ','gensyn','ostium','will btc','will eth','up or down - april',
               'up or down - march','up or down - may','btc price','eth price']
BLOCKED_KW = ['trump','tariff','epstein','ukraine',' war ','nuclear','nato',
               'election','democrat','republican',' senate','congress','president',
               'iran','russia','china tariff','trade war','musk tweet','musk post',
               'will elon','taiwan','xi jinping','ceasefire','immigration',
               'greenland','renan','bolsonaro','will trump say','how many times',
               'times will trump','will trump mention','will trump use']
WEATHER_KW = ['temperature','rainfall','humidity','precipitation','degrees celsius',
               'degrees fahrenheit','°c','°f','snowfall','highest temp','max temp',
               'daily high','will it rain','inches of rain','will it snow']
UD_KW      = ['opens up or down','up or down','close above','close below',
               'price above','price below','will the price','spx ','nasdaq',
               'nvda ','aapl ','msft ','tsla ','meta ','amzn ','googl ','ndx ',
               's&p ','russell 2','dow jones','nflx ','pltr ','palantir',
               ' qqq ',' spy ',' iwm ',' vix ','will apple','will nvidia',
               'will tesla','will microsoft','will amazon']
FINANCE_KW = ['gdp','inflation','cpi','fed rate','interest rate','fomc',
               'jobs report','nonfarm','unemployment','quarterly earnings',
               'ipo ','merger','bankruptcy','revenue','eps guidance']
SPORTS_KW  = ['nba ','nfl ','mlb ','nhl ','tennis','atp ','wta ','cs2',
               'counter-strike','dota','valorant','league of legends','soccer',
               'football match','premier league','bundesliga','ucl','champions league',
               'la liga','serie a','mls ','baseball','hockey',' lol ','esport',
               'wbc ','wnba','boxing','mma ','ufc ','super bowl','march madness',
               'ncaa ',' vs. ',' vs ','match winner','celtics','lakers',
               'warriors','knicks','bulls ','heat ','spurs','nuggets','thunder',
               'suns ','pistons','raptors','bucks ','sixers','nets ']

def classify(title):
    t = title.lower()
    if any(k in t for k in CRYPTO_KW):  return 'crypto'
    if any(k in t for k in BLOCKED_KW): return 'blocked'
    if any(k in t for k in WEATHER_KW): return 'weather'
    if any(k in t for k in UD_KW):      return 'ud_stock'
    if any(k in t for k in FINANCE_KW): return 'finance'
    if any(k in t for k in SPORTS_KW):  return 'sports'
    return 'other'

# ── HTTP ──────────────────────────────────────────────────────────────────────
def fetch(url, retries=3, timeout=15):
    for i in range(retries):
        try:
            req = urllib.request.Request(
                url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            if i < retries - 1: time.sleep(1.5)
        except Exception:
            if i < retries - 1: time.sleep(1.5)
    return None

# ── Phase 1: Mine wallet universe ──────────────────────────────────────────────
print("=" * 72)
print("POLY DISCOVERY v3 — MULTI-CATEGORY OPEN-MIND SCAN")
print(f"Started: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
print("=" * 72)

wallets = {}  # wallet_lower -> set of source tags

def add_wallet(w, source):
    if not w or len(w) < 40: return
    w = w.lower()
    if should_skip(w): return
    if w not in wallets: wallets[w] = set()
    wallets[w].add(source)

def mine_cids(cids, source_tag, limit_per_cid=200, delay=0.12):
    added = 0
    for cid in cids:
        trades = fetch(f"https://data-api.polymarket.com/trades?conditionId={cid}&limit={limit_per_cid}")
        if isinstance(trades, list):
            for t in trades:
                if t.get('side') == 'BUY':
                    add_wallet(t.get('proxyWallet', ''), source_tag)
                    added += 1
        time.sleep(delay)
    return added

# ── Source A: Leaderboard (try all windows, handle 404 gracefully) ─────────────
print("\n[A] Leaderboard (tries window=all/7d/1m/1w — handles 404)...")
lb_total = 0
for window in ['all', '7d', '1m', '1w']:
    if lb_total >= 80: break
    for offset in [0, 100, 200]:
        url = (f"https://data-api.polymarket.com/profiles/leaderboard"
               f"?window={window}&limit=100&offset={offset}&sortBy=profitAndLoss")
        d = fetch(url, timeout=10)
        if d is None:
            print(f"  LB {window}@{offset}: 404/error — skip")
            break
        items = d if isinstance(d, list) else d.get('data', [])
        if not items: break
        n = 0
        for item in items:
            w = (item.get('proxyWallet') or item.get('address') or
                 item.get('wallet') or '')
            pnl = float(item.get('pnl', item.get('profit',
                        item.get('profitAndLoss', 0))) or 0)
            if w and pnl > 50:
                add_wallet(w, f'lb_{window}')
                n += 1
                lb_total += 1
        print(f"  LB {window}@{offset}: {n} added (total={lb_total})")
        time.sleep(0.4)
print(f"  Leaderboard total: {lb_total} wallet signals")

# ── Source B: SPX / NDX / Stock Up-Down markets ───────────────────────────────
print("\n[B] SPX / NDX / Stock UD markets (finance+stocks tags, active+closed)...")
spx_cids = set()
UD_TITLE_KW = ['up or down', 'opens up or down', 'close above', 'close below',
                'spx', 'ndx', 's&p', 'nasdaq', 'nvda', 'aapl', 'msft', 'tsla',
                'amzn', 'googl', 'meta', 'nflx', 'pltr', 'palantir', 'qqq',
                'russell', 'dow jones', 'will apple close', 'will nvidia close',
                'will tesla close', 'will microsoft close', 'will amazon close']

for tag in ['finance', 'stocks']:
    for closed_val in ['false', 'true']:
        active_val = 'true' if closed_val == 'false' else 'false'
        for page in range(5):
            url = (f"https://gamma-api.polymarket.com/markets"
                   f"?active={active_val}&closed={closed_val}"
                   f"&limit=50&offset={page*50}&order=volume&ascending=false&tag_slug={tag}")
            d = fetch(url)
            items = d if isinstance(d, list) else (d.get('data', []) if isinstance(d, dict) else [])
            if not items: break
            for m in items:
                title = (m.get('question', '') or m.get('title', '') or '').lower()
                cid = m.get('conditionId')
                if cid and any(k in title for k in UD_TITLE_KW):
                    spx_cids.add(cid)
            time.sleep(0.2)

print(f"  Found {len(spx_cids)} SPX/stock-UD conditionIds")
n = mine_cids(list(spx_cids)[:150], 'spx_ud', limit_per_cid=300, delay=0.15)
print(f"  Mined {n} buy signals from SPX/stock-UD")

# ── Source C: Weather markets ──────────────────────────────────────────────────
print("\n[C] Weather markets...")
wx_cids = set()
for tag in ['weather', 'science', 'climate']:
    for closed_val in ['false', 'true']:
        active_val = 'true' if closed_val == 'false' else 'false'
        url = (f"https://gamma-api.polymarket.com/markets"
               f"?active={active_val}&closed={closed_val}"
               f"&limit=100&order=volume&ascending=false&tag_slug={tag}")
        d = fetch(url)
        items = d if isinstance(d, list) else (d.get('data', []) if isinstance(d, dict) else [])
        for m in items:
            title = (m.get('question', '') or m.get('title', '') or '').lower()
            cid = m.get('conditionId')
            if cid and any(k in title for k in WEATHER_KW):
                wx_cids.add(cid)
        time.sleep(0.2)

print(f"  Found {len(wx_cids)} weather conditionIds")
n = mine_cids(list(wx_cids)[:80], 'weather', limit_per_cid=200)
print(f"  Mined {n} buy signals from weather")

# ── Source D: Sports (multi-tag, active + recently closed) ────────────────────
print("\n[D] Sports — multi-tag active + closed...")
sport_cids = set()
for tag in ['nba', 'soccer', 'cs2', 'tennis', 'baseball', 'nhl', 'mma',
            'esports', 'dota', 'valorant', 'boxing', 'cricket', 'golf']:
    for closed_val in ['false', 'true']:
        active_val = 'true' if closed_val == 'false' else 'false'
        url = (f"https://gamma-api.polymarket.com/markets"
               f"?active={active_val}&closed={closed_val}"
               f"&limit=50&order=volume&ascending=false&tag_slug={tag}")
        d = fetch(url)
        items = d if isinstance(d, list) else (d.get('data', []) if isinstance(d, dict) else [])
        for m in items[:25]:
            cid = m.get('conditionId')
            if cid: sport_cids.add(cid)
        time.sleep(0.12)

print(f"  Found {len(sport_cids)} sports conditionIds")
n = mine_cids(list(sport_cids)[:200], 'sports', limit_per_cid=100, delay=0.1)
print(f"  Mined {n} buy signals from sports")

# ── Source E: Finance / economics / high-volume non-crypto ────────────────────
print("\n[E] Finance / economics / high-volume markets...")
fin_cids = set()
for tag in ['economics', 'business', 'politics', 'world']:
    url = (f"https://gamma-api.polymarket.com/markets"
           f"?limit=50&order=volume&ascending=false&tag_slug={tag}")
    d = fetch(url)
    items = d if isinstance(d, list) else (d.get('data', []) if isinstance(d, dict) else [])
    for m in items[:25]:
        title = (m.get('question', '') or m.get('title', '') or '').lower()
        cid = m.get('conditionId')
        # Skip crypto and hard-blocked content
        if cid and not any(k in title for k in CRYPTO_KW[:10]):
            fin_cids.add(cid)
    time.sleep(0.15)

# Top 50 overall volume (regardless of tag)
d = fetch("https://gamma-api.polymarket.com/markets?limit=50&order=volume&ascending=false")
items = d if isinstance(d, list) else (d.get('data', []) if isinstance(d, dict) else [])
for m in items[:40]:
    cid = m.get('conditionId')
    if cid: fin_cids.add(cid)

print(f"  Found {len(fin_cids)} finance/other conditionIds")
n = mine_cids(list(fin_cids)[:80], 'finance_hv', limit_per_cid=100, delay=0.1)
print(f"  Mined {n} buy signals from finance/high-volume")

# ── Source F: Monitor-list wallets (force-include) ────────────────────────────
print("\n[F] Monitor-list wallets (force-include)...")
MONITOR = [
    ('0xe3084ecc131468c9e12bffc99e024a5a4b2e4eb1', 'monitor_melonaire1'),
    ('0x0799daf859e32ec813845a58249172daee889452', 'monitor_0x0799'),
    ('0xaf32d3df3a83eed06b759e52da83088faf709868', 'monitor_UDHighFreq'),
]
for w, src in MONITOR:
    # Override skip check for monitor wallets
    wl = w.lower()
    if wl not in wallets: wallets[wl] = set()
    wallets[wl].add(src)
print(f"  Added {len(MONITOR)} monitor wallets")

print(f"\n[TOTAL WALLET UNIVERSE] {len(wallets)} unique novel wallets to profile")

# ── Phase 2: Full profile each wallet ─────────────────────────────────────────
print("\n" + "=" * 72)
print("PROFILING")
print("=" * 72)
now = time.time()

def profile_wallet(wallet):
    # Activity API
    activity = fetch(
        f"https://data-api.polymarket.com/activity?user={wallet}&limit=500")
    if not isinstance(activity, list) or not activity:
        return None

    buys  = [a for a in activity if a.get('type') == 'TRADE' and a.get('side') == 'BUY']
    sells = [a for a in activity if a.get('type') == 'TRADE' and a.get('side') == 'SELL']
    if len(buys) < 5:
        return None

    # Timestamps
    ts_list = []
    for b in buys:
        ts = b.get('timestamp', 0) or 0
        try: ts = float(ts)
        except: continue
        if ts > 4e12: ts /= 1000
        if ts > 1e9: ts_list.append(ts)
    if not ts_list: return None

    age_days    = (now - min(ts_list)) / 86400
    last_buy_h  = (now - max(ts_list)) / 3600
    buys_24h    = sum(1 for t in ts_list if now - t < 86400)
    buys_72h    = sum(1 for t in ts_list if now - t < 259200)
    buys_7d     = sum(1 for t in ts_list if now - t < 604800)

    # Stake calculation (try usdcSize first, then size*price)
    stakes = []
    ts_stake_pairs = []
    for b, ts in zip(buys, ts_list):
        try:
            usdc = float(b.get('usdcSize') or 0)
            if usdc > 0:
                stakes.append(usdc)
                ts_stake_pairs.append((ts, usdc))
            else:
                sz = float(b.get('size') or 0)
                pr = float(b.get('price') or b.get('avgPrice') or 0)
                if sz > 0 and pr > 0:
                    stakes.append(sz * pr)
                    ts_stake_pairs.append((ts, sz * pr))
        except: pass

    if not stakes: return None
    avg_stake = sum(stakes) / len(stakes)

    # Dollar flow last 7d
    dollar_flow_7d = sum(s for ts, s in ts_stake_pairs if now - ts < 604800)

    # Entry prices
    entries = []
    for b in buys:
        try:
            e = float(b.get('price') or b.get('avgPrice') or 0)
            if 0.02 < e < 0.98: entries.append(e)
        except: pass
    avg_entry = sum(entries) / len(entries) if entries else 0.5

    # Sell ratio & CLOB-exit detection
    sell_ratio = len(sells) / len(buys) if buys else 0
    sell_prices = []
    for s in sells:
        try:
            p = float(s.get('price') or s.get('avgPrice') or 0)
            if p > 0: sell_prices.append(p)
        except: pass
    # High-exit = sold at 0.97+ (in-game CLOB exits, NOT flipping losers)
    high_exit_count = sum(1 for p in sell_prices if p >= 0.97)
    high_exit_pct   = high_exit_count / len(sell_prices) if sell_prices else 0
    # True flipper = high sell ratio AND not dominated by near-certainty exits
    flipper = sell_ratio > HARD_MAX_SELL_RATIO and high_exit_pct < 0.70

    # Cluster detection (same-second buys)
    sec_counts = collections.Counter(int(t) for t in ts_list)
    clusters   = sum(1 for v in sec_counts.values() if v >= 2)

    # Category breakdown
    cats = collections.Counter()
    for b in buys:
        title = b.get('title', '') or b.get('market', '') or ''
        if isinstance(title, dict): title = title.get('question', '')
        cats[classify(str(title))] += 1

    total_b     = len(buys)
    crypto_pct  = cats['crypto']  / total_b
    blocked_pct = cats['blocked'] / total_b
    sports_pct  = cats['sports']  / total_b
    weather_pct = cats['weather'] / total_b
    ud_pct      = cats['ud_stock']/ total_b
    finance_pct = cats['finance'] / total_b
    other_pct   = cats['other']   / total_b

    # Dominant non-blocked category
    dom = max([('sports', sports_pct), ('ud_stock', ud_pct),
               ('weather', weather_pct), ('finance', finance_pct),
               ('other', other_pct)], key=lambda x: x[1])
    dom_cat = dom[0]

    # Positions (WR)
    pos_data = fetch(
        f"https://data-api.polymarket.com/positions?user={wallet}&sizeThreshold=0.001&limit=500")
    if not isinstance(pos_data, list): pos_data = []

    wins = losses = open_pos = open_blocked = 0
    for p in pos_data:
        try: cp = float(p.get('curPrice') or 0)
        except: cp = 0.5
        redeemable = p.get('redeemable', False)
        title_p = p.get('title', '') or p.get('market', '') or ''
        cat_p = classify(str(title_p))

        if redeemable:
            wins += 1
        elif cp <= 0.04:
            losses += 1
        else:
            open_pos += 1
            if cat_p in ('crypto', 'blocked'):
                open_blocked += 1

    resolved = wins + losses
    wr = wins / resolved if resolved > 0 else 0

    # Recent titles for display
    recent_buys = sorted(buys, key=lambda x: -(x.get('timestamp', 0) or 0))[:6]
    recent_titles = [b.get('title', '')[:60] for b in recent_buys]

    return {
        'wallet':         wallet,
        'age_days':       round(age_days, 1),
        'n_buys':         len(buys),
        'n_sells':        len(sells),
        'sell_ratio':     round(sell_ratio, 3),
        'flipper':        flipper,
        'high_exit_pct':  round(high_exit_pct, 2),
        'avg_stake':      round(avg_stake, 1),
        'avg_entry':      round(avg_entry, 3),
        'dollar_flow_7d': round(dollar_flow_7d, 1),
        'buys_24h':       buys_24h,
        'buys_72h':       buys_72h,
        'buys_7d':        buys_7d,
        'last_buy_h':     round(last_buy_h, 1),
        'clusters':       clusters,
        'wins':           wins,
        'losses':         losses,
        'open':           open_pos,
        'resolved':       resolved,
        'open_blocked':   open_blocked,
        'wr':             round(wr, 4),
        'crypto_pct':     round(crypto_pct, 3),
        'blocked_pct':    round(blocked_pct, 3),
        'sports_pct':     round(sports_pct, 3),
        'weather_pct':    round(weather_pct, 3),
        'ud_pct':         round(ud_pct, 3),
        'finance_pct':    round(finance_pct, 3),
        'other_pct':      round(other_pct, 3),
        'dom_cat':        dom_cat,
        'recent_titles':  recent_titles,
    }

profiles      = []
reject_counts = collections.Counter()
wallet_list   = list(wallets.items())

print(f"Profiling {len(wallet_list)} wallets...")
for i, (wallet, sources) in enumerate(wallet_list):
    if i % 30 == 0:
        print(f"  [{i}/{len(wallet_list)}] profiled={len(profiles)} "
              f"| {datetime.datetime.utcnow().strftime('%H:%M:%S')}")
        sys.stdout.flush()

    p = profile_wallet(wallet)
    if p is None:
        reject_counts['no_data'] += 1
        time.sleep(0.05)
        continue

    p['sources'] = sorted(sources)

    # ── Hard filters ──────────────────────────────────────────────────────
    hard_issues = []
    if p['age_days']    < HARD_MIN_AGE_DAYS:    hard_issues.append(f"young({p['age_days']:.0f}d)")
    if p['resolved']    < HARD_MIN_RESOLVED:    hard_issues.append(f"thin({p['resolved']}r)")
    if p['avg_stake']   < HARD_MIN_STAKE:       hard_issues.append(f"micro(${p['avg_stake']:.1f})")
    if p['clusters']    > HARD_MAX_CLUSTERS:    hard_issues.append(f"clusters({p['clusters']})")
    if p['crypto_pct']  > HARD_MAX_CRYPTO_PCT:  hard_issues.append(f"crypto({p['crypto_pct']:.0%})")
    if p['flipper']:                            hard_issues.append(f"flipper({p['sell_ratio']:.0%})")
    if p['wr']          < HARD_MIN_WR:          hard_issues.append(f"wr({p['wr']:.0%})")

    for iss in hard_issues:
        reject_counts[iss.split('(')[0]] += 1

    p['hard_issues']   = hard_issues
    p['_passes_hard']  = (len(hard_issues) == 0)

    # ── Soft filters ──────────────────────────────────────────────────────
    soft_issues = []
    if p['avg_entry']   > SOFT_MAX_ENTRY_PRICE:  soft_issues.append(f"entry({p['avg_entry']:.3f})")
    if p['last_buy_h']  > SOFT_MAX_STALENESS_H:  soft_issues.append(f"stale({p['last_buy_h']:.0f}h)")
    if p['open_blocked'] > SOFT_MAX_OPEN_DIRTY:  soft_issues.append(f"dirty_book({p['open_blocked']})")
    p['soft_issues'] = soft_issues

    # ── Composite score ────────────────────────────────────────────────────
    # EDGE (max 55)
    wr_pts = (25 if p['wr'] >= 0.98 else 20 if p['wr'] >= 0.95 else
              15 if p['wr'] >= 0.90 else 10 if p['wr'] >= 0.85 else 5)
    dep_pts = (15 if p['resolved'] >= 80 else 10 if p['resolved'] >= 40 else
               7  if p['resolved'] >= 20 else 4)
    stk_pts = (15 if p['avg_stake'] >= 50 else 10 if p['avg_stake'] >= 20 else
               6  if p['avg_stake'] >= 10 else 3)
    edge_score = wr_pts + dep_pts + stk_pts

    # FLOW (max 30)
    fl_vol = (20 if p['dollar_flow_7d'] >= 500 else 15 if p['dollar_flow_7d'] >= 200 else
              10 if p['dollar_flow_7d'] >= 100 else 6  if p['dollar_flow_7d'] >= 50  else
              3  if p['dollar_flow_7d'] >= 20  else 0)
    fl_ct  = (10 if p['buys_7d'] >= 10 else 6 if p['buys_7d'] >= 5 else
              3  if p['buys_7d'] >= 2  else 0)
    flow_score = fl_vol + fl_ct

    # COPYABILITY penalties (max -40)
    copy_pen = 0
    # Real flipper (not CLOB-exit trader)
    if p['sell_ratio'] > 0.25 and p['high_exit_pct'] < 0.70:
        copy_pen -= 15
    if p['clusters']    > 5:    copy_pen -= 10
    if p['blocked_pct'] > 0.20: copy_pen -= 10
    if p['open_blocked'] > 2:   copy_pen -= 5
    if p['crypto_pct']  > 0.15: copy_pen -= 5

    p['score_edge']     = edge_score
    p['score_flow']     = flow_score
    p['score_copy_pen'] = copy_pen
    p['score_total']    = edge_score + flow_score + copy_pen

    profiles.append(p)
    time.sleep(0.10)

# ── Phase 3: Output ────────────────────────────────────────────────────────────
print("\n" + "=" * 72)
print("RESULTS")
print("=" * 72)
print(f"Profiled: {len(profiles)} | Reject breakdown: {dict(reject_counts)}")

viable    = [p for p in profiles if p['_passes_hard'] and not p['soft_issues']]
soft_miss = [p for p in profiles if p['_passes_hard'] and p['soft_issues']]

viable.sort(key=lambda x: -x['score_total'])
soft_miss.sort(key=lambda x: -x['score_total'])

print(f"\n{'─'*72}")
print(f"VIABLE — passes ALL hard+soft filters: {len(viable)}")
print(f"{'─'*72}")
for p in viable:
    print(f"\n[SCORE={p['score_total']}  E={p['score_edge']} F={p['score_flow']} "
          f"C={p['score_copy_pen']}]  dom={p['dom_cat']}")
    print(f"  {p['wallet']}")
    print(f"  WR={p['wr']:.1%}({p['wins']}W/{p['losses']}L) res={p['resolved']} "
          f"age={p['age_days']:.0f}d")
    print(f"  stake=${p['avg_stake']} entry={p['avg_entry']} "
          f"sell={p['sell_ratio']:.0%}(hi_exit={p['high_exit_pct']:.0%}) "
          f"clust={p['clusters']}")
    print(f"  flow_7d=${p['dollar_flow_7d']} buys_7d={p['buys_7d']} "
          f"b24h={p['buys_24h']} last={p['last_buy_h']:.0f}h")
    print(f"  cat: spt={p['sports_pct']:.0%} ud={p['ud_pct']:.0%} "
          f"wx={p['weather_pct']:.0%} fin={p['finance_pct']:.0%} "
          f"oth={p['other_pct']:.0%} blk={p['blocked_pct']:.0%} "
          f"crypto={p['crypto_pct']:.0%}")
    print(f"  open_dirty={p['open_blocked']} sources={p['sources']}")
    print(f"  recent: {p['recent_titles'][:3]}")

print(f"\n{'─'*72}")
print(f"SOFT-MISS — passes hard, fails soft: {len(soft_miss)}")
print(f"{'─'*72}")
for p in soft_miss[:20]:
    print(f"  [{p['score_total']}] {p['wallet'][:22]}  "
          f"WR={p['wr']:.0%}({p['wins']}W/{p['losses']}L) "
          f"res={p['resolved']} stake=${p['avg_stake']} "
          f"flow7d=${p['dollar_flow_7d']} last={p['last_buy_h']:.0f}h "
          f"dom={p['dom_cat']} | soft={p['soft_issues']}")
    print(f"    {p['recent_titles'][:2]}")

print(f"\n{'─'*72}")
print(f"REJECT COUNTS: {dict(reject_counts)}")
print(f"{'─'*72}")

# Save
out = {
    'run_at':          datetime.datetime.utcnow().isoformat() + 'Z',
    'n_wallets_mined': len(wallets),
    'n_profiles':      len(profiles),
    'reject_counts':   dict(reject_counts),
    'viable':          viable,
    'soft_miss':       soft_miss[:30],
}
with open('/home/ubuntu/copytrade/discovery_v3_results.json', 'w') as f:
    json.dump(out, f, indent=2)
print(f"\nSaved → /home/ubuntu/copytrade/discovery_v3_results.json")
print("DONE.")
