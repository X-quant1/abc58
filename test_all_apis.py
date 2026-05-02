import urllib.request, json, time

# Login
data = json.dumps({"email": "admin", "password": "btc2026"}).encode()
req = urllib.request.Request("http://localhost:8000/api/auth/login", data=data)
req.add_header("Content-Type", "application/json")
resp = urllib.request.urlopen(req, timeout=10)
token = json.loads(resp.read())["access_token"]
print("Login: OK")

# Test all critical endpoints
for name, path in [
    ("Settings", "/api/settings/api"),
    ("Overview ", "/api/dashboard/overview"),
    ("PnL     ", "/api/dashboard/pnl_curve?days=30"),
    ("Trades  ", "/api/dashboard/recent_trades?limit=10"),
    ("Activities", "/api/activities"),
]:
    t0 = time.time()
    try:
        req = urllib.request.Request(f"http://localhost:8000{path}")
        req.add_header("Authorization", f"Bearer {token}")
        resp = urllib.request.urlopen(req, timeout=10)
        elapsed = time.time() - t0
        print(f"{name}: OK ({elapsed:.1f}s)")
    except Exception as e:
        elapsed = time.time() - t0
        print(f"{name}: FAILED ({elapsed:.1f}s) - {type(e).__name__}")
