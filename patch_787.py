#!/usr/bin/env python3
"""patch_787.py — v7.8.7: Re-add bigwhale1337 + Add InfoEdge-a2ed

ADDITIONS:
1. bigwhale1337 (0x77f623734a71c023f9df91011189eaeef891dbd1) — RE-ADD from emergency bench
   Evidence: scout 81.8%WR(27W/6L)@$114avg + positions sizeThreshold=0.001 → 40W/0L dust wins.
   100% sports (CS2+tennis+Dota2), $1,244 current avg stake, 86d, 0 clusters, 6% blocked.
   Emergency-benched v7.7 for "no edge_scores history" (NOT a performance failure — never copied).
   Settings: max_stake=$12, stop=-$15, stake_mult=0.6, priority=1 probationary.

2. InfoEdge-a2ed (0xa2ed440b6e3b9738a547c5a20f79616b63828808) — NEW from aggressive_scan4.py
   From niche-market trades scan (proxyWallet fix). 99%WR(97W/1L), 98 resolved, $291 avg stake,
   121d age, avg_entry=0.450, crypto_pct=10.3% (under 35% threshold), blocked_pct=13%.
   Specialty: Elon Musk tweet-count markets (niche informational edge) + soccer.
   hold=0.37 (CLOB-exit style), but bot copies BUY only → holds to $1.00 resolution.
   Settings: max_stake=$15, stop=-$20, stake_mult=0.6, priority=1 probationary.

REJECTS THIS PASS:
  0x0799daf859e32ec8: 100%WR but only 9 resolved — too thin; watchlist at 20+
  0x79433bec5603f9de: bot-pattern (9d old, $5 avg, 67 buys/24h, 6 clusters) — reject
"""
import shutil, sys

BOT = "/home/ubuntu/copytrade/copytrade_bot.py"
BAK = BOT + ".bak_pre787"

shutil.copy2(BOT, BAK)
print(f"Backup: {BAK}")

with open(BOT, "r") as f:
    text = f.read()

original_len = len(text)

# ── 1. Version string ─────────────────────────────────────────────────────────
OLD_VER = "Polymarket Autonomous Copy-Trade Bot  v7.8.6"
NEW_VER = "Polymarket Autonomous Copy-Trade Bot  v7.8.7"
assert text.count(OLD_VER) == 1, f"version string count={text.count(OLD_VER)}"
text = text.replace(OLD_VER, NEW_VER, 1)

# ── 2. Changelog ──────────────────────────────────────────────────────────────
OLD_CL = "v7.8.6 (2026-03-10) — Add chenpengzao (B_PROBATIONARY, whale):"
NEW_CL = (
    "v7.8.7 (2026-03-10) — Re-add bigwhale1337 + Add InfoEdge-a2ed (2 new, 10 total active):\n"
    "  bigwhale1337: scout 81.8%WR(27W/6L)@$114 + 40 dust wins (sizeThreshold=0.001). 100% sports\n"
    "  (CS2+tennis+Dota2), $1244 avg, 86d, 0 clusters, 6% blk. Emergency-benched v7.7 (not perf).\n"
    "  max_stake=$12, stop=-$15.\n"
    "  InfoEdge-a2ed (scan4): 99%WR(97W/1L)/98res, $291avg, 121d, entry=0.450. Musk-tweet+soccer.\n"
    "  Not blocked/crypto (crypto_pct=10%). hold=0.37 (CLOB-exit) mitigated: bot holds to $1.\n"
    "  max_stake=$15, stop=-$20.\n"
    "  Scan4 rejects: 0x0799 (9 resolved too thin), 0x79433 (bot-pattern/micro).\n"
    "v7.8.6 (2026-03-10) — Add chenpengzao (B_PROBATIONARY, whale):"
)
assert text.count(OLD_CL) == 1, f"changelog count={text.count(OLD_CL)}"
text = text.replace(OLD_CL, NEW_CL, 1)

# ── 3. PER_TRADER_STOP entries ────────────────────────────────────────────────
OLD_STOP = '        "chenpengzao":       -10,  # v7.8.6: probationary, 2x max_stake'
NEW_STOP = (
    '        "chenpengzao":       -10,  # v7.8.6: probationary, 2x max_stake\n'
    '        "bigwhale1337":       -15,  # v7.8.7: re-add from emergency bench\n'
    '        "InfoEdge-a2ed":      -20,  # v7.8.7: new scan4 find, Musk-tweet+soccer'
)
assert text.count(OLD_STOP) == 1, f"stop dict count={text.count(OLD_STOP)}"
text = text.replace(OLD_STOP, NEW_STOP, 1)

