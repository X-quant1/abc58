import urllib.request, json, time

# Login
data = json.dumps({"email": "admin", "password": "btc2026"}).encode()
req = urllib.request.Request("http://localhost:8000/api/auth/login", data=data)
req.add_header("Content-Type", "application/json")
resp = urllib.request.urlopen(req, timeout=10)
token = json.loads(resp.read())["access_token"]

# Hit test-connection endpoint (which calls OKX directly, not threaded)
req = urllib.request.Request("http://localhost:8000/api/settings/test-connection", method="POST")
req.add_header("Authorization", f"Bearer {token}")
req.add_header("Content-Type", "application/json")
try:
    resp = urllib.request.urlopen(req, timeout=30)
    print(f"Test connection: {resp.read().decode()}")
except Exception as e:
    print(f"Test connection: {e}")
    if hasattr(e, 'read'):
        print(f"  Body: {e.read().decode()}")
