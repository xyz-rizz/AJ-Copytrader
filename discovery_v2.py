#!/usr/bin/env python3
"""
discovery_v2.py — Multi-lane trader discovery pipeline
Version: 2.0 | Date: 2026-03-10

Lanes:
  A: co-occurrence from 7 CLEAN active bot seeds (30 markets each)
  B: gamma medium-volume CLOSED sports markets ($3k-$120k, last 21d)
  C: gamma medium-volume ACTIVE sports markets ($5k-$200k)
  NEAR_MISS: forced re-evaluation of 3 unexamined prior candidates

Fixes applied:
  - FIX-1: Proper curPrice=0.0 handling (not treated as falsy)
  - FIX-2: Recency-weighted sports_pct = max(lifetime, recent_30d)
  - FIX-3: Full 42-char addresses + source lane tracking
  - FIX-4: Broad thresholds (age>=14d, resolved>=10) separate from strict
  - FIX-5: Rejection reason counts at every filter stage
"""

import json, urllib.request, time, sys, math
from datetime import datetime, timezone
from collections import defaultdict

# ── API bases ──────────────────────────────────────────────────────────────────
DATA_API  = "https://data-api.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# ── Clean seeds: 7 active, proven, non-benched traders ────────────────────────
CLEAN_SEEDS = {
    "0xa83be3f6a49604556f45089799f2b2096e71def4": "Signal47-Bets",
    "0xf27e335d2e78a207e802879f72870449836bd69d": "Immense-Gokart",
    "0xe85d6567a750b7b15fcb51c01a7c6230f63095d8": "Triangular-Box",
    "0x146703a8a73ae1dff0f84ba44c45d878858a4372": "Unwieldy-Forage",
    "0xbb63e47263321b67d7535f3909f2ec3c10a0bea4": "gem62-NBA",
    "0xf21b5380ac186a254422e046a97b0e80c8a8894e": "gem61-WBC",
    "0x9c886f69a9e2e5dfcf53f5ef6058925865f16871": "NBA-9c88",
}

# ── Force-evaluate these regardless of lane discovery ─────────────────────────
KNOWN_NEAR_MISS = [
    ("0x0f5c37e3d248ed29e2f0a0913b2a3a0d8021cc27", "deep_scan_0305_score83.8"),
    ("0xe2c2ad73fe56a6f3786eac98a957753611f262e4", "dsfarwe_scout_wide2"),
    ("0x0caacf3919c50a4d59c784f7496116a809fdb2bd", "deep_scan_0305_score74.4"),
]


# ── Skip-list: already tracking, benched, blacklisted ─────────────────────────
KNOWN_WALLETS = set(CLEAN_SEEDS.keys()) | {
    # Already tracking
    "0x4b916c5ad935c58652dc1d5eb234a1f789ceb1fb",  # gem68-NBA (co-trader, hold)
    # Benched / blacklisted
    "0xbbef150918dfdf01dac7aa07cde7e5a5834d92a",  # Quixotic-Average
    "0x69aee045323f0e37afd4dc1702ed40b2ab99e9c5",  # GEM_0x69aee micro
    "0x8f80e8c2fabd57c5fe27f49e0fc3b8af7dbb3282",  # MultiSport-8f80 1W/11L
    "0x71971342cb4c2555f60366ac62abdcdd1a1d14c8",  # RawrRawr 1W/18L
    "0x4042a8ef98b5abf2a1cf2423f8475c91ee150bda",  # HeisenbergWalt ROI-69%
    "0x77f623734a71c023f9df91011189eaeef891dbd1",  # bigwhale1337
    "0x419be42e6a14a0a218fe8ff79d3e6bb83be95a49",  # Superb-Hyacinth
    "0x65b6662cc476ac85b9218a08f11db6a5e1d02e2f",  # CS2-LoL-Sharp 0W/5L
    "0xccbd4bbcc445e7f4b98abf3061aa2b9e0130f1b7",  # NBA Whale HFT bot
    "0x3f5ea0a8053e81ce2f59814118869322c35fe7db",  # piggyery 137 clusters
    "0x14ac84b66a27fc30e56ed620ebfa61cd8105cb21",  # BrokeMaxxing 158 clusters
    "0xdc16718af9f04590b38a8e8aa32dedcd034740a5",  # ELESTUDIO freq=193/d
    "0xbb15969cb69d5b430d40870aabdf2a1d91820f02",  # kkap8897
    "0x25a1a36e671aa52180be2e5ad498dc2013d9ddf8",  # SharpEdge-25a1 micro stake
    "0xb5124dae83419944bb000ebe28607560de9144a5",  # Veteran-b512
    "0x05b21f43e056cdf3f26ae5f28dc0238495e2a469",  # jack66666 entry=0.868
    "0xc33a100b8362bc732e78cce28c99739f173b3da3",  # Sharp-c33a ROI-41%
    "0xc97f638399a3cc5ff1cf1f76041ab2c1f77b547a",  # 0xc97f Turkish soccer
    "0x5524f06ff6e08c5e3dce9c1c6a2b36e70a0a3d6b",  # 0x5524 scalper
}

