#!/usr/bin/env python3
"""
patch_789.py — copytrade_bot.py v7.8.8 → v7.8.9
Proven-core effective-stake upgrade to $18-20 effective per trade.

Changes (4 proven core traders only — nothing else touched):
  Global stop:       -35  → -40
  Signal47 stop:     -15  → -20 | max_stake: 15.0 → 20.0
  Immense stop:      -15  → -20 | max_stake: 15.0 → 20.0
  Triangular stop:   -12  → -20 | stake_mult: 0.7 → 0.85 | max_stake: 12.0 → 20.0
  Unwieldy stop:     -12  → -20 | stake_mult: 0.8 → 0.9  | max_stake: 12.0 → 20.0

Effective stake math (STAKE_USDC=$20, edge_factor=1.5× for proven core):
  Signal47  (1.2×, $20 cap): 20×1.2×pf×1.5 → at p=0.6: $21.6 capped $20 ✓
  Immense   (0.9×, $20 cap): 20×0.9×pf×1.5 → at p=0.6: $16.2–$27 → $20 cap ✓
  Triangular(0.85×,$20 cap): 20×0.85×pf×1.5 → at p=0.5: $25.5→$20; p=0.6: $20.4→$20 ✓
  Unwieldy  (0.9×, $20 cap): 20×0.9×pf×1.5 → at p=0.5: $27→$20; p=0.6: $21.6→$20 ✓
"""

import shutil, sys, os

BOT = "/home/ubuntu/copytrade/copytrade_bot.py"
BAK = "/home/ubuntu/copytrade/copytrade_bot.py.bak_pre789"

# ── read ──────────────────────────────────────────────────────────────────────
with open(BOT, "r") as f:
    original = f.read()
text = original

errors = []

def replace_one(old, new, label):
    global text, errors
    count = text.count(old)
    if count != 1:
        errors.append(f"FAIL [{label}]: found {count} occurrences (expected 1)")
        return
    text = text.replace(old, new, 1)
    print(f"  OK  [{label}]")

# ── PATCH 1: version string ───────────────────────────────────────────────────
replace_one(
    "Polymarket Autonomous Copy-Trade Bot  v7.8.8",
    "Polymarket Autonomous Copy-Trade Bot  v7.8.9",
    "version_string"
)

# ── PATCH 2: version in docstring first line ──────────────────────────────────
replace_one(
    "v7.8.8 (2026-03-11) — Proven-core sizing upgrade (fresh capital $285) + bench chenpengzao:",
    "v7.8.9 (2026-03-11) — Proven-core effective-stake upgrade to $18-20 (4 traders only):\n  Signal47: max $15→$20, stop -$15→-$20 | Immense: max $15→$20, stop -$15→-$20\n  Triangular: mult 0.7→0.85, max $12→$20, stop -$12→-$20 | Unwieldy: mult 0.8→0.9, max $12→$20, stop -$12→-$20\n  Global stop: -$35→-$40. Nothing else touched.\nv7.8.8 (2026-03-11) — Proven-core sizing upgrade (fresh capital $285) + bench chenpengzao:",
    "docstring_version"
)

# ── PATCH 3: global stop -35 → -40 ────────────────────────────────────────────
replace_one(
    '    "global":     -35,   # v7.8.8: proportional to $285 bankroll | was: -25 survival',
    '    "global":     -40,   # v7.8.9: proportional to 4x$20 proven core sizing | was: -35',
    "global_stop"
)

# ── PATCH 4: Signal47 per-trader stop -15 → -20 ───────────────────────────────
replace_one(
    '        "Signal47-Bets":     -15,  # v7.8.8: proven core unlock | 54W/2L | was: -8 survival',
    '        "Signal47-Bets":     -20,  # v7.8.9: proven core $20 sizing | was: -15',
    "signal47_stop"
)

# ── PATCH 5: Immense per-trader stop -15 → -20 ────────────────────────────────
replace_one(
    '        "Immense-Gokart":    -15,  # v7.8.8: proven core unlock | 53W/0L | was: -10 survival',
    '        "Immense-Gokart":    -20,  # v7.8.9: proven core $20 sizing | was: -15',
    "immense_stop"
)

# ── PATCH 6: Triangular-Box per-trader stop -12 → -20 ─────────────────────────
replace_one(
    '        "Triangular-Box":    -12,  # v7.8.8: proven core upgrade | 198W/3L | was: -8 survival',
    '        "Triangular-Box":    -20,  # v7.8.9: proven core $20 sizing | was: -12',
    "triangular_stop"
)

# ── PATCH 7: Unwieldy-Forage per-trader stop -12 → -20 ────────────────────────
replace_one(
    '        "Unwieldy-Forage":   -12,  # v7.8.8: proven core upgrade | 160W/9L +94% ROI | was: -8 survival',
    '        "Unwieldy-Forage":   -20,  # v7.8.9: proven core $20 sizing | was: -12',
    "unwieldy_stop"
)

