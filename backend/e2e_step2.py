"""端到端测试 - Step 2: 确认持仓"""
import urllib.request, json, time
time.sleep(3)

BASE = "http://localhost:8000"

# 持仓
r1 = urllib.request.urlopen(f"{BASE}/api/trade/positions")
d1 = json.loads(r1.read())
print("=== Positions ===")
print(json.dumps(d1, indent=2, ensure_ascii=False)[:1500])

# 余额
r2 = urllib.request.urlopen(f"{BASE}/api/trade/balance")
d2 = json.loads(r2.read())
print("\n=== Balance ===")
eq = d2.get("total_equity", 0)
upl = d2.get("total_unrealized_pnl", 0)
avail = d2.get("details", [{}])[0].get("available", 0)
frozen = d2.get("details", [{}])[0].get("frozen", 0)
print(f"Equity: {eq:.4f} USDT")
print(f"Unrealized PnL: {upl:.4f} USDT")
print(f"Available: {avail:.4f} USDT")
print(f"Frozen: {frozen:.4f} USDT")

# 成交记录
r3 = urllib.request.urlopen(f"{BASE}/api/trade/fills")
d3 = json.loads(r3.read())
print("\n=== Recent Fills ===")
fills = d3 if isinstance(d3, list) else d3.get("fills", [])
for f in fills[:5]:
    print(json.dumps(f, ensure_ascii=False)[:200])

# 策略状态
r4 = urllib.request.urlopen(f"{BASE}/api/strategy/list")
d4 = json.loads(r4.read())
print("\n=== Strategy Status ===")
for s in d4.get("strategies", []):
    if s["id"] == 2:
        print(f"Position: {s['position']}")
        print(f"Running: {s['running']}")
