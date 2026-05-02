import urllib.request
import json

# Test just one thing - no auth needed
try:
    resp = urllib.request.urlopen("http://localhost:8000/api/health", timeout=3)
    print(f"Health: {resp.read().decode()}")
except Exception as e:
    print(f"Health FAILED: {type(e).__name__}: {e}")

# Test login
try:
    data = json.dumps({"email": "admin", "password": "btc2026"}).encode()
    req = urllib.request.Request("http://localhost:8000/api/auth/login", data=data)
    req.add_header("Content-Type", "application/json")
    resp = urllib.request.urlopen(req, timeout=3)
    print(f"Login: {resp.read().decode()[:80]}")
except Exception as e:
    print(f"Login FAILED: {type(e).__name__}: {e}")

# Test ticker (no auth needed for market endpoint? check if it exists)
try:
    resp = urllib.request.urlopen("http://localhost:8000/api/market/ticker?symbol=BTC-USDT", timeout=10)
    print(f"Ticker: {resp.read().decode()[:100]}")
except Exception as e:
    print(f"Ticker FAILED: {type(e).__name__}: {e}")
