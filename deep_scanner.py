#!/usr/bin/env python3
"""
deep_scanner.py  v1.1
Weekly deep scan: Polymarket 30-day leaderboard + winning-side cross-reference.
Runs ALONGSIDE daily scanner.py cron (does NOT replace it).

v1.1 changes vs v1.0:
  - Same-second cluster bot detection (≥3 clusters of ≥3 fills → bot)
  - Bell-curve entry scoring (peaks at $0.20 — rewards real underdog pricing)
  - Intersection bonus: +5pts if wallet appears in BOTH signals
  - Winner appearances bonus: +3pts if ≥7 XRef markets
  - MIN_WR = 0.60 hard filter (below 60% WR → skip before full scoring)
  - MAX_FREQ_PER_DAY 20 → 15 (stricter bot guard)
  - MIN_WIN_MARKETS 3 → 5 (stricter XRef threshold)
  - Added confirmed bots to KNOWN_WALLETS: ethanaz, KaneAnalytics, yyjjj3838

Cron (weekly Sunday 09:00 UTC):
  0 9 * * 0 cd /home/ubuntu/copytrade && source .env && \
            /home/ubuntu/venv/bin/python3 -u deep_scanner.py >> deep_scan.log 2>&1
"""

import os, sys, time, json, math, requests
from datetime import datetime, timezone
from collections import defaultdict, Counter

# ── Telegram ──────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")   # v1.2 fix: was TELEGRAM_TOKEN (wrong key — alerts never fired)
TELEGRAM_CHAT  = os.getenv("TELEGRAM_CHAT_ID", "")

# ── Thresholds ────────────────────────────────────────────────────────────────
GEM_THRESHOLD        = 60
MIN_RESOLVED         = 20
MIN_ACCOUNT_AGE_DAYS = 21
MAX_FREQ_PER_DAY     = 15      # v1.1: 20 → 15 (stricter)
WR_CREDIBILITY_N     = 15      # 100% WR on n≥15 capped to 0.95
MIN_WR               = 0.60    # v1.1: hard filter before scoring
LEADERBOARD_PAGES    = 2       # 2 × 100 = top 200
WINNING_MARKETS_N    = 30      # resolved sports markets to XRef
MIN_WIN_MARKETS      = 5       # v1.1: 3 → 5 (stricter XRef)
MIN_SPORTS_PCT       = 0.40
MAX_AVG_ENTRY        = 0.80    # v1.3: aligned with scanner.py (was 0.55 — inconsistent cutoff)
SAME_SEC_BOT_THRESH  = 3       # ≥3 clusters of ≥3 same-second fills → bot

# Entry bell-curve peak — reward genuine underdog pricing (~$0.20)
ENTRY_BELL_PEAK  = 0.20
ENTRY_BELL_WIDTH = 0.25        # σ — controls how fast score drops off

SPORTS_KEYWORDS = [
    "nba","nfl","mlb","nhl","mls","epl","laliga","bundesliga","seriea","ligue1",
    "premier league","champions league","europa league","ucl","uel",
    "warriors","lakers","celtics","nets","bulls","heat","knicks","suns","nuggets",
    "clippers","76ers","bucks","raptors","mavericks","rockets","spurs","grizzlies",
    "jazz","thunder","pelicans","wizards","magic","pistons","cavaliers","hawks",
    "hornets","pacers","kings","timberwolves","blazers","trail blazers",
    "chiefs","patriots","cowboys","eagles","packers","49ers","ravens","steelers",
    "broncos","bills","chargers","raiders","rams","bears","lions","giants","jets",
    "falcons","saints","buccaneers","panthers","texans","colts","jaguars","titans",
    "seahawks","cardinals","browns","bengals","dolphins","vikings","commanders",
    "yankees","dodgers","astros","braves","red sox","cubs","mets","phillies",
    "rangers","padres","brewers","twins","mariners","blue jays","orioles","rays",
    "white sox","tigers","guardians","royals","angels","rockies","marlins","nationals",
    "manchester","arsenal","chelsea","liverpool","tottenham","leicester",
    "real madrid","barcelona","atletico","juventus","inter","ac milan","roma",
    "psg","lyon","dortmund","bayern","ajax","porto","benfica",
    "wimbledon","us open","french open","australian open","atp","wta",
    "tennis","djokovic","nadal","federer","alcaraz","swiatek","medvedev",
    "cs2","csgo","dota","league of legends","valorant","overwatch","esports",
    "ncaa","march madness","college basketball","college football",
    "ufc","mma","boxing","f1","formula 1","grand prix","nascar",
    "cricket","ipl","test match","odi",
    " vs "," v ",
]

