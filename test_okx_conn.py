import requests, time

# Test OKX connectivity with and without proxy bypass
for label, proxies in [
    ("No proxy bypass", None),
    ("Proxy bypassed", {"http": None, "https": None}),
]:
    t0 = time.time()
    try:
        r = requests.get("https://www.okx.com/api/v5/public/time", timeout=5, proxies=proxies or {})
        print(f"{label}: OK {r.status_code} ({time.time()-t0:.1f}s)")
    except Exception as e:
        print(f"{label}: FAILED ({time.time()-t0:.1f}s) - {type(e).__name__}: {e}")
