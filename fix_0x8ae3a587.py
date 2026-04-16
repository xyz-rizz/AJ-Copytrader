with open('/home/ubuntu/copytrade/copytrade_bot.py', 'r') as f:
    content = f.read()

nl_pos = 31109
new_line = '\n        "0x8ae3a587":      -50,   # v7.8.33: $50 max_stake'
content = content[:nl_pos] + new_line + content[nl_pos:]

# verify it's in there
if '"0x8ae3a587":      -50' in content:
    with open('/home/ubuntu/copytrade/copytrade_bot.py', 'w') as f:
        f.write(content)
    print('SUCCESS: inserted 0x8ae3a587 daily_stop -50')
else:
    print('ERROR: insertion failed')
