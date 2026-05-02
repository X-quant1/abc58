import urllib.request
import json

# Login
data = json.dumps({"email": "admin", "password": "btc2026"}).encode()
req = urllib.request.Request("http://localhost:8000/api/auth/login", data=data)
req.add_header("Content-Type", "application/json")
resp = urllib.request.urlopen(req, timeout=10)
token = json.loads(resp.read())["access_token"]
print("Login: OK")

# Test ticker
req = urllib.request.Request("http://localhost:8000/api/market/ticker?symbol=BTC-USDT")
req.add_header("Authorization", f"Bearer {token}")
resp = urllib.request.urlopen(req, timeout=10)
r = json.loads(resp.read())
print(f"Ticker: last={r.get('last', 'N/A')}")

# Test activities
req = urllib.request.Request("http://localhost:8000/api/activities")
req.add_header("Authorization", f"Bearer {token}")
resp = urllib.request.urlopen(req, timeout=10)
r = json.loads(resp.read())
print(f"Activities: {len(r) if isinstance(r, list) else list(r.keys())}")

# Test dashboard overview
req = urllib.request.Request("http://localhost:8000/api/dashboard/overview")
req.add_header("Authorization", f"Bearer {token}")
resp = urllib.request.urlopen(req, timeout=10)
r = json.loads(resp.read())
k = list(r.keys())[:5] if isinstance(r, dict) else "N/A"
print(f"Overview: {k}")

# Test settings
req = urllib.request.Request("http://localhost:8000/api/settings/api")
req.add_header("Authorization", f"Bearer {token}")
resp = urllib.request.urlopen(req, timeout=10)
r = json.loads(resp.read())
k = list(r.keys())[:5]
print(f"Settings: {k}")

# Test profile update
data = json.dumps({"nickname": "Admin", "avatar": "/avatars/1.jpg"}).encode()
req = urllib.request.Request("http://localhost:8000/api/auth/profile", data=data, method="PUT")
req.add_header("Content-Type", "application/json")
req.add_header("Authorization", f"Bearer {token}")
resp = urllib.request.urlopen(req, timeout=10)
r = json.loads(resp.read())
print(f"Profile: {r.get('message', 'N/A')}")
