#!/usr/bin/env python3
"""
Phase 2: 15-min crypto Up/Down wallet discovery
Full 187-day history (Sep 13, 2025 – Mar 19, 2026) + last 30 days
Uses slug pattern "updown-15m" for precise filtering.

SAMPLING DISCLOSURE:
- Market fetching: ALL pages from offset 120000 to 600000 scanned (no sampling).
  Every market with slug matching "updown-15m" is included.
- Trades analysis (full history): stratified sample of up to 6000 markets.
- Trades analysis (last 30 days): stratified sample of up to 4000 markets (likely all).
"""
import requests, json, time, random, re
from datetime import datetime, timezone, timedelta
from collections import defaultdict

GAMMA_BASE = "https://gamma-api.polymarket.com"
TRADES_BASE = "https://data-api.polymarket.com"
SLEEP = 0.12  # seconds between requests

def is_15min_crypto_ud(market):
    """True if this is a 15-minute crypto Up/Down market (via slug pattern)."""
    slug = market.get("slug", "")
    return "updown-15m" in slug

def get_market_outcome(market):
    """Return (winning_token_id, losing_token_id) or None if not clearly resolved."""
    outcome_prices_raw = market.get("outcomePrices")
    if not outcome_prices_raw:
        return None
    try:
        if isinstance(outcome_prices_raw, str):
            prices = json.loads(outcome_prices_raw)
        else:
            prices = outcome_prices_raw
        prices = [float(p) for p in prices]
    except Exception:
        return None

    clobTokenIds_raw = market.get("clobTokenIds")
    if not clobTokenIds_raw:
        return None
    try:
        if isinstance(clobTokenIds_raw, str):
            tokens = json.loads(clobTokenIds_raw)
        else:
            tokens = clobTokenIds_raw
        tokens = [str(t) for t in tokens]
    except Exception:
        return None

    if len(tokens) < 2 or len(prices) < 2:
        return None

    # Find which token won (price = 1.0) or lost (price = 0.0)
    if prices[0] >= 0.99:
        return (tokens[0], tokens[1])  # tokens[0] won
    elif prices[1] >= 0.99:
        return (tokens[1], tokens[0])  # tokens[1] won
    return None  # Not clearly resolved

def fetch_all_15m_markets():
    """Fetch all resolved 15-min crypto UD markets by scanning relevant offset range."""
    print("Fetching all resolved 15-min crypto UD markets...")
    print("Scanning offsets 120000 to 600000 (step=500)...")
    markets = []
    
    START_OFFSET = 120000
    END_OFFSET = 600000
    LIMIT = 500
    
    total_pages = (END_OFFSET - START_OFFSET) // LIMIT
    pages_done = 0
    empty_streak = 0  # stop early if we hit many empty pages
    
    offset = START_OFFSET
    while offset < END_OFFSET:
        url = f"{GAMMA_BASE}/markets?closed=true&limit={LIMIT}&offset={offset}"
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            batch = r.json()
        except Exception as e:
            print(f"  Error at offset {offset}: {e}, retrying...")
            time.sleep(2)
            continue

        if not batch:
            empty_streak += 1
            if empty_streak >= 5:
                print(f"  5 consecutive empty pages at offset {offset}, stopping.")
                break
        else:
            empty_streak = 0

        matched = [m for m in batch if is_15min_crypto_ud(m)]
        markets.extend(matched)
        pages_done += 1

        if pages_done % 100 == 0:
            pct = (offset - START_OFFSET) / (END_OFFSET - START_OFFSET) * 100
            print(f"  offset={offset} ({pct:.0f}%), matched_so_far={len(markets)}, page_matched={len(matched)}")

        if len(batch) < LIMIT:
            print(f"  Batch smaller than limit at offset {offset} (got {len(batch)}), continuing...")
            # Don't break — might just be a gap

        offset += LIMIT
        time.sleep(SLEEP)

    print(f"Total resolved 15-min crypto UD markets found: {len(markets)}")
    return markets

def get_trades_for_market(condition_id):
    """Fetch all trades for a market (paginated up to 10 pages / 5000 trades)."""
    all_trades = []
    limit = 500
    offset = 0
    for _ in range(10):
        url = f"{TRADES_BASE}/trades?market={condition_id}&limit={limit}&offset={offset}"
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            trades = r.json()
        except Exception:
            break
        if not trades:
            break
        all_trades.extend(trades)
        if len(trades) < limit:
            break
        offset += limit
        time.sleep(0.05)
    return all_trades

