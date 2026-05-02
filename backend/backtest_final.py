"""Final scalping backtest report with optimal TP/SL per strategy.

Uses the best combo from sweep results, generates a detailed HTML report.

Usage:
  cd c:\LH\OKX\backend
  python backtest_final.py [timeframe] [limit]
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
    # 多指标组合策略
    "trend_break": {"ema_period": 21, "boll_period": 10, "boll_std": 1.5, "vol_ma_period": 10, "vol_ratio": 1.0},
    "rsi_macd": {"rsi_period": 6, "oversold": 35, "overbought": 65, "macd_fast": 6, "macd_slow": 13, "macd_signal": 5},
    "st_kdj": {"atr_period": 5, "multiplier": 2.0, "k_period": 5, "k_smooth": 3, "d_smooth": 3, "oversold": 30, "overbought": 70},
    "ribbon_macd": {"period1": 3, "period2": 7, "period3": 13, "period4": 21, "macd_fast": 6, "macd_slow": 13, "macd_signal": 5},
    "vol_break": {"lookback": 20, "vol_ma_period": 10, "vol_ratio": 1.5},
}

# Best TP/SL combo per strategy (from sweep results)
# (tp_pct, sl_pct, trailing_activation_pct, trailing_callback_pct)
BEST_COMBO = {
    "ma_cross":   (3.0, 1.0, 2.0, 0.5),     # 长数据最优：宽参数
    "rsi":        (3.0, 1.0, 2.0, 0.5),      # 长数据最优：宽参数
    "bollinger":  (2.0, 0.8, 0, 0),          # 长数据最优：NoTrail
    "macd":       (1.5, 0.5, 0, 0),          # 长数据最优
    "ema_volume": (3.0, 1.0, 2.0, 0.5),      # 长数据最优：宽参数
    "supertrend": (3.0, 1.0, 2.0, 0.5),      # 长数据最优
    "kdj":        (3.0, 1.0, 2.0, 0.5),      # 长数据最优
    "dual_ema":   (2.0, 0.8, 0, 0),          # 长数据最优：NoTrail
    "ma_ribbon":  (2.0, 0.8, 0, 0),          # 长数据最优：NoTrail（12天100%胜率是假象）
    "cci":        (3.0, 1.0, 2.0, 0.5),      # 长数据最优：宽参数
    # 组合策略 — 124天数据扫描最优
    "trend_break": (2.0, 0.8, 0, 0),         # 长数据最优！+1.3%
    "rsi_macd":   (3.0, 1.0, 2.0, 0.5),      # 长数据最优
    "st_kdj":     (2.0, 0.8, 0, 0),          # 长数据最优
    "ribbon_macd":(1.5, 0.5, 1.0, 0.2),      # 长数据最优！+0.8%
    "vol_break":  (2.0, 0.8, 1.2, 0.3),      # 长数据最优
}

timeframe = sys.argv[1] if len(sys.argv) > 1 else "1h"
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

# ── Generate HTML ──

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>BTC 高频回测报告 - 优化版</title>
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
  .strategy-header {{ background: linear-gradient(135deg, #f7931a, #ff9f43); color: #fff; padding: 12px 16px; }}
  .strategy-header h3 {{ font-size: 15px; }}
  .strategy-header .stats {{ font-size: 12px; opacity: 0.95; margin-top: 4px; }}
  .strategy-body {{ padding: 0; max-height: 500px; overflow-y: auto; }}
  .trade-table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
  .trade-table th {{ background: #21262d; padding: 7px 5px; text-align: left; font-weight: 600; color: #8b949e; border-bottom: 1px solid #30363d; position: sticky; top: 0; z-index: 1; }}
  .trade-table td {{ padding: 5px; border-bottom: 1px solid #21262d; }}
  .trade-table tr:hover {{ background: #1c2128; }}
  .trade-table .open-long {{ color: #ef5350; font-weight: 600; }}
  .trade-table .open-short {{ color: #26a69a; font-weight: 600; }}
  .trade-table .close-long {{ color: #26a69a; }}
  .trade-table .close-short {{ color: #ef5350; }}
  .badge {{ display: inline-block; padding: 1px 5px; border-radius: 8px; font-size: 10px; font-weight: 600; }}
  .badge-long {{ background: #3d1f1f; color: #ef5350; }}
  .badge-short {{ background: #1f3d2d; color: #26a69a; }}
  .badge-tp {{ background: #1f3d1f; color: #4caf50; }}
  .badge-sl {{ background: #3d1f2d; color: #e91e63; }}
  .badge-signal {{ background: #1f2d3d; color: #1976d2; }}
  .badge-trailing {{ background: #3d2d1f; color: #ff9800; }}
  .badge-end {{ background: #2d1f3d; color: #9c27b0; }}
  .pair-row {{ background: #1c2128; }}
  .top3 {{ background: #2d2000 !important; }}
  .note {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px 16px; margin-bottom: 20px; font-size: 12px; color: #8b949e; }}
  .note strong {{ color: #f7931a; }}
</style>
</head>
<body>
<h1>BTC 高频回测报告 - 优化版</h1>
<p class="subtitle">BTC-USDT-SWAP | {timeframe} | {t0.strftime('%Y-%m-%d')} ~ {t1.strftime('%Y-%m-%d')} ({days} 天) | 杠杆: {LEVERAGE}x</p>
<p class="config">每个策略使用参数扫描得出的最优止盈/止损/移动止盈组合</p>

<div class="note">
  <strong>说明：</strong> 每个策略使用参数扫描（10种组合）得出的最优止盈止损配置。<br>
  信号周期已缩短（如 MA 3/7, RSI 6, MACD 6/13/5），以在1小时级别产生更多信号。
</div>

<div class="summary">
<h2>策略对比（每策略最优止盈止损）</h2>
<table class="summary-table">
<thead>
<tr>
  <th>#</th><th>策略</th><th>止盈止损配置</th><th>收益率</th><th>最大回撤</th><th>夏普</th><th>胜率</th><th>盈亏比</th><th>交易数</th><th>信号/天</th><th>手续费</th><th>最终权益</th>
</tr>
</thead>
<tbody>
"""

