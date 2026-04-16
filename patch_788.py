#!/usr/bin/env python3
"""patch_788.py — v7.8.8: Proven-core sizing upgrade + chenpengzao bench

Context: Fresh capital deposit → total balance ~$285.
Audit findings:
  Signal47-Bets:   54W/2L  +67.8% ROI — PROVEN CORE. Survival cap $8 actively shutting it down.
  Immense-Gokart:  53W/0L  +53.9% ROI — PROVEN CORE. Zero losses ever. $10 is a leash, not a limit.
  Triangular-Box: 198W/3L  +48.2% ROI — PROVEN CORE. Highest volume, massive sample confidence.
  Unwieldy-Forage:160W/9L  +93.8% ROI — PROVEN CORE. Best ROI in the entire bot history.
  chenpengzao:     3W/4L   -48.1% ROI — FAILING. Probation rule: 4 losses > 2 before 3 wins. BENCH.

NO changes to:
  gem62-NBA (1W resolved, thin), gem61-WBC (1 fire, no resolved),
  NBA-9c88 (0W/1L early, keep current),
  bigwhale1337 (0 bot fires, active externally — let it prove itself),
  InfoEdge-a2ed (0 bot fires, active externally — let it prove itself).

CHANGES:
  Global stop:      -25 → -35  (proportional to $285 bankroll; 12.3% daily floor)
  Signal47-Bets:    max $8  → $15 | stop -$8  → -$15  (survival cap lifted; 54W/2L earned it)
  Immense-Gokart:   max $10 → $15 | stop -$10 → -$15  (53W/0L; zero losses ever)
  Triangular-Box:   max $8  → $12 | mult 0.6→0.7 | stop -$8 → -$12  (198W/3L; most trades)
  Unwieldy-Forage:  max $8  → $12 | mult 0.7→0.8 | stop -$8 → -$12  (93.8% ROI; best performer)
  chenpengzao:      priority 1 → 2 (BENCHED: 3W/4L, -48.1% ROI, failed probation)
"""
import shutil, sys

BOT = "/home/ubuntu/copytrade/copytrade_bot.py"
BAK = BOT + ".bak_pre788"

shutil.copy2(BOT, BAK)
print(f"Backup: {BAK}")

with open(BOT, "r") as f:
    text = f.read()

original_len = len(text)
changes = []

def replace_one(old, new, label):
    global text
    count = text.count(old)
    assert count == 1, f"FAIL [{label}]: count={count} for: {repr(old[:80])}"
    text = text.replace(old, new, 1)
    changes.append(label)
    print(f"  ✅ {label}")

# ── 1. Version string ─────────────────────────────────────────────────────────
replace_one(
    "Polymarket Autonomous Copy-Trade Bot  v7.8.7",
    "Polymarket Autonomous Copy-Trade Bot  v7.8.8",
    "version v7.8.8"
)

# ── 2. Changelog ──────────────────────────────────────────────────────────────
replace_one(
    "v7.8.7 (2026-03-10) — Re-add bigwhale1337 + Add InfoEdge-a2ed (2 new, 10 total active):",
    ("v7.8.8 (2026-03-11) — Proven-core sizing upgrade (fresh capital $285) + bench chenpengzao:\n"
     "  Signal47-Bets: max $8→$15, stop -$8→-$15 | 54W/2L +67.8% ROI — survival cap lifted.\n"
     "  Immense-Gokart: max $10→$15, stop -$10→-$15 | 53W/0L +53.9% ROI — zero losses ever.\n"
     "  Triangular-Box: max $8→$12 mult 0.6→0.7, stop -$8→-$12 | 198W/3L +48.2% ROI.\n"
     "  Unwieldy-Forage: max $8→$12 mult 0.7→0.8, stop -$8→-$12 | 160W/9L +93.8% ROI best.\n"
     "  Global stop: -$25→-$35 (12.3% of $285 bankroll).\n"
     "  chenpengzao BENCHED: 3W/4L -48.1% ROI — probation failed (4L > 2 before 3W).\n"
     "  No-change: gem62/gem61/NBA-9c88/bigwhale/InfoEdge — wait for resolved positions.\n"
     "v7.8.7 (2026-03-10) — Re-add bigwhale1337 + Add InfoEdge-a2ed (2 new, 10 total active):"),
    "changelog v7.8.8"
)

# ── 3. DAILY_LOSS_STOPS — global ──────────────────────────────────────────────
replace_one(
    '"global":     -25,   # v7.7: survival mode emergency floor | was: -200',
    '"global":     -35,   # v7.8.8: proportional to $285 bankroll | was: -25 survival',
    "global stop -25→-35"
)

# ── 4. DAILY_LOSS_STOPS — Signal47-Bets ──────────────────────────────────────
replace_one(
    '"Signal47-Bets":     -8,   # v7.7: survival mode | was: -30',
    '"Signal47-Bets":     -15,  # v7.8.8: proven core unlock | 54W/2L | was: -8 survival',
    "Signal47 stop -8→-15"
)

# ── 5. DAILY_LOSS_STOPS — Immense-Gokart ─────────────────────────────────────
replace_one(
    '"Immense-Gokart":    -10,  # v7.7: survival mode leash | was: -25',
    '"Immense-Gokart":    -15,  # v7.8.8: proven core unlock | 53W/0L | was: -10 survival',
    "Immense stop -10→-15"
)

# ── 6. DAILY_LOSS_STOPS — Triangular-Box ─────────────────────────────────────
replace_one(
    '"Triangular-Box":    -8,   # v7.7: survival mode | was: -25',
    '"Triangular-Box":    -12,  # v7.8.8: proven core upgrade | 198W/3L | was: -8 survival',
    "Triangular stop -8→-12"
)

