import urllib.request, json

# Login
data = json.dumps({"email": "admin", "password": "btc2026"}).encode()
req = urllib.request.Request("http://localhost:8000/api/auth/login", data=data)
req.add_header("Content-Type", "application/json")
resp = urllib.request.urlopen(req, timeout=10)
token = json.loads(resp.read())["access_token"]

# Check users API
req = urllib.request.Request("http://localhost:8000/api/admin/users?page=1&size=10")
req.add_header("Authorization", f"Bearer {token}")
resp = urllib.request.urlopen(req, timeout=10)
data = json.loads(resp.read())
for u in data.get("users", []):
    print(f"  id={u['id']} username={u['username']} okx_uid={u.get('okx_uid','MISSING')}")