BLOCKED_TITLE_KEYWORDS = [
    "president","election","congress","senate","republican","democrat",
    "trump","biden","harris","elon",
    "iran","ukraine","russia","ceasefire","nuclear","sanctions","missile","supreme leader",
    "crypto","bitcoin","ethereum","btc","eth","solana",
    "fed rate","interest rate","gdp","inflation",
]

# ── Known wallets (blacklist — skip scoring entirely) ─────────────────────────
KNOWN_WALLETS = {
    # ── Active roster (already copied) ──
    "0xa83be3f6a49604556f45089799f2b2096e71def4": "Signal47-Bets",
    "0xf27e335d2e78a207e802879f72870449836bd69d": "Immense-Gokart",
    "0x8f80e8c2a414f5acc0231f5b934045ab4e85b302": "MultiSport-8f80",
    "0x69aee04532c679ecd4060d9e31af19d6af319f18": "GEM-0x69aee",       # v6.8: added to bot
    "0xbbef15091aee07f8310d7314761d3a3063749838": "Quixotic-Average",  # v6.8: added to bot
    "0x65b6662c2cb28e3018cbb6a4983c5b83b2842108": "CS2-LoL-Sharp",     # v6.8: added to bot
    # ── Confirmed bots — high freq / short span ──
    "0x036c159d2097c695e8af8e4b8e740a0f56c53a1e": "HedgeMaster88",
    "0x2a696607ae04cd08f67d56b6ac71ba609dde39ff": "Gleeful-Cauliflower",
    "0xcdad73ee9fe1f2e7f47f4bc25b39c6efe40a2c17": "Drab-Muscatel",
    "0xfd1440993de7d5e8127f0de37f77d7fce2745b3a": "Speedy-Booster",
    "0x6a57d263c01d49e1fa895e3f0e20b5d21e4ec97f": "0x6a57D2",
    "0x91654fd5e0a03bc4fc5a4e5e36d86d8a2e24da6a": "C.SIN",
    # ── Confirmed bots — ladder / same-second fills ──
    "0x89cdac7bb09751d9802acd70e221e92d16d892b9": "New-Browser",
    "0x7e3a1f95c558f39a51ff334d789e3e039b553246": "KaneAnalytics",    # v1.1: same-second + $78K/37d
    "0xf28e42d20e4826f2b10a24bc952001697947cab2": "ethanaz",           # v1.1: 8 same-sec clusters
    "0xbc37414580f0fd76082d68e03a5265db2f662f65": "yyjjj3838",         # v1.1: laddering same market ×5
    # ── Wrong categories / no edge ──
    "0xbdf2db488915de74beaa89d52a344ccf4df7740b": "Phony-Mantel",
    "0x3173dce0c0446bf64e671886826b7c4bb03e7be4": "anon-0x3173",
    "0x28dc4b7744b433621de7efd47ea0ce7451ffa1f2": "Front-Soap",
}

# ── HTTP helpers ───────────────────────────────────────────────────────────────
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0"})

def get(url, params=None, retries=3):
    for attempt in range(retries):
        try:
            r = SESSION.get(url, params=params, timeout=15)
            if r.status_code == 200:
                return r.json()
            print(f"  [WARN] {r.status_code} → {url}")
        except Exception as e:
            print(f"  [WARN] attempt {attempt+1} {url}: {e}")
        time.sleep(2 ** attempt)
    return None

