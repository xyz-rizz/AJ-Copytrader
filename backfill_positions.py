#!/usr/bin/env python3
"""
v7.8.16 backfill: enrich legacy positions.json entries missing conditionId/outcome.
Queries Gamma API for each token_id, writes conditionId + outcome into _meta.
SAFE: only touches conditionId and outcome fields. Never alters stake/trader/etc.
"""
import json, time, sys
import urllib.request

POSITIONS_FILE = "/home/ubuntu/copytrade/positions.json"
GAMMA_API      = "https://gamma-api.polymarket.com"

def fetch_json(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "copytrade-backfill/1.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1.5)
            else:
                raise e

def get_market_meta(token_id):
    """Returns (conditionId, outcome_label) for a token_id via Gamma API."""
    url  = f"{GAMMA_API}/markets?clob_token_ids={token_id}"
    data = fetch_json(url)
    mkts = data if isinstance(data, list) else data.get("markets", [data]) if isinstance(data, dict) else []
    if not mkts:
        raise ValueError(f"No market data for {token_id[:20]}...")
    mkt = mkts[0]

    cid = mkt.get("conditionId") or mkt.get("condition_id")
    if not cid:
        raise ValueError(f"No conditionId in response for {token_id[:20]}...")

    # Resolve outcome name: match token_id to outcomes array
    outcome_label = "Unknown"
    try:
        raw_tokens   = mkt.get("clobTokenIds") or mkt.get("clob_token_ids") or "[]"
        raw_outcomes = mkt.get("outcomes") or "[]"
        tok_list = json.loads(raw_tokens) if isinstance(raw_tokens, str) else raw_tokens
        out_list = json.loads(raw_outcomes) if isinstance(raw_outcomes, str) else raw_outcomes
        for i, tid in enumerate(tok_list):
            if str(tid) == str(token_id):
                if i < len(out_list):
                    outcome_label = out_list[i]
                break
    except Exception:
        pass

    return cid, outcome_label

def main():
    with open(POSITIONS_FILE) as f:
        positions = json.load(f)

    # Collect token_ids that need backfill
    token_ids = [k for k in positions if not k.endswith("_meta")]
    missing   = []
    already   = []

    for tid in token_ids:
        meta = positions.get(f"{tid}_meta", {})
        if not meta.get("conditionId"):
            missing.append(tid)
        else:
            already.append(tid)

    print(f"\n=== BACKFILL AUDIT ===")
    print(f"Total open positions : {len(token_ids)}")
    print(f"Already have conditionId : {len(already)}")
    print(f"Missing conditionId (blind) : {len(missing)}")

    if not missing:
        print("Nothing to backfill.")
        return

    print(f"\n=== BACKFILLING {len(missing)} POSITIONS ===")
    ok_count   = 0
    fail_count = 0
    failures   = []

    for i, tid in enumerate(missing):
        meta = positions.get(f"{tid}_meta", {})
        try:
            cid, outcome = get_market_meta(tid)
            meta["conditionId"] = cid
            meta["outcome"]     = outcome
            positions[f"{tid}_meta"] = meta
            ok_count += 1
            print(f"  [{i+1}/{len(missing)}] ✓  {tid[:28]}…  cond={cid[:22]}…  outcome='{outcome}'")
        except Exception as e:
            fail_count += 1
            failures.append((tid, str(e)))
            print(f"  [{i+1}/{len(missing)}] ✗  {tid[:28]}…  ERROR: {e}")
        time.sleep(0.25)   # gentle rate limiting

    print(f"\n=== RESULTS ===")
    print(f"Successfully backfilled : {ok_count}/{len(missing)}")
    print(f"Failed                  : {fail_count}/{len(missing)}")
    if failures:
        print("Failures:")
        for tid, err in failures:
            print(f"  {tid[:28]}… : {err}")

    # Sample: print a before/after for one entry (the first that was missing)
    if missing:
        sample_tid = missing[0]
        print(f"\n=== SAMPLE (token={sample_tid[:28]}…) ===")
        print(json.dumps(positions.get(f"{sample_tid}_meta", {}), indent=2))

    # Write back ONLY if at least one success
    if ok_count > 0:
        with open(POSITIONS_FILE, "w") as f:
            json.dump(positions, f, indent=2)
        print(f"\n✅ positions.json saved ({ok_count} enriched)")
    else:
        print("\n⚠️  No changes written (0 successes)")

if __name__ == "__main__":
    main()
