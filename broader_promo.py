#!/usr/bin/env python3
"""
broader_promo.py — Probationary discovery pass with relaxed thresholds.
Version: 1.0 | Date: 2026-03-10

Thresholds (probationary):
  age >= 7d | resolved >= 10 | avg_stake >= $5 | avg_entry <= 0.78
  clusters < 10 | blocked_pct < 35% | sports >= 25% | crypto < 30%
  min WR ≥ 60% (non-negotiable even at probationary)

Sources:
  1. FORCE_CHECK — monitor list + prior near-misses (full known addresses)
  2. Leaderboard 30d — top 300 by PnL (full addresses via API)
  3. Hot markets — wallets active in last 24h in recent sports markets
"""
import json, urllib.request, time, sys, math
from datetime import datetime, timezone
from collections import defaultdict

DATA_API  = "https://data-api.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"

# ── Probationary thresholds ─────────────────────────────────────────────────────
P_MIN_AGE      = 7
P_MIN_RESOLVED = 10
P_MIN_STAKE    = 5.0
P_MAX_ENTRY    = 0.78
P_MAX_CLUSTERS = 10
P_MAX_BLOCKED  = 0.35
P_MIN_WR       = 60.0    # hard floor — below this, reject
P_MIN_SPORTS   = 0.25
P_MAX_CRYPTO   = 0.30
P_MAX_FREQ     = 30.0    # buys/day — above this = scalper risk
P_RECENT_24H   = True    # require at least 1 buy in last 24h? (soft signal)

# ── Skip list ────────────────────────────────────────────────────────────────────
ALREADY_TRACKING = {
    "0xa83be3f6a49604556f45089799f2b2096e71def4",
    "0xf27e335d2e78a207e802879f72870449836bd69d",
    "0xe85d6567a750b7b15fcb51c01a7c6230f63095d8",
    "0x146703a8a73ae1dff0f84ba44c45d878858a4372",
    "0xbb63e47263321b67d7535f3909f2ec3c10a0bea4",
    "0xf21b5380ac186a254422e046a97b0e80c8a8894e",
    "0x9c886f69a9e2e5dfcf53f5ef6058925865f16871",
    "0x419be42e6a14a0a218fe8ff79d3e6bb83be95a49",
}
BLACKLIST = {
    "0x8f80e8c2a414f5acc0231f5b934045ab4e85b302",
    "0x71971342cb4c2555f60366ac62abdcdd1a1d14c8",
    "0x4042a8ef98b5abf2a1cf2423f8475c91ee150bda",
    "0x77f623734a71c023f9df91011189eaeef891dbd1",
    "0xbbef15091aee07f8310d7314761d3a3063749838",
    "0x69aee04532c679ecd4060d9e31af19d6af319f18",
    "0x4b916c5ad935c58652dc1d5eb234a1f789ceb1fb",
    "0x3f5ea0a8053e81ce2f59814118869322c35fe7db",
    "0x14ac84b66a27fc30e56ed620ebfa61cd8105cb21",
    "0xdc16718af9f04590b38a8e8aa32dedcd034740a5",
    "0xbb15969cb69d5b430d40870aabdf2a1d91820f02",
    "0x25a1a36e671aa52180be2e5ad498dc2013d9ddf8",
    "0xb5124dae83419944bb000ebe28607560de9144a5",
    "0x05b21f43e056cdf3f26ae5f28dc0238495e2a469",
    "0xc33a100b8362bc732e78cce28c99739f173b3da3",
    "0x0caacf3919c50a4d59c784f7496116a809fdb2bd",
    "0xccbd4bbcc445e7f4b98abf3061aa2b9e0130f1b7",
}
KNOWN_BAD = ALREADY_TRACKING | BLACKLIST

# ── Force-evaluate these specific wallets ────────────────────────────────────────
FORCE_CHECK = [
    # (wallet, label, source_note)
    ("0xb2a48372404e6a0bfb6c2f23d715d3acc5a8cf8a", "chenpengzao",    "monitor_93%WR"),
    ("0x0f5c37e3d248ed29e2f0a0913b2a3a0d8021cc27", "deep_scan_83.8",  "prior_near_miss"),
    ("0xe2c2ad73fe56a6f3786eac98a957753611f262e4", "dsfarwe",          "scout_wide2"),
]


