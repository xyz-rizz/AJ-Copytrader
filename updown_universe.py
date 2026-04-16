#!/usr/bin/env python3
"""
Step 1: Identify the Up/Down market universe and extract conditionIds.
Targets: stocks tag Up/Down daily + finance tag index Up/Down.
Crypto hard-banned — skip.
"""
import urllib.request, json, time

def fetch(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read())
        except Exception as e:
            if i == retries-1: raise
            time.sleep(1)
    return []

# Target event slugs / keywords (non-crypto)
target_events = []

# Stocks tag
r = fetch('https://gamma-api.polymarket.com/events?active=true&closed=false&limit=100&order=volume24hr&ascending=false&tag_slug=stocks')
for e in r:
    title = e.get('title','')
    slug = e.get('slug','')
    tl = title.lower()
    # Include: Up/Down, closes above/below, price at close — for stocks/indices
    # Exclude: crypto, political, geo
    crypto_kw = ['bitcoin','ethereum','xrp','solana','doge','btc','eth ','bnb','crypto','coin price','token','nft']
    blocked_kw = ['iran','israel','trump','ukraine','russia','fed rate','interest rate','election','president','congress','senate','house','supreme']
    stock_kw = ['up or down','closes above','closes below','finish above','finish below','close above','close below','price at close','hit high','hit low','week of','march 11','march 12','march 13','march 14']
    
    is_crypto = any(kw in tl for kw in crypto_kw)
    is_blocked = any(kw in tl for kw in blocked_kw)
    is_stock_ud = any(kw in tl for kw in stock_kw)
    
    if is_stock_ud and not is_crypto and not is_blocked:
        target_events.append(e)

# Finance tag  
r2 = fetch('https://gamma-api.polymarket.com/events?active=true&closed=false&limit=100&order=volume24hr&ascending=false&tag_slug=finance')
for e in r2:
    title = e.get('title','')
    tl = title.lower()
    crypto_kw = ['bitcoin','ethereum','xrp','solana','doge','btc','eth ','bnb','crypto','coin price','token','nft']
    blocked_kw = ['iran','israel','trump','ukraine','russia','fed rate','interest rate','election','president','congress','senate','house','supreme','gold','silver','oil','crude']
    stock_kw = ['up or down','closes above','closes below','finish above','finish below','close above','close below','russell','s&p','nasdaq','dow','spx','ndx','spy','qqq']
    is_crypto = any(kw in tl for kw in crypto_kw)
    is_blocked = any(kw in tl for kw in blocked_kw)
    is_stock_ud = any(kw in tl for kw in stock_kw)
    if is_stock_ud and not is_crypto and not is_blocked:
        target_events.append(e)

print(f"=== TARGET EVENT UNIVERSE ({len(target_events)} events) ===")
all_condition_ids = []
event_map = {}  # conditionId -> event title

for e in sorted(target_events, key=lambda x: float(str(x.get('volume24hr') or 0)[:15] or 0), reverse=True):
    title = e.get('title','')
    vol = e.get('volume24hr') or 0
    slug = e.get('slug','')
    print(f"\n  EVENT: {title}")
    print(f"    vol24={vol:.1f} slug={slug}")
    
    # Get markets within this event
    markets = e.get('markets', [])
    if not markets:
        # Try fetching event detail
        try:
            detail = fetch(f"https://gamma-api.polymarket.com/events?slug={slug}")
            if detail:
                markets = detail[0].get('markets',[])
        except:
            pass
    
    for m in markets:
        cid = m.get('conditionId','')
        q = m.get('question','')
        liq = m.get('liquidity') or 0
        if cid:
            all_condition_ids.append(cid)
            event_map[cid] = title
            print(f"    market: {q[:70]} | liq={str(liq)[:10]} | cid={cid[:20]}...")

print(f"\n=== TOTAL conditionIds: {len(all_condition_ids)} ===")
# Save for next step
with open('/tmp/updown_cids.json','w') as f:
    json.dump({'cids': all_condition_ids, 'event_map': event_map, 'events': [e.get('title','') for e in target_events]}, f, indent=2)
print("Saved to /tmp/updown_cids.json")