# ── 4. TRADER entries ─────────────────────────────────────────────────────────
OLD_END = "    # END_TRADERS  \u2190 scanner auto-add injects new entries here"
NEW_ENTRY = (
    "    {\n"
    '        "name": "bigwhale1337",\n'
    '        "wallet": "0x77f623734a71c023f9df91011189eaeef891dbd1",\n'
    '        "roi": None, "priority": 1,  # v7.8.7: re-add — scout 81.8%WR(27W/6L) + 40 dust wins; emergency-benched never copied\n'
    '        "archetype": "specialist",\n'
    '        "stake_mult": 0.6, "max_stake": 12.0,  # v7.8.7: ~1% of $1244 real avg — probationary\n'
    '        "categories": [],  # 100% sports: CS2+tennis+Dota2 (crypto hard-banned by default)\n'
    '        "note": "bigwhale1337 | re-add v7.8.7 | scout 81.8%WR(27W/6L)@$114 | 40 dust wins 0L sizeThresh=0.001 | cur_avg=$1244 | 86d | CS2+tennis+Dota2 | 0clust | 6%blk | hold=0.55 | freq=1.3/d | emergency-benched v7.7 (no history not perf)",\n'
    "    },\n"
    "    {\n"
    '        "name": "InfoEdge-a2ed",\n'
    '        "wallet": "0xa2ed440b6e3b9738a547c5a20f79616b63828808",\n'
    '        "roi": None, "priority": 1,  # v7.8.7: new — 99%WR(97W/1L)/98res scan4 find\n'
    '        "archetype": "generalist",\n'
    '        "stake_mult": 0.6, "max_stake": 15.0,  # v7.8.7: ~5% of $291 avg — probationary\n'
    '        "categories": [],  # Musk tweet-count markets + soccer; crypto=10% (hard-banned anyway)\n'
    '        "note": "InfoEdge-a2ed | scan4 find v7.8.7 | 99%WR(97W/1L)/98res | $291avg | 121d | entry=0.450 | crypto=10% blk=13% spt=1% | hold=0.37(CLOB-exit mitigated) | Musk-tweet specialist+soccer | added v7.8.7 2026-03-10",\n'
    "    },\n"
    "    # END_TRADERS  \u2190 scanner auto-add injects new entries here"
)
assert text.count(OLD_END) == 1, f"END_TRADERS count={text.count(OLD_END)}"
text = text.replace(OLD_END, NEW_ENTRY, 1)

with open(BOT, "w") as f:
    f.write(text)

print(f"Written: {len(text)} chars (was {original_len})")

# ── Verification ──────────────────────────────────────────────────────────────
with open(BOT, "r") as f:
    v = f.read()

checks = [
    ("docstring v7.8.7",                  "Polymarket Autonomous Copy-Trade Bot  v7.8.7" in v),
    ("changelog v7.8.7",                  "v7.8.7 (2026-03-10)" in v),
    ("stop bigwhale1337 -15",             '"bigwhale1337":       -15,' in v),
    ("stop InfoEdge-a2ed -20",            '"InfoEdge-a2ed":      -20,' in v),
    ("trader bigwhale1337 name",          '"name": "bigwhale1337"' in v),
    ("trader bigwhale1337 wallet",        '"wallet": "0x77f623734a71c023f9df91011189eaeef891dbd1"' in v),
    ("bigwhale1337 max_stake 12.0",       '"max_stake": 12.0,' in v),
    ("trader InfoEdge-a2ed name",         '"name": "InfoEdge-a2ed"' in v),
    ("trader InfoEdge-a2ed wallet",       '"wallet": "0xa2ed440b6e3b9738a547c5a20f79616b63828808"' in v),
    ("InfoEdge-a2ed max_stake 15.0",      '"max_stake": 15.0,' in v),
    ("END_TRADERS preserved",             "# END_TRADERS" in v),
    ("v7.8.6 still present",              "v7.8.6 (2026-03-10)" in v),
    ("chenpengzao intact",                '"name": "chenpengzao"' in v),
    ("gem62-NBA intact",                  '"name": "gem62-NBA"' in v),
    ("no old version in docstring",       "Copy-Trade Bot  v7.8.6" not in v),
]

ok = True
for name, result in checks:
    status = "\u2705" if result else "\u274c"
    print(f"  {status} {name}")
    if not result:
        ok = False

if not ok:
    print("\nPATCH FAILED — restoring backup")
    shutil.copy2(BAK, BOT)
    sys.exit(1)
else:
    print("\n\u2705 All checks passed — patch v7.8.7 applied successfully")
