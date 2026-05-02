# -*- coding: utf-8 -*-
"""
MACD 背离策略回测 - 按配置文件逻辑重写

背离检测逻辑（按配置文件描述）:
- 顶背离：价格创新高但DIF未创新高 → 做空
- 底背离：价格创新低但DIF未创新低 → 做多

关键改进：
1. 找到局部峰值点（而不是当前K线）
2. 比较两个峰值之间的价格和DIF
3. 满足背离条件才触发信号
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


def calc_ema(data, period):
    """计算EMA"""
    alpha = 2 / (period + 1)
    result = [data[0]]
    for i in range(1, len(data)):
        result.append(alpha * data[i] + (1 - alpha) * result[-1])
    return result


def calc_macd(closes, fast=12, slow=26, signal=9):
    """计算MACD"""
    ema_fast = calc_ema(closes, fast)
    ema_slow = calc_ema(closes, slow)
    dif = [ema_fast[i] - ema_slow[i] for i in range(len(closes))]
    dea = calc_ema(dif, signal)
    macd_hist = [2 * (dif[i] - dea[i]) for i in range(len(closes))]
    return dif, dea, macd_hist


def find_peaks(data, window=5):
    """找到局部峰值点
    
    返回: [(index, value, is_high), ...]
    """
    peaks = []
    for i in range(window, len(data) - window):
        # 局部最高点
        is_high = all(data[i] >= data[i-j] for j in range(-window, window+1) if j != 0)
        if is_high:
            peaks.append((i, data[i], True))
        # 局部最低点
        is_low = all(data[i] <= data[i-j] for j in range(-window, window+1) if j != 0)
        if is_low:
            peaks.append((i, data[i], False))
    return peaks


def detect_divergence(prices, dif, lookback=50, threshold=0.9):
    """检测背离
    
    返回: 'short' (顶背离做空), 'long' (底背离做多), None (无信号)
    """
    if len(prices) < lookback + 10:
        return None
    
    # 找到价格和DIF的峰值点
    price_peaks = find_peaks(prices[-lookback-10:], window=3)
    dif_peaks = find_peaks(dif[-lookback-10:], window=3)
    
    if len(price_peaks) < 2 or len(dif_peaks) < 2:
        return None
    
    # 分离高点和低点
    price_highs = [(i, v) for i, v, is_high in price_peaks if is_high]
    price_lows = [(i, v) for i, v, is_high in price_peaks if not is_high]
    dif_highs = [(i, v) for i, v, is_high in dif_peaks if is_high]
    dif_lows = [(i, v) for i, v, is_high in dif_peaks if not is_high]
    
    # 顶背离检测：价格创新高但DIF未创新高
    if len(price_highs) >= 2 and len(dif_highs) >= 2:
        # 最近两个价格高点
        p1_idx, p1_val = price_highs[-2]
        p2_idx, p2_val = price_highs[-1]
        # 对应位置的DIF值
        d1_val = dif[p1_idx]
        d2_val = dif[p2_idx]
        
        # 价格创新高，DIF未创新高
        if p2_val > p1_val and d2_val < d1_val * threshold:
            return 'short'
    
    # 底背离检测：价格创新低但DIF未创新低
    if len(price_lows) >= 2 and len(dif_lows) >= 2:
        # 最近两个价格低点
        p1_idx, p1_val = price_lows[-2]
        p2_idx, p2_val = price_lows[-1]
        # 对应位置的DIF值
        d1_val = dif[p1_idx]
        d2_val = dif[p2_idx]
        
        # 价格创新低，DIF未创新低
        if p2_val < p1_val and d2_val > d1_val * (2 - threshold):
            return 'long'
    
    return None


def run_backtest(klines, tf, initial_capital=1000, leverage=100, size=1,
                 sl_pct=0.25, tp_pct=0.3, trail_act=0.2, trail_cb=15,
                 lookback=50, div_threshold=0.9):
    """
    回测引擎
    
    Args:
        sl_pct: 止损百分比（价格变动）
        tp_pct: 止盈百分比（价格变动）
        trail_act: 移动止盈激活（价格变动百分比）
        trail_cb: 移动止盈回调点数
    """
    closes = [k["close"] for k in klines]
    dif, dea, macd_hist = calc_macd(closes)
    
    capital = initial_capital
    position = None  # {'side': 'long'/'short', 'entry': price, 'highest': price, 'lowest': price}
    trades = []
    fees_total = 0
    
    # 手续费率
    maker_fee = 0.0002  # 0.02%
    taker_fee = 0.0005  # 0.05%
    
    # 面值
    face_value = 0.01  # BTC-USDT-SWAP
    
    # 最小K线数
    min_bars = lookback + 20
    
    for i in range(min_bars, len(klines)):
        current_price = klines[i]["close"]
        current_high = klines[i]["high"]
        current_low = klines[i]["low"]
        
        # 1. 检查持仓止盈止损
        if position:
            entry = position["entry"]
            side = position["side"]
            
            # 更新最高/最低价
            if side == "long":
                position["highest"] = max(position["highest"], current_high)
            else:
                position["lowest"] = min(position["lowest"], current_low)
            
            # 计算盈亏百分比
            if side == "long":
                pnl_pct = (current_price - entry) / entry * 100
            else:
                pnl_pct = (entry - current_price) / entry * 100
            
            # 止损检查
            if pnl_pct <= -sl_pct:
                # 止损触发
                if side == "long":
                    pnl = (current_price - entry) * size * face_value
                else:
                    pnl = (entry - current_price) * size * face_value
                close_fee = size * face_value * current_price * taker_fee
                fees_total += close_fee
                capital += pnl - close_fee
                trades.append({"type": "close", "side": side, "price": current_price, "pnl": pnl - close_fee, "reason": "sl"})
                position = None
                continue
            
            # 止盈检查
            if pnl_pct >= tp_pct:
                if side == "long":
                    pnl = (current_price - entry) * size * face_value
                else:
                    pnl = (entry - current_price) * size * face_value
                close_fee = size * face_value * current_price * taker_fee
                fees_total += close_fee
                capital += pnl - close_fee
                trades.append({"type": "close", "side": side, "price": current_price, "pnl": pnl - close_fee, "reason": "tp"})
                position = None
                continue
            
            # 移动止盈检查
            if trail_act > 0 and pnl_pct >= trail_act:
                if side == "long":
                    # 从最高价回落
                    drawdown = position["highest"] - current_price
                    if drawdown >= trail_cb:
                        pnl = (current_price - entry) * size * face_value
                        close_fee = size * face_value * current_price * taker_fee
                        fees_total += close_fee
                        capital += pnl - close_fee
                        trades.append({"type": "close", "side": side, "price": current_price, "pnl": pnl - close_fee, "reason": "trail"})
                        position = None
                        continue
                else:
                    # 从最低价反弹
                    bounce = current_price - position["lowest"]
                    if bounce >= trail_cb:
                        pnl = (entry - current_price) * size * face_value
                        close_fee = size * face_value * current_price * taker_fee
                        fees_total += close_fee
                        capital += pnl - close_fee
                        trades.append({"type": "close", "side": side, "price": current_price, "pnl": pnl - close_fee, "reason": "trail"})
                        position = None
                        continue
        
        # 2. 检查背离信号（无持仓时）
        if position is None:
            signal = detect_divergence(closes[:i+1], dif[:i+1], lookback, div_threshold)
            
            if signal == "long":
                # 开多
                open_fee = size * face_value * current_price * maker_fee
                fees_total += open_fee
                capital -= open_fee
                position = {"side": "long", "entry": current_price, "highest": current_high, "lowest": current_low}
                trades.append({"type": "open", "side": "long", "price": current_price, "fee": open_fee})
            
            elif signal == "short":
                # 开空
                open_fee = size * face_value * current_price * maker_fee
                fees_total += open_fee
                capital -= open_fee
                position = {"side": "short", "entry": current_price, "highest": current_high, "lowest": current_low}
                trades.append({"type": "open", "side": "short", "price": current_price, "fee": open_fee})
    
    # 最后平仓
    if position:
        final_price = klines[-1]["close"]
        if position["side"] == "long":
            pnl = (final_price - position["entry"]) * size * face_value
        else:
            pnl = (position["entry"] - final_price) * size * face_value
        close_fee = size * face_value * final_price * taker_fee
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
        "net_pnl": capital - initial_capital,
        "gross_pnl": total_pnl + fees_total,
        "fees": fees_total,
        "trade_count": len(close_trades),
        "win_count": len(win_trades),
        "lose_count": len(lose_trades),
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "trades": trades,
    }


def main():
    print("=" * 90)
    print("  MACD 背离策略回测 - 按配置文件逻辑重写")
    print("=" * 90)
    print(f"\n配置:")
    print(f"  本金: 1000 USDT")
    print(f"  杠杆: 100X")
    print(f"  开仓: 1 张")
    print(f"  止损: 0.25%")
    print(f"  止盈: 0.3%")
    print(f"  移动止盈激活: 0.2%")
    print(f"  移动止盈回调: 15 点")
    print(f"  手续费: 开仓 0.02% + 平仓 0.05%")
    
    # 获取K线
    klines_data = {}
    for tf in ["15m", "30m"]:
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
    
    # 回测
    print("\n" + "=" * 90)
    print("  回测结果")
    print("=" * 90)
    
    print(f"\n{'周期':<8} {'交易数':>8} {'胜率%':>8} {'盈亏比':>8} {'毛收益':>10} {'手续费':>10} {'净收益':>10} {'最终余额':>12}")
    print("-" * 90)
    
    for tf, klines in klines_data.items():
        result = run_backtest(
            klines, tf,
            initial_capital=1000,
            leverage=100,
            size=1,
            sl_pct=0.25,
            tp_pct=0.3,
            trail_act=0.2,
            trail_cb=15,
            lookback=50,
            div_threshold=0.9,
        )
        
        tc = result["trade_count"]
        wr = result["win_rate"]
        pf = result["profit_factor"]
        gross = result["gross_pnl"]
        fees = result["fees"]
        net = result["net_pnl"]
        final = result["final_capital"]
        
        marker = "*" if net > 0 else " "
        print(f"{marker} {tf:<8} {tc:>8} {wr:>8.1f} {pf:>8.2f} {gross:>10.2f}U {fees:>10.2f}U {net:>10.2f}U {final:>12.2f}U")
    
    # 对比
    print("\n" + "=" * 90)
    print("  配置文件中的结果 (对比)")
    print("=" * 90)
    print("""
| 周期 | 交易次数 | 胜率 | 盈利因子 | 毛收益 | 手续费 | 净收益 | 最终余额 |
| 15m  | 233 笔   | 55.4%| 0.98     | +119.30U| -124.80U| -5.50U | 994.50U  |
| 30m  | 227 笔   | 59.9%| 1.33     | +186.70U| -117.32U| +69.38U| 1069.38U |
""")


if __name__ == "__main__":
    main()
