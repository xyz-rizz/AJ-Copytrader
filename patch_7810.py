#!/usr/bin/env python3
"""patch_7810.py: v7.8.9 → v7.8.10 — Add UDWhale-cd82 + SPXOpens-f52c"""

import sys, shutil

BOT = "/home/ubuntu/copytrade/copytrade_bot.py"
BAK = BOT + ".bak_pre7810"

with open(BOT) as f:
    text = f.read()

errors = []
patches = []

def replace_one(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        errors.append(f"FAIL [{label}]: found {count} occurrences (expected 1)")
        return
    text = text.replace(old, new, 1)
    patches.append(label)

# P1: version changelog
replace_one(
    'v7.8.9 (2026-03-11) — Proven-core effective-stake upgrade to $18-20 (4 traders only)',
    'v7.8.10 (2026-03-11) — Add UDWhale-cd82 + SPXOpens-f52c (2 UD specialist probationary)\nv7.8.9 (2026-03-11) — Proven-core effective-stake upgrade to $18-20 (4 traders only)',
    'version_comment'
)

# P2: stop losses
replace_one(
    '        "InfoEdge-a2ed":      -20,  # v7.8.7: new scan4 find, Musk-tweet+soccer\n                "default":           -8,   # v7.7: survival mode floor',
    '        "InfoEdge-a2ed":      -20,  # v7.8.7: new scan4 find, Musk-tweet+soccer\n        "UDWhale-cd82":       -15,  # v7.8.10: UD specialist probationary, 2x max_stake\n        "SPXOpens-f52c":      -12,  # v7.8.10: SPX Opens UD probationary, 2x max_stake\n                "default":           -8,   # v7.7: survival mode floor',
    'stop_losses'
)

# P3: trader entries before END_TRADERS marker
replace_one(
    '    # END_TRADERS  \u2190 scanner auto-add injects new entries here',
    '''    {
        "name": "UDWhale-cd82",
        "wallet": "0x898ebb087c7768ed4d47462f85856269dd8cd82c",
        "roi": None, "priority": 1,  # v7.8.10: 99%WR(158W/1L)/159res, 148d, $101avg, 0clust
        "archetype": "specialist",
        "stake_mult": 0.6, "max_stake": 12.0,  # v7.8.10: probationary; real avg=$101, cap=$12
        "categories": [],  # 100% UD stock+index (SPX/NDX/NVDA/META etc); entry=0.486 balanced
        "note": "UDWhale-cd82 | v7.8.10 | 99%WR(158W/1L)/159res | $101avg | 148d | entry=0.486 | 0clust | 100%UD-specialist | crypto=0% | selective (9/272 CIDs) | added 2026-03-11",
    },
    {
        "name": "SPXOpens-f52c",
        "wallet": "0x40344cc4ba1a39648399b2d97d0d31c27122f52c",
        "roi": None, "priority": 1,  # v7.8.10: 91.6%WR(98W/9L)/107res, 43d, $13avg, 0clust
        "archetype": "specialist",
        "stake_mult": 0.6, "max_stake": 8.0,  # v7.8.10: probationary; real avg=$13, cap=$8
        "categories": [],  # SPX Opens Up or Down primary; 32 UD buys; entry=0.521
        "note": "SPXOpens-f52c | v7.8.10 | 91.6%WR(98W/9L)/107res | $13avg | 43d | entry=0.521 | 0clust | SPX-Opens specialist | crypto=2% | 32 UD buys confirmed | added 2026-03-11",
    },
    # END_TRADERS  \u2190 scanner auto-add injects new entries here''',
    'add_traders'
)

# Verify
checks = [
    ('"UDWhale-cd82":       -15' in text,                        'UDWhale stop loss'),
    ('"SPXOpens-f52c":      -12' in text,                        'SPXOpens stop loss'),
    ('"name": "UDWhale-cd82"' in text,                           'UDWhale config'),
    ('"name": "SPXOpens-f52c"' in text,                          'SPXOpens config'),
    ('0x898ebb087c7768ed4d47462f85856269dd8cd82c' in text,       'UDWhale wallet'),
    ('0x40344cc4ba1a39648399b2d97d0d31c27122f52c' in text,       'SPXOpens wallet'),
    ('"max_stake": 12.0,  # v7.8.10: probationary' in text,      'UDWhale max_stake 12'),
    ('"max_stake": 8.0,  # v7.8.10: probationary' in text,       'SPXOpens max_stake 8'),
    (text.count('# END_TRADERS  \u2190') == 1,                   'END_TRADERS arrow unique'),
    ('"InfoEdge-a2ed":      -20' in text,                        'InfoEdge intact'),
    ('"bigwhale1337":       -15' in text,                         'bigwhale intact'),
    ('v7.8.10' in text,                                           'v7.8.10 in changelog'),
    (text.count('"name": "UDWhale-cd82"') == 1,                  'UDWhale unique'),
    (text.count('"name": "SPXOpens-f52c"') == 1,                 'SPXOpens unique'),
]

passed = 0
for ok, label in checks:
    print(f"  {'PASS' if ok else 'FAIL'} [{label}]")
    if not ok: errors.append(label)
    else: passed += 1

print(f"\nPatches: {len(patches)}/3 — {patches}")
print(f"Checks:  {passed}/{len(checks)}")

if errors:
    print(f"\n❌ ERRORS: {errors}")
    sys.exit(1)

shutil.copy(BOT, BAK)
with open(BOT, 'w') as f:
    f.write(text)
print(f"\n✅ Backup: {BAK}")
print(f"✅ Written: {BOT}")
