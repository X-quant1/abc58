import urllib.request
import json

try:
    data = json.dumps({"email": "admin", "password": "btc2026"}).encode()
    req = urllib.request.Request("http://localhost:8000/api/auth/login", data=data)
    req.add_header("Content-Type", "application/json")
    resp = urllib.request.urlopen(req, timeout=10)
    result = json.loads(resp.read())
    print("Login OK:", result.get("message", ""))
except Exception as e:
    print(f"Login FAILED: {type(e).__name__}: {e}")