# ── Thresholds ─────────────────────────────────────────────────────────────────
BROAD_MIN_AGE      = 14     # days
BROAD_MIN_RESOLVED = 10
BROAD_MIN_STAKE    = 8.0
BROAD_MIN_SPORTS   = 0.30
BROAD_MAX_CRYPTO   = 0.30
BROAD_MAX_CLUSTERS = 10

STRICT_MIN_AGE      = 21
STRICT_MIN_RESOLVED = 15
STRICT_MIN_STAKE    = 10.0
STRICT_MIN_SPORTS   = 0.40
STRICT_MAX_ENTRY    = 0.80
STRICT_MAX_CLUSTERS = 4
STRICT_MAX_BLOCKED  = 0.20
STRICT_MIN_WR       = 75.0

SCAN_MARKETS_PER_SEED = 30


# ── Sport/crypto keyword lists ─────────────────────────────────────────────────
SPORT_KWS = [
    'nba','nfl','nhl','mlb','ufc','tennis','football','soccer','epl',
    'basketball','baseball','hockey','spread','o/u','moneyline','winner',
    'match','game',' vs ','playoff','championship','cup','league','tournament',
    'wbc','world series','super bowl','ncaa','mls','ligue','bundesliga',
    'serie a','la liga','premier league','lol','valorant','cs2','dota',
    'esport','overwatch','atp','wta','f1','formula','nascar','golf','pga',
]
CRYPTO_KWS = [
    'bitcoin','btc','eth ','ethereum','crypto','solana','price will',
    'pump','dump','matic','polygon','defi','nft','token',
]
SPORT_TAGS_GAMMA = [
    "sports","nba","nfl","mlb","nhl","soccer","tennis","ufc",
    "football","baseball","basketball","esports",
]

# ── API helpers ────────────────────────────────────────────────────────────────
def fetch_json(url, params=None, timeout=15):
    if params:
        qs = "&".join(f"{k}={urllib.request.quote(str(v), safe='')}" for k, v in params.items())
        url = f"{url}?{qs}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception:
        return None

def get_activity(wallet, limit=500):
    data = fetch_json(f"{DATA_API}/activity", {"user": wallet, "limit": limit})
    return data if data and isinstance(data, list) else []

def get_positions(wallet, limit=500):
    data = fetch_json(f"{DATA_API}/positions",
                      {"user": wallet, "limit": limit, "sizeThreshold": "0.01"})
    return data if data and isinstance(data, list) else []

def get_trades_for_market(condition_id, limit=300):
    data = fetch_json(f"{DATA_API}/trades", {"conditionId": condition_id, "limit": limit})
    return data if data and isinstance(data, list) else []

