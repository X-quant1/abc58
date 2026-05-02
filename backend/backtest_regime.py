"""市场状态过滤对比回测

对15个策略分别跑有/无市场状态过滤的124天回测，
对比过滤前后的胜率/收益率/交易数，验证过滤器是否有效。

Usage:
  cd c:\LH\OKX\backend
  python backtest_regime.py
  python backtest_regime.py 1h 10
"""

import sys
import json
import time
import os
import subprocess
from datetime import datetime

sys.path.insert(0, ".")

SYMBOL = "BTC-USDT-SWAP"
INITIAL_CAPITAL = 10000
LEVERAGE = 100
FEE_RATE = 0.0005
SLIPPAGE = 0.0005

# 策略指标参数（与 backtest_long.py 一致）
SCALP_PARAMS = {
    "ma_cross": {"fast_period": 3, "slow_period": 7},
    "rsi": {"period": 6, "oversold": 35, "overbought": 65},
    "bollinger": {"period": 10, "std_dev": 1.5},
    "macd": {"fast_period": 6, "slow_period": 13, "signal_period": 5},
    "ema_volume": {"fast_period": 5, "slow_period": 13, "volume_ma_period": 10, "volume_ratio": 1.0},
    "supertrend": {"atr_period": 5, "multiplier": 2.0},
    "kdj": {"k_period": 5, "k_smooth": 3, "d_smooth": 3, "oversold": 30, "overbought": 70},
    "dual_ema": {"trend_period": 21, "fast_period": 3, "slow_period": 8},
    "ma_ribbon": {"period1": 3, "period2": 7, "period3": 13, "period4": 21},
    "cci": {"period": 10, "oversold": -80, "overbought": 80},
    "trend_break": {"ema_period": 21, "boll_period": 10, "boll_std": 1.5, "vol_ma_period": 10, "vol_ratio": 1.0},
    "rsi_macd": {"rsi_period": 6, "oversold": 35, "overbought": 65, "macd_fast": 6, "macd_slow": 13, "macd_signal": 5},
    "st_kdj": {"atr_period": 5, "multiplier": 2.0, "k_period": 5, "k_smooth": 3, "d_smooth": 3, "oversold": 30, "overbought": 70},
    "ribbon_macd": {"period1": 3, "period2": 7, "period3": 13, "period4": 21, "macd_fast": 6, "macd_slow": 13, "macd_signal": 5},
    "vol_break": {"lookback": 20, "vol_ma_period": 10, "vol_ratio": 1.5},
}

BEST_COMBO = {
    "ma_cross":   (3.0, 1.0, 2.0, 0.5),
    "rsi":        (3.0, 1.0, 2.0, 0.5),
    "bollinger":  (2.0, 0.8, 0, 0),
    "macd":       (1.5, 0.5, 0, 0),
    "ema_volume": (3.0, 1.0, 2.0, 0.5),
    "supertrend": (3.0, 1.0, 2.0, 0.5),
    "kdj":        (3.0, 1.0, 2.0, 0.5),
    "dual_ema":   (2.0, 0.8, 0, 0),
    "ma_ribbon":  (2.0, 0.8, 0, 0),
    "cci":        (3.0, 1.0, 2.0, 0.5),
    "trend_break": (2.0, 0.8, 0, 0),
    "rsi_macd":   (3.0, 1.0, 2.0, 0.5),
    "st_kdj":     (2.0, 0.8, 0, 0),
    "ribbon_macd":(1.5, 0.5, 1.0, 0.2),
    "vol_break":  (2.0, 0.8, 1.2, 0.3),
}

# ─── OKX CLI 分页拉取 K 线 ───

OKX_CLI = r"C:\LH\OKX\tools\node-v20.18.0-win-x64\okx.cmd"
_node_dir = r"C:\LH\OKX\tools\node-v20.18.0-win-x64"
if _node_dir not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _node_dir + ";" + os.environ.get("PATH", "")