# ── 7. DAILY_LOSS_STOPS — Unwieldy-Forage ────────────────────────────────────
replace_one(
    '"Unwieldy-Forage":   -8,   # v7.7: survival mode | was: -25',
    '"Unwieldy-Forage":   -12,  # v7.8.8: proven core upgrade | 160W/9L +94% ROI | was: -8 survival',
    "Unwieldy stop -8→-12"
)

# ── 8. TRADERS — Signal47-Bets max_stake ─────────────────────────────────────
replace_one(
    '"stake_mult": 1.2, "max_stake": 8.0,    # v7.7: survival mode cap | was: 30.0 v7.0',
    '"stake_mult": 1.2, "max_stake": 15.0,   # v7.8.8: proven core unlock | 54W/2L earned | was: 8.0',
    "Signal47 max_stake 8→15"
)

# ── 9. TRADERS — Immense-Gokart max_stake ────────────────────────────────────
replace_one(
    '"stake_mult": 0.9, "max_stake": 10.0,   # v7.7: survival mode leash | was: 15.0 v7.6.14',
    '"stake_mult": 0.9, "max_stake": 15.0,   # v7.8.8: proven core unlock | 53W/0L zero losses | was: 10.0',
    "Immense max_stake 10→15"
)

# ── 10. TRADERS — Triangular-Box mult + max_stake ────────────────────────────
replace_one(
    '"stake_mult": 0.6, "max_stake": 8.0,    # v7.7: survival mode cap | was: 20.0',
    '"stake_mult": 0.7, "max_stake": 12.0,   # v7.8.8: proven core upgrade | 198W/3L +48% ROI | was: 8.0',
    "Triangular mult 0.6→0.7 max_stake 8→12"
)

# ── 11. TRADERS — Unwieldy-Forage mult + max_stake ───────────────────────────
replace_one(
    '"stake_mult": 0.7, "max_stake": 8.0,    # v7.7: survival mode cap | was: 22.0',
    '"stake_mult": 0.8, "max_stake": 12.0,   # v7.8.8: proven core upgrade | 160W/9L +94% ROI best | was: 8.0',
    "Unwieldy mult 0.7→0.8 max_stake 8→12"
)

# ── 12. TRADERS — chenpengzao bench (priority 1→2) ───────────────────────────
replace_one(
    '"roi": None, "priority": 1,  # v7.8.6: probationary — 91.7%WR/12res/14d whale | tight leash',
    '"roi": None, "priority": 2,  # v7.8.8: BENCHED — 3W/4L -48.1% ROI probation failed',
    "chenpengzao bench priority 1→2"
)

# ── Write ─────────────────────────────────────────────────────────────────────
with open(BOT, "w") as f:
    f.write(text)
print(f"\nWritten: {len(text)} chars (was {original_len}, delta={len(text)-original_len:+d})")

# ── Verification ──────────────────────────────────────────────────────────────
with open(BOT, "r") as f:
    v = f.read()

checks = [
    ("version v7.8.8",                    "Polymarket Autonomous Copy-Trade Bot  v7.8.8" in v),
    ("changelog v7.8.8",                  "v7.8.8 (2026-03-11)" in v),
    ("global stop -35",                   '"global":     -35,' in v),
    ("Signal47 stop -15",                 '"Signal47-Bets":     -15,' in v),
    ("Immense stop -15",                  '"Immense-Gokart":    -15,' in v),
    ("Triangular stop -12",               '"Triangular-Box":    -12,' in v),
    ("Unwieldy stop -12",                 '"Unwieldy-Forage":   -12,' in v),
    ("Signal47 max_stake 15.0",           '"stake_mult": 1.2, "max_stake": 15.0,' in v),
    ("Immense max_stake 15.0",            '"stake_mult": 0.9, "max_stake": 15.0,' in v),
    ("Triangular mult 0.7 max 12.0",      '"stake_mult": 0.7, "max_stake": 12.0,' in v),
    ("Unwieldy mult 0.8 max 12.0",        '"stake_mult": 0.8, "max_stake": 12.0,' in v),
    ("chenpengzao priority=2",            '"roi": None, "priority": 2,  # v7.8.8: BENCHED' in v),
    ("v7.8.7 changelog preserved",        "v7.8.7 (2026-03-10)" in v),
    ("v7.8.6 changelog preserved",        "v7.8.6 (2026-03-10)" in v),
    ("bigwhale1337 intact",               '"name": "bigwhale1337"' in v),
    ("InfoEdge-a2ed intact",              '"name": "InfoEdge-a2ed"' in v),
    ("gem62-NBA intact",                  '"name": "gem62-NBA"' in v),
    ("no survival cap on Signal47",       '"max_stake": 8.0,    # v7.7: survival mode cap | was: 30.0' not in v),
    ("no survival cap on Immense",        '"max_stake": 10.0,   # v7.7: survival mode leash' not in v),
    ("no survival cap on Triangular",     '"max_stake": 8.0,    # v7.7: survival mode cap | was: 20.0' not in v),
    ("no survival cap on Unwieldy",       '"max_stake": 8.0,    # v7.7: survival mode cap | was: 22.0' not in v),
    ("chenpengzao not priority=1",        '"priority": 1,  # v7.8.6: probationary' not in v),
]

ok = True
for name, result in checks:
    status = "✅" if result else "❌"
    print(f"  {status} {name}")
    if not result:
        ok = False

if not ok:
    print("\n❌ PATCH FAILED — restoring backup")
    shutil.copy2(BAK, BOT)
    sys.exit(1)
else:
    print(f"\n✅ All {len(checks)} checks passed — patch v7.8.8 applied successfully")
    print(f"   {len(changes)} changes: {', '.join(changes)}")
