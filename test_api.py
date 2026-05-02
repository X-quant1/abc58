import urllib.request
import json

# Login
data = json.dumps({"email": "admin", "password": "btc2026"}).encode()
req = urllib.request.Request("http://localhost:8000/api/auth/login", data=data, headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req, timeout=5)
token = json.loads(resp.read())["access_token"]
print("Login OK")

# Update profile
data = json.dumps({"nickname": "Admin", "avatar": "/avatars/1.jpg"}).encode()
req = urllib.request.Request("http://localhost:8000/api/auth/profile", data=data, method="PUT", headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
resp = urllib.request.urlopen(req, timeout=5)
print("Update OK:", resp.read().decode())