TIMEFRAME_MAP = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1H", "4h": "4H", "1d": "1D",
}


def _run_okx(args, timeout=30):
    cmd = [OKX_CLI] + args + ["--json"]
    env = os.environ.copy()
    env["OKX_SITE"] = "global"
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace", env=env)
    if result.returncode != 0:
        raise RuntimeError(f"okx CLI error: {result.stderr[:200]}")
    output = result.stdout.strip()
    if not output:
        return []
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return []


def fetch_klines_paginated(symbol="BTC-USDT-SWAP", timeframe="1h", pages=5):
    """分页拉取 K 线数据"""
    bar = TIMEFRAME_MAP.get(timeframe, "1H")
    all_candles = []
    after_ts = None

    for page in range(pages):
        args = ["market", "candles", symbol, "--bar", bar, "--limit", "300"]
        if after_ts:
            args += ["--after", str(after_ts)]

        print(f"  Fetching page {page+1}/{pages}{' (after=' + str(after_ts) + ')' if after_ts else ''}...")
        data = _run_okx(args)

        if not data or not isinstance(data, list):
            print(f"  Page {page+1}: no data returned, stopping")
            break

        page_candles = []
        for candle in data:
            if isinstance(candle, list) and len(candle) >= 9:
                ts_ms = int(candle[0])
                page_candles.append({
                    "timestamp": ts_ms,
                    "time": datetime.fromtimestamp(ts_ms / 1000).strftime("%Y-%m-%d %H:%M"),
                    "open": float(candle[1]),
                    "high": float(candle[2]),
                    "low": float(candle[3]),
                    "close": float(candle[4]),
                    "volume": float(candle[5]),
                    "quote_volume": float(candle[7]),
                })
            elif isinstance(candle, dict):
                ts_ms = int(candle.get("ts", 0))
                page_candles.append({
                    "timestamp": ts_ms,
                    "time": datetime.fromtimestamp(ts_ms / 1000).strftime("%Y-%m-%d %H:%M"),
                    "open": float(candle.get("o", 0)),
                    "high": float(candle.get("h", 0)),
                    "low": float(candle.get("l", 0)),
                    "close": float(candle.get("c", 0)),
                    "volume": float(candle.get("vol", 0)),
                    "quote_volume": float(candle.get("volCcy", 0)),
                })

        if not page_candles:
            break

        print(f"  Got {len(page_candles)} candles: {page_candles[-1]['time']} ~ {page_candles[0]['time']}")
        all_candles.extend(page_candles)
        after_ts = page_candles[-1]["timestamp"]

        if len(page_candles) < 300:
            print(f"  Less than 300 candles returned, reached data limit")
            break

        time.sleep(0.5)

    all_candles.sort(key=lambda x: x["timestamp"])
    seen = set()
    unique = []
    for c in all_candles:
        if c["timestamp"] not in seen:
            seen.add(c["timestamp"])
            unique.append(c)

    return unique


# ─── 主程序 ───

timeframe = sys.argv[1] if len(sys.argv) > 1 else "1h"
pages = int(sys.argv[2]) if len(sys.argv) > 2 else 10

print(f"=== Market Regime Filter Comparison ===")
print(f"Symbol: {SYMBOL}, Timeframe: {timeframe}, Pages: {pages}")
print(f"Fetching klines from OKX...\n")

klines = fetch_klines_paginated(symbol=SYMBOL, timeframe=timeframe, pages=pages)

if not klines or len(klines) < 50:
    print("ERROR: Failed to fetch enough klines data")
    sys.exit(1)

t0 = datetime.fromtimestamp(klines[0]["timestamp"] / 1000)
t1 = datetime.fromtimestamp(klines[-1]["timestamp"] / 1000)
days = (t1 - t0).days
print(f"\nTotal: {len(klines)} candles: {t0.strftime('%Y-%m-%d %H:%M')} ~ {t1.strftime('%Y-%m-%d %H:%M')} ({days} days)")

