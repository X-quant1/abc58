# -*- coding: utf-8 -*-
"""
MACD 背离策略参数优化

同时测试：
1. 峰值窗口优化（影响交易数）
2. 止盈止损优化
3. 移动止盈优化
"""
import sys, os, time
import requests as req_lib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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
        except:
            break
    seen = set()
    unique = []
    for k in all_klines:
        if k["timestamp"] not in seen:
            seen.add(k["timestamp"])
            unique.append(k)
    unique.sort(key=lambda x: x["timestamp"])
    return unique


def calc_ema(data, period):
    alpha = 2 / (period + 1)
    result = [data[0]]
    for i in range(1, len(data)):
        result.append(alpha * data[i] + (1 - alpha) * result[-1])
    return result


def calc_macd(closes, fast=12, slow=26, signal=9):
    ema_fast = calc_ema(closes, fast)
    ema_slow = calc_ema(closes, slow)
    dif = [ema_fast[i] - ema_slow[i] for i in range(len(closes))]
    dea = calc_ema(dif, signal)
    return dif, dea


def find_peaks(data, window=5):
    peaks = []
    for i in range(window, len(data) - window):
        is_peak = True
        for j in range(i - window, i + window + 1):
            if j != i and data[j] >= data[i]:
                is_peak = False
                break
        if is_peak:
            peaks.append((i, data[i]))
    return peaks


def find_troughs(data, window=5):
    troughs = []
    for i in range(window, len(data) - window):
        is_trough = True
        for j in range(i - window, i + window + 1):
            if j != i and data[j] <= data[i]:
                is_trough = False
                break
        if is_trough:
            troughs.append((i, data[i]))
    return troughs


