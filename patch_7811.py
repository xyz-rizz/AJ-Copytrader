#!/usr/bin/env python3
"""patch_7811.py: v7.8.10 → v7.8.11 — sizing only (stops already applied in-session)"""
import sys, shutil

BOT = "/home/ubuntu/copytrade/copytrade_bot.py"
BAK = BOT + ".bak_pre7811"

with open(BOT) as f:
    text = f.read()

errors = []
patches = []

def replace_one(old, new, label):
    global text
    c = text.count(old)
    if c != 1:
        errors.append(f"FAIL [{label}]: {c} occurrences (expected 1)")
        return
    text = text.replace(old, new, 1)
    patches.append(label)

# P1: version (may already be done — check first)
if "v7.8.11" not in text:
    replace_one(
        "v7.8.10 (2026-03-11) — Add UDWhale-cd82 + SPXOpens-f52c (2 UD specialist probationary)",
        "v7.8.11 (2026-03-11) — Upsize UDWhale-cd82 + SPXOpens-f52c to $15 starter (mult 0.6->0.75, max->$15, stop->-$20)\nv7.8.10 (2026-03-11) — Add UDWhale-cd82 + SPXOpens-f52c (2 UD specialist probationary)",
        "version"
    )
else:
    patches.append("version (already applied)")

# P2: UDWhale stop — check whether -15 or -20 in file
if '"UDWhale-cd82":       -15' in text:
    replace_one(
        '"UDWhale-cd82":       -15,  # v7.8.10: UD specialist probationary, 2x max_stake',
        '"UDWhale-cd82":       -20,  # v7.8.11: starter $15 sizing, stop=1.33x max',
        "UDWhale_stop"
    )
else:
    patches.append("UDWhale_stop (already applied)")

# P3: SPXOpens stop
if '"SPXOpens-f52c":      -12' in text:
    replace_one(
        '"SPXOpens-f52c":      -12,  # v7.8.10: SPX Opens UD probationary, 2x max_stake',
        '"SPXOpens-f52c":      -20,  # v7.8.11: starter $15 sizing, stop=1.33x max',
        "SPXOpens_stop"
    )
else:
    patches.append("SPXOpens_stop (already applied)")

# P4: UDWhale sizing — target the exact line from file
replace_one(
    '"stake_mult": 0.6, "max_stake": 12.0,  # v7.8.10: probationary; real avg=$101, cap=$12',
    '"stake_mult": 0.75, "max_stake": 15.0,  # v7.8.11: starter; eff~$15@p0.5 | real avg=$101',
    "UDWhale_sizing"
)

# P5: SPXOpens sizing
replace_one(
    '"stake_mult": 0.6, "max_stake": 8.0,  # v7.8.10: probationary; real avg=$13, cap=$8',
    '"stake_mult": 0.75, "max_stake": 15.0,  # v7.8.11: starter; eff~$15@p0.5 | real avg=$13',
    "SPXOpens_sizing"
)

# P6: UDWhale note
replace_one(
    '"note": "UDWhale-cd82 | v7.8.10 | 99%WR(158W/1L)/159res | $101avg | 148d | entry=0.486 | 0clust | 100%UD-specialist | crypto=0% | selective (9/272 CIDs) | added 2026-03-11"',
    '"note": "UDWhale-cd82 | v7.8.11 upsize | 99%WR(158W/1L)/159res | $101avg | 148d | entry=0.486 | 0clust | 100%UD-specialist | crypto=0% | audit@20copies | bench@2ugly | added 2026-03-11"',
    "UDWhale_note"
)

# P7: SPXOpens note
replace_one(
    '"note": "SPXOpens-f52c | v7.8.10 | 91.6%WR(98W/9L)/107res | $13avg | 43d | entry=0.521 | 0clust | SPX-Opens specialist | crypto=2% | 32 UD buys confirmed | added 2026-03-11"',
    '"note": "SPXOpens-f52c | v7.8.11 upsize | 91.6%WR(98W/9L)/107res | $13avg | 43d | entry=0.521 | 0clust | SPX-Opens specialist | crypto=2% | audit@20copies | bench@2ugly | added 2026-03-11"',
    "SPXOpens_note"
)

# ── VERIFY ────────────────────────────────────────────────────────────────────
checks = [
    ("v7.8.11" in text,                                                           "v7.8.11 present"),
    ('"UDWhale-cd82":       -20' in text,                                         "UDWhale stop=-20"),
    ('"SPXOpens-f52c":      -20' in text,                                         "SPXOpens stop=-20"),
    ('"stake_mult": 0.75, "max_stake": 15.0,  # v7.8.11: starter; eff~$15@p0.5 | real avg=$101' in text, "UDWhale 0.75/15"),
    ('"stake_mult": 0.75, "max_stake": 15.0,  # v7.8.11: starter; eff~$15@p0.5 | real avg=$13'  in text, "SPXOpens 0.75/15"),
    ('"stake_mult": 0.6, "max_stake": 12.0,  # v7.8.10: probationary; real avg=$101' not in text, "UDWhale old sizing gone"),
    ('"stake_mult": 0.6, "max_stake": 8.0,  # v7.8.10: probationary; real avg=$13'  not in text, "SPXOpens old sizing gone"),
    ('"UDWhale-cd82":       -15' not in text,                                     "UDWhale old stop gone"),
    ('"SPXOpens-f52c":      -12' not in text,                                     "SPXOpens old stop gone"),
    ('"bigwhale1337":       -15' in text,                                          "bigwhale intact"),
    ('"InfoEdge-a2ed":      -20' in text,                                          "InfoEdge intact"),
    ('"global":     -40' in text,                                                  "global -40 intact"),
    (text.count('"name": "UDWhale-cd82"') == 1,                                    "UDWhale unique"),
    (text.count('"name": "SPXOpens-f52c"') == 1,                                   "SPXOpens unique"),
]

passed = 0
for ok, label in checks:
    print(f"  {'PASS' if ok else 'FAIL'} [{label}]")
    if not ok:
        errors.append(label)
    else:
        passed += 1

print(f"\nPatches: {len(patches)}/7 — {patches}")
print(f"Checks:  {passed}/{len(checks)}")

if errors:
    print(f"\n❌ ERRORS: {errors}")
    sys.exit(1)

shutil.copy(BOT, BAK)
with open(BOT, "w") as f:
    f.write(text)
print(f"\n✅ Backup: {BAK}")
print(f"✅ Written: {BOT}")
