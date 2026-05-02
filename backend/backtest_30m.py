"""30m周期MACD背离完整回测"""
import sys, os, time
import requests as req_lib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.services.strategy import get_strategy_class
from app.services.backtest import BacktestEngine

OKX_BASE = "https://www.okx.com"

def fetch_klines(tf, total=1440):
    all_klines = []
    after = ""
    url = f"{OKX_BASE}/api/v5/market/history-candles"
    remaining = total
    while remaining > 0:
        batch = min(remaining, 300)
        params = {"instId": "BTC-USDT-SWAP", "bar": tf, "limit": str(batch)}
        if after:
            params["after"] = after
        try:
            resp = req_lib.get(url, params=params, timeout=30)
            data = resp.json()
            if data.get("code") != "0" or not data.get("data"):
                break
            for c in data["data"]:
                all_klines.append({
                    "timestamp": int(c[0]), "open": float(c[1]),
                    "high": float(c[2]), "low": float(c[3]),
                    "close": float(c[4]), "volume": float(c[5]),
                })
            remaining -= len(data["data"])
            after = str(int(data["data"][-1][0]))
            time.sleep(0.3)
        except Exception as e:
            print(f"  ERROR: {e}")
            break
    seen = set()
    unique = []
    for k in all_klines:
        if k["timestamp"] not in seen:
            seen.add(k["timestamp"])
            unique.append(k)
    unique.sort(key=lambda x: x["timestamp"])
    return unique

BASE = {
    "macd_fast": 12, "macd_slow": 26, "macd_signal": 9,
    "lookback_bars": 50, "price_near_high": 0.99, "price_near_low": 1.01,
    "macd_div_high": 0.9, "macd_div_low": 1.1,
    "size_mode": "fixed", "size": 1, "inst_id": "BTC-USDT-SWAP",
}

COMBOS = [
    ("default(0.3/0.25)", 0.3, 0.25, 0.2, 15),
    ("wide1(0.5/0.3)", 0.5, 0.3, 0.3, 20),
    ("wide2(1.0/0.5)", 1.0, 0.5, 0.5, 30),
    ("bigTP/smSL(1.5/0.3)", 1.5, 0.3, 0.8, 40),
    ("bigTP2(2.0/0.3)", 2.0, 0.3, 1.0, 50),
    ("xwide(3.0/0.5)", 3.0, 0.5, 1.5, 60),
    ("noTP/SL", 0, 0, 0, 0),
    ("trail_only(0.5%)", 0, 0, 0.5, 30),
    ("wide_trail(1.0%)", 0, 0, 1.0, 50),
    ("mid(0.5/0.25)", 0.5, 0.25, 0.3, 20),
    ("narrowSL(1.0/0.2)", 1.0, 0.2, 0.5, 25),
    ("SL_only(0/0.3)", 0, 0.3, 0, 0),
]

print("Fetching 30m klines (1440 bars)...")
klines = fetch_klines("30m", 1440)
days = (klines[-1]["timestamp"] - klines[0]["timestamp"]) / 1000 / 86400
print(f"Got {len(klines)} bars, {days:.1f} days")
print(f"Range: ${klines[0]['close']:.0f} ~ ${max(k['high'] for k in klines):.0f}")
print()

header = f"{'Combo':<24} {'Ret%':>8} {'WinR%':>8} {'PF':>8} {'Trades':>8} {'DD%':>8} {'Sharpe':>8} {'Fees':>8} {'Daily':>8}"
print(header)
print("-" * len(header))

results = []
for name, tp, sl, ta, tc in COMBOS:
    p = BASE.copy()
    p["tp_pct"] = tp
    p["sl_pct"] = sl
    p["trailing_activation_pct"] = ta
    p["trailing_callback_points"] = tc
    p["timeframe"] = "30m"
    
    eng = BacktestEngine()
    r = eng.run("macd_divergence", p, "BTC-USDT-SWAP", "30m", klines, 10000, 10)
    
    if not r or not r.get("ok"):
        print(f"{name:<24} FAILED")
        continue
    
    m = "*" if r["total_return"] > 0 else " "
    daily = r["trade_count"] / days
    print(f"{m} {name:<24} {r['total_return']:>8.2f} {r['win_rate']:>8.1f} {r['profit_factor']:>8.2f} {r['trade_count']:>8d} {r['max_drawdown']:>8.2f} {r['sharpe_ratio']:>8.2f} {r['total_fees']:>8.2f} {daily:>8.1f}")
    results.append((name, r))

# Best combo with leverage comparison
if results:
    best_name, best_r = max(results, key=lambda x: x[1]["total_return"])
    # Find the combo params
    best_combo = None
    for name, tp, sl, ta, tc in COMBOS:
        if name == best_name:
            best_combo = (tp, sl, ta, tc)
            break
    
    if best_combo:
        tp, sl, ta, tc = best_combo
        print(f"\n\nBest combo: {best_name} -> Leverage comparison:")
        print(f"{'Leverage':>8} {'Ret%':>8} {'WinR%':>8} {'PF':>8} {'Trades':>8} {'DD%':>8} {'Sharpe':>8}")
        print("-" * 60)
        
        for lev in [5, 10, 20, 50, 100]:
            p = BASE.copy()
            p["tp_pct"] = tp
            p["sl_pct"] = sl
            p["trailing_activation_pct"] = ta
            p["trailing_callback_points"] = tc
            p["timeframe"] = "30m"
            
            eng = BacktestEngine()
            r = eng.run("macd_divergence", p, "BTC-USDT-SWAP", "30m", klines, 10000, lev)
            
            if not r or not r.get("ok"):
                print(f"{lev:>6}X FAILED")
                continue
            
            m = "*" if r["total_return"] > 0 else " "
            print(f"{m} {lev:>6}X {r['total_return']:>8.2f} {r['win_rate']:>8.1f} {r['profit_factor']:>8.2f} {r['trade_count']:>8d} {r['max_drawdown']:>8.2f} {r['sharpe_ratio']:>8.2f}")
