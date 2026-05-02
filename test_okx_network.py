import requests, time

t0 = time.time()
try:
    r = requests.get("https://www.okx.com/api/v5/public/time", timeout=5, proxies={"http": None, "https": None})
    print(f"Direct OKX: {r.status_code} ({time.time()-t0:.1f}s)")
except Exception as e:
    print(f"Direct OKX: FAILED ({time.time()-t0:.1f}s) - {type(e).__name__}: {e}")

t0 = time.time()
try:
    r = requests.get("https://www.okx.com/api/v5/public/time", timeout=5)
    print(f"Proxied OKX: {r.status_code} ({time.time()-t0:.1f}s)")
except Exception as e:
    print(f"Proxied OKX: FAILED ({time.time()-t0:.1f}s) - {type(e).__name__}")
