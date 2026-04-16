import re, sys

with open('/home/ubuntu/copytrade/copytrade_bot.py', 'r') as f:
    content = f.read()

original = content
changes = []

# ─── 1. VERSION HEADER ──────────────────────────────────────────────────────
old_ver = 'v7.8.31'
new_ver_block = '''v7.8.32 (2026-03-20) — Abandon crypto15m; restore proven sports core (5-wallet stack)
  - BENCHED (priority=2): CryptoUD15m-b2a5, 639d, 5e62, a3ba — Stage-2 forensic confirmed -4.37% realized ROI,
    exclusively BTC UD (crypto hard-ban blocks all signals), cluster of automated bots, no edge.
    The entire crypto15m experiment is abandoned.
  - RESTORED (priority=1): Signal47-Bets (55W/3L NBA), Immense-Gokart (53W/0L CS2),
    Triangular-Box (198W/3L generalist), 0x8ae3a587 (3W/0L tennis/soccer, 49 buys today),
    bigwhale1337 (CS2+tennis, 25 buys today, 0 both-sides, Dota2 still blocked).
  - Stack: exactly 5 priority=1 wallets. Quality over quantity.
  - Backup: copytrade_bot.py.bak_pre7832
'''

# Insert v7.8.32 header before v7.8.31 header
old_header = 'v7.8.31'
if 'v7.8.32' not in content:
    # Find first line starting with v7.8.31
    idx = content.find('v7.8.31')
    if idx != -1:
        content = content[:idx] + new_ver_block + content[idx:]
        changes.append('Added v7.8.32 header')

# ─── 2. RESTORE SPORTS TRADERS TO PRIORITY=1 ──────────────────────────────
restore_wallets = [
    # (wallet_addr, old_comment, new_comment)
    (
        '0xa83be3f6a49604556f45089799f2b2096e71def4',
        '"priority": 2,  # v7.8.26: paused — replaced by crypto15m stack',
        '"priority": 1,  # v7.8.32: restored — crypto15m abandoned, proven core 55W/3L'
    ),
    (
        '0xf27e335d2e78a207e802879f72870449836bd69d',
        '"priority": 2,  # v7.8.26: paused — replaced by crypto15m stack',
        '"priority": 1,  # v7.8.32: restored — crypto15m abandoned, proven core 53W/0L'
    ),
    (
        '0xe85d6567a750b7b15fcb51c01a7c6230f63095d8',
        '"priority": 2,  # v7.8.26: paused — replaced by crypto15m stack',
        '"priority": 1,  # v7.8.32: restored — crypto15m abandoned, proven core 198W/3L'
    ),
    (
        '0x8ae3a5879abc085c27ba803d056ea7a170b43c15',
        '"priority": 2,  # v7.8.26: paused — replaced by crypto15m stack',
        '"priority": 1,  # v7.8.32: restored — 3W/0L eval@10, tennis+soccer, 49 buys today'
    ),
    (
        '0x77f623734a71c023f9df91011189eaeef891dbd1',
        '"priority": 2,  # v7.8.26: paused — replaced by crypto15m stack | was priority=1 v7.8.7',
        '"priority": 1,  # v7.8.32: restored — CS2+tennis, 25 buys today, 0 both-sides, Dota2 blocked'
    ),
]

for wallet, old_comment, new_comment in restore_wallets:
    # Search for the wallet line + priority line in a window
    wallet_pattern = rf'("wallet":\s*"{re.escape(wallet)}"[^\n]*\n\s*)({re.escape(old_comment)})'
    def replace_fn(m):
        return m.group(1) + new_comment
    new_content = re.sub(wallet_pattern, replace_fn, content)
    if new_content != content:
        changes.append(f'Restored {wallet[:12]}...')
        content = new_content
    else:
        # fallback: direct string replace on the comment
        if old_comment in content:
            # Only replace near this wallet — find wallet position, replace within 300 chars
            idx = content.find(wallet)
            if idx != -1:
                window = content[idx:idx+400]
                new_window = window.replace(old_comment, new_comment, 1)
                if new_window != window:
                    content = content[:idx] + new_window + content[idx+400:]
                    changes.append(f'Restored {wallet[:12]}... (fallback)')
                else:
                    print(f'WARNING: Could not restore {wallet[:12]}... - comment not found in window')
        else:
            print(f'WARNING: Could not restore {wallet[:12]}... - old comment not in file at all')

# ─── 3. BENCH CRYPTO15M WALLETS (priority=1 → 2) ────────────────────────
# Find all CryptoUD15m traders with priority=1 and set to priority=2
crypto15m_names = ['CryptoUD15m-b2a5', 'CryptoUD15m-639d', 'CryptoUD15m-5e62', 'CryptoUD15m-a3ba']

for name in crypto15m_names:
    # Find the name in content, then find priority=1 within next 400 chars
    idx = content.find(f'"name": "{name}"')
    if idx == -1:
        print(f'WARNING: {name} not found in file')
        continue
    window = content[idx:idx+500]
    # Replace priority: 1 (not 2) in this window
    new_window = re.sub(r'"priority":\s*1,', '"priority": 2,  # v7.8.32: benched — crypto15m abandoned, -4.37% ROI', window, count=1)
    if new_window != window:
        content = content[:idx] + new_window + content[idx+500:]
        changes.append(f'Benched {name}')
    else:
        print(f'WARNING: Could not bench {name} - priority=1 not found in window')

# ─── 4. VALIDATE ──────────────────────────────────────────────────────────
if content == original:
    print('ERROR: No changes made to file!')
    sys.exit(1)

# Write
with open('/home/ubuntu/copytrade/copytrade_bot.py', 'w') as f:
    f.write(content)

print(f'SUCCESS: Applied {len(changes)} changes:')
for c in changes:
    print(f'  - {c}')

# Quick sanity check: verify priority counts
priority1 = len(re.findall(r'"priority":\s*1[^0-9]', content))
priority2 = len(re.findall(r'"priority":\s*2[^0-9]', content))
print(f'\nPriority=1 traders: {priority1}')
print(f'Priority=2 traders: {priority2}')

# Show the priority=1 traders
print('\nPriority=1 traders (names):')
for m in re.finditer(r'"name":\s*"([^"]+)"[^\n]*\n[^\n]*"priority":\s*1[^0-9]', content):
    print(f'  {m.group(1)}')
