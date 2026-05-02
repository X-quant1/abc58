"""Scalping backtest with parameter sweep - find optimal TP/SL/Trailing for each strategy.

Runs multiple TP/SL/Trailing combos per strategy on the same data.
Reports the best combo for each strategy.

Usage:
  cd c:\LH\OKX\backend
  python backtest_sweep.py [timeframe] [limit]
  python backtest_sweep.py 1h 300
"""
import sys
import json
from datetime import datetime
from app.services.strategy import STRATEGY_REGISTRY
from app.services.backtest import backtest_engine
from app.services.market import market_service, _to_okx_instId, TIMEFRAME_MAP

SYMBOL = "BTC-USDT-SWAP"
INITIAL_CAPITAL = 10000
LEVERAGE = 100
FEE_RATE = 0.0005
SLIPPAGE = 0.0005

# Strategy-specific scalping params (short periods for more signals)
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

# TP/SL/Trailing parameter grid to sweep
# Format: (tp_pct, sl_pct, trailing_activation_pct, trailing_callback_pct)
SL_TP_COMBOS = [
    # User's original tight config
    (0.5, 0.3, 0.3, 0.06),
    # Slightly wider
    (0.8, 0.4, 0.5, 0.1),
    (1.0, 0.5, 0.6, 0.15),
    # Medium
    (1.5, 0.5, 1.0, 0.2),
    (2.0, 0.8, 1.2, 0.3),
    # Wider (swing)
    (3.0, 1.0, 2.0, 0.5),
    # No trailing, just fixed TP/SL
    (0.5, 0.3, 0, 0),
    (1.0, 0.5, 0, 0),
    (1.5, 0.5, 0, 0),
    (2.0, 0.8, 0, 0),
]

timeframe = sys.argv[1] if len(sys.argv) > 1 else "1h"
pages = int(sys.argv[2]) if len(sys.argv) > 2 else 1

# 分页拉取 K 线数据
print(f"Fetching BTC-USDT {timeframe} klines ({pages} pages x 300) from OKX...")

import os
import subprocess
import time as _time

OKX_CLI = r"C:\LH\OKX\tools\node-v20.18.0-win-x64\okx.cmd"
_node_dir = r"C:\LH\OKX\tools\node-v20.18.0-win-x64"
if _node_dir not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _node_dir + ";" + os.environ.get("PATH", "")

def _fetch_page(symbol, bar, after_ts=None):
    args = [OKX_CLI, "market", "candles", _to_okx_instId(symbol), "--bar", bar, "--limit", "300", "--json"]
    if after_ts:
        args += ["--after", str(after_ts)]
    env = os.environ.copy()
    env["OKX_SITE"] = "global"
    result = subprocess.run(args, capture_output=True, text=True, timeout=30,
                           encoding="utf-8", errors="replace", env=env)
    if result.returncode != 0:
        return []
    try:
        data = json.loads(result.stdout.strip())
    except:
        return []
    if not isinstance(data, list):
        return []
    candles = []
    for c in data:
        if isinstance(c, list) and len(c) >= 9:
            ts_ms = int(c[0])
            candles.append({
                "timestamp": ts_ms,
                "time": datetime.fromtimestamp(ts_ms / 1000).strftime("%Y-%m-%d %H:%M"),
                "open": float(c[1]), "high": float(c[2]), "low": float(c[3]), "close": float(c[4]),
                "volume": float(c[5]), "quote_volume": float(c[7]),
            })
        elif isinstance(c, dict):
            ts_ms = int(c.get("ts", 0))
            candles.append({
                "timestamp": ts_ms,
                "time": datetime.fromtimestamp(ts_ms / 1000).strftime("%Y-%m-%d %H:%M"),
                "open": float(c.get("o", 0)), "high": float(c.get("h", 0)),
                "low": float(c.get("l", 0)), "close": float(c.get("c", 0)),
                "volume": float(c.get("vol", 0)), "quote_volume": float(c.get("volCcy", 0)),
            })
    return candles

bar = TIMEFRAME_MAP.get(timeframe, "1H")
all_klines = []
after_ts = None
for p in range(pages):
    print(f"  Page {p+1}/{pages}...")
    page_data = _fetch_page("BTC-USDT", bar, after_ts)
    if not page_data:
        break
    all_klines.extend(page_data)
    after_ts = page_data[-1]["timestamp"]
    if len(page_data) < 300:
        break
    _time.sleep(0.3)

all_klines.sort(key=lambda x: x["timestamp"])
# 去重
seen = set()
klines = []
for c in all_klines:
    if c["timestamp"] not in seen:
        seen.add(c["timestamp"])
        klines.append(c)