def get_asset_from_title(title):
    """Extract crypto asset name from market title."""
    title_lower = title.lower()
    if "bitcoin" in title_lower or "btc" in title_lower:
        return "BTC"
    elif "ethereum" in title_lower or "eth" in title_lower:
        return "ETH"
    elif "solana" in title_lower or "sol" in title_lower:
        return "SOL"
    elif "xrp" in title_lower:
        return "XRP"
    elif "bnb" in title_lower:
        return "BNB"
    elif "dogecoin" in title_lower or "doge" in title_lower:
        return "DOGE"
    elif "hyperliquid" in title_lower or "hype" in title_lower:
        return "HYPE"
    return "OTHER"

def analyze_markets(markets, window_name, max_markets=None):
    """
    For a list of markets, fetch trades and compute per-wallet stats.
    SAMPLING: If max_markets < len(markets), uses stratified chronological sampling.
    Returns (wallet_stats, sampling_note).
    """
    sampled = markets
    sampling_note = f"All {len(markets)} markets (no sampling)"
    if max_markets and len(markets) > max_markets:
        # Stratified sample: evenly spaced chronologically
        step = len(markets) / max_markets
        indices = [int(i * step) for i in range(max_markets)]
        sampled = [markets[i] for i in indices]
        sampling_note = (
            f"Stratified sample of {len(sampled)} / {len(markets)} markets "
            f"(every {step:.1f}th market chronologically)"
        )

    print(f"\n[{window_name}] {sampling_note}")
    print(f"  Processing {len(sampled)} markets...")

    # wallet -> stats
    wallet_trades = defaultdict(list)
    wallet_days = defaultdict(set)
    wallet_assets = defaultdict(lambda: defaultdict(int))

    errors = 0
    markets_with_trades = 0

    for i, market in enumerate(sampled):
        condition_id = market.get("conditionId")
        if not condition_id:
            continue

        outcome = get_market_outcome(market)
        if outcome is None:
            continue  # Skip markets where we can't determine winner

        winning_token, losing_token = outcome
        title = market.get("question") or market.get("title") or ""
        asset = get_asset_from_title(title)
        end_date = (market.get("endDate") or "")[:10]

        trades = get_trades_for_market(condition_id)
        if not trades:
            errors += 1
        else:
            markets_with_trades += 1

        # Track per-wallet, per-market positions
        # key = proxyWallet, value = {winning_side_buys, losing_side_buys, sells, prices}
        market_positions = defaultdict(lambda: {
            "win_size": 0.0, "lose_size": 0.0,
            "win_buys": 0, "lose_buys": 0,
            "total_sells": 0, "prices": []
        })

        for t in trades:
            # Primary wallet identifier: proxyWallet
            wallet = (t.get("proxyWallet") or "").lower()
            if not wallet or wallet == "0x0000000000000000000000000000000000000000":
                continue

            side = (t.get("side") or "").upper()  # BUY or SELL
            asset_id = str(t.get("asset") or t.get("asset_id") or t.get("assetId") or "")
            price = float(t.get("price") or 0)
            size = float(t.get("size") or 0)

            try:
                ts = t.get("timestamp")
                if isinstance(ts, (int, float)):
                    trade_dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                    day_str = trade_dt.strftime("%Y-%m-%d")
                    wallet_days[wallet].add(day_str)
            except Exception:
                pass

            if side == "BUY":
                if asset_id == winning_token:
                    market_positions[wallet]["win_size"] += size
                    market_positions[wallet]["win_buys"] += 1
                elif asset_id == losing_token:
                    market_positions[wallet]["lose_size"] += size
                    market_positions[wallet]["lose_buys"] += 1
                market_positions[wallet]["prices"].append(price)
                wallet_assets[wallet][asset] += 1
            elif side == "SELL":
                market_positions[wallet]["total_sells"] += 1

        # Convert market positions to win/loss per wallet
        for wallet, pos in market_positions.items():
            win_size = pos["win_size"]
            lose_size = pos["lose_size"]
            prices = pos["prices"]

            # Determine net position result
            if win_size > 0 and lose_size == 0:
                result = "WIN"
            elif lose_size > 0 and win_size == 0:
                result = "LOSS"
            elif win_size > 0 and lose_size > 0:
                result = "MIXED"  # Bought both sides (market maker or hedger)
            else:
                continue  # No buy position

            total_buys = pos["win_buys"] + pos["lose_buys"]
            total_sells = pos["total_sells"]
            total_trades = total_buys + total_sells
            sell_ratio = total_sells / total_trades if total_trades > 0 else 0
            avg_price = sum(prices) / len(prices) if prices else 0

            wallet_trades[wallet].append({
                "result": result,
                "avg_price": avg_price,
                "buys": total_buys,
                "sells": total_sells,
                "sell_ratio": sell_ratio,
                "end_date": end_date,
                "asset": asset,
            })

        if (i + 1) % 200 == 0:
            elapsed_pct = (i + 1) / len(sampled) * 100
            print(f"  [{window_name}] {i+1}/{len(sampled)} ({elapsed_pct:.0f}%), "
                  f"{len(wallet_trades)} wallets, {errors} errors")

        time.sleep(SLEEP)

    print(f"  [{window_name}] Done. Markets: {len(sampled)}, with_trades={markets_with_trades}, "
          f"errors={errors}, unique_wallets={len(wallet_trades)}")

    # Compute per-wallet summary
    results = {}
    for wallet, positions in wallet_trades.items():
        wins = sum(1 for p in positions if p["result"] == "WIN")
        losses = sum(1 for p in positions if p["result"] == "LOSS")
        mixed = sum(1 for p in positions if p["result"] == "MIXED")
        total = wins + losses + mixed

        all_prices = [p["avg_price"] for p in positions if p["avg_price"] > 0]
        all_sell_ratios = [p["sell_ratio"] for p in positions]
        all_buys = sum(p["buys"] for p in positions)
        all_sells = sum(p["sells"] for p in positions)

        days = wallet_days.get(wallet, set())

        asset_mix = dict(wallet_assets[wallet])

        results[wallet] = {
            "wins": wins,
            "losses": losses,
            "mixed": mixed,
            "total_markets": total,
            "win_rate": wins / (wins + losses) if (wins + losses) > 0 else 0,
            "avg_entry_price": sum(all_prices) / len(all_prices) if all_prices else 0,
            "median_entry_price": sorted(all_prices)[len(all_prices) // 2] if all_prices else 0,
            "avg_sell_ratio": sum(all_sell_ratios) / len(all_sell_ratios) if all_sell_ratios else 0,
            "total_buys": all_buys,
            "total_sells": all_sells,
            "active_days": len(days),
            "trades_per_day": all_buys / len(days) if days else 0,
            "asset_mix": asset_mix,
        }

    return results, sampling_note


def apply_filters(stats, min_markets, min_wr):
    """Return list of flag strings for a wallet's stats. Empty list = clean."""
    total = stats["total_markets"]
    wr = stats["win_rate"]
    avg_price = stats["avg_entry_price"]
    sell_ratio = stats["avg_sell_ratio"]

    flags = []

    # Post-resolution settlement bot: consistently enters at very high prices
    if avg_price > 0.90 and total >= 5:
        flags.append("POST_RESOLUTION_BOT")

    # Market maker: too many mixed (both sides) positions
    if stats["mixed"] > max(stats["wins"] + stats["losses"], 1):
        flags.append("MARKET_MAKER")

    # High sell ratio (CLOB exit / scalper not holding to resolution)
    if sell_ratio > 0.70:
        flags.append("HIGH_SELL_RATIO_SCALPER")

    # Tiny sample
    if total < min_markets:
        flags.append("TINY_SAMPLE")

    # Low win rate
    if wr < min_wr and total >= min_markets:
        flags.append("LOW_WIN_RATE")

    return flags


def main():
    random.seed(42)
    start_time = datetime.now(timezone.utc)

    # 1. Fetch all markets
    all_markets = fetch_all_15m_markets()

    # Sort chronologically by endDate
    def get_end_ts(m):
        ed = m.get("endDate") or ""
        try:
            return datetime.fromisoformat(ed.replace("Z", "+00:00")).timestamp()
        except Exception:
            return 0
    all_markets.sort(key=get_end_ts)

    now = datetime.now(timezone.utc)
    cutoff_30d = now - timedelta(days=30)
    cutoff_start = datetime(2025, 9, 13, tzinfo=timezone.utc)

    # Split windows
    full_markets = []
    recent_markets = []
    for m in all_markets:
        ed = m.get("endDate") or ""
        try:
            end_dt = datetime.fromisoformat(ed.replace("Z", "+00:00"))
        except Exception:
            end_dt = None

        if end_dt is None or end_dt >= cutoff_start:
            full_markets.append(m)
            if end_dt and end_dt >= cutoff_30d:
                recent_markets.append(m)

    print(f"\nMarket windows:")
    print(f"  Full history (Sep 13, 2025 – Mar 19, 2026): {len(full_markets)} markets")
    print(f"  Last 30 days (Feb 18 – Mar 19, 2026): {len(recent_markets)} markets")

    # 2. Analyze both windows
    # Full history: sample up to 6000 markets (stratified chronologically)
    full_stats, full_note = analyze_markets(full_markets, "FULL_HISTORY", max_markets=6000)

    # Last 30 days: sample up to 4000 markets (likely under 4000, so no sampling)
    recent_stats, recent_note = analyze_markets(recent_markets, "LAST_30_DAYS", max_markets=4000)

    # 3. Apply filters and rank
    MAIN_MIN = 30          # full history: min resolved markets
    MAIN_RECENT_MIN = 15   # last 30 days: min resolved markets
    MAIN_WR = 0.65

    STRICT_MIN = 80        # strict full history
    STRICT_RECENT_MIN = 30 # strict last 30 days
    STRICT_WR = 0.70

    RECENT_DAY_MIN = 5     # must be active ≥5 different days

    full_wallet_ids = set(full_stats.keys())
    recent_wallet_ids = set(recent_stats.keys())
    intersection_ids = full_wallet_ids & recent_wallet_ids

    print(f"\nWallet overlap: {len(intersection_ids)} wallets appear in both windows")

    # Full history qualified
    full_qualified = []
    for w, s in full_stats.items():
        flags = apply_filters(s, MAIN_MIN, MAIN_WR)
        disqualifying = [f for f in flags if f not in ("LOW_WIN_RATE", "TINY_SAMPLE")]
        if not disqualifying and s["total_markets"] >= MAIN_MIN and s["win_rate"] >= MAIN_WR:
            full_qualified.append((w, s, flags))
    full_qualified.sort(key=lambda x: (-x[1]["win_rate"], -x[1]["total_markets"]))

    # Recent qualified
    recent_qualified = []
    for w, s in recent_stats.items():
        flags = apply_filters(s, MAIN_RECENT_MIN, MAIN_WR)
        disqualifying = [f for f in flags if f not in ("LOW_WIN_RATE", "TINY_SAMPLE")]
        if (not disqualifying and
                s["total_markets"] >= MAIN_RECENT_MIN and
                s["win_rate"] >= MAIN_WR and
                s["active_days"] >= RECENT_DAY_MIN):
            recent_qualified.append((w, s, flags))
    recent_qualified.sort(key=lambda x: (-x[1]["win_rate"], -x[1]["total_markets"]))

    # Intersection qualified (strong in BOTH windows)
    intersection_qualified = []
    for w in intersection_ids:
        fs = full_stats[w]
        rs = recent_stats[w]
        full_flags = apply_filters(fs, MAIN_MIN, MAIN_WR)
        recent_flags = apply_filters(rs, MAIN_RECENT_MIN, MAIN_WR)
        fdq = [f for f in full_flags if f not in ("LOW_WIN_RATE", "TINY_SAMPLE")]
        rdq = [f for f in recent_flags if f not in ("LOW_WIN_RATE", "TINY_SAMPLE")]
        if (not fdq and not rdq and
                fs["total_markets"] >= MAIN_MIN and fs["win_rate"] >= MAIN_WR and
                rs["total_markets"] >= MAIN_RECENT_MIN and rs["win_rate"] >= MAIN_WR and
                rs["active_days"] >= RECENT_DAY_MIN):
            intersection_qualified.append((w, fs, rs, full_flags, recent_flags))
    intersection_qualified.sort(
        key=lambda x: (-(x[1]["win_rate"] + x[2]["win_rate"]) / 2, -x[1]["total_markets"])
    )

    # High frequency (last 30 days)
    hf_qualified = [
        (w, s) for w, s in recent_stats.items()
        if (s["trades_per_day"] >= 3 and
            s["total_markets"] >= 15 and
            s["win_rate"] >= 0.60 and
            s["avg_entry_price"] < 0.90 and
            s["active_days"] >= 4 and
            s["avg_sell_ratio"] <= 0.70)
    ]
    hf_qualified.sort(key=lambda x: -x[1]["trades_per_day"])

    # Strict full-history shortlist
    strict_full = [
        (w, s, f) for w, s, f in full_qualified
        if s["total_markets"] >= STRICT_MIN and s["win_rate"] >= STRICT_WR
    ]

    # Strict recent shortlist
    strict_recent = [
        (w, s, f) for w, s, f in recent_qualified
        if s["total_markets"] >= STRICT_RECENT_MIN and s["win_rate"] >= STRICT_WR
        and s["active_days"] >= 7
    ]

    # Red flag wallets (post-resolution bots, MMs)
    red_flags_full = [
        (w, s, apply_filters(s, 10, 0))
        for w, s in full_stats.items()
        if (("POST_RESOLUTION_BOT" in apply_filters(s, 10, 0) or
             "MARKET_MAKER" in apply_filters(s, 10, 0)) and
            s["total_markets"] >= 15)
    ]
    red_flags_full.sort(key=lambda x: -x[1]["total_markets"])

    # 4. Build report
    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    lines = []
    lines.append("=" * 80)
    lines.append("PHASE 2: 15-MIN CRYPTO UP/DOWN WALLET DISCOVERY")
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"Runtime: {elapsed/60:.1f} minutes")
    lines.append("=" * 80)

    lines.append("\n--- 1. MARKET UNIVERSE ---")
    lines.append("Family: Polymarket 15-minute crypto Up/Down (slug: *-updown-15m-*)")
    lines.append("Full history span: Sep 13, 2025 – Mar 19, 2026 (187 days)")
    lines.append(f"Full history markets: {len(full_markets)}")
    lines.append(f"Last 30 days markets: {len(recent_markets)}")
    lines.append(f"Sampling (full history): {full_note}")
    lines.append(f"Sampling (last 30 days): {recent_note}")
    lines.append("Assets covered: BTC, ETH, SOL, XRP, BNB, DOGE, HYPE")

    lines.append("\n--- 2. WALLET UNIVERSE ---")
    lines.append(f"Full history unique wallets seen: {len(full_stats)}")
    lines.append(f"Last 30 days unique wallets seen: {len(recent_stats)}")
    lines.append(f"Intersection (in both): {len(intersection_ids)}")

    # Distribution stats for full history
    wr_dist = [0]*10  # 0-10%, 10-20%, ... 90-100%
    for s in full_stats.values():
        bucket = min(int(s["win_rate"] * 10), 9)
        wr_dist[bucket] += 1
    lines.append("\nWin rate distribution (full history, all wallets):")
    for i, cnt in enumerate(wr_dist):
        lines.append(f"  {i*10:3d}-{(i+1)*10:3d}%: {cnt} wallets")

    lines.append("\n--- 3. BEST FULL-HISTORY WALLETS (Top 25) ---")
    lines.append(f"Criteria: >={MAIN_MIN} resolved mkts, WR>={MAIN_WR:.0%}, no POST_RES_BOT/MM/HIGH_SELL flags")
    header = f"{'Wallet':<44} {'W':>5} {'L':>5} {'WR':>7} {'Mkts':>6} {'AvgPx':>7} {'SellR':>6} {'Days':>5} {'Top asset'}"
    lines.append(header)
    lines.append("-" * len(header))
    for w, s, f in full_qualified[:25]:
        top_asset = sorted(s["asset_mix"].items(), key=lambda x: -x[1])
        top_str = f"{top_asset[0][0]}({top_asset[0][1]})" if top_asset else ""
        lines.append(
            f"{w:<44} {s['wins']:>5} {s['losses']:>5} {s['win_rate']:>7.1%} "
            f"{s['total_markets']:>6} {s['avg_entry_price']:>7.3f} {s['avg_sell_ratio']:>6.1%} "
            f"{s['active_days']:>5} {top_str}"
        )

    lines.append(f"\n  Total qualified (full history): {len(full_qualified)}")

    lines.append(f"\n--- STRICT FULL-HISTORY SHORTLIST (>={STRICT_MIN} mkts, WR>={STRICT_WR:.0%}) ---")
    if strict_full:
        for w, s, f in strict_full[:15]:
            top_asset = sorted(s["asset_mix"].items(), key=lambda x: -x[1])
            top_str = "+".join(f"{a}({n})" for a, n in top_asset[:2])
            lines.append(
                f"  {w:<44} WR={s['win_rate']:.1%} ({s['wins']}W/{s['losses']}L/{s['total_markets']}tot) "
                f"avg_px={s['avg_entry_price']:.3f} sell={s['avg_sell_ratio']:.1%} "
                f"days={s['active_days']} buys={s['total_buys']} {top_str}"
            )
    else:
        lines.append("  (none qualified)")

    lines.append(f"\n--- 4. BEST LAST-30-DAY WALLETS (Top 25) ---")
    lines.append(f"Criteria: >={MAIN_RECENT_MIN} resolved, >={RECENT_DAY_MIN} active days, WR>={MAIN_WR:.0%}")
    header2 = f"{'Wallet':<44} {'W':>5} {'L':>5} {'WR':>7} {'Mkts':>6} {'AvgPx':>7} {'SellR':>6} {'Days':>5} {'T/day':>6}"
    lines.append(header2)
    lines.append("-" * len(header2))
    for w, s, f in recent_qualified[:25]:
        lines.append(
            f"{w:<44} {s['wins']:>5} {s['losses']:>5} {s['win_rate']:>7.1%} "
            f"{s['total_markets']:>6} {s['avg_entry_price']:>7.3f} {s['avg_sell_ratio']:>6.1%} "
            f"{s['active_days']:>5} {s['trades_per_day']:>6.1f}"
        )
    lines.append(f"\n  Total qualified (last 30 days): {len(recent_qualified)}")

    lines.append(f"\n--- STRICT LAST-30-DAY SHORTLIST (>={STRICT_RECENT_MIN} mkts, >={7} days, WR>={STRICT_WR:.0%}) ---")
    if strict_recent:
        for w, s, f in strict_recent[:15]:
            top_asset = sorted(s["asset_mix"].items(), key=lambda x: -x[1])
            top_str = "+".join(f"{a}({n})" for a, n in top_asset[:2])
            lines.append(
                f"  {w:<44} WR={s['win_rate']:.1%} ({s['wins']}W/{s['losses']}L/{s['total_markets']}tot) "
                f"avg_px={s['avg_entry_price']:.3f} sell={s['avg_sell_ratio']:.1%} "
                f"days={s['active_days']} T/day={s['trades_per_day']:.1f} {top_str}"
            )
    else:
        lines.append("  (none qualified)")

    lines.append(f"\n--- 5. INTERSECTION: STRONG IN BOTH WINDOWS ---")
    lines.append(f"Criteria: >={MAIN_MIN} full, >={MAIN_RECENT_MIN} recent, WR>={MAIN_WR:.0%} in both, >={RECENT_DAY_MIN} recent days")
    if intersection_qualified:
        for w, fs, rs, ff, rf in intersection_qualified[:20]:
            lines.append(
                f"  {w:<44} "
                f"FULL: {fs['win_rate']:.1%} ({fs['wins']}W/{fs['losses']}L/{fs['total_markets']}tot) | "
                f"RECENT: {rs['win_rate']:.1%} ({rs['wins']}W/{rs['losses']}L/{rs['total_markets']}tot) "
                f"days={rs['active_days']} px={rs['avg_entry_price']:.3f} sell={rs['avg_sell_ratio']:.1%}"
            )
    else:
        lines.append("  (none qualified in both windows)")

    lines.append(f"\n--- 6. HIGH-FREQUENCY SHORTLIST (>=3 T/day, >=15 mkts, WR>=60%) ---")
    if hf_qualified:
        for w, s in hf_qualified[:15]:
            top_asset = sorted(s["asset_mix"].items(), key=lambda x: -x[1])
            top_str = f"{top_asset[0][0]}" if top_asset else ""
            lines.append(
                f"  {w:<44} WR={s['win_rate']:.1%} ({s['wins']}W/{s['losses']}L) "
                f"T/day={s['trades_per_day']:.1f} days={s['active_days']} "
                f"px={s['avg_entry_price']:.3f} sell={s['avg_sell_ratio']:.1%} {top_str}"
            )
    else:
        lines.append("  (none qualified)")

    lines.append(f"\n--- 7. RED-FLAG WALLETS (Top 10 Post-Res Bots / Market Makers) ---")
    for w, s, f in red_flags_full[:10]:
        lines.append(
            f"  {w:<44} flags={f} avg_px={s['avg_entry_price']:.3f} "
            f"WR={s['win_rate']:.1%} ({s['total_markets']} mkts)"
        )

    lines.append(f"\n--- 8. SUMMARY ---")
    lines.append(f"  Markets scanned: Full={len(full_markets)}, Recent={len(recent_markets)}")
    lines.append(f"  Markets analyzed: Full={len(full_markets) if not (max(len(full_markets)-1,1)) else min(6000,len(full_markets))}, "
                 f"Recent={min(4000,len(recent_markets))}")
    lines.append(f"  Unique wallets: Full={len(full_stats)}, Recent={len(recent_stats)}, Intersection={len(intersection_ids)}")
    lines.append(f"  Qualified (>=30 mkts, WR>=65%, no bad flags): Full={len(full_qualified)}, Recent={len(recent_qualified)}")
    lines.append(f"  Intersection qualified (both windows): {len(intersection_qualified)}")
    lines.append(f"  Strict full shortlist (>=80 mkts, WR>=70%): {len(strict_full)}")
    lines.append(f"  Strict recent shortlist (>=30 mkts, WR>=70%): {len(strict_recent)}")
    lines.append(f"  High-freq (>=3 T/day): {len(hf_qualified)}")

    lines.append(f"\n--- 9. LIMITATIONS & SAMPLING DISCLOSURE ---")
    lines.append(f"  Market fetching: All pages scanned (offset 120000-600000, step 500).")
    lines.append(f"  Sampling (full): {full_note}")
    lines.append(f"  Sampling (recent): {recent_note}")
    lines.append(f"  Wallet ID: proxyWallet field from trades API (not raw EOA)")
    lines.append(f"  Outcome: determined from outcomePrices JSON field (price>=0.99 = winner)")
    lines.append(f"  WIN/LOSS: net buy position on winning vs losing token per market")
    lines.append(f"  MIXED positions (both sides bought) counted separately, excluded from WR numerator")
    lines.append(f"  Active days: based on trade timestamps")
    lines.append(f"  IMPORTANT: ALL crypto markets are hard-banned in copytrade bot config.")
    lines.append(f"  This analysis is informational only — no crypto trader can be added to bot.")
    lines.append(f"  Use this data for: edge verification, cross-market pattern detection,")
    lines.append(f"  understanding if crypto traders also bet on sports markets.")

    report = "\n".join(lines)
    print("\n" + report)

    # Save files
    with open("/home/ubuntu/copytrade/phase2_report.txt", "w") as f:
        f.write(report)

    output = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "runtime_minutes": round(elapsed / 60, 1),
        "sampling": {"full": full_note, "recent": recent_note},
        "market_counts": {"full": len(full_markets), "recent": len(recent_markets)},
        "wallet_counts": {
            "full": len(full_stats),
            "recent": len(recent_stats),
            "intersection": len(intersection_ids),
        },
        "qualified_counts": {
            "full": len(full_qualified),
            "recent": len(recent_qualified),
            "intersection": len(intersection_qualified),
            "strict_full": len(strict_full),
            "strict_recent": len(strict_recent),
            "high_freq": len(hf_qualified),
        },
        "full_top30": [(w, s) for w, s, f in full_qualified[:30]],
        "recent_top30": [(w, s) for w, s, f in recent_qualified[:30]],
        "intersection": [(w, fs, rs) for w, fs, rs, ff, rf in intersection_qualified[:20]],
        "strict_full": [(w, s) for w, s, f in strict_full[:15]],
        "strict_recent": [(w, s) for w, s, f in strict_recent[:15]],
        "high_freq": [(w, s) for w, s in hf_qualified[:15]],
        "red_flags": [(w, s, f) for w, s, f in red_flags_full[:20]],
        "full_stats_all": full_stats,
        "recent_stats_all": recent_stats,
    }

    with open("/home/ubuntu/copytrade/phase2_results.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nSaved: /home/ubuntu/copytrade/phase2_report.txt")
    print(f"Saved: /home/ubuntu/copytrade/phase2_results.json")
    print(f"Total runtime: {elapsed/60:.1f} minutes")


if __name__ == "__main__":
    main()
