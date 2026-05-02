"""端到端测试 - Step 3: 平仓"""
import urllib.request, json, time

BASE = "http://localhost:8000"

def api_post(path, data=None):
    if data is None:
        data = {}
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(data).encode(),
        method="POST",
        headers={"Content-Type": "application/json"}
    )
    try:
        r = urllib.request.urlopen(req, timeout=15)
        return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return {"_error": f"HTTP {e.code}", "_body": body[:800]}

# 一键平仓
print("=== Close All Positions ===")
result = api_post("/api/trade/close-all")
print(json.dumps(result, indent=2, ensure_ascii=False)[:1000])

# 等待平仓成交
time.sleep(5)

# 确认持仓已清空
r1 = urllib.request.urlopen(f"{BASE}/api/trade/positions")
d1 = json.loads(r1.read())
print("\n=== Positions After Close ===")
print(json.dumps(d1, indent=2, ensure_ascii=False)[:500])

# 余额
r2 = urllib.request.urlopen(f"{BASE}/api/trade/balance")
d2 = json.loads(r2.read())
print("\n=== Balance After Close ===")
eq = d2.get("total_equity", 0)
avail = d2.get("details", [{}])[0].get("available", 0)
frozen = d2.get("details", [{}])[0].get("frozen", 0)
print(f"Equity: {eq:.4f} USDT")
print(f"Available: {avail:.4f} USDT")
print(f"Frozen: {frozen:.4f} USDT")

# 计算费用
print(f"\n=== P&L Summary ===")
print(f"Initial equity: 279.82 USDT")
print(f"Current equity: {eq:.4f} USDT")
print(f"Net P&L: {eq - 279.82:.4f} USDT ({(eq - 279.82) / 279.82 * 100:.4f}%)")
