"""MACD背离策略回测 — 15m & 30m 长周期回测

使用OKX公开接口获取更多K线数据（最多1440根），
覆盖约15天(15m) / 30天(30m)的数据。
"""
import sys
import os
import time
import requests as req_lib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.strategy import get_strategy_class
from app.services.backtest import BacktestEngine

# ─── 回测配置 ───
SYMBOL = "BTC-USDT"
LEVERAGE = 10
INITIAL_CAPITAL = 10000
SIZE = 1
TIMEFRAMES = ["15m", "30m"]
OKX_BASE = "https://www.okx.com"


def fetch_klines_extended(symbol: str, timeframe: str, total: int = 1440) -> list:
    """从OKX公开接口分批获取K线数据（最多1440根）"""
    all_klines = []
    after = ""  # 获取更早的数据
    
    url = f"{OKX_BASE}/api/v5/market/history-candles"
    
    remaining = total
    while remaining > 0:
        batch = min(remaining, 300)
        params = {
            "instId": f"{symbol}-SWAP",
            "bar": timeframe,
            "limit": str(batch),
        }
        if after:
            params["after"] = after
        
        try:
            resp = req_lib.get(url, params=params, timeout=30)
            data = resp.json()
            
            if data.get("code") != "0" or not data.get("data"):
                break
            
            batch_klines = []
            for c in data["data"]:
                batch_klines.append({
                    "timestamp": int(c[0]),
                    "open": float(c[1]),
                    "high": float(c[2]),
                    "low": float(c[3]),
                    "close": float(c[4]),
                    "volume": float(c[5]),
                })
            
            if not batch_klines:
                break
            
            all_klines.extend(batch_klines)
            remaining -= len(batch_klines)
            
            # 最早K线的时间戳作为 after
            earliest_ts = str(batch_klines[-1]["timestamp"])
            after = earliest_ts
            
            # 限频
            time.sleep(0.3)
            
        except Exception as e:
            print(f"  ERROR: {e}")
            break
    
    # 去重 + 排序
    seen = set()
    unique = []
    for k in all_klines:
        if k["timestamp"] not in seen:
            seen.add(k["timestamp"])
            unique.append(k)
    
    unique.sort(key=lambda x: x["timestamp"])
    return unique


# MACD背离基础参数
BASE_PARAMS = {
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "lookback_bars": 50,
    "price_near_high": 0.99,
    "price_near_low": 1.01,
    "macd_div_high": 0.9,
    "macd_div_low": 1.1,
    "size_mode": "fixed",
    "size": SIZE,
    "inst_id": "BTC-USDT-SWAP",
}

# 止盈止损组合（精简版，聚焦有潜力的）
TP_SL_COMBOS = [
    # (name, tp_pct, sl_pct, trail_activate, trail_callback)
    ("默认(0.3/0.25)", 0.3, 0.25, 0.2, 15),
    ("宽TP1(0.5/0.3)", 0.5, 0.3, 0.3, 20),
    ("宽TP2(1.0/0.5)", 1.0, 0.5, 0.5, 30),
    ("大TP小SL(1.5/0.3)", 1.5, 0.3, 0.8, 40),
    ("大TP小SL2(2.0/0.3)", 2.0, 0.3, 1.0, 50),
    ("极宽TP(3.0/0.5)", 3.0, 0.5, 1.5, 60),
    ("无TP/SL纯信号", 0, 0, 0, 0),
    ("纯信号+移动止盈", 0, 0, 0.5, 30),
    ("纯信号+宽移动止盈", 0, 0, 1.0, 50),
    ("中等(0.5/0.25)", 0.5, 0.25, 0.3, 20),
    ("窄SL(1.0/0.2)", 1.0, 0.2, 0.5, 25),
    ("只SL无TP(0/0.3)", 0, 0.3, 0, 0),
]

LOOKBACK_VARIANTS = [30, 50, 70, 100]


def run_backtest(strategy_type, params, klines, timeframe, initial_capital, leverage):
    engine = BacktestEngine()
    return engine.run(
        strategy_type=strategy_type,
        params=params.copy(),
        symbol="BTC-USDT-SWAP",
        timeframe=timeframe,
        klines=klines,
        initial_capital=initial_capital,
        leverage=leverage,
    )


