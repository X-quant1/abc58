import urllib.request, json
data = json.dumps({"email":"admin","password":"btc2026"}).encode()
req = urllib.request.Request("http://localhost:8000/api/auth/login", data=data)
req.add_header("Content-Type", "application/json")
resp = urllib.request.urlopen(req, timeout=10)
token = json.loads(resp.read())["access_token"]

req = urllib.request.Request("http://localhost:8000/api/activities")
req.add_header("Authorization", f"Bearer {token}")
resp = urllib.request.urlopen(req, timeout=10)
raw = resp.read()
print("Raw length:", len(raw))
print("Raw[:500]:", raw[:500].decode("utf-8", errors="replace"))
