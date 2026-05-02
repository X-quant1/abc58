import urllib.request, json, time

data = json.dumps({"email": "admin", "password": "btc2026"}).encode()
req = urllib.request.Request("http://localhost:8000/api/auth/login", data=data)
req.add_header("Content-Type", "application/json")
resp = urllib.request.urlopen(req, timeout=10)
token = json.loads(resp.read())["access_token"]

t0 = time.time()
req = urllib.request.Request("http://localhost:8000/api/dashboard/overview")
req.add_header("Authorization", f"Bearer {token}")
resp = urllib.request.urlopen(req, timeout=20)
result = json.loads(resp.read())
elapsed = time.time() - t0
print(f"Overview: OK ({elapsed:.1f}s)")
print(f"  account_balance: {result.get('account_balance')}")
print(f"  unrealized_pnl: {result.get('unrealized_pnl')}")
print(f"  has_api_key: {result.get('has_api_key')}")
print(f"  btc_price: {result.get('btc_price')}")
print(f"  fear_greed: {result.get('fear_greed_index')}")