def get_gamma_markets(closed=True, tag=None, vol_min=3000, vol_max=120000, limit=50):
    params = {
        "closed": "true" if closed else "false",
        "order": "volume",
        "ascending": "false",
        "limit": limit,
    }
    if not closed:
        params["active"] = "true"
    if tag:
        params["tag"] = tag
    data = fetch_json(f"{GAMMA_API}/markets", params)
    if not data:
        return []
    markets = data if isinstance(data, list) else data.get("markets", [])
    results = []
    for m in markets:
        vol = float(m.get("volume") or m.get("volumeUsdc") or 0)
        if vol_min <= vol <= vol_max:
            results.append(m)
    return results


# ── FIX-1: curPrice=0.0 properly handled (0.0 is NOT falsy-default) ────────────
def safe_price(val, default=0.5):
    """Returns float; 0.0 stays 0.0 (confirmed loss), None → default."""
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default

def classify_wl(positions):
    """Returns (wins, losses, open_count)."""
    wins = losses = open_pos = 0
    for p in positions:
        cur_raw = p.get("curPrice")
        if cur_raw is None:
            cur_raw = p.get("currentPrice")
        cur = safe_price(cur_raw, default=None)
        if cur is None:
            cur = 0.5  # truly unknown → treat as open

        redeemable = bool(p.get("redeemable", False))
        cur_val    = float(p.get("currentValue") or 0)
        pnl        = float(p.get("percentPnl") or 0)

        if redeemable and cur_val > 0:
            wins += 1
        elif redeemable and cur_val == 0 and pnl <= -50:
            losses += 1
        elif cur <= 0.04 and not redeemable:
            losses += 1
        elif cur > 0.04 and not redeemable:
            open_pos += 1
    return wins, losses, open_pos

# ── FIX-2: Recency-weighted sports_pct ────────────────────────────────────────
def get_sports_crypto_pct(activity):
    """Returns (sports_pct, crypto_pct). sports_pct = max(lifetime, recent_30d)."""
    buys = [a for a in activity
            if (a.get("type") == "TRADE" and a.get("side") == "BUY")
            or a.get("type") == "BUY"]
    if not buys:
        buys = activity
    if not buys:
        return 0.0, 0.0

    def is_sports(item):
        t = (item.get("title") or item.get("market") or item.get("description") or "").lower()
        return any(k in t for k in SPORT_KWS)

    def is_crypto(item):
        t = (item.get("title") or item.get("market") or item.get("description") or "").lower()
        return any(k in t for k in CRYPTO_KWS)

    def parse_ts(item):
        ts = float(item.get("timestamp", 0) or 0)
        return ts / 1000 if ts > 4e12 else ts

    now = datetime.now(timezone.utc).timestamp()
    cutoff_30d = now - 30 * 86400

    total = len(buys)
    sports_life  = sum(1 for b in buys if is_sports(b))
    crypto_life  = sum(1 for b in buys if is_crypto(b))

    recent = [b for b in buys if parse_ts(b) >= cutoff_30d]
    if recent:
        sports_30d   = sum(1 for b in recent if is_sports(b))
        sports_30d_pct = sports_30d / len(recent)
    else:
        sports_30d_pct = sports_life / total if total else 0.0

    # FIX: take max (don't penalise recent sports pivots)
    sports_pct = max(sports_life / total if total else 0.0, sports_30d_pct)
    crypto_pct = crypto_life / total if total else 0.0
    return sports_pct, crypto_pct


def get_stake_freq_entry(activity, age_days):
    """Returns (avg_stake, freq_per_day, avg_entry). Uses usdcSize field."""
    buys = [a for a in activity
            if (a.get("type") == "TRADE" and a.get("side") == "BUY")
            or a.get("type") == "BUY"]
    if not buys:
        buys = activity

    def parse_ts(item):
        ts = float(item.get("timestamp", 0) or 0)
        return ts / 1000 if ts > 4e12 else ts

    amounts = [float(b.get("usdcSize") or b.get("amount") or b.get("size") or 0)
               for b in buys]
    amounts = [a for a in amounts if a > 0]
    avg_stake = sum(amounts) / len(amounts) if amounts else 0.0

    now = datetime.now(timezone.utc).timestamp()
    cutoff_30d = now - 30 * 86400
    recent = [b for b in buys if parse_ts(b) >= cutoff_30d]
    freq = len(recent) / 30.0 if recent else len(buys) / max(age_days, 1)

    prices = [float(b.get("price") or b.get("avgPrice") or 0) for b in buys]
    prices = [p for p in prices if 0.01 < p < 0.99]
    avg_entry = sum(prices) / len(prices) if prices else 0.0

    return avg_stake, freq, avg_entry

