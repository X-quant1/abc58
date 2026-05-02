"""通过后端API查询OKX账户配置和测试下单"""
import urllib.request
import json

BASE = "http://localhost:8000"

def api_get(path):
    r = urllib.request.urlopen(f"{BASE}{path}", timeout=15)
    return json.loads(r.read())

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

# 1. 查账户配置（通过 test-connection API 间接检查）
print("=" * 60)
print("  OKX Account Debug")
print("=" * 60)

# 2. 测试连接
print("\n[1] Test connection...")
tc = api_post("/api/settings/test-connection")
print(f"  Result: {json.dumps(tc, indent=2, ensure_ascii=False)[:500]}")

# 3. 查余额（需要API Key的接口）
print("\n[2] Balance...")
bal = api_get("/api/trade/balance")
print(f"  Equity: {bal.get('total_equity', 0):.4f} USDT")

# 4. 查持仓
print("\n[3] Positions...")
pos = api_get("/api/trade/positions")
print(f"  Positions: {json.dumps(pos, ensure_ascii=False)[:300]}")

# 5. 尝试开多 - 用 posSide=long (hedge mode)
print("\n[4] Try open-long with default params...")
result = api_post("/api/trade/open-long", {
    "inst_id": "BTC-USDT-SWAP",
    "sz": "1",
    "lever": 10,
    "td_mode": "cross",
})
if "_error" in result:
    print(f"  FAILED: {result['_error']}")
    print(f"  Body: {result.get('_body', '')[:500]}")
else:
    print(f"  SUCCESS: {json.dumps(result, indent=2, ensure_ascii=False)[:500]}")