# 导入策略和回测引擎
from app.services.strategy import STRATEGY_REGISTRY
from app.services.backtest import backtest_engine

# 运行对比回测
results_no_filter = {}  # 无过滤
results_with_filter = {}  # 有过滤

for stype, scls in sorted(STRATEGY_REGISTRY.items()):
    tp, sl, ta, tc = BEST_COMBO.get(stype, (1.0, 0.5, 0, 0))
    params = dict(scls.default_params)
    params.update(SCALP_PARAMS.get(stype, {}))
    params["timeframe"] = timeframe
    params["size_mode"] = "fixed"
    params["size"] = 1
    params["take_profit_pct"] = tp
    params["stop_loss_pct"] = sl
    params["trailing_activation_pct"] = ta
    params["trailing_stop_pct"] = tc
    params["inst_id"] = SYMBOL

    try:
        # 无过滤
        r_no = backtest_engine.run(
            strategy_type=stype, params=dict(params), symbol=SYMBOL,
            timeframe=timeframe, klines=klines, initial_capital=INITIAL_CAPITAL,
            leverage=LEVERAGE, fee_rate=FEE_RATE, slippage=SLIPPAGE,
            regime_filter=False,
        )
        # 有过滤
        r_yes = backtest_engine.run(
            strategy_type=stype, params=dict(params), symbol=SYMBOL,
            timeframe=timeframe, klines=klines, initial_capital=INITIAL_CAPITAL,
            leverage=LEVERAGE, fee_rate=FEE_RATE, slippage=SLIPPAGE,
            regime_filter=True,
        )

        if r_no.get("ok") and r_yes.get("ok"):
            results_no_filter[stype] = {"name": scls.strategy_name, "result": r_no, "combo": (tp, sl, ta, tc)}
            results_with_filter[stype] = {"name": scls.strategy_name, "result": r_yes, "combo": (tp, sl, ta, tc)}

            rn = r_no
            ry = r_yes
            regime = ry.get("regime_stats", {})
            print(f"  {scls.strategy_name:<16} "
                  f"NoFilter: {rn['total_return']:>6.1f}%/{rn['win_rate']:>5.1f}%wr/{rn['trade_count']:>3}trades | "
                  f"Filtered: {ry['total_return']:>6.1f}%/{ry['win_rate']:>5.1f}%wr/{ry['trade_count']:>3}trades | "
                  f"Regime: ST={regime.get('strong_trend',0)} T={regime.get('trending',0)} WT={regime.get('weak_trend',0)} "
                  f"R={regime.get('ranging',0)} V={regime.get('volatile',0)} "
                  f"Filtered={regime.get('filtered',0)}")
    except Exception as e:
        print(f"  {scls.strategy_name} ERROR: {e}")

