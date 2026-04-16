#!/usr/bin/env python3
"""
patch_7812.py — Apply v7.8.12 changes to copytrade_bot.py
Changes:
  1. Version bump to v7.8.12
  2. Bench UDWhale-cd82 (Bitcoin 5-min scalper — 24 crypto-blocked signals, 0 copies ever)
  3. Add daily stops for 3 new traders
  4. Add 3 new trader configs: NBAEdge-aeab, SoccerSharp-f23c, Sport-dd57
"""
import sys, shutil, re
from datetime import datetime

BOT = "/home/ubuntu/copytrade/copytrade_bot.py"
BAK = BOT + ".bak_pre7812"

# ── Load ───────────────────────────────────────────────────────────────────────
with open(BOT) as f:
    text = f.read()

original = text
patches_applied = 0
checks_passed = 0

def apply(label, old, new):
    global text, patches_applied
    count = text.count(old)
    if count == 0:
        print(f"  ✗ PATCH '{label}': old_string not found")
        sys.exit(1)
    if count > 1:
        print(f"  ✗ PATCH '{label}': old_string found {count} times (not unique)")
        sys.exit(1)
    text = text.replace(old, new, 1)
    patches_applied += 1
    print(f"  ✓ PATCH {patches_applied}: {label}")

def check(label, substring, present=True):
    global checks_passed
    found = substring in text
    if found == present:
        checks_passed += 1
        status = "present" if present else "absent"
        print(f"  ✓ CHECK {checks_passed}: {label} [{status}]")
    else:
        status = "MISSING" if present else "STILL PRESENT"
        print(f"  ✗ CHECK '{label}': expected {'present' if present else 'absent'} but {status}")
        print(f"    substring: {substring!r}")
        sys.exit(1)

print("=== patch_7812.py ===")
print(f"File: {BOT} ({len(text)} chars)")

# ── Patch 1: version comment ─────────────────────────────────────────────────
apply(
    "version comment",
    "v7.8.11 (2026-03-11) — Upsize UDWhale-cd82 + SPXOpens-f52c to $15 starter (mult 0.6->0.75, max->$15, stop->-$20)",
    "v7.8.12 (2026-03-11) — Bench UDWhale-cd82 (BTC scalper) + Add NBAEdge-aeab + SoccerSharp-f23c + Sport-dd57\nv7.8.11 (2026-03-11) — Upsize UDWhale-cd82 + SPXOpens-f52c to $15 starter (mult 0.6->0.75, max->$15, stop->-$20)"
)

# ── Patch 2: bench UDWhale-cd82 (priority 1→2) ──────────────────────────────
apply(
    "UDWhale-cd82 priority 1→2",
    '"priority": 1,  # v7.8.10: 99%WR(158W/1L)/159res, 148d, $101avg, 0clust',
    '"priority": 2,  # v7.8.12: BENCHED — BTC 5-min scalper; 24 crypto-blocked signals; 0 copies ever'
)

# ── Patch 3: add 3 new daily stops ──────────────────────────────────────────
apply(
    "add 3 new daily stops",
    '        "SPXOpens-f52c":      -20,  # v7.8.11: starter $15 sizing, stop=1.33x max',
    '        "SPXOpens-f52c":      -20,  # v7.8.11: starter $15 sizing, stop=1.33x max\n        "NBAEdge-aeab":       -15,  # v7.8.12: new, NBA spread/total/ML specialist\n        "SoccerSharp-f23c":   -20,  # v7.8.12: new, soccer+generalist\n        "Sport-dd57":         -12,  # v7.8.12: new probationary, mixed sports'
)

