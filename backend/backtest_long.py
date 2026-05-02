"""Long-range backtest with paginated kline fetching.

Fetches multiple pages of 1h klines from OKX (300 per page),
concatenates them into a single dataset, then runs all 15 strategies.

Usage:
  cd c:\LH\OKX\backend
  python backtest_long.py [timeframe] [pages]
  python backtest_long.py 1h 5        # 5 pages x 300 = 1500 candles (~62 days)
  python backtest_long.py 1h 10       # 10 pages x 300 = 3000 candles (~125 days)
"""
import sys
import json
import time
from datetime import datetime

# 延迟导入，避免循环引用
sys.path.insert(0, ".")

SYMBOL = "BTC-USDT-SWAP"
INITIAL_CAPITAL = 10000
LEVERAGE = 100
FEE_RATE = 0.0005
SLIPPAGE = 0.0005

# 策略指标参数
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
    # 组合策略
    "trend_break": {"ema_period": 21, "boll_period": 10, "boll_std": 1.5, "vol_ma_period": 10, "vol_ratio": 1.0},
    "rsi_macd": {"rsi_period": 6, "oversold": 35, "overbought": 65, "macd_fast": 6, "macd_slow": 13, "macd_signal": 5},
    "st_kdj": {"atr_period": 5, "multiplier": 2.0, "k_period": 5, "k_smooth": 3, "d_smooth": 3, "oversold": 30, "overbought": 70},
    "ribbon_macd": {"period1": 3, "period2": 7, "period3": 13, "period4": 21, "macd_fast": 6, "macd_slow": 13, "macd_signal": 5},
    "vol_break": {"lookback": 20, "vol_ma_period": 10, "vol_ratio": 1.5},
}

# 最优止盈止损组合（124天参数扫描结果）
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
    # 组合策略
    "trend_break": (2.0, 0.8, 0, 0),
    "rsi_macd":   (3.0, 1.0, 2.0, 0.5),
    "st_kdj":     (2.0, 0.8, 0, 0),
    "ribbon_macd":(1.5, 0.5, 1.0, 0.2),
    "vol_break":  (2.0, 0.8, 1.2, 0.3),
}

# ─── OKX CLI 分页拉取 K 线 ───

import os
import subprocess

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
    """分页拉取 K 线数据，拼接为时间正序"""
    bar = TIMEFRAME_MAP.get(timeframe, "1H")
    all_candles = []
    after_ts = None  # 分页游标

    for page in range(pages):
        args = ["market", "candles", symbol, "--bar", bar, "--limit", "300"]
        if after_ts:
            args += ["--after", str(after_ts)]
        
        print(f"  Fetching page {page+1}/{pages}{' (after=' + str(after_ts) + ')' if after_ts else ''}...")
        data = _run_okx(args)
        
        if not data or not isinstance(data, list):
            print(f"  Page {page+1}: no data returned, stopping")
            break
        
        # 解析 OKX 数组格式: [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
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
        
        # 设置游标为这页最旧K线的时间戳
        after_ts = page_candles[-1]["timestamp"]
        
        # 如果返回不足300根，说明没更多数据了
        if len(page_candles) < 300:
            print(f"  Less than 300 candles returned, reached data limit")
            break
        
        # 避免请求太频繁
        time.sleep(0.5)
    
    # OKX 返回最新在前，需要按时间正序排列
    all_candles.sort(key=lambda x: x["timestamp"])
    
    # 去重（按时间戳）
    seen = set()
    unique = []
    for c in all_candles:
        if c["timestamp"] not in seen:
            seen.add(c["timestamp"])
            unique.append(c)
    
    return unique


# ─── 主程序 ───

timeframe = sys.argv[1] if len(sys.argv) > 1 else "1h"
pages = int(sys.argv[2]) if len(sys.argv) > 2 else 5

print(f"=== Long-range Backtest ===")
print(f"Symbol: {SYMBOL}, Timeframe: {timeframe}, Pages: {pages} (max {pages*300} candles)")
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

