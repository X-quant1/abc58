"""Batch backtest with regime filter comparison - BTC-USDT-SWAP 1H.

Uses OKX REST API directly to fetch up to 3000 candles (125 days for 1H).
Compares all 15 strategies with/without regime filter.

Usage:
  cd c:\\LH\\OKX\\backend
  python batch_backtest_regime.py [timeframe] [days]
  python batch_backtest_regime.py 1h 125
"""
import sys, json, time, urllib.request
from datetime import datetime, timedelta
from app.services.strategy import STRATEGY_REGISTRY
from app.services.backtest import backtest_engine

# ── Config ──
SYMBOL = "BTC-USDT-SWAP"
SPOT = "BTC-USDT"
INITIAL_CAPITAL = 10000
LEVERAGE = 10
FEE_RATE = 0.0005
SLIPPAGE = 0.0005
OKX_BASE = "https://www.okx.com"

timeframe = sys.argv[1] if len(sys.argv) > 1 else "1h"
days = int(sys.argv[2]) if len(sys.argv) > 2 else 125

# OKX bar mapping
BAR_MAP = {"1h": "1H", "4h": "4H", "1d": "1D", "15m": "15m", "5m": "5m"}
bar = BAR_MAP.get(timeframe, "1H")


def fetch_klines_paged(inst_id: str, bar: str, total_days: int) -> list:
    """Fetch klines via OKX REST API with pagination (after param).
    
    OKX returns max 300 per request. We paginate backwards from now.
    Each page uses the oldest candle's ts as 'after' for next page.
    """
    all_candles = []
    after_ts = ""  # empty = start from latest
    pages_needed = (total_days * 24) // 300 + 2  # rough estimate for 1h
    max_pages = 20  # safety limit
    
    for page in range(max_pages):
        url = f"{OKX_BASE}/api/v5/market/candles?instId={inst_id}&bar={bar}&limit=300"
        if after_ts:
            url += f"&after={after_ts}"
        
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "BTC-Quant/1.0"})
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read())
        except Exception as e:
            print(f"  Page {page+1} fetch error: {e}")
            break
        
        if data.get("code") != "0":
            print(f"  Page {page+1} API error: {data.get('msg', '')}")
            break
        
        candles = data.get("data", [])
        if not candles:
            break
        
        all_candles.extend(candles)
        
        # Get oldest timestamp for next page
        oldest_ts = candles[-1][0]
        after_ts = str(oldest_ts)
        
        # Check if we have enough data
        oldest_time = datetime.fromtimestamp(int(oldest_ts) / 1000)
        cutoff = datetime.now() - timedelta(days=total_days)
        if oldest_time <= cutoff:
            break
        
        time.sleep(0.15)  # rate limit
    
    # Parse candles (OKX returns array format, newest first)
    result = []
    for c in all_candles:
        if not isinstance(c, (list, tuple)) or len(c) < 7:
            continue
        ts_ms = int(c[0])
        result.append({
            "timestamp": ts_ms,
            "time": datetime.fromtimestamp(ts_ms / 1000).strftime("%Y-%m-%d %H:%M"),
            "open": float(c[1]),
            "high": float(c[2]),
            "low": float(c[3]),
            "close": float(c[4]),
            "volume": float(c[5]),
            "quote_volume": float(c[6]) if len(c) > 6 else 0,
        })
    
    # Reverse to chronological order
    result.reverse()
    
    # Remove duplicates (pagination may overlap)
    seen = set()
    unique = []
    for c in result:
        if c["timestamp"] not in seen:
            seen.add(c["timestamp"])
            unique.append(c)
    
    # Sort by timestamp
    unique.sort(key=lambda x: x["timestamp"])
    
    # Trim to requested days
    cutoff_ts = int((datetime.now() - timedelta(days=total_days)).timestamp() * 1000)
    unique = [c for c in unique if c["timestamp"] >= cutoff_ts]
    
    return unique


# ── 1. Fetch klines ──
print(f"[1/3] Fetching BTC-USDT {timeframe} klines ({days} days) from OKX REST API...")
klines = fetch_klines_paged(SPOT + "-SWAP", bar, days)

if not klines or len(klines) < 50:
    print("ERROR: Failed to fetch klines data")
    sys.exit(1)

t0 = datetime.fromtimestamp(klines[0]["timestamp"] / 1000)
t1 = datetime.fromtimestamp(klines[-1]["timestamp"] / 1000)
actual_days = (t1 - t0).days
print(f"  Got {len(klines)} candles, {t0.strftime('%Y-%m-%d')} ~ {t1.strftime('%Y-%m-%d')} ({actual_days} days)")

# ── 2. Run backtests ──
print(f"\n[2/3] Running backtests for all {len(STRATEGY_REGISTRY)} strategies...")
print("=" * 130)
print(f"{'Strategy':<20} | {'--- Without Regime Filter ---':^50} | {'--- With Regime Filter ---':^55}")
print(f"{'':20} | {'Return%':>8} {'MaxDD%':>8} {'Sharpe':>7} {'WinRate':>8} {'Trades':>6} | {'Return%':>8} {'MaxDD%':>8} {'Sharpe':>7} {'WinRate':>8} {'Trades':>6} {'Delta':>7}")
print("-" * 130)

results = []