def tg(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        print(f"[TG] {msg}")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT, "text": msg, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as e:
        print(f"[TG ERROR] {e}")

# ── Bell-curve entry scorer ────────────────────────────────────────────────────
def entry_bell_score(avg_entry: float, max_pts: float = 20.0) -> float:
    """
    Gaussian bell curve peaking at ENTRY_BELL_PEAK ($0.20).
    Rewards genuine underdog pricing; penalises both near-zero (degenerate)
    and near-0.5+ (coin-flip / favourite) entries.
    Examples:
      $0.20 → 20.0 pts   $0.35 → 17.5 pts
      $0.45 → 13.8 pts   $0.55 → 10.2 pts  (MAX_AVG_ENTRY cutoff)
    """
    score = math.exp(
        -((avg_entry - ENTRY_BELL_PEAK) ** 2) / (2 * ENTRY_BELL_WIDTH ** 2)
    ) * max_pts
    return round(score, 2)

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 1 — Leaderboard mining (30-day P&L)
# ══════════════════════════════════════════════════════════════════════════════
def fetch_leaderboard(pages=LEADERBOARD_PAGES):
    """Pull top wallets by 30-day P&L. Confirmed endpoint: /v1/leaderboard"""
    wallets = {}
    for page in range(pages):
        offset = page * 100
        data = get(
            "https://data-api.polymarket.com/v1/leaderboard",
            params={"limit": 100, "offset": offset, "window": "30d"},
        )
        if not data:   # retry without window param
            data = get(
                "https://data-api.polymarket.com/v1/leaderboard",
                params={"limit": 100, "offset": offset},
            )
        if not data:
            print(f"  [WARN] Leaderboard page {page+1} empty")
            continue

        entries = data if isinstance(data, list) else data.get("data", data.get("results", []))
        print(f"  [LB] Page {page+1}: {len(entries)} entries")

        for e in entries:
            wallet = (e.get("proxyWallet") or e.get("proxy_wallet") or "").lower().strip()
            if not wallet or len(wallet) < 30:
                continue
            pnl  = float(e.get("pnl", 0) or 0)
            vol  = float(e.get("volume", e.get("vol", 0)) or 0)
            name = (e.get("name") or e.get("userName") or
                    e.get("pseudonym") or wallet[:12])
            if pnl > 0:
                wallets[wallet] = {"name": name, "pnl": pnl,
                                   "volume": vol, "source": "leaderboard"}
        time.sleep(0.5)

    print(f"[Phase 1] Leaderboard: {len(wallets)} positive-P&L wallets")
    return wallets


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — Winning-side cross-reference
# ══════════════════════════════════════════════════════════════════════════════
def fetch_resolved_sports_markets(n=WINNING_MARKETS_N):
    """Fetch recently resolved, high-volume sports markets via gamma-api."""
    markets = []
    offset  = 0
    while len(markets) < n:
        data = get(
            "https://gamma-api.polymarket.com/markets",
            params={"closed": "true", "limit": 50, "offset": offset,
                    "order": "volume", "ascending": "false"},
        )
        if not data:
            break
        batch = data if isinstance(data, list) else data.get("markets", [])
        if not batch:
            break

        for m in batch:
            title = (m.get("question") or m.get("title") or "").lower()
            if not any(kw in title for kw in SPORTS_KEYWORDS):
                continue
            if any(kw in title for kw in BLOCKED_TITLE_KEYWORDS):
                continue
            if not (m.get("resolved") or m.get("closed")):
                continue
            cid = m.get("conditionId") or m.get("condition_id")
            if not cid:
                continue

            # Identify winning token — check tokens list and outcomePrices
            win_tok, win_name = None, ""

            # Try outcomePrices + clobTokenIds (native gamma fields)
            prices_raw = m.get("outcomePrices", "[]")
            tokens_raw = m.get("clobTokenIds",  "[]")
            try:
                prices_list = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
                tokens_list = json.loads(tokens_raw) if isinstance(tokens_raw, str) else tokens_raw
                for i, p in enumerate(prices_list):
                    if float(p or 0) >= 0.95 and i < len(tokens_list):
                        win_tok  = str(tokens_list[i])
                        outcomes = m.get("outcomes", "[]")
                        if isinstance(outcomes, str):
                            outcomes = json.loads(outcomes)
                        win_name = outcomes[i] if i < len(outcomes) else "YES"
                        break
            except Exception:
                pass

            # Fallback: tokens dict list
            if not win_tok:
                for tok in (m.get("tokens") or m.get("outcomes") or []):
                    if not isinstance(tok, dict):
                        continue
                    price = float(tok.get("price", tok.get("outcome_price", 0)) or 0)
                    if price >= 0.95:
                        win_tok  = tok.get("token_id") or tok.get("tokenId")
                        win_name = tok.get("outcome") or tok.get("name", "YES")
                        break

            markets.append({
                "cid":       cid,
                "title":     m.get("question") or m.get("title", ""),
                "win_token": win_tok,
                "win_name":  win_name,
                "volume":    float(m.get("volume") or 0),
            })
            if len(markets) >= n:
                break

        offset += 50
        time.sleep(0.3)

    print(f"[Phase 2] Found {len(markets)} resolved sports markets")
    return markets


def fetch_winning_side_wallets(markets):
    """
    For each market, pull BUY-side trades on the winning token.
    Confirmed endpoint: /trades?conditionId=... field: proxyWallet
    """
    win_count   = defaultdict(int)
    win_markets = defaultdict(list)

    for i, mkt in enumerate(markets):
        print(f"  [XRef {i+1}/{len(markets)}] {mkt['title'][:65]}")
        data = get("https://data-api.polymarket.com/trades",
                   params={"conditionId": mkt["cid"], "limit": 500})
        if not data:
            time.sleep(0.5)
            continue

        trades = data if isinstance(data, list) else data.get("trades", [])
        seen   = set()

        for t in trades:
            if t.get("side", "").upper() != "BUY":
                continue
            tok = t.get("tokenId") or t.get("token_id") or ""
            if mkt["win_token"] and tok and tok != mkt["win_token"]:
                continue
            wallet = (t.get("proxyWallet") or t.get("proxy_wallet") or "").lower().strip()
            if not wallet or len(wallet) < 30 or wallet in seen:
                continue
            seen.add(wallet)
            win_count[wallet]  += 1
            win_markets[wallet].append(mkt["title"][:45])

        time.sleep(0.4)

    strong = {w: win_count[w] for w in win_count if win_count[w] >= MIN_WIN_MARKETS}
    print(f"[Phase 2] Winning-side wallets (≥{MIN_WIN_MARKETS} markets): {len(strong)}")
    return strong, win_markets

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 3 — Merge & de-dupe
# ══════════════════════════════════════════════════════════════════════════════
def merge_candidates(lb_wallets, win_wallets, win_markets):
    candidates = {}
    for w in set(lb_wallets) | set(win_wallets):
        if w in KNOWN_WALLETS:
            continue
        in_lb  = w in lb_wallets
        in_win = w in win_wallets
        candidates[w] = {
            "wallet":     w,
            "name":       lb_wallets.get(w, {}).get("name", w[:12]),
            "lb_pnl":     lb_wallets.get(w, {}).get("pnl", 0),
            "lb_volume":  lb_wallets.get(w, {}).get("volume", 0),
            "win_count":  win_wallets.get(w, 0),
            "win_sample": win_markets.get(w, [])[:3],
            "in_lb":      in_lb,
            "in_win":     in_win,
            "both":       in_lb and in_win,
        }
    n_both = sum(1 for c in candidates.values() if c["both"])
    print(f"[Phase 3] Candidates: {len(candidates)}  (both signals: {n_both})")
    return candidates


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 4 — Scoring pipeline
# ══════════════════════════════════════════════════════════════════════════════
def get_activity(wallet):
    data = get("https://data-api.polymarket.com/activity",
               params={"user": wallet, "limit": 500})
    if not data:
        return []
    return data if isinstance(data, list) else data.get("activity", [])

def get_positions(wallet):
    data = get("https://data-api.polymarket.com/positions",
               params={"user": wallet, "sizeThreshold": 0.01})
    if not data:
        return []
    return data if isinstance(data, list) else data.get("positions", [])

def compute_sports_pct(buy_entries):
    if not buy_entries:
        return 0.0
    sports = sum(1 for _, title, _ in buy_entries
                 if any(kw in title for kw in SPORTS_KEYWORDS))
    return sports / len(buy_entries)

def detect_same_second_bot(buys):
    """
    Return True if wallet shows bot-like same-second fill clusters.
    Threshold: ≥ SAME_SEC_BOT_THRESH clusters where ≥3 trades share a timestamp.
    Legitimate humans almost never have even 1 such cluster.
    """
    ts_counts = Counter(b.get("timestamp") for b in buys if b.get("timestamp"))
    clusters  = sum(1 for n in ts_counts.values() if n >= 3)
    return clusters >= SAME_SEC_BOT_THRESH, clusters

def score_candidate(wallet, name="?"):
    """
    Returns (score, info_dict) or (None, {"reason": "..."}).

    Score breakdown (base max ~100):
      WR          → 35 pts  (was 40; shifted 5 to bell curve)
      Entry bell  → 20 pts  (v1.1: Gaussian peak at $0.20)
      Freq        → 10 pts
      Diversity   → 10 pts
      Age         → 10 pts
      Sports pct  → 10 pts
      Intersection→  +5 pts bonus (both LB + XRef signals)
      XRef depth  →  +3 pts bonus (≥7 winning markets)
    """
    act = get_activity(wallet)
    pos = get_positions(wallet)

    if not act:
        return None, {"reason": "no_activity"}

    buys = [a for a in act if a.get("type") == "TRADE" and a.get("side") == "BUY"]
    if not buys:
        return None, {"reason": "no_buys"}

    # ── Bot check: same-second clusters (v1.1) ────────────────────────────────
    is_bot, cluster_count = detect_same_second_bot(buys)
    if is_bot:
        return None, {"reason": f"bot_same_second (clusters={cluster_count})"}

    # ── Timestamps & age ──────────────────────────────────────────────────────
    ts_all = [a.get("timestamp", 0) for a in act if a.get("timestamp")]
    if not ts_all:
        return None, {"reason": "no_timestamps"}
    ts_min    = min(ts_all)
    ts_max    = max(ts_all)
    span_days = max((ts_max - ts_min) / 86400, 1)
    acct_age  = (time.time() - ts_min) / 86400

    # ── Frequency ─────────────────────────────────────────────────────────────
    freq = len(buys) / span_days

    # ── Avg entry price ───────────────────────────────────────────────────────
    prices    = [float(b.get("price", 0)) for b in buys if b.get("price")]
    avg_entry = sum(prices) / len(prices) if prices else 0

    # ── Title analysis ────────────────────────────────────────────────────────
    buy_entries = [
        (float(b.get("price", 0)),
         (b.get("title") or b.get("market", "") or "").lower(),
         b.get("conditionId", ""))
        for b in buys
    ]
    blocked_n   = sum(1 for _, t, _ in buy_entries
                      if any(kw in t for kw in BLOCKED_TITLE_KEYWORDS))
    blocked_pct = blocked_n / len(buy_entries) if buy_entries else 1.0
    sports_pct  = compute_sports_pct(buy_entries)

    # ── WR from positions API ─────────────────────────────────────────────────
    wins = losses = 0
    for p in pos:
        redeemable = p.get("redeemable", False)
        # FIX: curPrice=0.0 is falsy in Python — use explicit None check
        _cp_raw    = p.get("curPrice") if p.get("curPrice") is not None else p.get("currentPrice")
        try:
            cur_price  = float(_cp_raw) if _cp_raw is not None else 0.5
        except (TypeError, ValueError):
            cur_price  = 0.5
        if redeemable:
            wins += 1
        elif cur_price <= 0.04:
            losses += 1
    resolved = wins + losses

    if resolved == 0:
        wr = 0.5
    else:
        wr = wins / resolved
        if resolved >= WR_CREDIBILITY_N and wr >= 1.0:
            wr = 0.95   # credibility cap

    # ── Diversity ─────────────────────────────────────────────────────────────
    cids      = set(cid for _, _, cid in buy_entries if cid)
    diversity = len(cids) / max(len(buys), 1)

    # ── Hard filters ──────────────────────────────────────────────────────────
    if acct_age < MIN_ACCOUNT_AGE_DAYS:
        return None, {"reason": f"too_young ({acct_age:.0f}d)"}
    if freq > MAX_FREQ_PER_DAY:
        return None, {"reason": f"too_frequent ({freq:.1f}/d)"}
    if resolved < MIN_RESOLVED:
        return None, {"reason": f"too_few_resolved ({resolved})"}
    if wr < MIN_WR:                             # v1.1: explicit WR floor
        return None, {"reason": f"wr_too_low ({wr:.1%})"}
    if blocked_pct > 0.30:
        return None, {"reason": f"blocked_markets {blocked_pct:.0%}"}
    if sports_pct < MIN_SPORTS_PCT:
        return None, {"reason": f"sports_pct={sports_pct:.0%} < {MIN_SPORTS_PCT:.0%}"}
    if avg_entry > MAX_AVG_ENTRY:
        return None, {"reason": f"avg_entry=${avg_entry:.3f} > ${MAX_AVG_ENTRY}"}

    # ── Score (v1.1) ──────────────────────────────────────────────────────────
    wr_score      = wr * 35                                    # 35 pts max
    bell_score    = entry_bell_score(avg_entry, max_pts=20)   # 20 pts (Gaussian)
    freq_score    = max(0, (MAX_FREQ_PER_DAY - freq) / MAX_FREQ_PER_DAY) * 10
    diversity_scr = diversity * 10
    age_score     = min(acct_age / 180, 1.0) * 10
    sports_score  = sports_pct * 10
    total         = wr_score + bell_score + freq_score + diversity_scr + age_score + sports_score

    return round(total, 1), {
        "wallet":       wallet,
        "name":         name,
        "score":        round(total, 1),
        "wr":           round(wr, 3),
        "resolved":     resolved,
        "wins":         wins,
        "losses":       losses,
        "avg_entry":    round(avg_entry, 3),
        "bell_score":   bell_score,
        "freq":         round(freq, 1),
        "age_days":     round(acct_age, 0),
        "acct_span_d":  round(span_days, 0),
        "sports_pct":   round(sports_pct, 3),
        "diversity":    round(diversity, 3),
        "blocked_pct":  round(blocked_pct, 3),
        "n_buys":       len(buys),
        "same_sec_clusters": cluster_count,
    }

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 5 — Alert
# ══════════════════════════════════════════════════════════════════════════════
def alert_gem(info, candidate):
    if candidate.get("both"):
        badge = "🎯 LEADERBOARD + WINNING-SIDE"
    elif candidate.get("in_lb"):
        badge = "📈 LEADERBOARD"
    else:
        badge = "🏆 WINNING-SIDE XRef"

    wr_tag = " ✂️ capped" if (info["wr"] == 0.95 and info["resolved"] >= WR_CREDIBILITY_N) else ""

    msg = (
        f"🔭 <b>DEEP SCAN GEM</b>  {badge}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Name   : {info['name']}\n"
        f"Score  : {info['score']}  |  WR: {info['wr']:.1%}{wr_tag} "
        f"({info['wins']}W / {info['losses']}L  n={info['resolved']})\n"
        f"Entry  : ${info['avg_entry']:.3f} (bell={info['bell_score']:.1f}pts)"
        f"  |  Freq: {info['freq']:.1f}/d  |  Age: {info['age_days']:.0f}d\n"
        f"Sports : {info['sports_pct']:.0%}  |  Diversity: {info['diversity']:.2f}"
        f"  |  Same-sec clusters: {info['same_sec_clusters']}\n"
        f"Wallet : <code>{info['wallet']}</code>\n"
    )
    if candidate.get("lb_pnl"):
        msg += f"30d P&L: ${candidate['lb_pnl']:.0f}  Vol: ${candidate.get('lb_volume',0):.0f}\n"
    if candidate.get("win_count"):
        msg += f"XRef wins: {candidate['win_count']} markets\n"
        for sample in candidate.get("win_sample", [])[:2]:
            msg += f"  · {sample}\n"

    tg(msg)
    print(f"\n  🔭 GEM: {info['name']}  score={info['score']}"
          f"  WR={info['wr']:.1%}  entry=${info['avg_entry']:.3f}"
          f"  freq={info['freq']:.1f}/d  age={info['age_days']:.0f}d"
          f"  bell={info['bell_score']:.1f}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    start = datetime.now(timezone.utc)
    print(f"\n{'='*62}")
    print(f"  deep_scanner.py  v1.1   {start.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  LB top-{LEADERBOARD_PAGES*100}  |  XRef {WINNING_MARKETS_N} markets"
          f"  |  MIN_WIN_MARKETS={MIN_WIN_MARKETS}  |  MAX_FREQ={MAX_FREQ_PER_DAY}")
    print(f"{'='*62}\n")

    tg(f"🔭 <b>Deep Scan v1.1 started</b>  {start.strftime('%Y-%m-%d %H:%M UTC')}\n"
       f"LB: {LEADERBOARD_PAGES}×100  |  XRef: {WINNING_MARKETS_N} mkts"
       f"  |  MIN_WIN={MIN_WIN_MARKETS}  |  MIN_WR={MIN_WR:.0%}")

    # Phase 1
    print("[Phase 1] Fetching leaderboard (30d P&L) ...")
    lb_wallets = fetch_leaderboard()

    # Phase 2
    print("\n[Phase 2] Fetching resolved sports markets ...")
    markets = fetch_resolved_sports_markets()
    print("[Phase 2] Scanning winning-side traders ...")
    win_wallets, win_markets_map = fetch_winning_side_wallets(markets)

    # Phase 3
    print("\n[Phase 3] Merging candidates ...")
    candidates = merge_candidates(lb_wallets, win_wallets, win_markets_map)

    if not candidates:
        msg = "🔭 Deep scan complete — 0 new candidates after filtering known wallets"
        tg(msg); print(msg); return

    # Phase 4 — score
    print(f"\n[Phase 4] Scoring {len(candidates)} candidates ...")
    gems     = []
    rejected = []

    sorted_cands = sorted(
        candidates.items(),
        key=lambda kv: (kv[1]["both"], kv[1]["in_lb"], kv[1]["win_count"]),
        reverse=True,
    )

    for wallet, cand in sorted_cands:
        name = cand["name"]
        src  = ("BOTH" if cand["both"] else "LB" if cand["in_lb"]
                else f"XREF×{cand['win_count']}")
        print(f"  [{src}] {name} ({wallet[:10]}...) ", end="", flush=True)

        score, info = score_candidate(wallet, name)
        time.sleep(0.5)

        if score is None:
            reason = info.get("reason", "no_data")
            print(f"→ SKIP  ({reason})")
            rejected.append({"wallet": wallet, "name": name, "reason": reason})
        elif score >= GEM_THRESHOLD:
            # v1.1: apply intersection / XRef depth bonuses
            bonus = 0
            if cand.get("both"):
                bonus += 5
            if cand.get("win_count", 0) >= 7:
                bonus += 3
            if bonus:
                info["score"] = round(score + bonus, 1)
                info["bonus"] = bonus
                print(f"→ 🔥 GEM  score={score}+{bonus}={info['score']}")
            else:
                info["bonus"] = 0
                print(f"→ 🔥 GEM  score={score}")
            gems.append((info["score"], info, cand))
        else:
            print(f"→ score={score}  (below {GEM_THRESHOLD})")
            rejected.append({"wallet": wallet, "name": name,
                              "reason": f"score={score}", "info": info})

    # Phase 5 — alert
    gems.sort(reverse=True, key=lambda x: x[0])
    duration_m = (datetime.now(timezone.utc) - start).seconds // 60

    print(f"\n{'='*62}")
    print(f"  Results: {len(gems)} gem(s) / {len(candidates)} candidates  |  {duration_m}m")
    # Rejection breakdown
    reasons = Counter(r["reason"].split("(")[0].strip() for r in rejected)
    for reason, cnt in reasons.most_common(8):
        print(f"    {cnt:3d}× {reason}")
    print(f"{'='*62}\n")

    if gems:
        for score, info, cand in gems:
            alert_gem(info, cand)
    else:
        tg(f"🔭 Deep scan v1.1 complete — no gems\n"
           f"Scored: {len(candidates)}  |  Threshold: {GEM_THRESHOLD}")

    summary = (
        f"🔭 <b>Deep Scan v1.1 complete</b>\n"
        f"Leaderboard : {len(lb_wallets)} wallets\n"
        f"Winning-side: {len(win_wallets)} wallets (≥{MIN_WIN_MARKETS} mkts)\n"
        f"Candidates  : {len(candidates)}\n"
        f"Gems ≥{GEM_THRESHOLD}     : {len(gems)}\n"
        f"Duration    : {duration_m}m"
    )
    tg(summary)
    print(summary)

    # Save JSON
    out_path = f"/home/ubuntu/copytrade/deep_scan_{start.strftime('%Y%m%d')}.json"
    try:
        with open(out_path, "w") as f:
            json.dump({
                "run_date": start.isoformat(), "version": "1.1",
                "lb_count": len(lb_wallets), "xref_count": len(win_wallets),
                "candidates": len(candidates), "gems_found": len(gems),
                "gems": [{"score": s, "info": i,
                           "source": {"in_lb": c["in_lb"], "in_win": c["in_win"],
                                      "both": c["both"], "lb_pnl": c.get("lb_pnl", 0),
                                      "win_count": c.get("win_count", 0)}}
                          for s, i, c in gems],
                "top_rejected": rejected[:30],
            }, f, indent=2)
        print(f"Saved → {out_path}")
    except Exception as e:
        print(f"[WARN] Could not save JSON: {e}")


if __name__ == "__main__":
    main()