all_results = {}
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
        result = backtest_engine.run(
            strategy_type=stype, params=params, symbol=SYMBOL,
            timeframe=timeframe, klines=klines, initial_capital=INITIAL_CAPITAL,
            leverage=LEVERAGE, fee_rate=FEE_RATE, slippage=SLIPPAGE,
        )
        if result.get("ok"):
            all_results[stype] = {"name": scls.strategy_name, "result": result, "combo": (tp, sl, ta, tc)}
            r = result
            sig_day = r["trade_count"] / max(days, 1)
            trail_str = f"Trail:{ta}%>{tc}%" if ta > 0 else "NoTrail"
            print(f"  {scls.strategy_name:<16} TP={tp}%/SL={sl}%/{trail_str:<20} "
                  f"Return={r['total_return']:>6.1f}%  Sig/Day={sig_day:>4.1f}  "
                  f"WinRate={r['win_rate']:>5.1f}%  Sharpe={r['sharpe_ratio']:>5.2f}  "
                  f"Trades={r['trade_count']:>3}  PF={r['profit_factor']:>5.2f}")
    except Exception as e:
        print(f"  {scls.strategy_name} ERROR: {e}")


# ─── 生成 HTML 报告 ───

# 读取 backtest_final.py 的 HTML 模板逻辑，这里直接生成简化版
html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>BTC 长周期回测报告 ({days}天)</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family: -apple-system, 'Segoe UI', sans-serif; background:#0d1117; color:#e6edf3; padding:30px; }}
  h1 {{ text-align:center; color:#f7931a; font-size:24px; margin-bottom:8px; }}
  .subtitle {{ text-align:center; color:#8b949e; font-size:14px; margin-bottom:6px; }}
  .config {{ text-align:center; color:#58a6ff; font-size:13px; margin-bottom:20px; }}
  .note {{ background:#161b22; border:1px solid #30363d; border-radius:8px; padding:12px 18px; margin:0 auto 24px; max-width:900px; color:#8b949e; font-size:13px; line-height:1.6; }}
  h2 {{ text-align:center; color:#f7931a; margin:25px 0 16px; }}
  .summary-table {{ border-collapse:collapse; margin:0 auto 30px; font-size:13px; }}
  .summary-table th, .summary-table td {{ padding:8px 12px; border:1px solid #30363d; text-align:center; }}
  .summary-table th {{ background:#161b22; color:#f7931a; font-weight:600; }}
  .summary-table tr:nth-child(even) {{ background:#161b22; }}
  .positive {{ color:#3fb950; font-weight:bold; }}
  .negative {{ color:#f85149; font-weight:bold; }}
  .badge {{ display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600; }}
  .badge-tp {{ background:#1f6feb33; color:#58a6ff; }}
  .badge-sl {{ background:#da363333; color:#f85149; }}
  .badge-signal {{ background:#3fb95033; color:#3fb950; }}
  .badge-trailing {{ background:#a371f733; color:#a371f7; }}
  .badge-end {{ background:#8b949e33; color:#8b949e; }}
  .badge-long {{ background:#3fb95033; color:#3fb950; }}
  .badge-short {{ background:#f8514933; color:#f85149; }}
  .open-long {{ color:#3fb950; }}
  .close-long {{ color:#3fb950; opacity:0.7; }}
  .open-short {{ color:#f85149; }}
  .close-short {{ color:#f85149; opacity:0.7; }}
  .strategy-section {{ background:#161b22; border:1px solid #30363d; border-radius:10px; margin:20px auto; max-width:1200px; padding:20px; }}
  .strategy-section h3 {{ color:#f7931a; margin-bottom:10px; }}
  .stats {{ color:#8b949e; font-size:13px; margin-bottom:12px; }}
  .trade-table {{ border-collapse:collapse; width:100%; font-size:12px; }}
  .trade-table th, .trade-table td {{ padding:5px 8px; border:1px solid #21262d; text-align:center; }}
  .trade-table th {{ background:#0d1117; color:#8b949e; font-size:11px; }}
  .chart-container {{ max-width:1200px; margin:30px auto; background:#161b22; border-radius:10px; padding:20px; }}
</style>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3"></script>
</head>
<body>

<h1>BTC 长周期回测报告</h1>
<p class="subtitle">BTC-USDT-SWAP | {timeframe} | {t0.strftime('%Y-%m-%d')} ~ {t1.strftime('%Y-%m-%d')} ({days} 天) | 杠杆: {LEVERAGE}x</p>
<p class="config">数据量: {len(klines)} 根K线 | 每策略使用参数扫描最优止盈止损组合</p>

<div class="note">
  <strong>说明：</strong> 通过 OKX API 分页拉取 {pages} 页 x 300 根 = {len(klines)} 根 1h K线，覆盖 {days} 天。<br>
  每个策略使用参数扫描（10种组合）得出的最优止盈止损配置。信号周期已缩短以产生更多信号。
</div>

<h2>策略对比（每策略最优止盈止损）</h2>
<table class="summary-table">
<thead>
<tr>
  <th>#</th><th>策略</th><th>止盈止损配置</th><th>收益率</th><th>最大回撤</th><th>夏普</th><th>胜率</th><th>盈亏比</th><th>交易数</th><th>信号/天</th><th>手续费</th><th>最终权益</th>
</tr>
</thead>
<tbody>
"""

# 按收益率排序
sorted_results = sorted(all_results.items(), key=lambda x: x[1]["result"]["total_return"], reverse=True)

for i, (stype, data) in enumerate(sorted_results, 1):
    r = data["result"]
    tp, sl, ta, tc = data["combo"]
    trail_str = f"T:{ta}%>{tc}%" if ta > 0 else "无移动"
    combo_str = f"止盈{tp}/止损{sl}/{trail_str}"
    ret_cls = "positive" if r["total_return"] >= 0 else "negative"
    sig_day = r["trade_count"] / max(days, 1)
    
    html += f"""<tr>
  <td>{i}</td>
  <td>{data['name']}</td>
  <td style="font-size:11px;">{combo_str}</td>
  <td class="{ret_cls}">{r['total_return']:.1f}%</td>
  <td class="{'negative' if r['max_drawdown'] < -5 else ''}">{r['max_drawdown']:.1f}%</td>
  <td>{r['sharpe_ratio']:.2f}</td>
  <td>{r['win_rate']:.1f}%</td>
  <td>{r['profit_factor']:.2f}</td>
  <td>{r['trade_count']}</td>
  <td>{sig_day:.1f}</td>
  <td>{r.get('total_fees', 0):.2f}</td>
  <td>{r.get('final_capital', INITIAL_CAPITAL):.2f}</td>
</tr>
"""

html += "</tbody></table>\n"

# ─── 逐笔交易明细 ───
html += '<h2 style="text-align:center; color:#f7931a; margin-bottom:16px;">逐笔交易明细</h2>\n'

for i, (stype, data) in enumerate(sorted_results, 1):
    r = data["result"]
    tp, sl, ta, tc = data["combo"]
    trail_str = f"移动止盈: {ta}%激活, {tc}%回调" if ta > 0 else "无移动止盈"
    ret_cls = "positive" if r["total_return"] >= 0 else "negative"
    sig_day = r["trade_count"] / max(days, 1)
    
    html += f"""<div class="strategy-section">
  <h3>#{i} {data['name']}</h3>
  <div class="stats">
    止盈={tp}% | 止损={sl}% | {trail_str} | 收益: <strong class="{ret_cls}">{r['total_return']:.1f}%</strong> |
    信号/天: {sig_day:.1f} | 胜率: {r['win_rate']:.1f}% | 交易数: {r['trade_count']}
  </div>
"""
    
    trades = r.get("trades", [])
    if not trades:
        html += '<div style="padding:20px;text-align:center;color:#8b949e;">未产生交易</div>'
    else:
        html += """<table class="trade-table">
<thead>
<tr><th>#</th><th>时间</th><th>操作</th><th>方向</th><th>价格</th><th>张数</th><th>保证金</th><th>盈亏</th><th>盈亏%</th><th>手续费</th><th>原因</th></tr>
</thead>
<tbody>
"""
        for j, t in enumerate(trades, 1):
            side = t.get("side", "")
            is_open = "open" in side
            if "long" in side:
                dir_badge = '<span class="badge badge-long">多</span>'
                action_cls = "open-long" if is_open else "close-long"
            else:
                dir_badge = '<span class="badge badge-short">空</span>'
                action_cls = "open-short" if is_open else "close-short"
            action = "开仓" if is_open else "平仓"
            
            reason = t.get("reason", "signal")
            reason_map = {"take_profit": "止盈", "stop_loss": "止损", "signal": "信号", "trailing_stop": "移动止盈", "backtest_end": "回测结束"}
            badge_map = {"take_profit": "badge-tp", "stop_loss": "badge-sl", "signal": "badge-signal", "trailing_stop": "badge-trailing", "backtest_end": "badge-end"}
            reason_text = reason_map.get(reason, reason)
            reason_badge = badge_map.get(reason, "badge-signal")
            
            pnl = t.get("pnl", 0)
            pnl_cls = "positive" if pnl >= 0 else "negative"
            pnl_pct = t.get("pnl_pct", 0)
            
            # 时间戳转可读格式
            raw_time = t.get('time', '')
            if isinstance(raw_time, (int, float)) and raw_time > 1000000000000:
                display_time = datetime.fromtimestamp(raw_time / 1000).strftime("%Y-%m-%d %H:%M")
            elif isinstance(raw_time, (int, float)) and raw_time > 1000000000:
                display_time = datetime.fromtimestamp(raw_time).strftime("%Y-%m-%d %H:%M")
            else:
                display_time = str(raw_time)
            html += f"""<tr>
  <td>{j}</td>
  <td style="font-size:11px;">{display_time}</td>
  <td class="{action_cls}">{action}</td>
  <td>{dir_badge}</td>
  <td>{t.get('price',0):.2f}</td>
  <td>{t.get('sz',0)}</td>
  <td>{t.get('margin',0):.2f}</td>
  <td class="{pnl_cls}">{pnl:.2f}</td>
  <td class="{pnl_cls}">{pnl_pct:.2f}%</td>
  <td>{t.get('fee',0):.4f}</td>
  <td><span class="badge {reason_badge}">{reason_text}</span></td>
</tr>
"""
        html += "</tbody></table>\n"
    
    html += "</div>\n"

# ─── 权益曲线 ───
html += '<h2 style="text-align:center; color:#f7931a; margin:25px 0 16px;">权益曲线</h2>\n'
html += '<div class="chart-container"><canvas id="equityChart" height="400"></canvas></div>\n'

# 构建权益曲线数据
equity_datasets = []
colors = ["#f7931a","#3fb950","#58a6ff","#f85149","#a371f7","#d29922","#79c0ff","#7ee787",
          "#ff7b72","#d2a8ff","#ffa657","#56d4dd","#f778ba","#adc6ff","#bfdcff"]
for idx, (stype, data) in enumerate(sorted_results):
    r = data["result"]
    equity_curve = r.get("equity_curve", [])
    if equity_curve:
        points = [{"x": p["time"] if isinstance(p["time"], str) else datetime.fromtimestamp(p["time"]/1000).strftime("%Y-%m-%d %H:%M"), "y": round(p["equity"], 2)} for p in equity_curve]
        equity_datasets.append({
            "label": data["name"],
            "data": points,
            "borderColor": colors[idx % len(colors)],
            "borderWidth": 2,
            "pointRadius": 0,
            "fill": False,
            "tension": 0.3,
        })

html += f"""
<script>
const ctx = document.getElementById('equityChart').getContext('2d');
new Chart(ctx, {{
  type: 'line',
  data: {{ datasets: {json.dumps(equity_datasets)} }},
  options: {{
    responsive: true,
    interaction: {{ mode: 'index', intersect: false }},
    plugins: {{
      legend: {{ labels: {{ color: '#8b949e', font: {{ size: 11 }} }} }},
      tooltip: {{ backgroundColor: '#161b22', titleColor: '#f7931a', bodyColor: '#e6edf3', borderColor: '#30363d', borderWidth: 1 }}
    }},
    scales: {{
      x: {{ type: 'time', time: {{ tooltipFormat: 'MM-dd HH:mm' }}, title: {{ display: true, text: '日期', color: '#8b949e' }}, ticks: {{ color: '#8b949e' }}, grid: {{ color: '#21262d' }} }},
      y: {{ title: {{ display: true, text: '权益 (USDT)', color: '#8b949e' }}, ticks: {{ color: '#8b949e' }}, grid: {{ color: '#21262d' }} }}
    }}
  }}
}});
</script>
"""

html += "</body></html>"

# 保存
output_file = f"backtest_long_{timeframe}_{pages}p.html"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(html)
print(f"\nReport saved to: {output_file}")
