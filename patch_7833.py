import re, sys

with open('/home/ubuntu/copytrade/copytrade_bot.py', 'r') as f:
    content = f.read()

original = content
changes = []

# ─── 1. VERSION HEADER ───────────────────────────────────────────────────────
v_block = """v7.8.33 (2026-03-20) — Size up to $50/trade across all 5 active traders
  - MAX_STAKE_PER_TRADE: $40 → $50 (global hard cap)
  - Signal47-Bets:   max_stake $20 → $50 | daily_stop -$20 → -$100
  - Immense-Gokart:  max_stake $20 → $50 | daily_stop -$20 → -$100
  - Triangular-Box:  max_stake $20 → $50 | daily_stop -$20 → -$100
  - bigwhale1337:    max_stake $12 → $50 | daily_stop -$15 → -$50
  - 0x8ae3a587:      max_stake  $8 → $50 | daily_stop  -$8 → -$50
  - DAILY_LOSS_STOPS["global"]: -$40 → -$150 (3× max_stake, 5-wallet stack)
  - Backup: copytrade_bot.py.bak_pre7833
"""
if 'v7.8.33' not in content:
    idx = content.find('v7.8.32')
    if idx != -1:
        content = content[:idx] + v_block + content[idx:]
        changes.append('v7.8.33 header')

# ─── 2. MAX_STAKE_PER_TRADE global: 40 → 50 ──────────────────────────────────
old = 'MAX_STAKE_PER_TRADE= float(os.getenv("MAX_STAKE_PER_TRADE", "40.0"))'
new = 'MAX_STAKE_PER_TRADE= float(os.getenv("MAX_STAKE_PER_TRADE", "50.0"))  # v7.8.33: $40→$50'
if old in content:
    content = content.replace(old, new, 1)
    changes.append('MAX_STAKE_PER_TRADE 40→50')
else:
    print('WARNING: MAX_STAKE_PER_TRADE line not found exactly')

# ─── 3. DAILY_LOSS_STOPS global: -40 → -150 ─────────────────────────────────
old = '"global":     -40,   # v7.8.9: proportional to 4x$20 proven core sizing | was: -35'
new = '"global":     -150,  # v7.8.33: 3×$50 — 5-wallet stack at $50/trade | was: -40'
if old in content:
    content = content.replace(old, new, 1)
    changes.append('global daily_stop -40→-150')
else:
    print('WARNING: global daily_stop line not found')

# ─── 4. Per-trader DAILY_LOSS_STOPS ──────────────────────────────────────────
dl_changes = [
    ('"Signal47-Bets":     -20,  # v7.8.9: proven core $20 sizing | was: -15',
     '"Signal47-Bets":     -100,  # v7.8.33: proven core $50 sizing (2× max_stake)'),
    ('"Immense-Gokart":    -20,  # v7.8.9: proven core $20 sizing | was: -15',
     '"Immense-Gokart":    -100,  # v7.8.33: proven core $50 sizing (2× max_stake)'),
    ('"Triangular-Box":    -20,  # v7.8.9: proven core $20 sizing | was: -12',
     '"Triangular-Box":    -100,  # v7.8.33: proven core $50 sizing (2× max_stake)'),
    ('"bigwhale1337":       -15,  # v7.8.7: re-add from emergency bench',
     '"bigwhale1337":       -50,   # v7.8.33: $50 max_stake | was: -15'),
]
for old, new in dl_changes:
    if old in content:
        content = content.replace(old, new, 1)
        changes.append(f'DAILY_LOSS_STOPS {old[:25].strip()}')
    else:
        print(f'WARNING: daily_stop entry not found: {old[:50]}')

# 0x8ae3a587 daily_stop — find in DAILY_LOSS_STOPS dict and update, or add if missing
if '"0x8ae3a587"' in content:
    # Already in dict — find and update
    old_ae = re.search(r'"0x8ae3a587"\s*:\s*-\d+.*', content)
    if old_ae:
        content = content[:old_ae.start()] + '"0x8ae3a587":      -50,   # v7.8.33: $50 max_stake' + content[old_ae.end():]
        changes.append('DAILY_LOSS_STOPS 0x8ae3a587')
    else:
        print('WARNING: 0x8ae3a587 in content but no match for daily_stop pattern')