sorted_strategies = sorted(all_results.items(), key=lambda x: x[1]["result"]["total_return"], reverse=True)

for i, (stype, data) in enumerate(sorted_strategies, 1):
    r = data["result"]
    tp, sl, ta, tc = data["combo"]
    trail_str = f"T:{ta}%>{tc}%" if ta > 0 else "无移动"
    combo_str = f"止盈{tp}/止损{sl}/{trail_str}"
    ret_cls = "positive" if r["total_return"] > 0 else "negative"
    sig_day = r["trade_count"] / max(days, 1)
    top3_cls = ' class="top3"' if i <= 3 else ""
    html += f"""<tr{top3_cls}>
  <td>{i}</td>
  <td><strong>{data['name']}</strong></td>
  <td style="font-size:10px;font-family:monospace;">{combo_str}</td>
  <td class="{ret_cls}">{r['total_return']:.1f}%</td>
  <td>{r['max_drawdown']:.1f}%</td>
  <td>{r['sharpe_ratio']:.2f}</td>
  <td>{r['win_rate']:.1f}%</td>
  <td>{r['profit_factor']:.2f}</td>
  <td>{r['trade_count']}</td>
  <td>{sig_day:.1f}</td>
  <td>${r['total_fees']:.2f}</td>
  <td>${r['final_capital']:.2f}</td>
</tr>
"""

html += """</tbody></table></div>
<h2 style="text-align:center; color:#f7931a; margin-bottom:16px;">逐笔交易明细</h2>
"""

for i, (stype, data) in enumerate(sorted_strategies, 1):
    r = data["result"]
    trades = r.get("trades", [])
    ret_cls = "positive" if r["total_return"] > 0 else "negative"
    sig_day = r["trade_count"] / max(days, 1)
    tp, sl, ta, tc = data["combo"]
    trail_str = f"移动止盈: {ta}%激活, {tc}%回调" if ta > 0 else "无移动止盈"

    html += f"""
<div class="strategy-card">
<div class="strategy-header">
  <h3>#{i} {data['name']}</h3>
  <div class="stats">
    止盈={tp}% | 止损={sl}% | {trail_str} | 收益: <strong class="{ret_cls}">{r['total_return']:.1f}%</strong> |
    信号/天: {sig_day:.1f} | 胜率: {r['win_rate']:.1f}% | 交易数: {r['trade_count']}
  </div>
</div>
<div class="strategy-body">
"""

    if not trades:
        html += '<div style="padding:20px;text-align:center;color:#8b949e;">未产生交易</div>'
    else:
        html += """<table class="trade-table">
<thead>
<tr><th>#</th><th>时间</th><th>操作</th><th>方向</th><th>价格</th><th>张数</th><th>保证金</th><th>盈亏</th><th>盈亏%</th><th>手续费</th><th>原因</th></tr>
</thead>
<tbody>
"""
        trade_num = 0
        for t in trades:
            side = t.get("side", "")
            is_open = side.startswith("open_")
            if is_open:
                trade_num += 1

            ts = t.get("time", "")
            if isinstance(ts, (int, float)) and ts > 1000000000000:
                time_str = datetime.fromtimestamp(ts / 1000).strftime('%m-%d %H:%M')
            elif isinstance(ts, (int, float)) and ts > 1000000000:
                time_str = datetime.fromtimestamp(ts).strftime('%m-%d %H:%M')
            else:
                time_str = str(ts)

            if "long" in side:
                dir_badge = '<span class="badge badge-long">多</span>'
                action_cls = "open-long" if is_open else "close-long"
            else:
                dir_badge = '<span class="badge badge-short">空</span>'
                action_cls = "open-short" if is_open else "close-short"

            action = "开仓" if is_open else "平仓"

            reason = t.get("reason", "")
            reason_map = {"take_profit": "止盈", "stop_loss": "止损", "signal": "信号", "trailing_stop": "移动止盈", "backtest_end": "回测结束"}
            badge_map = {"take_profit": "badge-tp", "stop_loss": "badge-sl", "signal": "badge-signal", "trailing_stop": "badge-trailing", "backtest_end": "badge-end"}
            reason_badge = f'<span class="badge {badge_map.get(reason, "")}">{reason_map.get(reason, reason)}</span>'

            pnl = t.get("pnl", "")
            pnl_str = f"${pnl:.2f}" if isinstance(pnl, (int, float)) else ""
            pnl_cls = "positive" if isinstance(pnl, (int, float)) and pnl > 0 else ("negative" if isinstance(pnl, (int, float)) and pnl < 0 else "")

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
<h2 style="text-align:center; color:#f7931a; margin:25px 0 16px;">权益曲线</h2>
<div class="strategy-card" style="padding:16px;">
<canvas id="equityChart" height="350"></canvas>
</div>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns"></script>
<script>
"""

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
      x: { type: 'time', time: { tooltipFormat: 'MM-dd HH:mm' }, title: { display: true, text: '日期', color: '#8b949e' }, ticks: { color: '#8b949e' }, grid: { color: '#21262d' } },
      y: { title: { display: true, text: '权益 (USDT)', color: '#8b949e' }, ticks: { color: '#8b949e' }, grid: { color: '#21262d' } }
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

output_path = "backtest_final_report.html"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\nReport saved to: {output_path}")
