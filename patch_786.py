#!/usr/bin/env python3
"""patch_786.py — v7.8.6: Add chenpengzao (B_PROBATIONARY whale) to copytrade_bot.py

Scan result: broader_promo.py 244 candidates → 1 viable (chenpengzao)
  edge_score=238.3 | copy_score=78.6 | bucket=B_PROBATIONARY
  91.7%WR(11W/1L) | avg_stake=$1794 | avg_entry=0.57 | age=14d | sport=49%
  clusters=1 | blocked=19% | hold=0.00(CLOB-exit) | 3 buys last 24h
Decision: ADD at max_stake=$5, stop=-$10 (minimum leash).
Hold concern mitigated: we copy BUY only; their CLOB exits at 0.95 → we hold to $1.00.
"""
import shutil, sys

BOT = "/home/ubuntu/copytrade/copytrade_bot.py"
BAK = BOT + ".bak_pre786"

shutil.copy2(BOT, BAK)
print(f"Backup: {BAK}")

with open(BOT, "r") as f:
    text = f.read()

original_len = len(text)

# ── 1. Version string in docstring ─────────────────────────────────────────
OLD_VER = "Polymarket Autonomous Copy-Trade Bot  v7.8.5"
NEW_VER = "Polymarket Autonomous Copy-Trade Bot  v7.8.6"
assert text.count(OLD_VER) == 1, f"version string count={text.count(OLD_VER)}"
text = text.replace(OLD_VER, NEW_VER, 1)

# ── 2. Changelog entry (prepend before v7.8.5 line) ────────────────────────
OLD_CL = "v7.8.5 (2026-03-10) — Promote gem61-WBC + NBA-9c88 to priority=1 (active):"
NEW_CL = (
    "v7.8.6 (2026-03-10) — Add chenpengzao (B_PROBATIONARY, whale):\n"
    "  broader_promo.py scan: 244 candidates \u2192 1 viable (chenpengzao).\n"
    "  chenpengzao (0xb2a48372): 91.7%WR(11W/1L) | $1794 avg_stake | 14d age | entry=0.57\n"
    "  sport=49% | hold=0.00(CLOB-exit,mitigated) | clust=1 | blk=19%\n"
    "  Added max_stake=$5, stop=-$10 (minimum probationary leash).\n"
    "  Structural: 189/244 too_young (77.5%) confirms sparse market pool.\n"
    "v7.8.5 (2026-03-10) — Promote gem61-WBC + NBA-9c88 to priority=1 (active):"
)
assert text.count(OLD_CL) == 1, f"changelog count={text.count(OLD_CL)}"
text = text.replace(OLD_CL, NEW_CL, 1)

# ── 3. PER_TRADER_STOP entry ────────────────────────────────────────────────
OLD_STOP = '        "NBA-9c88":          -12,  # v7.8.4: probationary'
NEW_STOP = (
    '        "NBA-9c88":          -12,  # v7.8.4: probationary\n'
    '        "chenpengzao":       -10,  # v7.8.6: probationary, 2x max_stake'
)
assert text.count(OLD_STOP) == 1, f"stop dict count={text.count(OLD_STOP)}"
text = text.replace(OLD_STOP, NEW_STOP, 1)

# ── 4. TRADER entry before END_TRADERS marker ───────────────────────────────
OLD_END = "    # END_TRADERS  \u2190 scanner auto-add injects new entries here"
NEW_ENTRY = (
    "    {\n"
    '        "name": "chenpengzao",\n'
    '        "wallet": "0xb2a48372404e6a0bfb6c2f23d715d3acc5a8cf8a",\n'
    '        "roi": None, "priority": 1,  # v7.8.6: probationary — 91.7%WR/12res/14d whale | tight leash\n'
    '        "archetype": "generalist",\n'
    '        "stake_mult": 0.3, "max_stake": 5.0,   # v7.8.6: minimum cap — $1794 whale, copy at $5 flat\n'
    '        "categories": [],   # sport=49%, crypto_pct=0.6% (crypto hard-banned; hold=0.00 mitigated)\n'
    '        "note": "chenpengzao | B_PROB broader_promo | 91.7%WR(11W/1L) | avg_stake=$1794 | avg_entry=0.57 | 14d age | freq=5.7/d | clust=1 | blk=19% | hold=0.00(CLOB-exit) | added v7.8.6 2026-03-10",\n'
    "    },\n"
    "    # END_TRADERS  \u2190 scanner auto-add injects new entries here"
)
assert text.count(OLD_END) == 1, f"END_TRADERS count={text.count(OLD_END)}"
text = text.replace(OLD_END, NEW_ENTRY, 1)

with open(BOT, "w") as f:
    f.write(text)

print(f"Written: {len(text)} chars (was {original_len})")

# ── Verification ─────────────────────────────────────────────────────────────
with open(BOT, "r") as f:
    v = f.read()

checks = [
    ("docstring v7.8.6",              "Polymarket Autonomous Copy-Trade Bot  v7.8.6" in v),
    ("changelog v7.8.6",              "v7.8.6 (2026-03-10)" in v),
    ("stop_dict chenpengzao -10",     '"chenpengzao":       -10,' in v),
    ("trader name",                   '"name": "chenpengzao"' in v),
    ("trader wallet",                 '"wallet": "0xb2a48372404e6a0bfb6c2f23d715d3acc5a8cf8a"' in v),
    ("priority 1",                    '"priority": 1,  # v7.8.6: probationary' in v),
    ("max_stake 5.0",                 '"max_stake": 5.0,' in v),
    ("stake_mult 0.3",                '"stake_mult": 0.3,' in v),
    ("END_TRADERS preserved",         "# END_TRADERS" in v),
    ("v7.8.5 still present",          "v7.8.5 (2026-03-10)" in v),  # changelog history intact
    ("gem62-NBA intact",              '"name": "gem62-NBA"' in v),
    ("NBA-9c88 intact",               '"name": "NBA-9c88"' in v),
    ("no old version in docstring",   "Copy-Trade Bot  v7.8.5" not in v),
]

ok = True
for name, result in checks:
    status = "✅" if result else "❌"
    print(f"  {status} {name}")
    if not result:
        ok = False

if not ok:
    print("\nPATCH FAILED — restoring backup")
    shutil.copy2(BAK, BOT)
    sys.exit(1)
else:
    print("\n✅ All checks passed — patch v7.8.6 applied successfully")
