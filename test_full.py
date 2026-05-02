import urllib.request
import json

# Test login
data = json.dumps({"email": "admin", "password": "btc2026"}).encode()
req = urllib.request.Request("http://localhost:8000/api/auth/login", data=data, headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req, timeout=10)
result = json.loads(resp.read())
print("Login OK, token:", result["access_token"][:20] + "...")

# Test profile update
token = result["access_token"]
data = json.dumps({"nickname": "Admin", "avatar": "/avatars/1.jpg"}).encode()
req = urllib.request.Request("http://localhost:8000/api/auth/profile", data=data, method="PUT",
                              headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
resp = urllib.request.urlopen(req, timeout=10)
print("Profile update OK:", resp.read().decode())
