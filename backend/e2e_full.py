"""端到端测试 - 完整流程: 开多 → 确认持仓 → 平仓 → 确认清空"""
import urllib.request, json, time

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

print("=" * 60)
print("  Full E2E Test: Open Long -> Verify -> Close -> Verify")
print("=" * 60)

# 记录初始余额
bal0 = api_get("/api/trade/balance")
eq0 = bal0.get("total_equity", 0)
print(f"\n[0] Initial equity: {eq0:.4f} USDT")

# Step 1: 开多仓
print("\n[1] Opening LONG 0.01 contract BTC-USDT-SWAP...")
result = api_post("/api/trade/open-long", {
    "inst_id": "BTC-USDT-SWAP",
    "sz": "0.01",
    "lever": 10,
    "td_mode": "cross",
})
if "_error" in result:
    print(f"  FAILED: {result}")
    exit(1)
ord_id = ""
if isinstance(result.get("result"), list) and result["result"]:
    ord_id = result["result"][0].get("ordId", "")
    s_code = result["result"][0].get("sCode", "")
    s_msg = result["result"][0].get("sMsg", "")
print(f"  Order placed! ordId={ord_id}, sCode={s_code}, sMsg={s_msg}")

# Step 2: 确认持仓
time.sleep(5)
pos = api_get("/api/trade/positions")
positions = pos.get("positions", [])
if not positions:
    print("  [FAIL] No position found after opening!")
    exit(1)
p = positions[0]
print(f"\n[2] Position confirmed:")
print(f"  Symbol: {p.get('symbol')}")
print(f"  Side: {p.get('side')}")
print(f"  Size: {p.get('size')}")
print(f"  Avg Price: {p.get('avg_price')}")
print(f"  Unrealized PnL: {p.get('unrealized_pnl'):.4f}")
print(f"  Leverage: {p.get('leverage')}x")
print(f"  Liq Price: {p.get('liq_price'):.2f}")

# Step 3: 平仓
print("\n[3] Closing position...")
close_result = api_post("/api/trade/close-all")
if "_error" in close_result:
    print(f"  Close FAILED: {close_result}")
    # 尝试单独平仓
    print("  Trying individual close...")
    close_result2 = api_post("/api/trade/close", {
        "inst_id": "BTC-USDT-SWAP",
        "pos_side": "long",
        "mgn_mode": "cross",
    })
    print(f"  Individual close: {json.dumps(close_result2, ensure_ascii=False)[:300]}")
else:
    print(f"  Close result: closed={close_result.get('closed', 0)}")
    for r in close_result.get("results", []):
        print(f"    {r.get('inst_id')} {r.get('pos_side')}: {r.get('status')}")

# Step 4: 确认清空
time.sleep(5)
pos2 = api_get("/api/trade/positions")
positions2 = pos2.get("positions", [])
bal1 = api_get("/api/trade/balance")
eq1 = bal1.get("total_equity", 0)
frozen1 = bal1.get("details", [{}])[0].get("frozen", 0)

print(f"\n[4] After close:")
print(f"  Open positions: {len(positions2)}")
print(f"  Frozen margin: {frozen1:.4f} USDT")
print(f"  Final equity: {eq1:.4f} USDT")
print(f"  Net P&L: {eq1 - eq0:.4f} USDT ({(eq1 - eq0) / eq0 * 100:.4f}%)")

# Step 5: 验证
print(f"\n[5] Verification:")
all_pass = True
if len(positions2) > 0:
    print("  [FAIL] Still has open positions!")
    all_pass = False
else:
    print("  [PASS] No open positions")

if frozen1 > 0.01:
    print(f"  [WARN] Frozen margin not zero: {frozen1:.4f}")
    all_pass = False
else:
    print("  [PASS] No frozen margin")

total_fees = eq0 - eq1  # approx
if total_fees > 2:  # 2 USDT is way too much for 1 contract
    print(f"  [WARN] High fees detected: {total_fees:.4f} USDT")
else:
    print(f"  [PASS] Fees reasonable: ~{abs(total_fees):.4f} USDT")

print(f"\n{'=' * 60}")
if all_pass:
    print("  E2E TEST PASSED!")
else:
    print("  E2E TEST HAS ISSUES - review above")
print(f"{'=' * 60}")