def run_backtest(klines, tf, params):
    closes = [k["close"] for k in klines]
    timestamps = [k["timestamp"] for k in klines]
    highs = [k["high"] for k in klines]
    lows = [k["low"] for k in klines]
    
    dif, dea = calc_macd(closes, params["fast"], params["slow"], params["signal"])
    
    price_peaks = find_peaks(closes, params["peak_window"])
    price_troughs = find_troughs(closes, params["peak_window"])
    dif_peaks = find_peaks(dif, params["peak_window"])
    dif_troughs = find_troughs(dif, params["peak_window"])
    
    peak_map = {i: v for i, v in price_peaks}
    trough_map = {i: v for i, v in price_troughs}
    dif_peak_map = {i: v for i, v in dif_peaks}
    dif_trough_map = {i: v for i, v in dif_troughs}
    
    capital = params["initial_capital"]
    position = None
    trades = []
    fees_total = 0
    last_trade_time = 0
    
    maker_fee = 0.0002
    taker_fee = 0.0005
    face_value = 0.01
    
    cooldown_ms = params["cooldown_ms"]
    min_bars = params["slow"] + params["signal"] + 50
    
    for i in range(min_bars, len(klines)):
        current_price = closes[i]
        current_high = highs[i]
        current_low = lows[i]
        current_time = timestamps[i]
        
        if position:
            entry = position["entry"]
            side = position["side"]
            
            if side == "long":
                position["highest"] = max(position["highest"], current_high)
            else:
                position["lowest"] = min(position["lowest"], current_low)
            
            if side == "long":
                price_change_pct = (current_price - entry) / entry
            else:
                price_change_pct = (entry - current_price) / entry
            
            if price_change_pct <= -params["sl_pct"]:
                if side == "long":
                    pnl = (current_price - entry) * params["size"] * face_value
                else:
                    pnl = (entry - current_price) * params["size"] * face_value
                close_fee = current_price * params["size"] * face_value * taker_fee
                fees_total += close_fee
                capital += pnl - close_fee
                trades.append({"type": "close", "side": side, "price": current_price, "pnl": pnl - close_fee, "reason": "sl"})
                last_trade_time = current_time
                position = None
                continue
            
            if price_change_pct >= params["tp_pct"]:
                if side == "long":
                    pnl = (current_price - entry) * params["size"] * face_value
                else:
                    pnl = (entry - current_price) * params["size"] * face_value
                close_fee = current_price * params["size"] * face_value * taker_fee
                fees_total += close_fee
                capital += pnl - close_fee
                trades.append({"type": "close", "side": side, "price": current_price, "pnl": pnl - close_fee, "reason": "tp"})
                last_trade_time = current_time
                position = None
                continue
            
            if params["trail_act"] > 0 and price_change_pct >= params["trail_act"]:
                if side == "long":
                    drawdown_points = position["highest"] - current_price
                    if drawdown_points >= params["trail_cb"]:
                        pnl = (current_price - entry) * params["size"] * face_value
                        close_fee = current_price * params["size"] * face_value * taker_fee
                        fees_total += close_fee
                        capital += pnl - close_fee
                        trades.append({"type": "close", "side": side, "price": current_price, "pnl": pnl - close_fee, "reason": "trail"})
                        last_trade_time = current_time
                        position = None
                        continue
                else:
                    bounce_points = current_price - position["lowest"]
                    if bounce_points >= params["trail_cb"]:
                        pnl = (entry - current_price) * params["size"] * face_value
                        close_fee = current_price * params["size"] * face_value * taker_fee
                        fees_total += close_fee
                        capital += pnl - close_fee
                        trades.append({"type": "close", "side": side, "price": current_price, "pnl": pnl - close_fee, "reason": "trail"})
                        last_trade_time = current_time
                        position = None
                        continue
        
        if position is None:
            if current_time - last_trade_time < cooldown_ms:
                continue
            
            signal = None
            
            if i in peak_map:
                prev_peaks = [(idx, val) for idx, val in price_peaks if idx < i]
                if len(prev_peaks) >= 2:
                    prev_peak1_idx, prev_peak1_val = prev_peaks[-1]
                    prev_peak2_idx, prev_peak2_val = prev_peaks[-2]
                    
                    if prev_peak1_val > prev_peak2_val:
                        prev_dif_peaks = [(idx, val) for idx, val in dif_peaks if idx < i]
                        if len(prev_dif_peaks) >= 2:
                            prev_dif1_idx, prev_dif1_val = prev_dif_peaks[-1]
                            prev_dif2_idx, prev_dif2_val = prev_dif_peaks[-2]
                            
                            if prev_dif1_val < prev_dif2_val:
                                signal = "short"
            
            if i in trough_map:
                prev_troughs = [(idx, val) for idx, val in price_troughs if idx < i]
                if len(prev_troughs) >= 2:
                    prev_trough1_idx, prev_trough1_val = prev_troughs[-1]
                    prev_trough2_idx, prev_trough2_val = prev_troughs[-2]
                    
                    if prev_trough1_val < prev_trough2_val:
                        prev_dif_troughs = [(idx, val) for idx, val in dif_troughs if idx < i]
                        if len(prev_dif_troughs) >= 2:
                            prev_dif1_idx, prev_dif1_val = prev_dif_troughs[-1]
                            prev_dif2_idx, prev_dif2_val = prev_dif_troughs[-2]
                            
                            if prev_dif1_val > prev_dif2_val:
                                signal = "long"
            
            if signal == "long":
                open_fee = current_price * params["size"] * face_value * maker_fee
                fees_total += open_fee
                capital -= open_fee
                position = {"side": "long", "entry": current_price, "highest": current_high, "lowest": current_low}
                trades.append({"type": "open", "side": "long", "price": current_price})
            
            elif signal == "short":
                open_fee = current_price * params["size"] * face_value * maker_fee
                fees_total += open_fee
                capital -= open_fee
                position = {"side": "short", "entry": current_price, "highest": current_high, "lowest": current_low}
                trades.append({"type": "open", "side": "short", "price": current_price})
    
    if position:
        final_price = closes[-1]
        if position["side"] == "long":
            pnl = (final_price - position["entry"]) * params["size"] * face_value
        else:
            pnl = (position["entry"] - final_price) * params["size"] * face_value
        close_fee = final_price * params["size"] * face_value * taker_fee
        fees_total += close_fee
        capital += pnl - close_fee
        trades.append({"type": "close", "side": position["side"], "price": final_price, "pnl": pnl - close_fee, "reason": "end"})
    
    close_trades = [t for t in trades if t["type"] == "close"]
    win_trades = [t for t in close_trades if t.get("pnl", 0) > 0]
    lose_trades = [t for t in close_trades if t.get("pnl", 0) < 0]
    
    total_pnl = sum(t.get("pnl", 0) for t in close_trades)
    gross_profit = sum(t["pnl"] for t in win_trades) if win_trades else 0
    gross_loss = abs(sum(t["pnl"] for t in lose_trades)) if lose_trades else 1
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
    win_rate = len(win_trades) / len(close_trades) * 100 if close_trades else 0
    
    return {
        "final_capital": capital,
        "net_pnl": capital - params["initial_capital"],
        "gross_pnl": total_pnl + fees_total,
        "fees": fees_total,
        "trade_count": len(close_trades),
        "win_rate": win_rate,
        "profit_factor": profit_factor,
    }