else:
    # Add it before the closing brace of per_trader dict
    # Find a good insertion point after bigwhale1337 entry
    insert_after = '"bigwhale1337":       -50,   # v7.8.33: $50 max_stake | was: -15'
    if insert_after in content:
        idx = content.find(insert_after)
        end = idx + len(insert_after)
        content = content[:end] + '\n        "0x8ae3a587":      -50,   # v7.8.33: $50 max_stake' + content[end:]
        changes.append('DAILY_LOSS_STOPS 0x8ae3a587 (added)')

# ─── 5. TRADERS max_stake per trader ─────────────────────────────────────────

# Signal47: target the specific line with v7.8.9 comment
old = '"stake_mult": 1.2, "max_stake": 20.0,   # v7.8.9: proven core $20 sizing | was: 15.0'
new = '"stake_mult": 1.2, "max_stake": 50.0,   # v7.8.33: size up $20→$50'
if old in content:
    content = content.replace(old, new, 1)
    changes.append('Signal47 max_stake 20→50')
else:
    print('WARNING: Signal47 max_stake line not found')

# Immense-Gokart
old = '"stake_mult": 0.9, "max_stake": 20.0,   # v7.8.9: proven core $20 sizing | was: 15.0'
new = '"stake_mult": 0.9, "max_stake": 50.0,   # v7.8.33: size up $20→$50'
if old in content:
    content = content.replace(old, new, 1)
    changes.append('Immense max_stake 20→50')
else:
    print('WARNING: Immense max_stake line not found')

# Triangular-Box
old = '"stake_mult": 0.85, "max_stake": 20.0,  # v7.8.9: proven core $20 sizing | mult 0.7→0.85 | was: 12.0'
new = '"stake_mult": 0.85, "max_stake": 50.0,  # v7.8.33: size up $20→$50'
if old in content:
    content = content.replace(old, new, 1)
    changes.append('Triangular max_stake 20→50')
else:
    print('WARNING: Triangular max_stake line not found')

# bigwhale1337 active entry (the v7.8.7 re-add with stake_mult=0.6, max_stake=12.0)
old = '"stake_mult": 0.6, "max_stake": 12.0,  # v7.8.7: ~1% of $1244 real avg — probationary'
new = '"stake_mult": 0.6, "max_stake": 50.0,  # v7.8.33: size up $12→$50'
if old in content:
    content = content.replace(old, new, 1)
    changes.append('bigwhale max_stake 12→50')
else:
    print('WARNING: bigwhale active max_stake line not found')

# 0x8ae3a587 — long comment line
old = '"stake_mult": 0.7, "max_stake": 8.0,   # v7.8.18: audit cap — unreviewed auto-add; 30 fires/24h flagged; no cluster/sell data; cut from $15 | re-eval after 10 resolved'
new = '"stake_mult": 0.7, "max_stake": 50.0,  # v7.8.33: size up $8→$50'
if old in content:
    content = content.replace(old, new, 1)
    changes.append('0x8ae3a587 max_stake 8→50')
else:
    print('WARNING: 0x8ae3a587 max_stake line not found — trying fallback')
    # fallback: find by wallet
    idx = content.find('0x8ae3a5879abc085c27ba803d056ea7a170b43c15')
    if idx != -1:
        window = content[idx:idx+600]
        new_window = re.sub(
            r'"stake_mult":\s*0\.7,\s*"max_stake":\s*8\.0,[^\n]*',
            '"stake_mult": 0.7, "max_stake": 50.0,  # v7.8.33: size up $8→$50',
            window, count=1
        )
        if new_window != window:
            content = content[:idx] + new_window + content[idx+600:]
            changes.append('0x8ae3a587 max_stake 8→50 (fallback)')

# ─── 6. VALIDATE ──────────────────────────────────────────────────────────────
if content == original:
    print('ERROR: No changes made!')
    sys.exit(1)

with open('/home/ubuntu/copytrade/copytrade_bot.py', 'w') as f:
    f.write(content)

print(f'SUCCESS: {len(changes)} changes applied:')
for c in changes:
    print(f'  + {c}')