for stype, scls in STRATEGY_REGISTRY.items():
    params = {**scls.default_params}
    params["timeframe"] = timeframe
    params["size_mode"] = "fixed"
    params["size"] = 1
    params["take_profit_pct"] = 0
    params["stop_loss_pct"] = 5
    params["trailing_stop_pct"] = 0
    params["inst_id"] = SYMBOL

    # Without regime filter
    try:
        r_no = backtest_engine.run(
            strategy_type=stype,
            params={**params},
            symbol=SYMBOL,
            timeframe=timeframe,
            klines=klines,
            initial_capital=INITIAL_CAPITAL,
            leverage=LEVERAGE,
            fee_rate=FEE_RATE,
            slippage=SLIPPAGE,
            regime_filter=False,
        )
    except Exception as e:
        r_no = {"ok": False, "msg": str(e)}

    # With regime filter
    try:
        r_yes = backtest_engine.run(
            strategy_type=stype,
            params={**params},
            symbol=SYMBOL,
            timeframe=timeframe,
            klines=klines,
            initial_capital=INITIAL_CAPITAL,
            leverage=LEVERAGE,
            fee_rate=FEE_RATE,
            slippage=SLIPPAGE,
            regime_filter=True,
        )
    except Exception as e:
        r_yes = {"ok": False, "msg": str(e)}

    no_ok = r_no.get("ok", False)
    yes_ok = r_yes.get("ok", False)

    if no_ok and yes_ok:
        delta = r_yes["total_return"] - r_no["total_return"]
        delta_str = f"{delta:+.1f}%"
        print(f"{scls.strategy_name:<20} | "
              f"{r_no['total_return']:>7.1f}% {r_no['max_drawdown']:>7.1f}% {r_no['sharpe_ratio']:>7.2f} {r_no['win_rate']:>7.1f}% {r_no['trade_count']:>6} | "
              f"{r_yes['total_return']:>7.1f}% {r_yes['max_drawdown']:>7.1f}% {r_yes['sharpe_ratio']:>7.2f} {r_yes['win_rate']:>7.1f}% {r_yes['trade_count']:>6} {delta_str:>7}")
        results.append({
            "type": stype,
            "name": scls.strategy_name,
            "ret_no": r_no["total_return"],
            "dd_no": r_no["max_drawdown"],
            "sharpe_no": r_no["sharpe_ratio"],
            "wr_no": r_no["win_rate"],
            "trades_no": r_no["trade_count"],
            "pf_no": r_no["profit_factor"],
            "ret_yes": r_yes["total_return"],
            "dd_yes": r_yes["max_drawdown"],
            "sharpe_yes": r_yes["sharpe_ratio"],
            "wr_yes": r_yes["win_rate"],
            "trades_yes": r_yes["trade_count"],
            "pf_yes": r_yes["profit_factor"],
            "delta": delta,
        })
    elif no_ok:
        print(f"{scls.strategy_name:<20} | "
              f"{r_no['total_return']:>7.1f}% {r_no['max_drawdown']:>7.1f}% {r_no['sharpe_ratio']:>7.2f} {r_no['win_rate']:>7.1f}% {r_no['trade_count']:>6} | "
              f"REGIME FILTER FAILED")
    elif yes_ok:
        print(f"{scls.strategy_name:<20} | "
              f"BASE FAILED | "
              f"{r_yes['total_return']:>7.1f}% {r_yes['max_drawdown']:>7.1f}% {r_yes['sharpe_ratio']:>7.2f} {r_yes['win_rate']:>7.1f}% {r_yes['trade_count']:>6}")
    else:
        print(f"{scls.strategy_name:<20} | BOTH FAILED: {r_no.get('msg','')[:30]}")

# ── 3. Rankings ──
print(f"\n[3/3] Regime Filter Impact Rankings ({actual_days} days, {timeframe})")
print("=" * 90)

if results:
    # Most improved by regime filter
    by_delta = sorted(results, key=lambda x: x["delta"], reverse=True)
    print("\n  Most Improved by Regime Filter (Delta = regime_ret - baseline_ret):")
    for i, r in enumerate(by_delta, 1):
        marker = " [UP]" if r["delta"] > 0 else ""
        print(f"    #{i:<2} {r['name']:<18} delta={r['delta']:>+6.1f}%  "
              f"(base={r['ret_no']:>+.1f}% -> regime={r['ret_yes']:>+.1f}%, "
              f"trades={r['trades_no']}->{r['trades_yes']}){marker}")

    # Best with regime filter (absolute)
    by_ret_yes = sorted(results, key=lambda x: x["ret_yes"], reverse=True)
    print(f"\n  Best Return WITH Regime Filter:")
    for i, r in enumerate(by_ret_yes[:5], 1):
        print(f"    #{i} {r['name']:<18} ret={r['ret_yes']:>+.1f}%  sharpe={r['sharpe_yes']:.2f}  wr={r['wr_yes']:.1f}%  trades={r['trades_yes']}  pf={r['pf_yes']:.2f}")

    # Best without regime filter (absolute)
    by_ret_no = sorted(results, key=lambda x: x["ret_no"], reverse=True)
    print(f"\n  Best Return WITHOUT Regime Filter (baseline):")
    for i, r in enumerate(by_ret_no[:5], 1):
        print(f"    #{i} {r['name']:<18} ret={r['ret_no']:>+.1f}%  sharpe={r['sharpe_no']:.2f}  wr={r['wr_no']:.1f}%  trades={r['trades_no']}  pf={r['pf_no']:.2f}")

    # Summary
    improved = sum(1 for r in results if r["delta"] > 0)
    declined = sum(1 for r in results if r["delta"] < 0)
    neutral = sum(1 for r in results if r["delta"] == 0)
    avg_delta = sum(r["delta"] for r in results) / len(results)
    print(f"\n  Summary: {improved} improved, {declined} declined, {neutral} neutral | Avg delta: {avg_delta:+.1f}%")

print("\nDone.")