# ── PATCH 8: Signal47 max_stake 15.0 → 20.0 ──────────────────────────────────
replace_one(
    '        "stake_mult": 1.2, "max_stake": 15.0,   # v7.8.8: proven core unlock | 54W/2L earned | was: 8.0',
    '        "stake_mult": 1.2, "max_stake": 20.0,   # v7.8.9: proven core $20 sizing | was: 15.0',
    "signal47_max_stake"
)

# ── PATCH 9: Immense max_stake 15.0 → 20.0 ───────────────────────────────────
replace_one(
    '        "stake_mult": 0.9, "max_stake": 15.0,   # v7.8.8: proven core unlock | 53W/0L zero losses | was: 10.0',
    '        "stake_mult": 0.9, "max_stake": 20.0,   # v7.8.9: proven core $20 sizing | was: 15.0',
    "immense_max_stake"
)

# ── PATCH 10: Triangular stake_mult 0.7→0.85, max_stake 12.0→20.0 ─────────────
replace_one(
    '        "stake_mult": 0.7, "max_stake": 12.0,   # v7.8.8: proven core upgrade | 198W/3L +48% ROI | was: 8.0',
    '        "stake_mult": 0.85, "max_stake": 20.0,  # v7.8.9: proven core $20 sizing | mult 0.7→0.85 | was: 12.0',
    "triangular_mult_and_max"
)

# ── PATCH 11: Unwieldy stake_mult 0.8→0.9, max_stake 12.0→20.0 ───────────────
replace_one(
    '        "stake_mult": 0.8, "max_stake": 12.0,   # v7.8.8: proven core upgrade | 160W/9L +94% ROI best | was: 8.0',
    '        "stake_mult": 0.9, "max_stake": 20.0,   # v7.8.9: proven core $20 sizing | mult 0.8→0.9 | was: 12.0',
    "unwieldy_mult_and_max"
)

# ── ABORT if any patch failed ─────────────────────────────────────────────────
if errors:
    print("\n\nPATCH FAILED — no changes written:")
    for e in errors:
        print(" ", e)
    sys.exit(1)

# ── VERIFY: key values present in final text ──────────────────────────────────
print("\n── verification checks ──")
checks = [
    ('v7.8.9',                                                      "version_in_text"),
    ('"global":     -40,',                                          "global_stop_is_40"),
    ('"Signal47-Bets":     -20,',                                   "signal47_stop_is_20"),
    ('"Immense-Gokart":    -20,',                                   "immense_stop_is_20"),
    ('"Triangular-Box":    -20,',                                   "triangular_stop_is_20"),
    ('"Unwieldy-Forage":   -20,',                                   "unwieldy_stop_is_20"),
    ('"stake_mult": 1.2, "max_stake": 20.0,',                       "signal47_max_is_20"),
    ('"stake_mult": 0.9, "max_stake": 20.0,',                       "immense_max_is_20"),
    ('"stake_mult": 0.85, "max_stake": 20.0,',                      "triangular_mult_085_max_20"),
    # Unwieldy now has 0.9/20.0 — but Immense also has 0.9/20.0 so check count=2
    # (they are on different lines so replacement was unique at patch time)
    ('"gem62-NBA":         -12,',                                    "gem62_stop_unchanged"),
    ('"bigwhale1337":       -15,',                                   "bigwhale_stop_unchanged"),
    ('"InfoEdge-a2ed":      -20,',                                   "infoedge_stop_unchanged"),
    ('"chenpengzao":       -10,',                                    "chenpengzao_unchanged"),
    # Ensure old proven-core values are gone (other traders may still have 12/15 — that's fine)
    ('"global":     -35,',                                           "old_global_gone"),
    ('"Signal47-Bets":     -15,',                                    "old_signal47_stop_gone"),
    ('"Immense-Gokart":    -15,',                                    "old_immense_stop_gone"),
    ('"Triangular-Box":    -12,',                                    "old_triangular_stop_gone"),
    ('"Unwieldy-Forage":   -12,',                                    "old_unwieldy_stop_gone"),
    # NOTE: "max_stake": 12.0 and 15.0 may still exist for OTHER (benched) traders — do not check for absence
]

fail_checks = []
for needle, label in checks:
    present = needle in text
    # checks starting with "old_" should be ABSENT; others should be PRESENT
    if label.startswith("old_"):
        if present:
            fail_checks.append(f"FAIL [{label}]: old value still present: {needle!r}")
        else:
            print(f"  OK  [{label}] — correctly absent")
    else:
        if not present:
            fail_checks.append(f"FAIL [{label}]: expected value missing: {needle!r}")
        else:
            print(f"  OK  [{label}]")

if fail_checks:
    print("\n\nVERIFICATION FAILED — no changes written:")
    for f in fail_checks:
        print(" ", f)
    sys.exit(1)

# ── write ─────────────────────────────────────────────────────────────────────
shutil.copy2(BOT, BAK)
print(f"\nBackup: {BAK}")

with open(BOT, "w") as f:
    f.write(text)

print(f"Written: {BOT}")
print("patch_789.py COMPLETE — v7.8.9 ready.")
