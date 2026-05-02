# -*- coding: utf-8 -*-
"""严格按照 MACD-Divergence-Strategy-Config.md 参数回测

配置:
- 本金: 1000 USDT
- 杠杆: 100X
- 每次开仓: 1 张
- 止损: 0.25%
- 止盈: 0.3%
- 移动止盈激活: 0.2%
- 移动止盈回调: 15 点
- lookback: 50
- 手续费: 开仓0.02% + 平仓0.05% = 0.07%
"""
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


# 严格按照配置文件的参数
CONFIG_PARAMS = {
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "lookback_bars": 50,
    "price_near_high": 0.99,
    "price_near_low": 1.01,
    "macd_div_high": 0.9,
    "macd_div_low": 1.1,
    # 100X 杠杆下: 价格变动 0.25% = 杠杆收益 25%
    "sl_pct": 25,
    "tp_pct": 30,
    "trailing_activation_pct": 20,
    "trailing_callback_points": 15,
    "size_mode": "fixed",
    "size": 1,
    "inst_id": "BTC-USDT-SWAP",
}

INITIAL_CAPITAL = 1000
LEVERAGE = 100
TIMEFRAMES = ["15m", "30m"]


def run_backtest(tf, klines):
    params = CONFIG_PARAMS.copy()
    params["timeframe"] = tf
    engine = BacktestEngine()
    result = engine.run(
        strategy_type="macd_divergence",
        params=params,
        symbol="BTC-USDT-SWAP",
        timeframe=tf,
        klines=klines,
        initial_capital=INITIAL_CAPITAL,
        leverage=LEVERAGE,
        fee_rate=0.00035,
    )
    return result


def main():
    print("=" * 80)
    print("  MACD 背离策略回测 - 严格按照配置文件参数")
    print("=" * 80)
    print(f"\n配置:")
    print(f"  本金: {INITIAL_CAPITAL} USDT")
    print(f"  杠杆: {LEVERAGE}X")
    print(f"  开仓: 1 张")
    print(f"  止损: 0.25% (杠杆收益 25%)")
    print(f"  止盈: 0.3% (杠杆收益 30%)")
    print(f"  移动止盈激活: 0.2% (杠杆收益 20%)")
    print(f"  移动止盈回调: 15 点")
    print(f"  手续费: 0.035%")
    
    klines_data = {}
    for tf in TIMEFRAMES:
        print(f"\n获取 {tf} K线数据...")
        klines = fetch_klines(tf, 1440)
        if not klines:
            print(f"  无法获取 {tf} K线")
            continue
        days = (klines[-1]["timestamp"] - klines[0]["timestamp"]) / 1000 / 86400
        print(f"  获取到 {len(klines)} 根K线, 覆盖 {days:.1f} 天")
        klines_data[tf] = klines
    
    if not klines_data:
        print("ERROR: 无法获取K线数据")
        return
    
    print("\n" + "=" * 80)
    print("  回测结果")
    print("=" * 80)
    
    header = f"{'周期':<8} {'交易数':>8} {'胜率%':>8} {'盈亏比':>8} {'毛收益':>10} {'手续费':>10} {'净收益':>10} {'最终余额':>12} {'回撤%':>8}"
    print(f"\n{header}")
    print("-" * 95)
    
    for tf, klines in klines_data.items():
        result = run_backtest(tf, klines)
        
        if not result or not result.get("ok"):
            print(f"{tf:<8} FAILED")
            continue
        
        tc = result["trade_count"]
        wr = result["win_rate"]
        pf = result["profit_factor"]
        fees = result["total_fees"]
        dd = result["max_drawdown"]
        final = result["final_capital"]
        net = final - INITIAL_CAPITAL
        gross = net + fees
        
        print(f"{tf:<8} {tc:>8} {wr:>8.1f} {pf:>8.2f} {gross:>10.2f}U {fees:>10.2f}U {net:>10.2f}U {final:>12.2f}U {dd:>8.2f}")
    
    print("\n" + "=" * 80)
    print("  配置文件中的结果 (对比)")
    print("=" * 80)
    print("""
| 周期 | 交易次数 | 胜率 | 盈利因子 | 毛收益 | 手续费 | 净收益 | 最终余额 | 回撤 |
| 15m  | 233 笔   | 55.4%| 0.98     | +119.30U| -124.80U| -5.50U | 994.50U  | 3.2% |
| 30m  | 227 笔   | 59.9%| 1.33     | +186.70U| -117.32U| +69.38U| 1069.38U | 2.0% |
""")


if __name__ == "__main__":
    main()