SPORT_KWS = ['nba','nfl','nhl','mlb','ufc','tennis','football','soccer','epl',
             'basketball','baseball','hockey','spread','o/u','moneyline','match',
             ' vs ',' v ','playoff','cup','league','wbc','world series','super bowl',
             'ncaa','lol','valorant','cs2','dota','esport','overwatch','atp','wta',
             'f1','formula','cricket','rugby','golf','pga','mls','ligue','bundesliga']
CRYPTO_KWS = ['bitcoin','btc','eth ','ethereum','crypto','solana','price will',
              'pump','dump','token','nft','defi','matic','polygon']

def fetch_json(url, params=None, timeout=12):
    if params:
        qs = "&".join(f"{k}={urllib.request.quote(str(v),safe='')}" for k,v in params.items())
        url = f"{url}?{qs}"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception:
        return None

def get_activity(wallet, limit=500):
    d = fetch_json(f"{DATA_API}/activity", {"user": wallet, "limit": limit})
    return d if d and isinstance(d, list) else []

def get_positions(wallet, limit=500):
    d = fetch_json(f"{DATA_API}/positions", {"user": wallet, "limit": limit, "sizeThreshold": "0.01"})
    return d if d and isinstance(d, list) else []

def get_trades_for_market(cid, limit=200):
    d = fetch_json(f"{DATA_API}/trades", {"conditionId": cid, "limit": limit})
    return d if d and isinstance(d, list) else []

def safe_price(v, default=0.5):
    if v is None: return default
    try: return float(v)
    except: return default

def parse_ts(item):
    ts = float(item.get("timestamp", 0) or 0)
    return ts / 1000 if ts > 4e12 else ts

def get_buys(activity):
    return [a for a in activity
            if (a.get("type") == "TRADE" and a.get("side") == "BUY") or a.get("type") == "BUY"]

def classify_wl(positions):
    wins = losses = open_pos = 0
    for p in positions:
        cur_raw = p.get("curPrice") if p.get("curPrice") is not None else p.get("currentPrice")
        cur = safe_price(cur_raw, default=None)
        if cur is None: cur = 0.5
        redeemable = bool(p.get("redeemable", False))
        cur_val = float(p.get("currentValue") or 0)
        pnl = float(p.get("percentPnl") or 0)
        if redeemable and cur_val > 0: wins += 1
        elif redeemable and cur_val == 0 and pnl <= -50: losses += 1
        elif cur <= 0.04 and not redeemable: losses += 1
        elif cur > 0.04 and not redeemable: open_pos += 1
    return wins, losses, open_pos

def get_age_days(activity):
    timestamps = [parse_ts(a) for a in activity if parse_ts(a) > 0]
    if not timestamps: return 0.0
    return (datetime.now(timezone.utc).timestamp() - min(timestamps)) / 86400

def is_sports(item):
    t = (item.get("title") or item.get("market") or item.get("description") or "").lower()
    return any(k in t for k in SPORT_KWS)

def is_crypto(item):
    t = (item.get("title") or item.get("market") or item.get("description") or "").lower()
    return any(k in t for k in CRYPTO_KWS)

def get_sports_pct(activity):
    buys = get_buys(activity) or activity
    if not buys: return 0.0, 0.0
    now = datetime.now(timezone.utc).timestamp()
    cutoff_30d = now - 30*86400
    total = len(buys)
    s_life = sum(1 for b in buys if is_sports(b))
    c_life = sum(1 for b in buys if is_crypto(b))
    recent = [b for b in buys if parse_ts(b) >= cutoff_30d]
    s_30d_pct = sum(1 for b in recent if is_sports(b))/len(recent) if recent else s_life/total if total else 0
    sports_pct = max(s_life/total if total else 0, s_30d_pct)
    crypto_pct = c_life/total if total else 0
    return sports_pct, crypto_pct

