import urllib.request, json, time

data = json.dumps({"email": "admin", "password": "btc2026"}).encode()
req = urllib.request.Request("http://localhost:8000/api/auth/login", data=data)
req.add_header("Content-Type", "application/json")
resp = urllib.request.urlopen(req, timeout=10)
token = json.loads(resp.read())["access_token"]

t0 = time.time()
req = urllib.request.Request("http://localhost:8000/api/activities")
req.add_header("Authorization", f"Bearer {token}")
resp = urllib.request.urlopen(req, timeout=10)
result = json.loads(resp.read())
elapsed = time.time() - t0
print(f"Activities: {len(result) if isinstance(result, list) else type(result)} ({elapsed:.1f}s)")
if isinstance(result, list):
    for a in result[:3]:
        print(f"  - {a.get('title','')} | {a.get('link','')}")
