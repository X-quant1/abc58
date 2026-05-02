import urllib.request

try:
    resp = urllib.request.urlopen("http://localhost:8000/api/health", timeout=5)
    print("Health check OK:", resp.read().decode())
except Exception as e:
    print(f"Health check failed: {e}")
