"""Backtest Detail Report - Generate detailed trade-by-trade report for all strategies.

Usage:
  cd c:\LH\OKX\backend
  python backtest_report.py [timeframe] [limit]
  python backtest_report.py 4h 300
"""
import sys
import json
from datetime import datetime
from app.services.strategy import STRATEGY_REGISTRY
from app.services.backtest import backtest_engine
from app.services.market import market_service

SYMBOL = "BTC-USDT-SWAP"
INITIAL_CAPITAL = 10000
LEVERAGE = 10
FEE_RATE = 0.0005
SLIPPAGE = 0.0005

timeframe = sys.argv[1] if len(sys.argv) > 1 else "4h"
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

# Collect all results
all_results = {}

for stype, scls in STRATEGY_REGISTRY.items():
    params = {**scls.default_params}
    params["timeframe"] = timeframe
    params["size_mode"] = "fixed"
    params["size"] = 1
    params["take_profit_pct"] = 0
    params["stop_loss_pct"] = 5
    params["trailing_stop_pct"] = 0
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
            }
    except Exception as e:
        print(f"  {scls.strategy_name} ERROR: {e}")

# Build HTML report
html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>BTC Quant Backtest Report</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, 'Segoe UI', Roboto, sans-serif; background: #f0f2f5; color: #333; padding: 20px; }}
  h1 {{ text-align: center; color: #f7931a; margin-bottom: 5px; font-size: 28px; }}
  .subtitle {{ text-align: center; color: #666; margin-bottom: 30px; font-size: 14px; }}
  .summary {{ background: #fff; border-radius: 12px; padding: 20px; margin-bottom: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
  .summary h2 {{ color: #333; margin-bottom: 15px; font-size: 18px; }}
  .summary-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  .summary-table th {{ background: #f7931a; color: #fff; padding: 10px 8px; text-align: center; font-weight: 600; }}
  .summary-table td {{ padding: 8px; text-align: center; border-bottom: 1px solid #eee; }}
  .summary-table tr:hover {{ background: #fff8f0; }}
  .positive {{ color: #ef5350; font-weight: 600; }}
  .negative {{ color: #26a69a; font-weight: 600; }}
  .strategy-card {{ background: #fff; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); overflow: hidden; }}
  .strategy-header {{ background: linear-gradient(135deg, #f7931a, #ff9f43); color: #fff; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; }}
  .strategy-header h3 {{ font-size: 18px; }}
  .strategy-header .stats {{ font-size: 13px; opacity: 0.95; }}
  .strategy-body {{ padding: 0; }}
  .trade-table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
  .trade-table th {{ background: #fafafa; padding: 10px 8px; text-align: left; font-weight: 600; color: #555; border-bottom: 2px solid #eee; position: sticky; top: 0; }}
  .trade-table td {{ padding: 8px; border-bottom: 1px solid #f5f5f5; }}
  .trade-table tr:hover {{ background: #fff8f0; }}
  .trade-table .open-long {{ color: #ef5350; font-weight: 600; }}
  .trade-table .open-short {{ color: #26a69a; font-weight: 600; }}
  .trade-table .close-long {{ color: #26a69a; }}
  .trade-table .close-short {{ color: #ef5350; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }}
  .badge-long {{ background: #fde8e8; color: #ef5350; }}
  .badge-short {{ background: #e0f5f0; color: #26a69a; }}
  .badge-tp {{ background: #e8f5e9; color: #4caf50; }}
  .badge-sl {{ background: #fce4ec; color: #e91e63; }}
  .badge-signal {{ background: #e3f2fd; color: #1976d2; }}
  .badge-trailing {{ background: #fff3e0; color: #ff9800; }}
  .badge-end {{ background: #f3e5f5; color: #9c27b0; }}
  .pair-row {{ background: #fafafa; }}
  .no-trades {{ padding: 30px; text-align: center; color: #999; }}
  .top3 {{ background: #fff8e1 !important; }}
</style>
</head>
<body>
<h1>BTC Quant Backtest Report</h1>
<p class="subtitle">BTC-USDT-SWAP | {timeframe} | {t0.strftime('%Y-%m-%d')} ~ {t1.strftime('%Y-%m-%d')} ({days} days) | Capital: ${INITIAL_CAPITAL} | Leverage: {LEVERAGE}x | Fee: {FEE_RATE*100}% | Slippage: {SLIPPAGE*100}%</p>

<div class="summary">
<h2>Strategy Comparison</h2>
<table class="summary-table">
<thead>
<tr>
  <th>#</th><th>Strategy</th><th>Return</th><th>MaxDD</th><th>Sharpe</th><th>WinRate</th><th>P/F</th><th>Trades</th><th>Wins</th><th>Losses</th><th>Fees</th><th>Final</th>
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
  <td>{r['win_count']}</td>
  <td>{r['lose_count']}</td>
  <td>${r['total_fees']:.2f}</td>
  <td>${r['final_capital']:.2f}</td>
</tr>
"""

html += """</tbody></table></div>
<h2 style="text-align:center; color:#333; margin-bottom:20px;">Trade-by-Trade Details</h2>
"""

# Detailed trade tables for each strategy
for i, (stype, data) in enumerate(sorted_strategies, 1):
    r = data["result"]
    trades = r.get("trades", [])
    ret_cls = "positive" if r["total_return"] > 0 else "negative"

    html += f"""
<div class="strategy-card">
<div class="strategy-header">
  <h3>#{i} {data['name']}</h3>
  <div class="stats">
    Return: <strong class="{ret_cls}">{r['total_return']:.1f}%</strong> |
    Sharpe: {r['sharpe_ratio']:.2f} |
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
<tr><th>#</th><th>Time</th><th>Action</th><th>Direction</th><th>Price</th><th>Size</th><th>Margin</th><th>PnL</th><th>Fee</th><th>Reason</th></tr>
</thead>
<tbody>
"""
        # Pair open/close trades for visual grouping
        trade_num = 0
        pair_open = False
        for j, t in enumerate(trades):
            side = t.get("side", "")
            is_open = side.startswith("open_")
            is_close = side.startswith("close_")

            if is_open:
                trade_num += 1
                pair_open = True

            # Format time
            ts = t.get("time", "")
            if isinstance(ts, (int, float)) and ts > 1000000000000:
                dt = datetime.fromtimestamp(ts / 1000)
                time_str = dt.strftime('%Y-%m-%d %H:%M')
            elif isinstance(ts, (int, float)) and ts > 1000000000:
                dt = datetime.fromtimestamp(ts)
                time_str = dt.strftime('%Y-%m-%d %H:%M')
            else:
                time_str = str(ts)

            # Direction
            if "long" in side:
                direction = "Long"
                dir_badge = '<span class="badge badge-long">Long</span>'
                action_cls = "open-long" if is_open else "close-long"
            else:
                direction = "Short"
                dir_badge = '<span class="badge badge-short">Short</span>'
                action_cls = "open-short" if is_open else "close-short"

            action = "Open" if is_open else "Close"

            # Reason badge
            reason = t.get("reason", "")
            if reason == "take_profit":
                reason_badge = '<span class="badge badge-tp">TP</span>'
            elif reason == "stop_loss":
                reason_badge = '<span class="badge badge-sl">SL</span>'
            elif reason == "signal":
                reason_badge = '<span class="badge badge-signal">Signal</span>'
            elif reason == "trailing_stop":
                reason_badge = '<span class="badge badge-trailing">Trailing</span>'
            elif reason == "backtest_end":
                reason_badge = '<span class="badge badge-end">End</span>'
            else:
                reason_badge = reason

            # PnL
            pnl = t.get("pnl", "")
            pnl_str = f"${pnl:.2f}" if isinstance(pnl, (int, float)) else ""
            pnl_cls = "positive" if isinstance(pnl, (int, float)) and pnl > 0 else ("negative" if isinstance(pnl, (int, float)) and pnl < 0 else "")

            margin = t.get("margin", "")
            margin_str = f"${margin:.2f}" if isinstance(margin, (int, float)) else ""

            fee = t.get("fee", 0)
            fee_str = f"${fee:.2f}" if isinstance(fee, (int, float)) else ""

            row_cls = ' class="pair-row"' if is_close and pair_open else ""
            pair_open = False if is_close else pair_open

            html += f"""<tr{row_cls}>
  <td>{trade_num}</td>
  <td>{time_str}</td>
  <td class="{action_cls}">{action}</td>
  <td>{dir_badge}</td>
  <td>${t.get('price', ''):.2f}</td>
  <td>{t.get('sz', '')}</td>
  <td>{margin_str}</td>
  <td class="{pnl_cls}">{pnl_str}</td>
  <td>{fee_str}</td>
  <td>{reason_badge}</td>
</tr>
"""

        html += "</tbody></table>"

    html += "</div></div>"

# Add equity curve section with inline charts
html += """
<h2 style="text-align:center; color:#333; margin:30px 0 20px;">Equity Curves</h2>
<div class="strategy-card" style="padding:20px;">
<canvas id="equityChart" height="400"></canvas>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<script>
"""

# Prepare equity curve data for Chart.js
html += "const equityData = {\n  datasets: [\n"
colors = ['#f7931a', '#ef5350', '#26a69a', '#1976d2', '#9c27b0', '#ff9800', '#4caf50', '#e91e63', '#00bcd4', '#795548']
for i, (stype, data) in enumerate(sorted_strategies):
    r = data["result"]
    curve = r.get("equity_curve", [])
    points = []
    for pt in curve:
        ts = pt.get("time", 0)
        if isinstance(ts, (int, float)) and ts > 1000000000000:
            dt = new_date = f"new Date({int(ts)})"
        else:
            dt = f"new Date({int(ts) * 1000})" if isinstance(ts, (int, float)) else "new Date()"
        points.append(f"{{x: {dt}, y: {pt.get('equity', 0)}}}")

    color = colors[i % len(colors)]
    html += f"""  {{
    label: '{data['name']}',
    data: [{','.join(points[:500])}],
    borderColor: '{color}',
    backgroundColor: '{color}22',
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
      x: { type: 'time', time: { tooltipFormat: 'yyyy-MM-dd HH:mm' }, title: { display: true, text: 'Date' } },
      y: { title: { display: true, text: 'Equity (USDT)' } }
    },
    plugins: {
      legend: { position: 'top' },
      tooltip: { callbacks: { label: (ctx) => ctx.dataset.label + ': $' + ctx.parsed.y.toFixed(2) } }
    }
  }
});
</script>
"""

html += """
</body>
</html>
"""

# Write to file
output_path = "backtest_report.html"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\nReport saved to: {output_path}")
print(f"Strategies: {len(all_results)}")
