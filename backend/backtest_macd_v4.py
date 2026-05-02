# -*- coding: utf-8 -*-
"""
MACD 背离策略回测 v4 - 按照用户提供的精确参数规则

参数规则（用户确认）：
- 100X杠杆，70000点做多
- 40%止盈 = 70280 (价格变动 0.4%)
- 25%止损 = 69825 (价格变动 0.25%)
- 30%激活 = 70210 (价格变动 0.3%)
- 回调30点 = 价格回调 30 点
- 收益 = (平仓价 - 开仓价) × 张数 × 0.01
- 手续费：挂单 0.02% × 价格 × 张数 × 0.01，吃单 0.05% × 价格 × 张数 × 0.01
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


def run_backtest(klines, tf, params):
    """
    回测逻辑：
    - 止盈止损基于杠杆收益率（40% TP = 价格变动 0.4%）
    - 收益 = 点数差 × 张数 × 0.01
    - 手续费 = 价格 × 张数 × 0.01 × 费率
    """
    closes = [k["close"] for k in klines]
    timestamps = [k["timestamp"] for k in klines]
    highs = [k["high"] for k in klines]
    lows = [k["low"] for k in klines]
    
    dif, dea = calc_macd(closes, params["fast"], params["slow"], params["signal"])
    
    capital = params["initial_capital"]
    position = None
    trades = []
    fees_total = 0
    last_trade_time = 0
    
    # 手续费率
    maker_fee = 0.0002  # 0.02%
    taker_fee = 0.0005  # 0.05%
    face_value = 0.01   # BTC合约面值
    
    lookback = params["lookback"]
    cooldown_ms = params["cooldown_ms"]
    
    # 止盈止损：杠杆收益率 -> 价格变动率
    # 40% TP (杠杆) = 0.4% 价格变动
    # 25% SL (杠杆) = 0.25% 价格变动
    # 30% 激活 (杠杆) = 0.3% 价格变动
    tp_price_pct = params["tp_pct"] / 100  # 0.4% -> 0.004
    sl_price_pct = params["sl_pct"] / 100  # 0.25% -> 0.0025
    trail_act_pct = params["trail_act"] / 100  # 0.3% -> 0.003
    trail_cb_points = params["trail_cb"]  # 15 点
    
    min_bars = params["slow"] + params["signal"] + lookback + 10
    
    for i in range(min_bars, len(klines)):
        current_price = closes[i]
        current_high = highs[i]
        current_low = lows[i]
        current_time = timestamps[i]
        
        # 1. 持仓检查止盈止损
        if position:
            entry = position["entry"]
            side = position["side"]
            
            # 更新极值
            if side == "long":
                position["highest"] = max(position["highest"], current_high)
            else:
                position["lowest"] = min(position["lowest"], current_low)
            
            # 计算价格变动百分比（不是杠杆收益率）
            if side == "long":
                price_change_pct = (current_price - entry) / entry
            else:
                price_change_pct = (entry - current_price) / entry
            
            # 止损：价格变动 -0.25%
            if price_change_pct <= -sl_price_pct:
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
            
            # 止盈：价格变动 +0.4%
            if price_change_pct >= tp_price_pct:
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
            
            # 移动止盈：激活后回调 N 点
            if params["trail_act"] > 0 and price_change_pct >= trail_act_pct:
                if side == "long":
                    # 从最高点回调
                    drawdown_points = position["highest"] - current_price
                    if drawdown_points >= trail_cb_points:
                        pnl = (current_price - entry) * params["size"] * face_value
                        close_fee = current_price * params["size"] * face_value * taker_fee
                        fees_total += close_fee
                        capital += pnl - close_fee
                        trades.append({"type": "close", "side": side, "price": current_price, "pnl": pnl - close_fee, "reason": "trail"})
                        last_trade_time = current_time
                        position = None
                        continue
                else:
                    # 从最低点反弹
                    bounce_points = current_price - position["lowest"]
                    if bounce_points >= trail_cb_points:
                        pnl = (entry - current_price) * params["size"] * face_value
                        close_fee = current_price * params["size"] * face_value * taker_fee
                        fees_total += close_fee
                        capital += pnl - close_fee
                        trades.append({"type": "close", "side": side, "price": current_price, "pnl": pnl - close_fee, "reason": "trail"})
                        last_trade_time = current_time
                        position = None
                        continue
        
        # 2. 背离信号检测（无持仓且冷却期外）
        if position is None:
            # 检查冷却
            if current_time - last_trade_time < cooldown_ms:
                continue
            
            # 回看窗口（不含当前K线）
            lookback_prices = closes[i-lookback:i]
            lookback_dif = dif[i-lookback:i]
            
            if len(lookback_prices) < lookback:
                continue
            
            # 区间极值
            price_high = max(lookback_prices)
            price_low = min(lookback_prices)
            dif_high = max(lookback_dif)
            dif_low = min(lookback_dif)
            
            current_dif = dif[i]
            
            signal = None
            
            # 顶背离：当前价格接近区间最高价，但DIF未接近最高DIF
            if current_price >= price_high * params["price_near_high"]:
                if current_dif < dif_high * params["macd_div_high"]:
                    signal = "short"
            
            # 底背离：当前价格接近区间最低价，但DIF未接近最低DIF
            if current_price <= price_low * params["price_near_low"]:
                if current_dif > dif_low * params["macd_div_low"]:
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
    # 按照用户确认的参数规则
    params = {
        "fast": 12,
        "slow": 26,
        "signal": 9,
        "lookback": 50,
        "price_near_high": 0.99,
        "price_near_low": 1.01,
        "macd_div_high": 0.9,
        "macd_div_low": 1.1,
        "sl_pct": 25,           # 25% 杠杆收益率 = 0.25% 价格变动
        "tp_pct": 40,           # 40% 杠杆收益率 = 0.4% 价格变动
        "trail_act": 30,        # 30% 杠杆收益率 = 0.3% 价格变动
        "trail_cb": 15,         # 15 点
        "cooldown_ms": 30 * 60 * 1000,  # 30分钟
        "initial_capital": 1000,
        "leverage": 100,
        "size": 1,
    }
    
    print("=" * 90)
    print("  MACD 背离策略回测 v4 - 按照用户确认的参数规则")
    print("=" * 90)
    print(f"\n配置:")
    print(f"  本金: 1000 USDT, 杠杆: 100X, 开仓: 1 张")
    print(f"  止损: 25% (价格变动 0.25%)")
    print(f"  止盈: 40% (价格变动 0.4%)")
    print(f"  移动止盈: 激活 30% (价格变动 0.3%), 回调 15 点")
    print(f"  冷却: 30 分钟")
    print(f"  lookback: 50, div_threshold: 0.9/1.1")
    
    # 获取K线
    klines_data = {}
    for tf in ["15m", "30m"]:
        print(f"\n获取 {tf} K线...")
        klines = fetch_klines(tf, 1440)
        if klines:
            days = (klines[-1]["timestamp"] - klines[0]["timestamp"]) / 1000 / 86400
            print(f"  {len(klines)} 根K线, {days:.1f} 天")
            klines_data[tf] = klines
    
    if not klines_data:
        print("ERROR: 无法获取K线")
        return
    
    # 回测
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
