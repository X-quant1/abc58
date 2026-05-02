"""Batch backtest - compare all strategies on BTC-USDT-SWAP.

Usage:
  cd c:\\LH\\OKX\\backend
  python batch_backtest.py [timeframe] [limit]
  python batch_backtest.py 4h 300
"""
import sys
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

print(f"[1/3] Fetching BTC-USDT {timeframe} klines (limit={limit}) from OKX...")
klines = market_service.get_klines(symbol="BTC-USDT", timeframe=timeframe, limit=limit)

if not klines or len(klines) < 50:
    print("ERROR: Failed to fetch klines data")
    sys.exit(1)

print(f"  Got {len(klines)} candles, from {klines[0].get('time','')} to {klines[-1].get('time','')}")
# Calculate date range
if klines[0].get("timestamp") and klines[-1].get("timestamp"):
    from datetime import datetime
    t0 = datetime.fromtimestamp(klines[0]["timestamp"] / 1000)
    t1 = datetime.fromtimestamp(klines[-1]["timestamp"] / 1000)
    days = (t1 - t0).days
    print(f"  Date range: {t0.strftime('%Y-%m-%d')} ~ {t1.strftime('%Y-%m-%d')} ({days} days)")

print(f"\n[2/3] Running backtests for all {len(STRATEGY_REGISTRY)} strategies (TF={timeframe})...")
print("-" * 95)
print(f"{'Strategy':<20} {'Return%':>8} {'MaxDD%':>8} {'Sharpe':>7} {'WinRate':>8} {'P/F':>6} {'Trades':>7} {'Fees':>10}")
print("-" * 95)

results = []

for stype, scls in STRATEGY_REGISTRY.items():
    params = {**scls.default_params}
    # Override timeframe to match data
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
            row = {
                "type": stype,
                "name": scls.strategy_name,
                "return": result["total_return"],
                "max_dd": result["max_drawdown"],
                "sharpe": result["sharpe_ratio"],
                "win_rate": result["win_rate"],
                "pf": result["profit_factor"],
                "trades": result["trade_count"],
                "fees": result["total_fees"],
                "final": result["final_capital"],
            }
            results.append(row)
            print(f"{scls.strategy_name:<20} {row['return']:>7.1f}% {row['max_dd']:>7.1f}% {row['sharpe']:>7.2f} {row['win_rate']:>7.1f}% {row['pf']:>6.2f} {row['trades']:>7} {row['fees']:>9.2f}")
        else:
            print(f"{scls.strategy_name:<20} FAILED: {result.get('msg','')}")
    except Exception as e:
        print(f"{scls.strategy_name:<20} ERROR: {e}")

# Rankings
print(f"\n[3/3] Strategy Rankings (data: {len(klines)} {timeframe} candles)")
print("-" * 60)

if results:
    by_return = sorted(results, key=lambda x: x["return"], reverse=True)
    print("\n  By Total Return:")
    for i, r in enumerate(by_return, 1):
        marker = " <<<" if i <= 3 else ""
        print(f"    #{i} {r['name']:<18} {r['return']:>7.1f}%{marker}")

    by_sharpe = sorted(results, key=lambda x: x["sharpe"], reverse=True)
    print("\n  By Sharpe Ratio:")
    for i, r in enumerate(by_sharpe, 1):
        marker = " <<<" if i <= 3 else ""
        print(f"    #{i} {r['name']:<18} {r['sharpe']:>7.2f}{marker}")

    by_pf = sorted(results, key=lambda x: x["pf"], reverse=True)
    print("\n  By Profit Factor:")
    for i, r in enumerate(by_pf, 1):
        marker = " <<<" if i <= 3 else ""
        print(f"    #{i} {r['name']:<18} {r['pf']:>6.2f}{marker}")

    # Composite score
    for r in results:
        r["score"] = (
            max(r["return"], -50) * 0.3 +
            r["sharpe"] * 10 * 0.3 +
            r["win_rate"] * 0.2 +
            min(r["pf"], 5) * 20 * 0.2
        )
    by_score = sorted(results, key=lambda x: x["score"], reverse=True)
    print("\n  Overall Score (Return*0.3 + Sharpe*10*0.3 + WinRate*0.2 + PF*20*0.2):")
    for i, r in enumerate(by_score, 1):
        marker = " <<<" if i <= 3 else ""
        print(f"    #{i} {r['name']:<18} score={r['score']:>6.1f}  (ret={r['return']:>6.1f}%, sharpe={r['sharpe']:>5.2f}, wr={r['win_rate']:>5.1f}%, pf={r['pf']:>4.2f}){marker}")

print("\nDone.")
