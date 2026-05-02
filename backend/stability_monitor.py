"""12小时稳定性测试 - 监控检查脚本
运行方式: python stability_monitor.py
功能: 检查系统关键指标，输出 PASS/FAIL 判定
"""
import urllib.request
import json
import sys
from datetime import datetime

BASE = "http://localhost:8000"

def api(path):
    try:
        r = urllib.request.urlopen(f"{BASE}{path}", timeout=10)
        return json.loads(r.read())
    except Exception as e:
        return {"_error": str(e)}

def check():
    print("=" * 60)
    print(f"  Stability Test Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    issues = []
    
    # 1. Backend alive
    health = api("/api/monitor/health")
    if "_error" in health:
        print("[FAIL] Backend not responding:", health["_error"])
        issues.append("backend_down")
    else:
        print(f"[PASS] Backend alive, uptime={health.get('uptime_human','?')}")
        if health.get('status') != 'ok':
            issues.append("backend_unhealthy")
            print(f"[WARN] Backend status: {health['status']}")
    
    # 2. Strategy running
    strategies = api("/api/strategy/list")
    running = [s for s in strategies.get('strategies', []) if s['running']]
    if len(running) == 0:
        print("[FAIL] No strategy running!")
        issues.append("no_strategy")
    else:
        for s in running:
            print(f"[PASS] Strategy #{s['id']} {s['name']} running, position={s['position']}")
    
    # 3. Position consistency
    positions = api("/api/trade/positions")
    okx_positions = positions.get('positions', [])
    strategy = next((s for s in strategies.get('strategies', []) if s['id'] == 2), None)
    if strategy:
        strat_pos = strategy.get('position', 'none')
        has_okx_pos = len(okx_positions) > 0
        # Simple consistency: if strategy says long/short, OKX should have position
        if strat_pos in ('long', 'short') and not has_okx_pos:
            print(f"[WARN] Strategy says {strat_pos} but OKX has no position")
            issues.append("position_mismatch")
        elif strat_pos == 'none' and has_okx_pos:
            print(f"[WARN] Strategy says none but OKX has position")
            issues.append("position_mismatch")
        else:
            print(f"[PASS] Position consistent: strategy={strat_pos}, okx_positions={len(okx_positions)}")
    
    # 4. Account balance
    balance = api("/api/trade/balance")
    equity = balance.get('total_equity', 0)
    if equity > 0:
        print(f"[PASS] Account equity: {equity:.4f} USDT")
    else:
        print("[FAIL] Account equity is 0 or unavailable")
        issues.append("balance_error")
    
    # 5. Error logs
    logs = api("/api/monitor/logs?limit=50")
    error_logs = [l for l in logs.get('logs', []) if l.get('level') == 'error']
    if error_logs:
        print(f"[WARN] {len(error_logs)} error logs in last 50 entries")
        for el in error_logs[:3]:
            print(f"       {el.get('time','')[:19]} {el.get('message','')[:100]}")
        issues.append(f"errors_{len(error_logs)}")
    else:
        print("[PASS] No error logs")
    
    # 6. WebSocket (check via recent trades or dashboard)
    overview = api("/api/dashboard/overview")
    btc_price = overview.get('btc_price', 0)
    if btc_price > 0:
        print(f"[PASS] Market data flowing: BTC=${btc_price:,.1f}")
    else:
        print("[WARN] No market data")
        issues.append("no_market_data")
    
    # 7. DB health
    if health.get('db_ok'):
        print(f"[PASS] DB healthy, size={health.get('db_size_mb',0):.2f}MB")
    else:
        print("[FAIL] DB unhealthy")
        issues.append("db_error")
    
    # Summary
    print(f"\n{'=' * 60}")
    if issues:
        print(f"  RESULT: ISSUES DETECTED ({len(issues)})")
        for i in issues:
            print(f"    - {i}")
    else:
        print(f"  RESULT: ALL CHECKS PASSED")
    print(f"{'=' * 60}")
    
    return issues

if __name__ == "__main__":
    issues = check()
    sys.exit(len(issues))
