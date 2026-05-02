import urllib.request
import json

data = json.dumps({"email": "admin", "password": "btc2026"}).encode()
req = urllib.request.Request("http://localhost:8000/api/auth/login", data=data)
req.add_header("Content-Type", "application/json")
resp = urllib.request.urlopen(req, timeout=10)
token = json.loads(resp.read())["access_token"]
print("Login: OK")

for name, path in [
    ("Ticker   ", "/api/market/ticker?symbol=BTC-USDT"),
    ("Activities", "/api/activities"),
    ("Overview  ", "/api/dashboard/overview"),
    ("Settings  ", "/api/settings/api"),
]:
    try:
        req = urllib.request.Request(f"http://localhost:8000{path}")
        req.add_header("Authorization", f"Bearer {token}")
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())
        k = list(result.keys())[:4] if isinstance(result, dict) else "list"
        print(f"{name}: OK ({k})")
    except Exception as e:
        print(f"{name}: FAILED - {type(e).__name__}: {e}")
