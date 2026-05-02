"""High-frequency scalping backtest - short timeframe + tight TP/SL + trailing.

Target: 3-4 signals per day per strategy
Config: 100x leverage, 0.3% SL, 0.5% TP, 0.3% trailing activation, 0.06% trailing callback

Usage:
  cd c:\LH\OKX\backend
  python backtest_hf.py [timeframe] [limit]
  python backtest_hf.py 15m 300
  python backtest_hf.py 1h 300
"""
import sys
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

# Tight TP/SL for scalping (based on user's example):
# 70000 做多 → 69800 SL (-0.286%) / 70380 TP (+0.543%)
# 70200 activate trailing, 40 point callback = 0.057%
TAKE_PROFIT_PCT = 0.5       # 止盈 0.5%
STOP_LOSS_PCT = 0.3          # 止损 0.3%
TRAILING_ACTIVATION_PCT = 0.3  # 盈利0.3%激活移动止盈
TRAILING_CALLBACK_PCT = 0.06   # 激活后回调0.06%止盈

# Strategy-specific scalping params (short periods for more signals)
SCALP_PARAMS = {
    "ma_cross": {
        "fast_period": 3,
        "slow_period": 7,
    },
    "rsi": {
        "period": 6,
        "oversold": 35,
        "overbought": 65,
    },
    "bollinger": {
        "period": 10,
        "std_dev": 1.5,
    },
    "macd": {
        "fast_period": 6,
        "slow_period": 13,
        "signal_period": 5,
    },
    "ema_volume": {
        "fast_period": 5,
        "slow_period": 13,
        "volume_ma_period": 10,
        "volume_ratio": 1.0,  # 降低量能门槛
    },
    "supertrend": {
        "atr_period": 5,
        "multiplier": 2.0,   # 降低倍数，更敏感
    },
    "kdj": {
        "k_period": 5,
        "k_smooth": 3,
        "d_smooth": 3,
        "oversold": 30,
        "overbought": 70,
    },
    "dual_ema": {
        "trend_period": 21,    # 缩短趋势周期
        "fast_period": 3,
        "slow_period": 8,
    },
    "ma_ribbon": {
        "period1": 3,
        "period2": 7,
        "period3": 13,
        "period4": 21,
    },
    "cci": {
        "period": 10,
        "oversold": -80,      # 放宽区间
        "overbought": 80,
    },
}

timeframe = sys.argv[1] if len(sys.argv) > 1 else "15m"
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 300

print(f"Fetching BTC-USDT {timeframe} klines (limit={limit}) from OKX...")
klines = market_service.get_klines(symbol="BTC-USDT", timeframe=timeframe, limit=limit)

if not klines or len(klines) < 50:
    print("ERROR: Failed to fetch klines data")
    sys.exit(1)

t0 = datetime.fromtimestamp(klines[0]["timestamp"] / 1000)
t1 = datetime.fromtimestamp(klines[-1]["timestamp"] / 1000)
days = (t1 - t0).days
print(f"Got {len(klines)} candles: {t0.strftime('%Y-%m-%d %H:%M')} ~ {t1.strftime('%Y-%m-%d %H:%M')} ({days} days)")

# Run all strategies
all_results = {}
for stype, scls in sorted(STRATEGY_REGISTRY.items()):
    # Merge: default params < scalping overrides < common params
    params = dict(scls.default_params)
    params.update(SCALP_PARAMS.get(stype, {}))
    params["timeframe"] = timeframe
    params["size_mode"] = "fixed"
    params["size"] = 1
    params["take_profit_pct"] = TAKE_PROFIT_PCT
    params["stop_loss_pct"] = STOP_LOSS_PCT
    params["trailing_activation_pct"] = TRAILING_ACTIVATION_PCT
    params["trailing_stop_pct"] = TRAILING_CALLBACK_PCT
    params["inst_id"] = SYMBOL

    try:
        result = backtest_engine.run(
            strategy_type=stype,
            params=params,
            symbol=SYMBOL,
            timeframe=timeframe,
            klines=klines,
            initial_capital=INITIAL_CAPITAL,
            leverage=LEVERAGE,
            fee_rate=FEE_RATE,
            slippage=SLIPPAGE,
        )
        if result.get("ok"):
            all_results[stype] = {
                "name": scls.strategy_name,
                "result": result,
                "params": params,
            }
            r = result
            signals_per_day = r["trade_count"] / max(days, 1)
            print(f"  {scls.strategy_name:<16} Return={r['total_return']:>6.1f}%  Trades={r['trade_count']:>3}  "
                  f"Sig/Day={signals_per_day:>4.1f}  WinRate={r['win_rate']:>5.1f}%  "
                  f"Sharpe={r['sharpe_ratio']:>5.2f}  MaxDD={r['max_drawdown']:>5.1f}%  "
                  f"PF={r['profit_factor']:>5.2f}  Fees=${r['total_fees']:>8.2f}")
    except Exception as e:
        print(f"  {scls.strategy_name} ERROR: {e}")

