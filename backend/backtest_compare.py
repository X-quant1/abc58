"""Multi-timeframe comparison report.

Runs all strategies on multiple timeframes, generates a single HTML comparison report.

Usage:
  cd c:\LH\OKX\backend
  python backtest_compare.py
"""
import json
from datetime import datetime
from app.services.strategy import STRATEGY_REGISTRY
from app.services.backtest import backtest_engine
from app.services.market import market_service

SYMBOL = "BTC-USDT-SWAP"
INITIAL_CAPITAL = 10000
LEVERAGE = 100
FEE_RATE = 0.0005
SLIPPAGE = 0.0005

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
}

BEST_COMBO = {
    "ma_cross":   (0.5, 0.3, 0.3, 0.06),
    "rsi":        (1.5, 0.5, 0, 0),
    "bollinger":  (3.0, 1.0, 2.0, 0.5),
    "macd":       (1.0, 0.5, 0, 0),
    "ema_volume": (0.8, 0.4, 0.5, 0.1),
    "supertrend": (3.0, 1.0, 2.0, 0.5),
    "kdj":        (3.0, 1.0, 2.0, 0.5),
    "dual_ema":   (3.0, 1.0, 2.0, 0.5),
    "ma_ribbon":  (3.0, 1.0, 2.0, 0.5),
    "cci":        (1.0, 0.5, 0, 0),
}

TIMEFRAMES = ["15m", "30m", "1h", "2h", "4h"]
LIMIT = 300

# Collect data
all_data = {}  # {tf: {stype: {name, result, combo, days}}}

for tf in TIMEFRAMES:
    print(f"\n=== {tf} ===")
    klines = market_service.get_klines(symbol="BTC-USDT", timeframe=tf, limit=LIMIT)
    if not klines or len(klines) < 50:
        print(f"  ERROR: {tf} klines failed")
        continue

    t0 = datetime.fromtimestamp(klines[0]["timestamp"] / 1000)
    t1 = datetime.fromtimestamp(klines[-1]["timestamp"] / 1000)
    days = (t1 - t0).days
    print(f"  {len(klines)} candles: {t0.strftime('%m-%d')}~{t1.strftime('%m-%d')} ({days} days)")

    all_data[tf] = {}
    for stype, scls in sorted(STRATEGY_REGISTRY.items()):
        tp, sl, ta, tc = BEST_COMBO.get(stype, (1.0, 0.5, 0, 0))
        params = dict(scls.default_params)
        params.update(SCALP_PARAMS.get(stype, {}))
        params["timeframe"] = tf
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
                timeframe=tf, klines=klines, initial_capital=INITIAL_CAPITAL,
                leverage=LEVERAGE, fee_rate=FEE_RATE, slippage=SLIPPAGE,
            )
            if result.get("ok"):
                all_data[tf][stype] = {
                    "name": scls.strategy_name, "result": result,
                    "combo": (tp, sl, ta, tc), "days": days
                }
                r = result
                sig_day = r["trade_count"] / max(days, 1)
                print(f"  {scls.strategy_name:<16} Return={r['total_return']:>6.1f}%  "
                      f"Sig/Day={sig_day:>4.1f}  WinRate={r['win_rate']:>5.1f}%  "
                      f"Sharpe={r['sharpe_ratio']:>5.2f}  Trades={r['trade_count']:>3}")
        except Exception as e:
            print(f"  {scls.strategy_name} ERROR: {e}")

# ── Generate HTML ──

