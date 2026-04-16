#!/usr/bin/env python3
"""Get live CLOB balance and full capital state"""
import sys
sys.path.insert(0, '/home/ubuntu/copytrade')
from dotenv import load_dotenv
load_dotenv('/home/ubuntu/copytrade/.env')
import os

try:
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import ApiCreds
    host = "https://clob.polymarket.com"
    key = os.getenv("PRIVATE_KEY")
    chain_id = 137
    client = ClobClient(host, key=key, chain_id=chain_id,
                        signature_type=2,
                        funder=os.getenv("FUNDER_ADDRESS","0xacBcB5edEC9cdDF2d1CE72dD8A2E734E849AF6bf"))
    client.set_api_creds(client.create_or_derive_api_creds())
    bal = client.get_balance()
    print(f"LIVE CLOB BALANCE: ${float(bal):.2f}")
except Exception as e:
    print(f"CLOB client error: {e}")
    # Fallback: read from bot.log
    import subprocess
    r = subprocess.run(['grep', 'CLOB balance', '/home/ubuntu/copytrade/bot.log'],
                       capture_output=True, text=True)
    lines = r.stdout.strip().split('\n')
    print(f"Last logged CLOB: {lines[-1] if lines else 'N/A'}")