def get_stake_freq_entry(activity, age_days):
    buys = get_buys(activity) or activity
    amounts = [float(b.get("usdcSize") or b.get("amount") or b.get("size") or 0) for b in buys]
    amounts = [a for a in amounts if a > 0]
    avg_stake = sum(amounts)/len(amounts) if amounts else 0.0
    now = datetime.now(timezone.utc).timestamp()
    recent = [b for b in buys if parse_ts(b) >= now - 30*86400]
    freq = len(recent)/30.0 if recent else len(buys)/max(age_days,1)
    prices = [float(b.get("price") or b.get("avgPrice") or 0) for b in buys]
    prices = [p for p in prices if 0.01 < p < 0.99]
    avg_entry = sum(prices)/len(prices) if prices else 0.0
    return avg_stake, freq, avg_entry

def detect_clusters(activity):
    buys = get_buys(activity) or activity
    ts_counts = defaultdict(int)
    for b in buys:
        ts = int(parse_ts(b))
        if ts > 0: ts_counts[ts] += 1
    return sum(1 for c in ts_counts.values() if c >= 3)

def get_blocked_pct(activity):
    buys = get_buys(activity) or activity
    if not buys: return 0.0
    return sum(1 for b in buys if float(b.get("price") or b.get("avgPrice") or 0) > 0.90) / len(buys)

def get_recent_24h(activity):
    now = datetime.now(timezone.utc).timestamp()
    buys = get_buys(activity) or activity
    return sum(1 for b in buys if parse_ts(b) >= now - 86400)

def get_hold_behavior(activity):
    """Returns hold_score: 1.0 = pure hold, 0.0 = pure flip. Checks sell ratio."""
    sells = [a for a in activity
             if (a.get("type") == "TRADE" and a.get("side") == "SELL") or a.get("type") == "SELL"]
    buys = get_buys(activity)
    if not buys: return 0.5
    sell_ratio = len(sells) / len(buys) if buys else 0
    return 1.0 - min(sell_ratio, 1.0)  # 1.0 = never sells early = hold


def score_candidate_broad(wallet, source, reject_stats):
    acts = get_activity(wallet, limit=500)
    if not acts:
        reject_stats["no_activity"] = reject_stats.get("no_activity", 0) + 1
        return None

    age_days = get_age_days(acts)
    if age_days < P_MIN_AGE:
        reject_stats["too_young"] = reject_stats.get("too_young", 0) + 1
        return None

    positions = get_positions(wallet)
    time.sleep(0.1)
    wins, losses, open_pos = classify_wl(positions)
    resolved = wins + losses

    if resolved < P_MIN_RESOLVED:
        reject_stats["few_resolved"] = reject_stats.get("few_resolved", 0) + 1
        return None

    wr = wins / resolved if resolved > 0 else 0.0
    if wr * 100 < P_MIN_WR:
        reject_stats["low_wr"] = reject_stats.get("low_wr", 0) + 1
        return None

    avg_stake, freq, avg_entry = get_stake_freq_entry(acts, age_days)
    if avg_stake < P_MIN_STAKE:
        reject_stats["micro_bettor"] = reject_stats.get("micro_bettor", 0) + 1
        return None

    if avg_entry > P_MAX_ENTRY:
        reject_stats["high_entry"] = reject_stats.get("high_entry", 0) + 1
        return None

    if freq > P_MAX_FREQ:
        reject_stats["scalper"] = reject_stats.get("scalper", 0) + 1
        return None

    sports_pct, crypto_pct = get_sports_pct(acts)
    if crypto_pct > P_MAX_CRYPTO:
        reject_stats["crypto"] = reject_stats.get("crypto", 0) + 1
        return None

    if sports_pct < P_MIN_SPORTS:
        reject_stats["non_sports"] = reject_stats.get("non_sports", 0) + 1
        return None

    clusters = detect_clusters(acts)
    if clusters >= P_MAX_CLUSTERS:
        reject_stats["bot_clusters"] = reject_stats.get("bot_clusters", 0) + 1
        return None

    blocked_pct = get_blocked_pct(acts)
    if blocked_pct > P_MAX_BLOCKED:
        reject_stats["blocked_book"] = reject_stats.get("blocked_book", 0) + 1
        return None

    recent_24h = get_recent_24h(acts)
    hold_score = get_hold_behavior(acts)
    age_bonus = min(age_days / 100.0, 2.0)
    edge_score = wr * 100.0 * math.log(resolved + 1) * (1 + age_bonus * 0.1)

    # Copyability score (0-100)
    copy_score = 100.0
    copy_score -= min(clusters * 5, 30)          # cluster penalty
    copy_score -= min(blocked_pct * 80, 25)      # blocked book penalty
    copy_score -= max(0, (freq - 5) * 2)         # high freq penalty (>5/d costs points)
    copy_score += min(hold_score * 20, 20)        # hold bonus
    copy_score = max(0, min(100, copy_score))

    buys = get_buys(acts)
    sport_names = []
    for b in buys[:30]:
        t = (b.get("title") or b.get("market") or "").lower()
        for kw in ['nba','mlb','nfl','nhl','cs2','wbc','ufc','tennis','soccer','football',
                   'basketball','dota','esport','lol','valorant']:
            if kw in t:
                sport_names.append(kw)
                break
    from collections import Counter
    top_sport = Counter(sport_names).most_common(1)
    top_sport_name = top_sport[0][0] if top_sport else "unknown"

    # Bucket classification
    if (wr*100 >= 80 and resolved >= 20 and avg_stake >= 15 and avg_entry <= 0.75
            and clusters <= 4 and blocked_pct <= 0.15 and age_days >= 21):
        bucket = "A_STRONG"
    elif (wr*100 >= 70 and resolved >= 12 and avg_stake >= 8 and avg_entry <= 0.78
            and clusters <= 6 and blocked_pct <= 0.25):
        bucket = "B_PROBATIONARY"
    else:
        bucket = "C_REJECT"

    return {
        "wallet":      wallet,
        "source":      source,
        "edge_score":  round(edge_score, 1),
        "copy_score":  round(copy_score, 1),
        "bucket":      bucket,
        "wr":          round(wr * 100, 1),
        "wins":        wins,
        "losses":      losses,
        "resolved":    resolved,
        "open":        open_pos,
        "age_days":    round(age_days, 1),
        "avg_stake":   round(avg_stake, 2),
        "freq":        round(freq, 2),
        "avg_entry":   round(avg_entry, 3),
        "sports_pct":  round(sports_pct, 3),
        "crypto_pct":  round(crypto_pct, 3),
        "clusters":    clusters,
        "blocked_pct": round(blocked_pct, 3),
        "hold_score":  round(hold_score, 2),
        "recent_24h":  recent_24h,
        "top_sport":   top_sport_name,
    }