def get_account_age(activity):
    """Age in days based on earliest activity timestamp."""
    def parse_ts(item):
        ts = float(item.get("timestamp", 0) or 0)
        return ts / 1000 if ts > 4e12 else ts

    timestamps = [parse_ts(a) for a in activity if parse_ts(a) > 0]
    if not timestamps:
        return 0.0
    earliest = min(timestamps)
    return (datetime.now(timezone.utc).timestamp() - earliest) / 86400

def detect_clusters(activity):
    """Count seconds where >=3 buys land simultaneously (bot signature)."""
    buys = [a for a in activity
            if (a.get("type") == "TRADE" and a.get("side") == "BUY")
            or a.get("type") == "BUY"]
    ts_counts = defaultdict(int)
    for b in buys:
        ts = float(b.get("timestamp", 0) or 0)
        if ts > 4e12:
            ts /= 1000
        sec = int(ts)
        if sec > 0:
            ts_counts[sec] += 1
    return sum(1 for c in ts_counts.values() if c >= 3)

def get_blocked_pct(activity):
    """Fraction of buys at price > 0.90 (near-certainty / block-farming)."""
    buys = [a for a in activity
            if (a.get("type") == "TRADE" and a.get("side") == "BUY")
            or a.get("type") == "BUY"]
    if not buys:
        return 0.0
    high_conf = sum(1 for b in buys
                    if float(b.get("price") or b.get("avgPrice") or 0) > 0.90)
    return high_conf / len(buys)


# ── Core scorer ────────────────────────────────────────────────────────────────
def score_candidate(wallet, source_tag, reject_stats):
    """
    Score a wallet against broad thresholds.
    Returns result dict on pass, None on reject. reject_stats dict updated in place.
    """
    acts = get_activity(wallet, limit=500)
    if not acts:
        reject_stats["no_activity"] = reject_stats.get("no_activity", 0) + 1
        return None

    age_days = get_account_age(acts)
    if age_days < BROAD_MIN_AGE:
        reject_stats["too_young"] = reject_stats.get("too_young", 0) + 1
        return None

    positions = get_positions(wallet)
    wins, losses, open_pos = classify_wl(positions)
    resolved = wins + losses

    if resolved < BROAD_MIN_RESOLVED:
        reject_stats["few_resolved"] = reject_stats.get("few_resolved", 0) + 1
        return None

    wr = wins / resolved if resolved > 0 else 0.0
    avg_stake, freq, avg_entry = get_stake_freq_entry(acts, age_days)

    if avg_stake < BROAD_MIN_STAKE:
        reject_stats["micro_bettor"] = reject_stats.get("micro_bettor", 0) + 1
        return None

    sports_pct, crypto_pct = get_sports_crypto_pct(acts)

    if crypto_pct > BROAD_MAX_CRYPTO:
        reject_stats["crypto"] = reject_stats.get("crypto", 0) + 1
        return None

    if sports_pct < BROAD_MIN_SPORTS:
        reject_stats["non_sports"] = reject_stats.get("non_sports", 0) + 1
        return None

    clusters = detect_clusters(acts)
    if clusters >= BROAD_MAX_CLUSTERS:
        reject_stats["bot_clusters"] = reject_stats.get("bot_clusters", 0) + 1
        return None

    blocked_pct = get_blocked_pct(acts)

    # Score: WR × log(resolved+1) × age_bonus
    age_bonus = min(age_days / 100.0, 2.0)
    score = wr * 100.0 * math.log(resolved + 1) * (1 + age_bonus * 0.1)

    return {
        "wallet":      wallet,
        "source":      source_tag,
        "score":       round(score, 1),
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
    }