def main():
    print("=" * 100)
    print("  MACD 背离策略参数优化")
    print("=" * 100)
    
    # 获取K线
    print("\n获取K线数据...")
    klines_data = {}
    for tf in ["15m", "30m"]:
        klines = fetch_klines(tf, 1440)
        if klines:
            days = (klines[-1]["timestamp"] - klines[0]["timestamp"]) / 1000 / 86400
            print(f"  {tf}: {len(klines)} 根K线, {days:.1f} 天")
            klines_data[tf] = klines
    
    if not klines_data:
        print("ERROR: 无法获取K线")
        return
    
    # 测试参数组合
    test_cases = [
        # 峰值窗口优化（影响交易数）
        {"name": "峰值窗口=3", "peak_window": 3, "sl_pct": 0.0025, "tp_pct": 0.003, "trail_act": 0.002, "trail_cb": 15, "cooldown_min": 30},
        {"name": "峰值窗口=5 (基准)", "peak_window": 5, "sl_pct": 0.0025, "tp_pct": 0.003, "trail_act": 0.002, "trail_cb": 15, "cooldown_min": 30},
        {"name": "峰值窗口=7", "peak_window": 7, "sl_pct": 0.0025, "tp_pct": 0.003, "trail_act": 0.002, "trail_cb": 15, "cooldown_min": 30},
        {"name": "峰值窗口=10", "peak_window": 10, "sl_pct": 0.0025, "tp_pct": 0.003, "trail_act": 0.002, "trail_cb": 15, "cooldown_min": 30},
        
        # 止盈止损优化
        {"name": "止损0.2%", "peak_window": 5, "sl_pct": 0.002, "tp_pct": 0.003, "trail_act": 0.002, "trail_cb": 15, "cooldown_min": 30},
        {"name": "止损0.3%", "peak_window": 5, "sl_pct": 0.003, "tp_pct": 0.003, "trail_act": 0.002, "trail_cb": 15, "cooldown_min": 30},
        {"name": "止盈0.4%", "peak_window": 5, "sl_pct": 0.0025, "tp_pct": 0.004, "trail_act": 0.002, "trail_cb": 15, "cooldown_min": 30},
        {"name": "止盈0.5%", "peak_window": 5, "sl_pct": 0.0025, "tp_pct": 0.005, "trail_act": 0.002, "trail_cb": 15, "cooldown_min": 30},
        
        # 移动止盈优化
        {"name": "移动激活0.15%", "peak_window": 5, "sl_pct": 0.0025, "tp_pct": 0.003, "trail_act": 0.0015, "trail_cb": 15, "cooldown_min": 30},
        {"name": "移动激活0.25%", "peak_window": 5, "sl_pct": 0.0025, "tp_pct": 0.003, "trail_act": 0.0025, "trail_cb": 15, "cooldown_min": 30},
        {"name": "回调10点", "peak_window": 5, "sl_pct": 0.0025, "tp_pct": 0.003, "trail_act": 0.002, "trail_cb": 10, "cooldown_min": 30},
        {"name": "回调20点", "peak_window": 5, "sl_pct": 0.0025, "tp_pct": 0.003, "trail_act": 0.002, "trail_cb": 20, "cooldown_min": 30},
        
        # 冷却时间优化
        {"name": "冷却15分钟", "peak_window": 5, "sl_pct": 0.0025, "tp_pct": 0.003, "trail_act": 0.002, "trail_cb": 15, "cooldown_min": 15},
        {"name": "冷却45分钟", "peak_window": 5, "sl_pct": 0.0025, "tp_pct": 0.003, "trail_act": 0.002, "trail_cb": 15, "cooldown_min": 45},
        {"name": "冷却60分钟", "peak_window": 5, "sl_pct": 0.0025, "tp_pct": 0.003, "trail_act": 0.002, "trail_cb": 15, "cooldown_min": 60},
        
        # 组合优化
        {"name": "组合A(窗口3+止损0.2%)", "peak_window": 3, "sl_pct": 0.002, "tp_pct": 0.003, "trail_act": 0.0015, "trail_cb": 10, "cooldown_min": 15},
        {"name": "组合B(窗口7+止盈0.4%)", "peak_window": 7, "sl_pct": 0.0025, "tp_pct": 0.004, "trail_act": 0.002, "trail_cb": 15, "cooldown_min": 30},
        {"name": "组合C(窗口10+冷却60)", "peak_window": 10, "sl_pct": 0.0025, "tp_pct": 0.003, "trail_act": 0.002, "trail_cb": 15, "cooldown_min": 60},
    ]
    
    results = []
    
    for case in test_cases:
        params = {
            "fast": 12,
            "slow": 26,
            "signal": 9,
            "peak_window": case["peak_window"],
            "sl_pct": case["sl_pct"],
            "tp_pct": case["tp_pct"],
            "trail_act": case["trail_act"],
            "trail_cb": case["trail_cb"],
            "cooldown_ms": case["cooldown_min"] * 60 * 1000,
            "initial_capital": 1000,
            "leverage": 100,
            "size": 1,
        }
        
        row = {"name": case["name"]}
        for tf in ["15m", "30m"]:
            result = run_backtest(klines_data[tf], tf, params)
            row[f"{tf}_trades"] = result["trade_count"]
            row[f"{tf}_wr"] = result["win_rate"]
            row[f"{tf}_pf"] = result["profit_factor"]
            row[f"{tf}_net"] = result["net_pnl"]
            row[f"{tf}_final"] = result["final_capital"]
        
        results.append(row)
    
    # 输出结果
    print("\n" + "=" * 100)
    print("  15m 周期结果")
    print("=" * 100)
    print(f"\n{'参数组合':<25} {'交易数':>8} {'胜率%':>8} {'盈亏比':>8} {'净收益':>10} {'最终余额':>12}")
    print("-" * 100)
    
    for r in results:
        marker = "*" if r["15m_net"] > 0 else " "
        print(f"{marker} {r['name']:<25} {r['15m_trades']:>8} {r['15m_wr']:>8.1f} {r['15m_pf']:>8.2f} {r['15m_net']:>10.2f}U {r['15m_final']:>12.2f}U")
    
    print("\n" + "=" * 100)
    print("  30m 周期结果")
    print("=" * 100)
    print(f"\n{'参数组合':<25} {'交易数':>8} {'胜率%':>8} {'盈亏比':>8} {'净收益':>10} {'最终余额':>12}")
    print("-" * 100)
    
    for r in results:
        marker = "*" if r["30m_net"] > 0 else " "
        print(f"{marker} {r['name']:<25} {r['30m_trades']:>8} {r['30m_wr']:>8.1f} {r['30m_pf']:>8.2f} {r['30m_net']:>10.2f}U {r['30m_final']:>12.2f}U")
    
    # 找出最优参数
    print("\n" + "=" * 100)
    print("  最优参数")
    print("=" * 100)
    
    best_15m = max(results, key=lambda x: x["15m_net"])
    best_30m = max(results, key=lambda x: x["30m_net"])
    
    print(f"\n15m 最优: {best_15m['name']}")
    print(f"  交易数: {best_15m['15m_trades']}, 胜率: {best_15m['15m_wr']:.1f}%, 净收益: {best_15m['15m_net']:.2f}U, 最终余额: {best_15m['15m_final']:.2f}U")
    
    print(f"\n30m 最优: {best_30m['name']}")
    print(f"  交易数: {best_30m['30m_trades']}, 胜率: {best_30m['30m_wr']:.1f}%, 净收益: {best_30m['30m_net']:.2f}U, 最终余额: {best_30m['30m_final']:.2f}U")
    
    print("\n" + "=" * 100)
    print("  配置文件结果 (对比)")
    print("=" * 100)
    print("""
| 周期 | 交易数 | 胜率 | 盈亏比 | 毛收益 | 手续费 | 净收益 | 最终余额 |
| 15m  | 233    | 55.4%| 0.98   | +119.30U| -124.80U| -5.50U | 994.50U  |
| 30m  | 227    | 59.9%| 1.33   | +186.70U| -117.32U| +69.38U| 1069.38U |
""")


if __name__ == "__main__":
    main()