def fetch_leaderboard_wallets(limit=300):
    """Fetch top-30d leaderboard wallets with FULL addresses."""
    print(f"\n[LEADERBOARD] Fetching top-{limit} 30d PnL wallets...")
    # Try v1 leaderboard endpoint
    data = fetch_json(f"{DATA_API}/v1/leaderboard", {"window": "30d", "limit": limit})
    if not data:
        data = fetch_json(f"{DATA_API}/leaderboard", {"window": "30d", "limit": limit})
    if not data:
        print("  WARN: leaderboard API unavailable")
        return []
    entries = data if isinstance(data, list) else data.get("data", data.get("results", []))
    wallets = []
    for e in entries:
        w = (e.get("proxyWallet") or e.get("wallet") or e.get("address") or "").lower()
        pnl = float(e.get("pnl") or e.get("profit") or 0)
        if len(w) == 42 and w not in KNOWN_BAD:
            wallets.append((w, pnl))
    print(f"  Got {len(wallets)} unique non-known wallets from leaderboard")
    return wallets

def fetch_hot_market_wallets():
    """Wallets active in last 24h from our active traders' current markets."""
    print("\n[HOT MARKETS] Scanning last 24h activity from active traders...")
    active_seeds = {
        "0xa83be3f6a49604556f45089799f2b2096e71def4": "Signal47",
        "0xf27e335d2e78a207e802879f72870449836bd69d": "Immense",
        "0xe85d6567a750b7b15fcb51c01a7c6230f63095d8": "Triangular",
        "0x146703a8a73ae1dff0f84ba44c45d878858a4372": "Unwieldy",
        "0xbb63e47263321b67d7535f3909f2ec3c10a0bea4": "gem62",
        "0xf21b5380ac186a254422e046a97b0e80c8a8894e": "gem61",
        "0x9c886f69a9e2e5dfcf53f5ef6058925865f16871": "NBA-9c88",
    }
    now = datetime.now(timezone.utc).timestamp()
    cutoff_24h = now - 86400
    wallets_found = {}
    total_markets = 0

    for seed, name in active_seeds.items():
        acts = get_activity(seed, limit=100)
        time.sleep(0.1)
        buys = get_buys(acts)
        # Get markets from last 7d (to have enough hot markets)
        recent_cids = []
        for b in buys:
            if parse_ts(b) >= now - 7*86400:
                cid = b.get("conditionId") or b.get("market")
                if cid and cid not in [c for c,_ in recent_cids]:
                    recent_cids.append((cid, parse_ts(b)))
            if len(recent_cids) >= 10:
                break

        for cid, ts in recent_cids[:5]:  # Top 5 most recent markets per seed
            trades = get_trades_for_market(cid, limit=300)
            time.sleep(0.1)
            for t in trades:
                t_ts = float(t.get("timestamp") or 0)
                if t_ts > 4e12: t_ts /= 1000
                w = (t.get("maker") or t.get("proxyWallet") or t.get("trader") or "").lower()
                if len(w) == 42 and w not in KNOWN_BAD and t_ts >= cutoff_24h:
                    wallets_found.setdefault(w, {"seeds": set(), "last_ts": 0})
                    wallets_found[w]["seeds"].add(name)
                    wallets_found[w]["last_ts"] = max(wallets_found[w]["last_ts"], t_ts)
            total_markets += 1

    # Also try gamma active sports markets
    for tag in ["nba", "mlb", "nhl", "soccer", "esports"]:
        mkt_data = fetch_json(f"{GAMMA_API}/markets",
                              {"closed": "false", "active": "true", "tag": tag,
                               "order": "volume", "ascending": "false", "limit": "10"})
        time.sleep(0.2)
        if not mkt_data: continue
        markets = mkt_data if isinstance(mkt_data, list) else mkt_data.get("markets", [])
        for m in markets[:3]:
            vol = float(m.get("volume") or 0)
            if vol < 3000: continue
            cid = m.get("conditionId") or m.get("id")
            if not cid: continue
            trades = get_trades_for_market(cid, limit=300)
            time.sleep(0.1)
            for t in trades:
                t_ts = float(t.get("timestamp") or 0)
                if t_ts > 4e12: t_ts /= 1000
                w = (t.get("maker") or t.get("proxyWallet") or t.get("trader") or "").lower()
                if len(w) == 42 and w not in KNOWN_BAD and t_ts >= cutoff_24h:
                    wallets_found.setdefault(w, {"seeds": set(), "last_ts": 0})
                    wallets_found[w]["seeds"].add(f"gamma:{tag}")
                    wallets_found[w]["last_ts"] = max(wallets_found[w]["last_ts"], t_ts)
            total_markets += 1

    print(f"  {total_markets} markets scanned → {len(wallets_found)} active-24h wallets")
    return [(w, f"hot_market({','.join(sorted(v['seeds'])[:3])})")
            for w, v in sorted(wallets_found.items(), key=lambda x: -x[1]["last_ts"])]