# ─── 生成 HTML 对比报告 ───

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>Market Regime Filter Comparison ({days}d)</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family: -apple-system, 'Segoe UI', sans-serif; background:#0d1117; color:#e6edf3; padding:30px; }}
  h1 {{ text-align:center; color:#f7931a; font-size:24px; margin-bottom:8px; }}
  .subtitle {{ text-align:center; color:#8b949e; font-size:14px; margin-bottom:6px; }}
  .config {{ text-align:center; color:#58a6ff; font-size:13px; margin-bottom:20px; }}
  .note {{ background:#161b22; border:1px solid #30363d; border-radius:8px; padding:12px 18px; margin:0 auto 24px; max-width:900px; color:#8b949e; font-size:13px; line-height:1.6; }}
  h2 {{ text-align:center; color:#f7931a; margin:25px 0 16px; }}
  table {{ border-collapse:collapse; margin:0 auto 30px; font-size:13px; }}
  table th, table td {{ padding:8px 10px; border:1px solid #30363d; text-align:center; }}
  table th {{ background:#161b22; color:#f7931a; font-weight:600; font-size:11px; }}
  table tr:nth-child(even) {{ background:#161b22; }}
  .positive {{ color:#3fb950; font-weight:bold; }}
  .negative {{ color:#f85149; font-weight:bold; }}
  .improved {{ color:#58a6ff; font-weight:bold; }}
  .worse {{ color:#f85149; font-weight:bold; }}
  .badge {{ display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600; }}
  .badge-up {{ background:#3fb95033; color:#3fb950; }}
  .badge-down {{ background:#f8514933; color:#f85149; }}
  .badge-same {{ background:#8b949e33; color:#8b949e; }}
  .section {{ background:#161b22; border:1px solid #30363d; border-radius:10px; margin:20px auto; max-width:1400px; padding:20px; }}
</style>
</head>
<body>

<h1>Market Regime Filter Comparison</h1>
<p class="subtitle">BTC-USDT-SWAP | {timeframe} | {t0.strftime('%Y-%m-%d')} ~ {t1.strftime('%Y-%m-%d')} ({days} days) | Leverage: {LEVERAGE}x</p>
<p class="config">Market Regime Detector: ADX + Volatility Ratio + MA Deviation + ATR Change Rate | Filter: ranging = no new positions</p>

<div class="note">
  <strong>How it works:</strong> Before opening a new position, the system checks if the market is in a trending, ranging, or volatile state.
  If the market is <strong>ranging</strong> (oscillating sideways), the opening signal is suppressed.
  This should reduce false breakouts and improve win rate at the cost of fewer trades.
</div>

<h2>Comparison Table</h2>
<table>
<thead>
<tr>
  <th rowspan="2">#</th>
  <th rowspan="2">Strategy</th>
  <th rowspan="2">TP/SL</th>
  <th colspan="3">No Filter</th>
  <th colspan="3">With Filter</th>
  <th colspan="3">Delta</th>
  <th rowspan="2">Regime Stats</th>
</tr>
<tr>
  <th>Return</th><th>WinRate</th><th>Trades</th>
  <th>Return</th><th>WinRate</th><th>Trades</th>
  <th>Return</th><th>WinRate</th><th>Trades</th>
</tr>
</thead>
<tbody>
"""

# 按无过滤收益率排序
sorted_types = sorted(results_no_filter.keys(),
                      key=lambda x: results_no_filter[x]["result"]["total_return"],
                      reverse=True)

for i, stype in enumerate(sorted_types, 1):
    rn = results_no_filter[stype]["result"]
    ry = results_with_filter[stype]["result"]
    name = results_no_filter[stype]["name"]
    tp, sl, ta, tc = results_no_filter[stype]["combo"]
    trail_str = f"T:{ta}%>{tc}%" if ta > 0 else "NoTrail"
    combo_str = f"TP{tp}/SL{sl}/{trail_str}"

    # Delta
    d_ret = ry["total_return"] - rn["total_return"]
    d_wr = ry["win_rate"] - rn["win_rate"]
    d_trades = ry["trade_count"] - rn["trade_count"]

    ret_cls_no = "positive" if rn["total_return"] >= 0 else "negative"
    ret_cls_yes = "positive" if ry["total_return"] >= 0 else "negative"
    d_ret_cls = "improved" if d_ret > 0.1 else ("worse" if d_ret < -0.1 else "")
    d_wr_cls = "improved" if d_wr > 0.5 else ("worse" if d_wr < -0.5 else "")

    # Regime stats
    regime = ry.get("regime_stats", {})
    regime_str = f"ST:{regime.get('strong_trend',0)} T:{regime.get('trending',0)} WT:{regime.get('weak_trend',0)} R:{regime.get('ranging',0)} V:{regime.get('volatile',0)} F:{regime.get('filtered',0)}"

    html += f"""<tr>
  <td>{i}</td>
  <td>{name}</td>
  <td style="font-size:11px;">{combo_str}</td>
  <td class="{ret_cls_no}">{rn['total_return']:.1f}%</td>
  <td>{rn['win_rate']:.1f}%</td>
  <td>{rn['trade_count']}</td>
  <td class="{ret_cls_yes}">{ry['total_return']:.1f}%</td>
  <td>{ry['win_rate']:.1f}%</td>
  <td>{ry['trade_count']}</td>
  <td class="{d_ret_cls}">{'+' if d_ret > 0 else ''}{d_ret:.1f}%</td>
  <td class="{d_wr_cls}">{'+' if d_wr > 0 else ''}{d_wr:.1f}%</td>
  <td>{d_trades:+d}</td>
  <td style="font-size:10px;">{regime_str}</td>
</tr>
"""

html += "</tbody></table>\n"

# ─── 详细市场状态分布 ───

html += '<h2 style="text-align:center; color:#f7931a; margin:25px 0 16px;">Market Regime Distribution</h2>\n'
html += '<div class="section"><table style="font-size:12px;">\n'
html += '<thead><tr><th>Strategy</th><th>Strong Trend</th><th>Trending</th><th>Weak Trend</th><th>Ranging</th><th>Volatile</th><th>Filtered Out</th><th>Filter Rate</th></tr></thead>\n<tbody>\n'

for stype in sorted_types:
    ry = results_with_filter[stype]["result"]
    name = results_no_filter[stype]["name"]
    regime = ry.get("regime_stats", {})
    st_count = regime.get("strong_trend", 0)
    t_count = regime.get("trending", 0)
    wt_count = regime.get("weak_trend", 0)
    r_count = regime.get("ranging", 0)
    v_count = regime.get("volatile", 0)
    f_count = regime.get("filtered", 0)
    total_signal_checks = st_count + t_count + wt_count + r_count + v_count
    filter_rate = f"{100 * f_count / max(total_signal_checks, 1):.1f}%" if total_signal_checks > 0 else "N/A"

    html += f"""<tr>
  <td>{name}</td>
  <td style="color:#3fb950;">{st_count}</td>
  <td style="color:#58a6ff;">{t_count}</td>
  <td style="color:#d29922;">{wt_count}</td>
  <td style="color:#f85149;">{r_count}</td>
  <td style="color:#a371f7;">{v_count}</td>
  <td>{f_count}</td>
  <td>{filter_rate}</td>
</tr>
"""

html += "</tbody></table></div>\n"

# ─── 结论 ───

improved = sum(1 for stype in sorted_types
               if results_with_filter[stype]["result"]["total_return"] >
               results_no_filter[stype]["result"]["total_return"] + 0.1)
worsened = sum(1 for stype in sorted_types
               if results_with_filter[stype]["result"]["total_return"] <
               results_no_filter[stype]["result"]["total_return"] - 0.1)
same = len(sorted_types) - improved - worsened

wr_improved = sum(1 for stype in sorted_types
                  if results_with_filter[stype]["result"]["win_rate"] >
                  results_no_filter[stype]["result"]["win_rate"] + 0.5)

html += f"""
<div class="note" style="max-width:700px;">
  <strong>Summary:</strong><br>
  Total strategies: {len(sorted_types)}<br>
  Return improved by filter: <span class="positive">{improved}</span> |
  Return worsened: <span class="negative">{worsened}</span> |
  No significant change: {same}<br>
  Win rate improved: <span class="positive">{wr_improved}</span> / {len(sorted_types)}<br><br>
  <strong>Key insight:</strong> If the filter improves win rate without destroying too many trades,
  it's worth enabling in live trading. The goal is quality over quantity.
</div>
"""

html += "</body></html>"

# 保存
filename = f"backtest_regime_{timeframe}_{pages}p.html"
with open(filename, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\nReport saved to: {filename}")