def main():
    print("=" * 95)
    print("  MACD背离策略回测 — 15m & 30m 长周期多参数对比")
    print("=" * 95)
    
    strategy_cls = get_strategy_class("macd_divergence")
    if not strategy_cls:
        print("ERROR: macd_divergence 策略未找到")
        return
    
    # 获取K线数据
    klines_data = {}
    for tf in TIMEFRAMES:
        print(f"\n获取 {tf} K线数据（最多1440根）...")
        klines = fetch_klines_extended(SYMBOL, tf, total=1440)
        if not klines:
            print(f"  无法获取 {tf} K线，跳过")
            continue
        days = (klines[-1]["timestamp"] - klines[0]["timestamp"]) / 1000 / 86400
        print(f"  获取到 {len(klines)} 根K线, 覆盖 {days:.1f} 天")
        print(f"  时间: {time.strftime('%Y-%m-%d %H:%M', time.localtime(klines[0]['timestamp']/1000))} ~ {time.strftime('%Y-%m-%d %H:%M', time.localtime(klines[-1]['timestamp']/1000))}")
        print(f"  价格: ${klines[0]['close']:.0f} ~ ${max(k['high'] for k in klines):.0f}")
        klines_data[tf] = klines
    
    if not klines_data:
        print("ERROR: 无法获取任何K线数据")
        return
    
    # ─── PART 1: 止盈止损组合 ───
    print("\n" + "=" * 95)
    print("  PART 1: 止盈止损参数对比 (杠杆=10X)")
    print("=" * 95)
    
    all_results = []
    
    for tf, klines in klines_data.items():
        days = (klines[-1]["timestamp"] - klines[0]["timestamp"]) / 1000 / 86400
        print(f"\n{'─' * 95}")
        print(f"  周期: {tf}  |  K线: {len(klines)}根  |  天数: {days:.1f}天  |  杠杆: {LEVERAGE}X")
        print(f"{'─' * 95}")
        print(f"  {'组合':<24} {'收益%':>8} {'胜率%':>8} {'盈亏比':>8} {'交易数':>8} {'回撤%':>8} {'夏普':>8} {'手续费':>10} {'日均交易':>8}")
        print(f"{'─' * 95}")
        
        for name, tp, sl, trail_act, trail_cb in TP_SL_COMBOS:
            params = BASE_PARAMS.copy()
            params["tp_pct"] = tp
            params["sl_pct"] = sl
            params["trailing_activation_pct"] = trail_act
            params["trailing_callback_points"] = trail_cb
            params["timeframe"] = tf
            
            result = run_backtest("macd_divergence", params, klines, tf, INITIAL_CAPITAL, LEVERAGE)
            
            if not result or not result.get("ok"):
                print(f"  {name:<24} FAILED")
                continue
            
            ret = result["total_return"]
            wr = result["win_rate"]
            pf = result["profit_factor"]
            tc = result["trade_count"]
            dd = result["max_drawdown"]
            sr = result["sharpe_ratio"]
            fees = result["total_fees"]
            daily_trades = tc / days if days > 0 else 0
            
            all_results.append({
                "timeframe": tf, "combo": name,
                "tp": tp, "sl": sl, "trail_act": trail_act, "trail_cb": trail_cb,
                "return": ret, "win_rate": wr, "profit_factor": pf,
                "trade_count": tc, "drawdown": dd, "sharpe": sr, "fees": fees,
                "daily_trades": daily_trades, "days": days,
            })
            
            marker = "★" if ret > 0 else " "
            print(f"{marker} {name:<24} {ret:>8.2f} {wr:>8.1f} {pf:>8.2f} {tc:>8d} {dd:>8.2f} {sr:>8.2f} {fees:>10.2f} {daily_trades:>8.1f}")
    
    # ─── PART 2: lookback_bars ───
    print("\n" + "=" * 95)
    print("  PART 2: lookback_bars 变体（使用各周期最优止盈止损）")
    print("=" * 95)
    
    for tf, klines in klines_data.items():
        tf_results = [r for r in all_results if r["timeframe"] == tf]
        best = max(tf_results, key=lambda x: x["return"]) if tf_results else {"tp": 0.3, "sl": 0.25, "trail_act": 0.2, "trail_cb": 15, "combo": "默认"}
        
        days = (klines[-1]["timestamp"] - klines[0]["timestamp"]) / 1000 / 86400
        print(f"\n{'─' * 80}")
        print(f"  周期: {tf}  |  天数: {days:.1f}天  |  使用: {best['combo']} (TP={best['tp']}% SL={best['sl']}%)")
        print(f"{'─' * 80}")
        print(f"  {'lookback':>10} {'收益%':>8} {'胜率%':>8} {'盈亏比':>8} {'交易数':>8} {'回撤%':>8} {'夏普':>8}")
        print(f"{'─' * 80}")
        
        for lb in LOOKBACK_VARIANTS:
            params = BASE_PARAMS.copy()
            params["tp_pct"] = best["tp"]
            params["sl_pct"] = best["sl"]
            params["trailing_activation_pct"] = best["trail_act"]
            params["trailing_callback_points"] = best["trail_cb"]
            params["lookback_bars"] = lb
            params["timeframe"] = tf
            
            result = run_backtest("macd_divergence", params, klines, tf, INITIAL_CAPITAL, LEVERAGE)
            
            if not result or not result.get("ok"):
                print(f"  {lb:>10} FAILED")
                continue
            
            ret = result["total_return"]
            wr = result["win_rate"]
            pf = result["profit_factor"]
            tc = result["trade_count"]
            dd = result["max_drawdown"]
            sr = result["sharpe_ratio"]
            
            marker = "★" if ret > 0 else " "
            print(f"{marker} {lb:>10} {ret:>8.2f} {wr:>8.1f} {pf:>8.2f} {tc:>8d} {dd:>8.2f} {sr:>8.2f}")
    
    # ─── PART 3: 杠杆对比 ───
    print("\n" + "=" * 95)
    print("  PART 3: 杠杆倍数对比（使用各周期最优参数）")
    print("=" * 95)
    
    for tf, klines in klines_data.items():
        tf_results = [r for r in all_results if r["timeframe"] == tf]
        if not tf_results:
            continue
        best = max(tf_results, key=lambda x: x["return"])
        
        print(f"\n{'─' * 80}")
        print(f"  周期: {tf}  |  最优组合: {best['combo']}")
        print(f"{'─' * 80}")
        print(f"  {'杠杆':>6} {'收益%':>8} {'胜率%':>8} {'盈亏比':>8} {'交易数':>8} {'回撤%':>8} {'夏普':>8}")
        print(f"{'─' * 80}")
        
        for lev in [5, 10, 20, 50, 100]:
            params = BASE_PARAMS.copy()
            params["tp_pct"] = best["tp"]
            params["sl_pct"] = best["sl"]
            params["trailing_activation_pct"] = best["trail_act"]
            params["trailing_callback_points"] = best["trail_cb"]
            params["timeframe"] = tf
            
            result = run_backtest("macd_divergence", params, klines, tf, INITIAL_CAPITAL, lev)
            
            if not result or not result.get("ok"):
                print(f"  {lev:>4}X FAILED")
                continue
            
            ret = result["total_return"]
            wr = result["win_rate"]
            pf = result["profit_factor"]
            tc = result["trade_count"]
            dd = result["max_drawdown"]
            sr = result["sharpe_ratio"]
            
            marker = "★" if ret > 0 else " "
            print(f"{marker} {lev:>4}X {ret:>8.2f} {wr:>8.1f} {pf:>8.2f} {tc:>8d} {dd:>8.2f} {sr:>8.2f}")
    
    # ─── 汇总 ───
    print("\n" + "=" * 95)
    print("  ★★★ 汇总：各周期最优参数 ★★★")
    print("=" * 95)
    
    for tf in klines_data:
        tf_results = [r for r in all_results if r["timeframe"] == tf]
        if not tf_results:
            continue
        
        best_ret = max(tf_results, key=lambda x: x["return"])
        best_wr = max(tf_results, key=lambda x: x["win_rate"])
        best_sr = max(tf_results, key=lambda x: x["sharpe"])
        
        print(f"\n{'─' * 60}")
        print(f"  {tf} 周期 ({best_ret['days']:.1f}天)")
        print(f"{'─' * 60}")
        print(f"  最高收益: {best_ret['combo']} → {best_ret['return']:.2f}%")
        print(f"    TP={best_ret['tp']}% SL={best_ret['sl']}% TrailAct={best_ret['trail_act']}% TrailCB={best_ret['trail_cb']}pts")
        print(f"    胜率={best_ret['win_rate']:.1f}% 盈亏比={best_ret['profit_factor']:.2f} 回撤={best_ret['drawdown']:.2f}% 夏普={best_ret['sharpe']:.2f}")
        print(f"    交易数={best_ret['trade_count']} 日均={best_ret['daily_trades']:.1f} 手续费={best_ret['fees']:.2f}")
        
        if best_wr != best_ret:
            print(f"\n  最高胜率: {best_wr['combo']} → {best_wr['win_rate']:.1f}%")
            print(f"    收益={best_wr['return']:.2f}% 盈亏比={best_wr['profit_factor']:.2f}")
        
        if best_sr != best_ret:
            print(f"\n  最高夏普: {best_sr['combo']} → {best_sr['sharpe']:.2f}")
            print(f"    收益={best_sr['return']:.2f}% 胜率={best_sr['win_rate']:.1f}%")


if __name__ == "__main__":
    main()