if not klines or len(klines) < 50:
    print("ERROR: Failed to fetch klines data")
    sys.exit(1)

t0 = datetime.fromtimestamp(klines[0]["timestamp"] / 1000)
t1 = datetime.fromtimestamp(klines[-1]["timestamp"] / 1000)
days = (t1 - t0).days
print(f"Got {len(klines)} candles: {t0.strftime('%Y-%m-%d %H:%M')} ~ {t1.strftime('%Y-%m-%d %H:%M')} ({days} days)")
print(f"Testing {len(SL_TP_COMBOS)} TP/SL combos x {len(STRATEGY_REGISTRY)} strategies = {len(SL_TP_COMBOS) * len(STRATEGY_REGISTRY)} backtests\n")

# Run sweep
all_best = {}  # stype -> best result

for stype, scls in sorted(STRATEGY_REGISTRY.items()):
    print(f"--- {scls.strategy_name} ---")
    best_score = -999
    best_result = None
    best_combo = None

    for tp, sl, trail_act, trail_cb in SL_TP_COMBOS:
        params = dict(scls.default_params)
        params.update(SCALP_PARAMS.get(stype, {}))
        params["timeframe"] = timeframe
        params["size_mode"] = "fixed"
        params["size"] = 1
        params["take_profit_pct"] = tp
        params["stop_loss_pct"] = sl
        params["trailing_activation_pct"] = trail_act
        params["trailing_stop_pct"] = trail_cb
        params["inst_id"] = SYMBOL

        try:
            result = backtest_engine.run(
                strategy_type=stype, params=params, symbol=SYMBOL,
                timeframe=timeframe, klines=klines, initial_capital=INITIAL_CAPITAL,
                leverage=LEVERAGE, fee_rate=FEE_RATE, slippage=SLIPPAGE,
            )
        except Exception as e:
            continue

        if not result.get("ok"):
            continue

        r = result
        sig_day = r["trade_count"] / max(days, 1)

        # Composite score: weighted return + sharpe + winrate + signal frequency
        # Bonus for reaching target signal frequency
        freq_bonus = min(sig_day, 4) * 5  # up to 20 points for 4+ sig/day
        score = (
            max(r["total_return"], -20) * 2.0 +
            r["sharpe_ratio"] * 10 +
            r["win_rate"] * 0.3 +
            freq_bonus +
            min(r["profit_factor"], 3) * 10
        )

        trail_str = f"Trail:{trail_act}%>{trail_cb}%" if trail_act > 0 else "NoTrail"
        combo_str = f"TP={tp}%/SL={sl}%/{trail_str}"
        marker = " <<<" if score > best_score else ""
        print(f"  {combo_str:<35} Return={r['total_return']:>6.1f}%  Sig/Day={sig_day:>4.1f}  "
              f"WinRate={r['win_rate']:>5.1f}%  Sharpe={r['sharpe_ratio']:>5.2f}  "
              f"Trades={r['trade_count']:>3}  PF={r['profit_factor']:>4.2f}  "
              f"Score={score:>6.1f}{marker}")

        if score > best_score:
            best_score = score
            best_result = result
            best_combo = (tp, sl, trail_act, trail_cb)

    if best_result:
        all_best[stype] = {
            "name": scls.strategy_name,
            "result": best_result,
            "combo": best_combo,
            "score": best_score,
        }

    print()

# ── Summary ──
print("\n" + "=" * 100)
print("  BEST TP/SL COMBO PER STRATEGY")
print("=" * 100)
print(f"{'Strategy':<18} {'Best Combo':<35} {'Return':>8} {'Sig/Day':>8} {'WinRate':>8} {'Sharpe':>7} {'Trades':>7} {'Score':>7}")
print("-" * 100)

sorted_best = sorted(all_best.items(), key=lambda x: x[1]["score"], reverse=True)
for stype, data in sorted_best:
    r = data["result"]
    tp, sl, ta, tc = data["combo"]
    trail_str = f"Trail:{ta}%>{tc}%" if ta > 0 else "NoTrail"
    combo_str = f"TP={tp}%/SL={sl}%/{trail_str}"
    sig_day = r["trade_count"] / max(days, 1)
    print(f"{data['name']:<18} {combo_str:<35} {r['total_return']:>7.1f}% {sig_day:>7.1f} {r['win_rate']:>7.1f}% {r['sharpe_ratio']:>6.2f} {r['trade_count']:>7} {data['score']:>7.1f}")

print("\nDone.")
