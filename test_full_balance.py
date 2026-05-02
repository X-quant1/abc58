import urllib.request, json, time

data = json.dumps({"email": "admin", "password": "btc2026"}).encode()
req = urllib.request.Request("http://localhost:8000/api/auth/login", data=data)
req.add_header("Content-Type", "application/json")
resp = urllib.request.urlopen(req, timeout=10)
token = json.loads(resp.read())["access_token"]
print("Login OK")

# Test balance endpoint directly
req = urllib.request.Request("http://localhost:8000/api/settings/api")
req.add_header("Authorization", f"Bearer {token}")
resp = urllib.request.urlopen(req, timeout=10)
settings = json.loads(resp.read())
print(f"Settings key: {settings['key']}")
print(f"has_api_key from settings: {bool(settings['key'])}")

# Test overview
t0 = time.time()
req = urllib.request.Request("http://localhost:8000/api/dashboard/overview")
req.add_header("Authorization", f"Bearer {token}")
resp = urllib.request.urlopen(req, timeout=30)
result = json.loads(resp.read())
print(f"Overview ({time.time()-t0:.1f}s): balance={result.get('account_balance')}, has_key={result.get('has_api_key')}")