strategy_types = sorted(STRATEGY_REGISTRY.keys())
strategy_names = {stype: STRATEGY_REGISTRY[stype].strategy_name for stype in strategy_types}

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>BTC 多周期回测对比报告</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, 'Segoe UI', Roboto, 'Microsoft YaHei', sans-serif; background: #0d1117; color: #c9d1d9; padding: 20px; }}
  h1 {{ text-align: center; color: #f7931a; margin-bottom: 5px; font-size: 26px; }}
  .subtitle {{ text-align: center; color: #8b949e; margin-bottom: 8px; font-size: 13px; }}
  .config {{ text-align: center; color: #58a6ff; margin-bottom: 25px; font-size: 12px; font-family: monospace; }}
  .section {{ background: #161b22; border-radius: 12px; padding: 20px; margin-bottom: 25px; border: 1px solid #30363d; }}
  .section h2 {{ color: #f7931a; margin-bottom: 12px; font-size: 16px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
  th {{ background: #21262d; color: #f7931a; padding: 8px 5px; text-align: center; font-weight: 600; border-bottom: 1px solid #30363d; position: sticky; top: 0; z-index: 1; }}
  td {{ padding: 6px 5px; text-align: center; border-bottom: 1px solid #21262d; }}
  tr:hover {{ background: #1c2128; }}
  .positive {{ color: #ef5350; font-weight: 600; }}
  .negative {{ color: #26a69a; font-weight: 600; }}
  .best {{ background: #2d2000 !important; }}
  .tf-header {{ background: #21262d; color: #58a6ff; font-weight: 700; font-size: 13px; }}
  .note {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px 16px; margin-bottom: 20px; font-size: 12px; color: #8b949e; }}
  .note strong {{ color: #f7931a; }}
  .chart-container {{ background: #161b22; border-radius: 12px; padding: 16px; margin-bottom: 25px; border: 1px solid #30363d; }}
  canvas {{ max-height: 400px; }}
</style>
</head>
<body>
<h1>BTC 多周期回测对比报告</h1>
<p class="subtitle">BTC-USDT-SWAP | {LIMIT}根K线/周期 | 杠杆: {LEVERAGE}x | 每策略最优止盈止损</p>
<p class="config">对比 15m / 30m / 1h / 2h / 4h 五个时间框架的表现</p>

<div class="note">
  <strong>说明：</strong> 同一套短线参数（MA 3/7, RSI 6, MACD 6/13/5等），每个策略使用参数扫描得出的最优止盈止损组合。<br>
  高亮行 = 该策略在所有周期中收益率最高的周期。
</div>
"""

# ── Table 1: Cross-timeframe comparison (one section per metric) ──

# Metric comparison table
metrics = [
    ("total_return", "收益率 (%)", ".1f", True),
    ("sharpe_ratio", "夏普比率", ".2f", True),
    ("win_rate", "胜率 (%)", ".1f", True),
    ("trade_count", "交易数", "d", False),
    ("profit_factor", "盈亏比", ".2f", True),
    ("max_drawdown", "最大回撤 (%)", ".1f", False),
    ("total_fees", "手续费 ($)", ".2f", False),
]

for metric_key, metric_name, fmt, higher_is_better in metrics:
    html += f"""
<div class="section">
<h2>{metric_name} 对比</h2>
<div style="overflow-x:auto;">
<table>
<thead>
<tr>
  <th style="text-align:left;min-width:100px;">策略</th>
"""
    for tf in TIMEFRAMES:
        days_str = ""
        if tf in all_data:
            sample = list(all_data[tf].values())[0] if all_data[tf] else None
            if sample:
                days_str = f" ({sample['days']}天)"
        html += f'  <th>{tf}{days_str}</th>\n'
    html += "</tr>\n</thead>\n<tbody>\n"

    for stype in strategy_types:
        sname = strategy_names[stype]
        html += f'  <tr><td style="text-align:left;font-weight:600;">{sname}</td>\n'

        # Find best timeframe for this strategy
        best_tf = None
        best_val = None
        for tf in TIMEFRAMES:
            if tf in all_data and stype in all_data[tf]:
                r = all_data[tf][stype]["result"]
                val = r.get(metric_key, 0)
                if best_val is None or (higher_is_better and val > best_val) or (not higher_is_better and val < best_val):
                    best_val = val
                    best_tf = tf

        for tf in TIMEFRAMES:
            if tf in all_data and stype in all_data[tf]:
                r = all_data[tf][stype]["result"]
                val = r.get(metric_key, 0)
                is_best = (tf == best_tf)
                cls = "best" if is_best else ""
                val_cls = ""
                if metric_key == "total_return":
                    val_cls = "positive" if val > 0 else "negative"
                if fmt == "d":
                    html += f'    <td class="{cls} {val_cls}">{int(val)}</td>\n'
                else:
                    html += f'    <td class="{cls} {val_cls}">{val:{fmt}}</td>\n'
            else:
                html += '    <td style="color:#484f58;">-</td>\n'
        html += "  </tr>\n"

    html += "</tbody>\n</table>\n</div>\n</div>\n"

# ── Table 2: Signals per day comparison ──
html += """
<div class="section">
<h2>信号频率（信号数/天）对比</h2>
<div style="overflow-x:auto;">
<table>
<thead>
<tr>
  <th style="text-align:left;min-width:100px;">策略</th>
"""
for tf in TIMEFRAMES:
    html += f"  <th>{tf}</th>\n"
html += "</tr>\n</thead>\n<tbody>\n"

for stype in strategy_types:
    sname = strategy_names[stype]
    html += f'  <tr><td style="text-align:left;font-weight:600;">{sname}</td>\n'
    for tf in TIMEFRAMES:
        if tf in all_data and stype in all_data[tf]:
            r = all_data[tf][stype]["result"]
            days = all_data[tf][stype]["days"]
            sig_day = r["trade_count"] / max(days, 1)
            color = "#4caf50" if sig_day >= 3 else "#ff9800" if sig_day >= 1 else "#8b949e"
            html += f'    <td style="color:{color};font-weight:600;">{sig_day:.1f}</td>\n'
        else:
            html += '    <td style="color:#484f58;">-</td>\n'
    html += "  </tr>\n"
html += "</tbody>\n</table>\n</div>\n</div>\n"

# ── Chart: Bar chart comparing returns across timeframes ──
html += """
<div class="chart-container">
<h2 style="color:#f7931a;margin-bottom:12px;font-size:16px;">各策略不同周期收益率对比</h2>
<canvas id="returnChart" height="350"></canvas>
</div>

<div class="chart-container">
<h2 style="color:#f7931a;margin-bottom:12px;font-size:16px;">各策略不同周期夏普比率对比</h2>
<canvas id="sharpeChart" height="350"></canvas>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<script>
"""

# Build chart data
colors_tf = {'15m': '#e91e63', '30m': '#ff9800', '1h': '#f7931a', '2h': '#4caf50', '4h': '#58a6ff'}

# Return chart
html += "const returnDatasets = [\n"
for tf in TIMEFRAMES:
    vals = []
    for stype in strategy_types:
        if tf in all_data and stype in all_data[tf]:
            vals.append(all_data[tf][stype]["result"]["total_return"])
        else:
            vals.append(0)
    html += f"""  {{
    label: '{tf}',
    data: {json.dumps(vals)},
    backgroundColor: '{colors_tf[tf]}',
    borderColor: '{colors_tf[tf]}',
    borderWidth: 1,
  }},
"""
html += "];\n"

labels = [strategy_names[s] for s in strategy_types]
html += f"const labels = {json.dumps(labels)};\n"

html += """
new Chart(document.getElementById('returnChart'), {
  type: 'bar',
  data: { labels: labels, datasets: returnDatasets },
  options: {
    responsive: true,
    plugins: {
      legend: { position: 'top', labels: { color: '#c9d1d9' } },
      tooltip: { callbacks: { label: (ctx) => ctx.dataset.label + ': ' + ctx.parsed.y.toFixed(1) + '%' } }
    },
    scales: {
      x: { ticks: { color: '#8b949e', font: { size: 10 } }, grid: { color: '#21262d' } },
      y: { title: { display: true, text: '收益率 (%)', color: '#8b949e' }, ticks: { color: '#8b949e' }, grid: { color: '#21262d' } }
    }
  }
});
"""

# Sharpe chart
html += "const sharpeDatasets = [\n"
for tf in TIMEFRAMES:
    vals = []
    for stype in strategy_types:
        if tf in all_data and stype in all_data[tf]:
            vals.append(all_data[tf][stype]["result"]["sharpe_ratio"])
        else:
            vals.append(0)
    html += f"""  {{
    label: '{tf}',
    data: {json.dumps(vals)},
    backgroundColor: '{colors_tf[tf]}',
    borderColor: '{colors_tf[tf]}',
    borderWidth: 1,
  }},
"""
html += "];\n"

html += """
new Chart(document.getElementById('sharpeChart'), {
  type: 'bar',
  data: { labels: labels, datasets: sharpeDatasets },
  options: {
    responsive: true,
    plugins: {
      legend: { position: 'top', labels: { color: '#c9d1d9' } },
      tooltip: { callbacks: { label: (ctx) => ctx.dataset.label + ': ' + ctx.parsed.y.toFixed(2) } }
    },
    scales: {
      x: { ticks: { color: '#8b949e', font: { size: 10 } }, grid: { color: '#21262d' } },
      y: { title: { display: true, text: '夏普比率', color: '#8b949e' }, ticks: { color: '#8b949e' }, grid: { color: '#21262d' } }
    }
  }
});
</script>
</body>
</html>
"""

output_path = "backtest_compare_report.html"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\nMulti-timeframe comparison report saved to: {output_path}")
