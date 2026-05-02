"""停止并重启策略"""
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
        return {"_error": f"HTTP {e.code}", "_body": body[:500]}

# 停止策略
print("Stopping strategy #2...")
result = api_post("/api/strategy/2/stop")
print(f"  Result: {result}")

time.sleep(3)

# 确认无持仓
r1 = urllib.request.urlopen(f"{BASE}/api/trade/positions")
d1 = json.loads(r1.read())
print(f"\nCurrent positions: {len(d1.get('positions', []))}")

# 重新启动
print("\nRestarting strategy #2...")
result2 = api_post("/api/strategy/2/start")
print(f"  Result: {result2}")

time.sleep(3)

# 查状态
r2 = urllib.request.urlopen(f"{BASE}/api/strategy/list")
d2 = json.loads(r2.read())
for s in d2.get("strategies", []):
    if s["id"] == 2:
        print(f"\nStrategy #2: running={s['running']}, enabled={s['enabled']}, position={s['position']}")

# 查日志
r3 = urllib.request.urlopen(f"{BASE}/api/monitor/logs?limit=5")
d3 = json.loads(r3.read())
print("\nRecent logs:")
for log in d3.get("logs", [])[:5]:
    print(f"  [{log.get('level','')}] {log.get('message','')[:100]}")