def is_promotable(r):
    """Strict promotion thresholds. Returns (bool, reason_str)."""
    if r["age_days"]    < STRICT_MIN_AGE:       return False, f"too_young({r['age_days']:.0f}d)"
    if r["resolved"]    < STRICT_MIN_RESOLVED:   return False, f"few_res({r['resolved']})"
    if r["avg_stake"]   < STRICT_MIN_STAKE:      return False, f"micro(${r['avg_stake']:.0f})"
    if r["sports_pct"]  < STRICT_MIN_SPORTS:     return False, f"non_sports({r['sports_pct']:.0%})"
    if r["avg_entry"]   > STRICT_MAX_ENTRY:      return False, f"entry({r['avg_entry']:.2f})"
    if r["clusters"]    > STRICT_MAX_CLUSTERS:   return False, f"clusters({r['clusters']})"
    if r["blocked_pct"] > STRICT_MAX_BLOCKED:    return False, f"blocked({r['blocked_pct']:.0%})"
    if r["wr"]          < STRICT_MIN_WR:         return False, f"low_wr({r['wr']:.1f}%)"
    return True, "OK"


# ── Lane A: Co-occurrence from clean seeds ─────────────────────────────────────
def lane_a_cooccurrence():
    print("\n[LANE A] Co-occurrence from clean seeds (30 markets/seed)")
    cids_used   = set()
    wallets_out = {}  # wallet → set of seed names

    for seed_wallet, seed_name in CLEAN_SEEDS.items():
        acts  = get_activity(seed_wallet, limit=500)
        buys  = [a for a in acts
                 if (a.get("type") == "TRADE" and a.get("side") == "BUY")
                 or a.get("type") == "BUY"]
        cids  = []
        for a in buys:
            cid = a.get("conditionId") or a.get("market")
            if cid and cid not in cids_used:
                cids_used.add(cid)
                cids.append(cid)
            if len(cids) >= SCAN_MARKETS_PER_SEED:
                break

        found_this_seed = 0
        for cid in cids:
            trades = get_trades_for_market(cid)
            time.sleep(0.1)
            for t in trades:
                w = (t.get("maker") or t.get("proxyWallet") or t.get("trader") or "").lower()
                if len(w) == 42 and w not in KNOWN_WALLETS:
                    wallets_out.setdefault(w, set()).add(seed_name)
                    found_this_seed += 1

        print(f"  {seed_name}: {len(cids)} markets → {found_this_seed} co-traders")
        time.sleep(0.3)

    print(f"  [LANE A] total unique candidates: {len(wallets_out)}")
    return {w: {"source": f"A({','.join(sorted(srcs))})"} for w, srcs in wallets_out.items()}

# ── Lane B: Gamma medium-volume CLOSED sports ──────────────────────────────────
def lane_b_medium_closed():
    print("\n[LANE B] Gamma medium-volume CLOSED sports ($3k-$120k, last 21d)")
    wallets_out  = {}
    markets_used = 0
    now_ts = datetime.now(timezone.utc).timestamp()
    cutoff = now_ts - 21 * 86400

    for tag in SPORT_TAGS_GAMMA:
        mkts = get_gamma_markets(closed=True, tag=tag, vol_min=3000, vol_max=120000, limit=50)
        time.sleep(0.3)

        for m in mkts:
            # recency check: closed within last 21d
            end_raw = m.get("endDateIso") or m.get("endDate") or ""
            try:
                if "T" in str(end_raw):
                    from datetime import datetime as _dt
                    end_ts = _dt.fromisoformat(str(end_raw).replace("Z", "+00:00")).timestamp()
                else:
                    end_ts = float(end_raw)
                if end_ts < cutoff:
                    continue
            except Exception:
                pass  # can't parse — include it

            cid = m.get("conditionId") or m.get("id")
            if not cid:
                continue

            trades = get_trades_for_market(cid)
            time.sleep(0.1)
            for t in trades:
                w = (t.get("maker") or t.get("proxyWallet") or t.get("trader") or "").lower()
                if len(w) == 42 and w not in KNOWN_WALLETS:
                    wallets_out.setdefault(w, set()).add(f"B:{tag}")
            markets_used += 1

        if markets_used > 0 and markets_used % 20 == 0:
            print(f"  [LANE B] {markets_used} markets, {len(wallets_out)} candidates so far")
        time.sleep(0.3)

    print(f"  [LANE B] {markets_used} markets seeded → {len(wallets_out)} unique candidates")
    return {w: {"source": f"B({','.join(sorted(srcs))})"} for w, srcs in wallets_out.items()}