# ── Generate HTML Report ──

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>BTC Scalping Backtest Report</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, 'Segoe UI', Roboto, sans-serif; background: #0d1117; color: #c9d1d9; padding: 20px; }}
  h1 {{ text-align: center; color: #f7931a; margin-bottom: 5px; font-size: 26px; }}
  .subtitle {{ text-align: center; color: #8b949e; margin-bottom: 8px; font-size: 13px; }}
  .config {{ text-align: center; color: #58a6ff; margin-bottom: 25px; font-size: 12px; font-family: monospace; }}
  .summary {{ background: #161b22; border-radius: 12px; padding: 20px; margin-bottom: 25px; border: 1px solid #30363d; }}
  .summary h2 {{ color: #f7931a; margin-bottom: 12px; font-size: 16px; }}
  .summary-table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
  .summary-table th {{ background: #21262d; color: #f7931a; padding: 8px 6px; text-align: center; font-weight: 600; border-bottom: 1px solid #30363d; }}
  .summary-table td {{ padding: 6px; text-align: center; border-bottom: 1px solid #21262d; }}
  .summary-table tr:hover {{ background: #1c2128; }}
  .positive {{ color: #ef5350; font-weight: 600; }}
  .negative {{ color: #26a69a; font-weight: 600; }}
  .strategy-card {{ background: #161b22; border-radius: 12px; margin-bottom: 16px; border: 1px solid #30363d; overflow: hidden; }}
  .strategy-header {{ background: linear-gradient(135deg, #f7931a, #ff9f43); color: #fff; padding: 12px 16px; display: flex; justify-content: space-between; align-items: center; }}
  .strategy-header h3 {{ font-size: 15px; }}
  .strategy-header .stats {{ font-size: 12px; opacity: 0.95; }}
  .strategy-body {{ padding: 0; max-height: 600px; overflow-y: auto; }}
  .trade-table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
  .trade-table th {{ background: #21262d; padding: 8px 6px; text-align: left; font-weight: 600; color: #8b949e; border-bottom: 1px solid #30363d; position: sticky; top: 0; z-index: 1; }}
  .trade-table td {{ padding: 6px; border-bottom: 1px solid #21262d; }}
  .trade-table tr:hover {{ background: #1c2128; }}
  .trade-table .open-long {{ color: #ef5350; font-weight: 600; }}
  .trade-table .open-short {{ color: #26a69a; font-weight: 600; }}
  .trade-table .close-long {{ color: #26a69a; }}
  .trade-table .close-short {{ color: #ef5350; }}
  .badge {{ display: inline-block; padding: 1px 6px; border-radius: 8px; font-size: 10px; font-weight: 600; }}
  .badge-long {{ background: #3d1f1f; color: #ef5350; }}
  .badge-short {{ background: #1f3d2d; color: #26a69a; }}
  .badge-tp {{ background: #1f3d1f; color: #4caf50; }}
  .badge-sl {{ background: #3d1f2d; color: #e91e63; }}
  .badge-signal {{ background: #1f2d3d; color: #1976d2; }}
  .badge-trailing {{ background: #3d2d1f; color: #ff9800; }}
  .badge-end {{ background: #2d1f3d; color: #9c27b0; }}
  .pair-row {{ background: #1c2128; }}
  .no-trades {{ padding: 20px; text-align: center; color: #8b949e; }}
  .top3 {{ background: #2d2000 !important; }}
  .warn {{ background: #2d1f00; border: 1px solid #f7931a44; border-radius: 8px; padding: 10px 16px; margin-bottom: 20px; color: #f7931a; font-size: 12px; }}
</style>
</head>
<body>
<h1>BTC Scalping Backtest Report</h1>
<p class="subtitle">BTC-USDT-SWAP | {timeframe} | {t0.strftime('%Y-%m-%d')} ~ {t1.strftime('%Y-%m-%d')} ({days} days)</p>
<p class="config">Leverage: {LEVERAGE}x | TP: {TAKE_PROFIT_PCT}% | SL: {STOP_LOSS_PCT}% | Trailing Activate: +{TRAILING_ACTIVATION_PCT}% | Trailing Callback: {TRAILING_CALLBACK_PCT}% | Fee: {FEE_RATE*100}% | Slippage: {SLIPPAGE*100}%</p>

<div class="warn">
  Target: 3-4 signals/day | TP/SL: {TAKE_PROFIT_PCT}%/{STOP_LOSS_PCT}% | Trailing: {TRAILING_ACTIVATION_PCT}% activate, {TRAILING_CALLBACK_PCT}% callback | Leverage: {LEVERAGE}x
</div>

<div class="summary">
<h2>Strategy Comparison</h2>
<table class="summary-table">
<thead>
<tr>
  <th>#</th><th>Strategy</th><th>Return</th><th>MaxDD</th><th>Sharpe</th><th>WinRate</th><th>P/F</th><th>Trades</th><th>Sig/Day</th><th>Wins</th><th>Losses</th><th>Fees</th><th>Final</th>
</tr>
</thead>
<tbody>
"""

# Sort by composite score
sorted_strategies = sorted(all_results.items(), key=lambda x: (
    max(x[1]["result"]["total_return"], -50) * 0.3 +
    x[1]["result"]["sharpe_ratio"] * 10 * 0.3 +
    x[1]["result"]["win_rate"] * 0.2 +
    min(x[1]["result"]["profit_factor"], 5) * 20 * 0.2
), reverse=True)

for i, (stype, data) in enumerate(sorted_strategies, 1):
    r = data["result"]
    ret_cls = "positive" if r["total_return"] > 0 else "negative"
    sig_day = r["trade_count"] / max(days, 1)
    top3_cls = ' class="top3"' if i <= 3 else ""
    html += f"""<tr{top3_cls}>
  <td>{i}</td>
  <td><strong>{data['name']}</strong></td>
  <td class="{ret_cls}">{r['total_return']:.1f}%</td>
  <td>{r['max_drawdown']:.1f}%</td>
  <td>{r['sharpe_ratio']:.2f}</td>
  <td>{r['win_rate']:.1f}%</td>
  <td>{r['profit_factor']:.2f}</td>
  <td>{r['trade_count']}</td>
  <td>{sig_day:.1f}</td>
  <td>{r['win_count']}</td>
  <td>{r['lose_count']}</td>
  <td>${r['total_fees']:.2f}</td>
  <td>${r['final_capital']:.2f}</td>
</tr>
"""

html += """</tbody></table></div>
<h2 style="text-align:center; color:#f7931a; margin-bottom:16px;">Trade-by-Trade Details</h2>
"""

# Detailed trade tables for each strategy
for i, (stype, data) in enumerate(sorted_strategies, 1):
    r = data["result"]
    trades = r.get("trades", [])
    ret_cls = "positive" if r["total_return"] > 0 else "negative"
    sig_day = r["trade_count"] / max(days, 1)

    html += f"""
<div class="strategy-card">
<div class="strategy-header">
  <h3>#{i} {data['name']}</h3>
  <div class="stats">
    Return: <strong class="{ret_cls}">{r['total_return']:.1f}%</strong> |
    Signals/Day: {sig_day:.1f} |
    WinRate: {r['win_rate']:.1f}% |
    Trades: {r['trade_count']}
  </div>
</div>
<div class="strategy-body">
"""

    if not trades:
        html += '<div class="no-trades">No trades generated</div>'
    else:
        html += """<table class="trade-table">
<thead>
<tr><th>#</th><th>Time</th><th>Action</th><th>Dir</th><th>Price</th><th>Sz</th><th>Margin</th><th>PnL</th><th>PnL%</th><th>Fee</th><th>Reason</th></tr>
</thead>
<tbody>
"""
        trade_num = 0
        for t in trades:
            side = t.get("side", "")
            is_open = side.startswith("open_")

            if is_open:
                trade_num += 1

            # Format time
            ts = t.get("time", "")
            if isinstance(ts, (int, float)) and ts > 1000000000000:
                time_str = datetime.fromtimestamp(ts / 1000).strftime('%m-%d %H:%M')
            elif isinstance(ts, (int, float)) and ts > 1000000000:
                time_str = datetime.fromtimestamp(ts).strftime('%m-%d %H:%M')
            else:
                time_str = str(ts)

            # Direction
            if "long" in side:
                dir_badge = '<span class="badge badge-long">L</span>'
                action_cls = "open-long" if is_open else "close-long"
            else:
                dir_badge = '<span class="badge badge-short">S</span>'
                action_cls = "open-short" if is_open else "close-short"

            action = "OPEN" if is_open else "CLOSE"

            # Reason badge
            reason = t.get("reason", "")
            if reason == "take_profit":
                reason_badge = '<span class="badge badge-tp">TP</span>'
            elif reason == "stop_loss":
                reason_badge = '<span class="badge badge-sl">SL</span>'
            elif reason == "signal":
                reason_badge = '<span class="badge badge-signal">Sig</span>'
            elif reason == "trailing_stop":
                reason_badge = '<span class="badge badge-trailing">Trail</span>'
            elif reason == "backtest_end":
                reason_badge = '<span class="badge badge-end">End</span>'
            else:
                reason_badge = reason

            # PnL
            pnl = t.get("pnl", "")
            pnl_str = f"${pnl:.2f}" if isinstance(pnl, (int, float)) else ""
            pnl_cls = "positive" if isinstance(pnl, (int, float)) and pnl > 0 else ("negative" if isinstance(pnl, (int, float)) and pnl < 0 else "")

            # PnL%
            margin = t.get("margin", "")
            if isinstance(pnl, (int, float)) and isinstance(margin, (int, float)) and margin > 0:
                pnl_pct_str = f"{pnl/margin*100:.1f}%"
            else:
                pnl_pct_str = ""

            margin_str = f"${margin:.2f}" if isinstance(margin, (int, float)) else ""
            fee = t.get("fee", 0)
            fee_str = f"${fee:.2f}" if isinstance(fee, (int, float)) else ""

            row_cls = ' class="pair-row"' if not is_open else ""

            html += f"""<tr{row_cls}>
  <td>{trade_num}</td>
  <td>{time_str}</td>
  <td class="{action_cls}">{action}</td>
  <td>{dir_badge}</td>
  <td>${t.get('price', 0):,.2f}</td>
  <td>{t.get('sz', '')}</td>
  <td>{margin_str}</td>
  <td class="{pnl_cls}">{pnl_str}</td>
  <td class="{pnl_cls}">{pnl_pct_str}</td>
  <td>{fee_str}</td>
  <td>{reason_badge}</td>
</tr>
"""

        html += "</tbody></table>"

    html += "</div></div>"

# Equity curve
html += """
<h2 style="text-align:center; color:#f7931a; margin:25px 0 16px;">Equity Curves</h2>
<div class="strategy-card" style="padding:16px;">
<canvas id="equityChart" height="350"></canvas>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns"></script>
<script>
"""

# Chart data
html += "const equityData = {\n  datasets: [\n"
colors = ['#f7931a', '#ef5350', '#26a69a', '#58a6ff', '#9c27b0', '#ff9800', '#4caf50', '#e91e63', '#00bcd4', '#795548']
for i, (stype, data) in enumerate(sorted_strategies):
    r = data["result"]
    curve = r.get("equity_curve", [])
    points = []
    for pt in curve:
        ts = pt.get("time", 0)
        if isinstance(ts, (int, float)) and ts > 1000000000000:
            dt = f"new Date({int(ts)})"
        else:
            dt = f"new Date({int(ts) * 1000})" if isinstance(ts, (int, float)) else "new Date()"
        points.append(f"{{x: {dt}, y: {pt.get('equity', 0)}}}")

    color = colors[i % len(colors)]
    html += f"""  {{
    label: '{data['name']}',
    data: [{','.join(points[:500])}],
    borderColor: '{color}',
    borderWidth: 1.5,
    pointRadius: 0,
    fill: false,
    tension: 0.1,
  }},
"""

html += """  ]
};

new Chart(document.getElementById('equityChart'), {
  type: 'line',
  data: equityData,
  options: {
    responsive: true,
    interaction: { mode: 'index', intersect: false },
    scales: {
      x: { type: 'time', time: { tooltipFormat: 'MM-dd HH:mm' }, title: { display: true, text: 'Date', color: '#8b949e' }, ticks: { color: '#8b949e' }, grid: { color: '#21262d' } },
      y: { title: { display: true, text: 'Equity (USDT)', color: '#8b949e' }, ticks: { color: '#8b949e' }, grid: { color: '#21262d' } }
    },
    plugins: {
      legend: { position: 'top', labels: { color: '#c9d1d9' } },
      tooltip: { callbacks: { label: (ctx) => ctx.dataset.label + ': $' + ctx.parsed.y.toFixed(2) } }
    }
  }
});
</script>
</body>
</html>
"""

# Save
output_path = "backtest_hf_report.html"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\nReport saved to: {output_path}")
print(f"Strategies: {len(all_results)}")
