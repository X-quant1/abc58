"""端到端交易测试脚本"""
import urllib.request
import json
import time

BASE = "http://localhost:8000"

def api(path, method="GET", data=None):
    if data is not None:
        data = json.dumps(data).encode()
    req = urllib.request.Request(f"{BASE}{path}", data=data, method=method,
                                headers={"Content-Type": "application/json"} if data else {})
    try:
        r = urllib.request.urlopen(req, timeout=15)
        return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return {"_error": f"HTTP {e.code}", "_body": body[:500]}

# Step 1: 查账户配置
print("=" * 60)
print("  End-to-End Trade Test")
print("=" * 60)

print("\n[Step 1] Account config via OKX positions...")
pos = api("/api/trade/positions")
print(f"  Current positions: {json.dumps(pos, ensure_ascii=False)[:300]}")

# Step 2: 查余额
bal = api("/api/trade/balance")
print(f"\n[Step 2] Balance:")
print(f"  Total equity: {bal.get('total_equity', 0):.4f} USDT")
print(f"  Available: {bal.get('details', [{}])[0].get('available', 0):.4f} USDT")

# Step 3: 开多仓 1张 BTC-USDT-SWAP
print("\n[Step 3] Opening LONG 1 contract BTC-USDT-SWAP...")
result = api("/api/trade/open-long", method="POST", data={
    "inst_id": "BTC-USDT-SWAP",
    "sz": "1",
    "lever": 10,
    "td_mode": "cross",
})
print(f"  Result: {json.dumps(result, indent=2, ensure_ascii=False)[:500]}")

if "_error" in result:
    print(f"\n  !! OPEN FAILED: {result['_error']}")
    print(f"  !! Body: {result.get('_body', '')}")
    print("\n  Trying with posSide=long (hedge mode)...")
    # 如果账户是双向持仓模式，需要 posSide=long
    # 但后端API目前只支持 net 模式
    print("  Need to check account position mode first.")
else:
    # Step 4: 确认持仓
    time.sleep(3)
    pos = api("/api/trade/positions")
    print(f"\n[Step 4] Positions after open:")
    print(f"  {json.dumps(pos, indent=2, ensure_ascii=False)[:500]}")
    
    # Step 5: 平仓
    if pos.get("positions"):
        print(f"\n[Step 5] Closing position...")
        close_result = api("/api/trade/close-all", method="POST", data={})
        print(f"  Result: {json.dumps(close_result, indent=2, ensure_ascii=False)[:500]}")
        
        time.sleep(3)
        final_pos = api("/api/trade/positions")
        print(f"\n[Step 6] Positions after close:")
        print(f"  {json.dumps(final_pos, indent=2, ensure_ascii=False)[:300]}")