# ── Lane C: Gamma medium-volume ACTIVE sports ──────────────────────────────────
def lane_c_active_sports():
    print("\n[LANE C] Gamma medium-volume ACTIVE sports ($5k-$200k)")
    wallets_out  = {}
    markets_used = 0

    for tag in SPORT_TAGS_GAMMA[:8]:
        mkts = get_gamma_markets(closed=False, tag=tag, vol_min=5000, vol_max=200000, limit=30)
        time.sleep(0.3)

        for m in mkts:
            cid = m.get("conditionId") or m.get("id")
            if not cid:
                continue

            trades = get_trades_for_market(cid)
            time.sleep(0.1)
            for t in trades:
                w = (t.get("maker") or t.get("proxyWallet") or t.get("trader") or "").lower()
                if len(w) == 42 and w not in KNOWN_WALLETS:
                    wallets_out.setdefault(w, set()).add(f"C:{tag}")
            markets_used += 1
        time.sleep(0.3)

    print(f"  [LANE C] {markets_used} markets seeded → {len(wallets_out)} unique candidates")
    return {w: {"source": f"C({','.join(sorted(srcs))})"} for w, srcs in wallets_out.items()}

# ── Main ────────────────────────────────────────────────────────────────────────
def main():
    start = datetime.now(timezone.utc)
    print("=" * 72)
    print(f"DISCOVERY V2  —  {start.strftime('%Y-%m-%d %H:%M')} UTC")
    print("Lanes: A(co-occur/clean) + B(gamma-med-closed) + C(gamma-med-active) + NEAR_MISS")
    print("=" * 72)

    # ── Force-evaluate known near-misses first ──────────────────────────────
    print("\n[NEAR_MISS] Force-evaluating 3 known past candidates")
    near_miss_scored = {}
    for wallet, tag in KNOWN_NEAR_MISS:
        print(f"  → {wallet[:16]}... ({tag})", end="  ", flush=True)
        rs = {}
        result = score_candidate(wallet, f"near_miss:{tag}", rs)
        time.sleep(0.4)
        if result:
            near_miss_scored[wallet] = result
            ok, reason = is_promotable(result)
            flag = "✅PROMOTABLE" if ok else f"⚠️ {reason}"
            print(f"{flag} WR={result['wr']}%({result['wins']}W/{result['losses']}L) "
                  f"stake=${result['avg_stake']:.0f} age={result['age_days']:.0f}d "
                  f"sports={result['sports_pct']:.0%} entry={result['avg_entry']:.2f} "
                  f"clusters={result['clusters']}")
        else:
            reason = next(iter(rs.keys()), "unknown") if rs else "unknown"
            print(f"❌ FAIL: {reason}")

    # ── Collect candidates from all lanes ───────────────────────────────────
    candidates = {}
    for lane_fn in [lane_a_cooccurrence, lane_b_medium_closed, lane_c_active_sports]:
        lane_result = lane_fn()
        for w, meta in lane_result.items():
            if w in candidates:
                candidates[w]["source"] += "+" + meta["source"]
            else:
                candidates[w] = meta

    # Remove near-miss wallets from normal scoring (already done above)
    for w, _ in KNOWN_NEAR_MISS:
        candidates.pop(w, None)

    total_unique = len(candidates)
    print(f"\n[COMBINED] {total_unique} unique new candidates across lanes A+B+C")
    print(f"[SCORING]  Broad pass (age≥{BROAD_MIN_AGE}d / res≥{BROAD_MIN_RESOLVED} / "
          f"stake≥${BROAD_MIN_STAKE} / sports≥{BROAD_MIN_SPORTS:.0%}) ...")

    # ── Score all candidates ─────────────────────────────────────────────────
    scored   = list(near_miss_scored.values())   # start with near-miss results
    rej_stats = {}
    done = 0

    for wallet, meta in candidates.items():
        done += 1
        if done % 100 == 0:
            sys.stdout.write(f"\r  Progress {done}/{total_unique} | broad_pass={len(scored)}   ")
            sys.stdout.flush()
        result = score_candidate(wallet, meta["source"], rej_stats)
        time.sleep(0.25)
        if result:
            scored.append(result)

    print(f"\n  Done. {len(scored)} passed broad filters (incl. {len(near_miss_scored)} near-miss)")


    # ── Strict filter pass ───────────────────────────────────────────────────
    scored.sort(key=lambda x: -x["score"])
    promotable = []

    print("\n[PROMOTABLE] Strict filter results:")
    hdr = f"{'Wallet':18} {'WR%':>6} {'W':>4} {'L':>4} {'Age':>5} {'Stake':>7} "
    hdr += f"{'Sprt':>5} {'Ent':>5} {'Clst':>5}  Reason/Source"
    print(hdr)
    print("-" * 90)

    for r in scored:
        ok, reason = is_promotable(r)
        nm = "🔁" if r["source"].startswith("near_miss") else "  "
        row = (f"{nm}{r['wallet'][:16]:16} {r['wr']:>6.1f} {r['wins']:>4} {r['losses']:>4} "
               f"{r['age_days']:>5.0f}d ${r['avg_stake']:>6.0f} "
               f"{r['sports_pct']:>5.0%} {r['avg_entry']:>5.2f} {r['clusters']:>5}")
        if ok:
            promotable.append(r)
            print(f"  ✅{row}  OK | {r['source'][:35]}")
        else:
            print(f"  ❌{row}  {reason} | {r['source'][:35]}")

    # ── Save results ─────────────────────────────────────────────────────────
    output = {
        "run_at":     start.isoformat(),
        "lane_stats": {
            "a_seeds":         len(CLEAN_SEEDS),
            "total_unique":    total_unique,
            "near_miss_pass":  len(near_miss_scored),
            "broad_pass":      len(scored),
            "promotable":      len(promotable),
        },
        "rejection_counts": rej_stats,
        "ranked_all":   scored,
        "promotable":   promotable,
    }
    out_path = "/home/ubuntu/copytrade/discovery_v2_results.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    # ── Final summary ────────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print(f"SUMMARY: {total_unique} candidates → {len(scored)} broad pass → "
          f"{len(promotable)} promotable")
    print(f"Rejection breakdown: {json.dumps(rej_stats)}")
    print("=" * 72)
    if promotable:
        print("\nPROMOTABLE SHORTLIST (for manual add decision):")
        print(f"{'#':>2}  {'Wallet':42} {'WR%':>6} {'W/L':>8} {'Age':>5} "
              f"{'Stake':>7} {'Sprt':>5} {'Ent':>5} {'Clst':>5}")
        print("-" * 95)
        for i, r in enumerate(promotable, 1):
            nm = " [NEAR-MISS]" if r["source"].startswith("near_miss") else ""
            print(f"{i:>2}  {r['wallet']:42} {r['wr']:>6.1f} "
                  f"{r['wins']:>4}W/{r['losses']:<3}L {r['age_days']:>5.0f}d "
                  f"${r['avg_stake']:>6.0f} {r['sports_pct']:>5.0%} "
                  f"{r['avg_entry']:>5.2f} {r['clusters']:>5}{nm}")
            print(f"    source: {r['source']}")
    else:
        print("\nNo promotable candidates found. See near-miss section and ranked_all in JSON.")

    print(f"\nResults → {out_path}")
    print("Done.")

if __name__ == "__main__":
    main()
