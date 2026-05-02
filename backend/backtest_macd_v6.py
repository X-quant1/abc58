# -*- coding: utf-8 -*-
"""
MACD 背离策略回测 v6 - 峰值背离检测

核心逻辑：
1. 找到价格和DIF的局部峰值/谷值
2. 比较相邻两个峰值：价格创新高但DIF未创新高 = 顶背离
3. 比较相邻两个谷值：价格创新低但DIF未创新低 = 底背离
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
    """找到局部峰值"""
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
    """找到局部谷值"""
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
    """峰值背离检测回测"""
    closes = [k["close"] for k in klines]
    timestamps = [k["timestamp"] for k in klines]
    highs = [k["high"] for k in klines]
    lows = [k["low"] for k in klines]
    
    dif, dea = calc_macd(closes, params["fast"], params["slow"], params["signal"])
    
    # 预计算峰值和谷值
    price_peaks = find_peaks(closes, params["peak_window"])
    price_troughs = find_troughs(closes, params["peak_window"])
    dif_peaks = find_peaks(dif, params["peak_window"])
    dif_troughs = find_troughs(dif, params["peak_window"])
    
    # 建立索引映射
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
        
        # 1. 持仓检查止盈止损
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
            
            # 止损
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
            
            # 止盈
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
            
            # 移动止盈
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
        
        # 2. 峰值背离信号检测
        if position is None:
            if current_time - last_trade_time < cooldown_ms:
                continue
            
            signal = None
            
            # 检查当前是否是峰值点
            if i in peak_map:
                # 找到之前最近的两个价格峰值
                prev_peaks = [(idx, val) for idx, val in price_peaks if idx < i]
                if len(prev_peaks) >= 2:
                    prev_peak1_idx, prev_peak1_val = prev_peaks[-1]
                    prev_peak2_idx, prev_peak2_val = prev_peaks[-2]
                    
                    # 价格创新高
                    if prev_peak1_val > prev_peak2_val:
                        # 检查DIF是否创新高
                        prev_dif_peaks = [(idx, val) for idx, val in dif_peaks if idx < i]
                        if len(prev_dif_peaks) >= 2:
                            prev_dif1_idx, prev_dif1_val = prev_dif_peaks[-1]
                            prev_dif2_idx, prev_dif2_val = prev_dif_peaks[-2]
                            
                            # DIF未创新高 = 顶背离
                            if prev_dif1_val < prev_dif2_val:
                                signal = "short"
            
            # 检查当前是否是谷值点
            if i in trough_map:
                prev_troughs = [(idx, val) for idx, val in price_troughs if idx < i]
                if len(prev_troughs) >= 2:
                    prev_trough1_idx, prev_trough1_val = prev_troughs[-1]
                    prev_trough2_idx, prev_trough2_val = prev_troughs[-2]
                    
                    # 价格创新低
                    if prev_trough1_val < prev_trough2_val:
                        prev_dif_troughs = [(idx, val) for idx, val in dif_troughs if idx < i]
                        if len(prev_dif_troughs) >= 2:
                            prev_dif1_idx, prev_dif1_val = prev_dif_troughs[-1]
                            prev_dif2_idx, prev_dif2_val = prev_dif_troughs[-2]
                            
                            # DIF未创新低 = 底背离
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
    
    # 最后平仓
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
    
    # 统计
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
        "trades": trades,
    }


def main():
    params = {
        "fast": 12,
        "slow": 26,
        "signal": 9,
        "peak_window": 5,       # 峰值检测窗口
        "sl_pct": 0.0025,
        "tp_pct": 0.003,
        "trail_act": 0.002,
        "trail_cb": 15,
        "cooldown_ms": 30 * 60 * 1000,
        "initial_capital": 1000,
        "leverage": 100,
        "size": 1,
    }
    
    print("=" * 90)
    print("  MACD 背离策略回测 v6 - 峰值背离检测")
    print("=" * 90)
    print(f"\n配置:")
    print(f"  本金: 1000 USDT, 杠杆: 100X, 开仓: 1 张")
    print(f"  止损: 0.25%, 止盈: 0.3%")
    print(f"  移动止盈: 激活 0.2%, 回调 15 点")
    print(f"  冷却: 30 分钟")
    print(f"  峰值检测窗口: 5")
    
    klines_data = {}
    for tf in ["5m", "15m", "30m", "1H"]:
        print(f"\n获取 {tf} K线...")
        klines = fetch_klines(tf, 1440)
        if klines:
            days = (klines[-1]["timestamp"] - klines[0]["timestamp"]) / 1000 / 86400
            print(f"  {len(klines)} 根K线, {days:.1f} 天")
            klines_data[tf] = klines
    
    if not klines_data:
        print("ERROR: 无法获取K线")
        return
    
    print("\n" + "=" * 90)
    print("  回测结果")
    print("=" * 90)
    
    print(f"\n{'周期':<8} {'交易数':>8} {'胜率%':>8} {'盈亏比':>8} {'毛收益':>10} {'手续费':>10} {'净收益':>10} {'最终余额':>12}")
    print("-" * 90)
    
    for tf, klines in klines_data.items():
        result = run_backtest(klines, tf, params)
        
        tc = result["trade_count"]
        wr = result["win_rate"]
        pf = result["profit_factor"]
        gross = result["gross_pnl"]
        fees = result["fees"]
        net = result["net_pnl"]
        final = result["final_capital"]
        
        marker = "*" if net > 0 else " "
        print(f"{marker} {tf:<8} {tc:>8} {wr:>8.1f} {pf:>8.2f} {gross:>10.2f}U {fees:>10.2f}U {net:>10.2f}U {final:>12.2f}U")
    
    print("\n" + "=" * 90)
    print("  配置文件结果 (对比)")
    print("=" * 90)
    print("""
| 周期 | 交易数 | 胜率 | 盈亏比 | 毛收益 | 手续费 | 净收益 | 最终余额 |
| 15m  | 233    | 55.4%| 0.98   | +119.30U| -124.80U| -5.50U | 994.50U  |
| 30m  | 227    | 59.9%| 1.33   | +186.70U| -117.32U| +69.38U| 1069.38U |
""")


if __name__ == "__main__":
    main()