# ── Patch 4: add 3 new trader configs before END_TRADERS ────────────────────
apply(
    "add 3 new trader configs",
    '    # END_TRADERS  ← scanner auto-add injects new entries here',
    '''    {
        "name": "NBAEdge-aeab",
        "wallet": "0xaeab8222e044ab64b7253a3c10c16ba75096a2ed",
        "roi": None, "priority": 1,  # v7.8.12: 97.4%WR(113W/3L)/116res, 81d, $12avg, 0clust
        "archetype": "specialist",
        "stake_mult": 0.6, "max_stake": 12.0,  # v7.8.12: eff~$12@p0.5 | real avg=$12
        "categories": [],  # pure NBA spreads/totals/moneylines; entry=0.419; sports=34.5%; crypto=2.4%
        "note": "NBAEdge-aeab | v7.8.12 new | 97.4%WR(113W/3L)/116res | $12avg | 81d | entry=0.419 | 0clust | NBA specialist (spread/total/ML) | crypto=2.4% blk=0% spt=34.5% | 7b/24h | added 2026-03-11",
    },
    {
        "name": "SoccerSharp-f23c",
        "wallet": "0xf23ca65324b789016acaffb6c2dccae48657555d",
        "roi": None, "priority": 1,  # v7.8.12: 99.2%WR(130W/1L)/131res, 94d, $23avg, 1clust
        "archetype": "generalist",
        "stake_mult": 0.65, "max_stake": 15.0,  # v7.8.12: eff~$13@p0.5 | real avg=$23.5
        "categories": [],  # soccer BTTS/ML + NBA; crypto=0%; blk=0.7%; entry=0.582
        "note": "SoccerSharp-f23c | v7.8.12 new | 99.2%WR(130W/1L)/131res | $23avg | 94d | entry=0.582 | 1clust | soccer+NBA generalist | crypto=0% blk=0.7% spt=15.1% | 6b/24h | added 2026-03-11",
    },
    {
        "name": "Sport-dd57",
        "wallet": "0xdd57cbe710edcb13a0e315003ec68c00c18e530f",
        "roi": None, "priority": 1,  # v7.8.12: 97%WR(32W/1L)/33res, 28.8d, $31avg, 0clust
        "archetype": "generalist",
        "stake_mult": 0.5, "max_stake": 8.0,  # v7.8.12: light — young 29d, 33 resolved only
        "categories": [],  # soccer+CS2+NBA; crypto=13.4%(blocked); blk=2.1%; entry=0.568
        "note": "Sport-dd57 | v7.8.12 new probationary | 97%WR(32W/1L)/33res | $31avg | 28.8d | entry=0.568 | 0clust | mixed sports (soccer+CS2+NBA) | crypto=13.4%(blocked) blk=2.1% | 9b/24h | added 2026-03-11",
    },
    # END_TRADERS  ← scanner auto-add injects new entries here'''
)

print(f"\nPatches applied: {patches_applied}/4")

# ── Verification checks ──────────────────────────────────────────────────────
print("\n=== CHECKS ===")
check("version v7.8.12", "v7.8.12 (2026-03-11)")
check("version v7.8.11 preserved", "v7.8.11 (2026-03-11)")
check("UDWhale priority=2", '"priority": 2,  # v7.8.12: BENCHED — BTC 5-min scalper')
check("UDWhale priority=1 gone", '"priority": 1,  # v7.8.10: 99%WR(158W/1L)/159res, 148d', present=False)
check("NBAEdge-aeab stop", '"NBAEdge-aeab":       -15,')
check("SoccerSharp-f23c stop", '"SoccerSharp-f23c":   -20,')
check("Sport-dd57 stop", '"Sport-dd57":         -12,')
check("NBAEdge-aeab trader config", '"name": "NBAEdge-aeab"')
check("SoccerSharp-f23c trader config", '"name": "SoccerSharp-f23c"')
check("Sport-dd57 trader config", '"name": "Sport-dd57"')
check("NBAEdge wallet", '0xaeab8222e044ab64b7253a3c10c16ba75096a2ed')
check("SoccerSharp wallet", '0xf23ca65324b789016acaffb6c2dccae48657555d')
check("Sport-dd57 wallet", '0xdd57cbe710edcb13a0e315003ec68c00c18e530f')
check("END_TRADERS marker", '# END_TRADERS  ← scanner auto-add injects new entries here')

print(f"\nChecks passed: {checks_passed}/14")

# ── Write ────────────────────────────────────────────────────────────────────
shutil.copy(BOT, BAK)
print(f"\nBackup: {BAK}")
with open(BOT, "w") as f:
    f.write(text)
print("Written: copytrade_bot.py v7.8.12")
print(f"Patch summary: {patches_applied}/4 applied, {checks_passed}/14 checks passed — ALL OK")