def print_result(r, prefix=""):
    bkt = {"A_STRONG": "✅ STRONG", "B_PROBATIONARY": "⚠️  PROB ", "C_REJECT": "❌ REJECT"}
    tag = bkt.get(r["bucket"], "?")
    print(f"{prefix}{tag} | {r['wallet'][:18]}  "
          f"WR={r['wr']:.1f}%({r['wins']}W/{r['losses']}L)  "
          f"age={r['age_days']:.0f}d  stake=${r['avg_stake']:.0f}  "
          f"entry={r['avg_entry']:.2f}  sport={r['sports_pct']:.0%}  "
          f"freq={r['freq']:.1f}/d  clust={r['clusters']}  "
          f"blk={r['blocked_pct']:.0%}  hold={r['hold_score']:.2f}  "
          f"24h={r['recent_24h']}  top={r['top_sport']}")
    print(f"  {'':4}edge={r['edge_score']:.1f}  copy={r['copy_score']:.1f}  "
          f"res={r['resolved']}  open={r['open']}  src={r['source'][:45]}")

def main():
    start = datetime.now(timezone.utc)
    print("=" * 72)
    print(f"BROADER PROMO PASS — {start.strftime('%Y-%m-%d %H:%M')} UTC")
    print(f"Thresholds: age≥{P_MIN_AGE}d | res≥{P_MIN_RESOLVED} | "
          f"stake≥${P_MIN_STAKE} | entry≤{P_MAX_ENTRY} | "
          f"clust<{P_MAX_CLUSTERS} | blk<{P_MAX_BLOCKED:.0%} | WR≥{P_MIN_WR}%")
    print("=" * 72)

    all_candidates = {}   # wallet -> source tag (deduplicated)
    reject_stats = {}
    scored = []

    # ── 1. Force-check known candidates ──────────────────────────────────────
    print("\n[FORCE_CHECK] Evaluating known candidates under broad thresholds")
    for wallet, label, source in FORCE_CHECK:
        print(f"  → {label} {wallet[:16]}...", end="  ", flush=True)
        rs = {}
        result = score_candidate_broad(wallet, f"force:{label}", rs)
        time.sleep(0.3)
        if result:
            print_result(result, prefix="    ")
            scored.append(result)
        else:
            reason = list(rs.keys())[0] if rs else "unknown"
            print(f"❌ {reason}")

    # ── 2. Leaderboard wallets ────────────────────────────────────────────────
    lb_wallets = fetch_leaderboard_wallets(limit=300)
    for w, pnl in lb_wallets:
        all_candidates[w] = f"leaderboard_30d(pnl=${pnl:.0f})"

    # ── 3. Hot market wallets (active 24h) ────────────────────────────────────
    hot_wallets = fetch_hot_market_wallets()
    for w, src in hot_wallets:
        if w in all_candidates:
            all_candidates[w] += "+hot24h"
        else:
            all_candidates[w] = src

    # Remove force-checked wallets from normal scoring
    for wallet, _, _ in FORCE_CHECK:
        all_candidates.pop(wallet, None)

    total = len(all_candidates)
    print(f"\n[COMBINED] {total} unique candidates (leaderboard + hot markets)")
    print(f"[SCORING]  Broad probationary pass...")

    done = 0
    for wallet, source in all_candidates.items():
        done += 1
        if done % 50 == 0:
            sys.stdout.write(f"\r  {done}/{total} | pass={len(scored)}   ")
            sys.stdout.flush()
        result = score_candidate_broad(wallet, source, reject_stats)
        time.sleep(0.2)
        if result:
            scored.append(result)

    print(f"\n  Done. {len(scored)} passed (incl. force-checks)")
    print(f"  Rejection: {json.dumps(reject_stats)}")

    # ── Classify and rank ─────────────────────────────────────────────────────
    scored.sort(key=lambda x: (-{"A_STRONG":3,"B_PROBATIONARY":2,"C_REJECT":0}.get(x["bucket"],0),
                                -x["edge_score"]))
    a_strong = [r for r in scored if r["bucket"] == "A_STRONG"]
    b_prob   = [r for r in scored if r["bucket"] == "B_PROBATIONARY"]
    c_rej    = [r for r in scored if r["bucket"] == "C_REJECT"]

    print(f"\n{'='*72}")
    print(f"RESULTS: {len(a_strong)} STRONG | {len(b_prob)} PROBATIONARY | {len(c_rej)} REJECT")
    print(f"{'='*72}")

    if a_strong:
        print("\n── BUCKET A: STRONG (add now at standard caps) ──")
        for r in a_strong:
            print_result(r, "  ")

    if b_prob:
        print("\n── BUCKET B: PROBATIONARY (add tiny $5 stop=-$10) ──")
        for r in b_prob[:10]:
            print_result(r, "  ")

    if c_rej:
        print(f"\n── BUCKET C: REJECT ({len(c_rej)} total, top 5 shown) ──")
        for r in c_rej[:5]:
            print_result(r, "  ")

    # Save
    out = {
        "run_at": start.isoformat(),
        "total_scored": len(scored),
        "a_strong": len(a_strong),
        "b_probationary": len(b_prob),
        "c_reject": len(c_rej),
        "rejection_counts": reject_stats,
        "results": scored,
    }
    out_path = "/home/ubuntu/copytrade/broader_promo_results.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nResults → {out_path}")
    print("Done.")

if __name__ == "__main__":
    main()
