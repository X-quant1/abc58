"""参数网格搜索 v2 - 修正字段名+添加size参数"""
import sys
import json
import itertools
from app.services.market import market_service
from app.services.backtest import BacktestEngine
from app.services.strategy import get_strategy_class


def grid_search(strategy_type, param_grid, klines, regime_filter=True, label=""):
    """参数网格搜索"""
    keys = list(param_grid.keys())
    values = list(param_grid.values())
    combos = list(itertools.product(*values))

    print(f"\n{'='*60}")
    print(f"Strategy: {strategy_type} {label}")
    print(f"Grid: {len(combos)} combinations")
    print(f"{'='*60}")

    engine = BacktestEngine()
    results = []

    for i, combo in enumerate(combos):
        params = dict(zip(keys, combo))
        params["timeframe"] = "1h"
        params["size"] = 1  # 固定1张

        try:
            result = engine.run(
                strategy_type=strategy_type,
                params=params,
                klines=klines,
                initial_capital=10000,
                leverage=10,
                regime_filter=regime_filter,
            )
            ret = result.get("total_return", 0)
            sharpe = result.get("sharpe_ratio", 0)
            wr = result.get("win_rate", 0)
            trades = result.get("trade_count", 0)

            results.append({
                "params": {k: v for k, v in params.items() if k not in ("timeframe", "size")},
                "return": ret,
                "sharpe": sharpe,
                "win_rate": wr,
                "trades": trades,
            })

            # 只打印有交易的组合
            if trades > 0:
                p = {k: v for k, v in params.items() if k not in ("timeframe", "size")}
                print(f"  [{i+1}/{len(combos)}] ret={ret:+.2f}% sharpe={sharpe:.2f} wr={wr:.0f}% trades={trades} | {p}")

        except Exception as e:
            print(f"  [{i+1}/{len(combos)}] ERROR: {e}")

    # 按收益率排序
    results_with_trades = [r for r in results if r["trades"] > 0]
    results_with_trades.sort(key=lambda x: x["return"], reverse=True)

    print(f"\n--- Top 5 {strategy_type} {label} ---")
    for rank, r in enumerate(results_with_trades[:5], 1):
        print(f"  #{rank} ret={r['return']:+.2f}% sharpe={r['sharpe']:.2f} wr={r['win_rate']:.0f}% trades={r['trades']}")
        print(f"      params: {r['params']}")

    if not results_with_trades:
        print("  (no trades in any combination)")

    return results_with_trades


def main():
    print("Fetching BTC-USDT 1H klines via OKX CLI (1440 bars = 60 days)...")
    klines = market_service.get_klines(symbol="BTC-USDT", timeframe="1h", limit=1440)
    print(f"Got {len(klines)} klines")
    if not klines:
        print("No data!")
        return

    # ─── 布林带突破策略参数网格 ───
    bollinger_grid = {
        "period": [10, 15, 20, 25, 30],
        "std_dev": [1.5, 2.0, 2.5, 3.0],
        "take_profit_pct": [1.0, 1.5, 2.0, 3.0],
        "stop_loss_pct": [0.5, 0.8, 1.0, 1.5],
    }
    # 5*4*4*4 = 320

    # ─── 均线排列+MACD策略参数网格 ───
    ribbon_macd_grid = {
        "period1": [3, 5],
        "period2": [7, 10],
        "period3": [13, 21],
        "period4": [21, 30, 55],
        "macd_fast": [6, 12],
        "macd_slow": [13, 26],
        "macd_signal": [5, 9],
        "take_profit_pct": [1.0, 2.0, 3.0],
        "stop_loss_pct": [0.5, 1.0],
    }
    # 2*2*2*3*2*2*2*3*2 = 576

    # Regime ON
    boll_on = grid_search("bollinger", bollinger_grid, klines, regime_filter=True, label="regime=ON")
    ribbon_on = grid_search("ribbon_macd", ribbon_macd_grid, klines, regime_filter=True, label="regime=ON")

    # Regime OFF
    boll_off = grid_search("bollinger", bollinger_grid, klines, regime_filter=False, label="regime=OFF")
    ribbon_off = grid_search("ribbon_macd", ribbon_macd_grid, klines, regime_filter=False, label="regime=OFF")

    # 保存结果
    output = {
        "bollinger_regime_on": boll_on[:20],
        "bollinger_regime_off": boll_off[:20],
        "ribbon_macd_regime_on": ribbon_on[:20],
        "ribbon_macd_regime_off": ribbon_off[:20],
    }
    with open("grid_search_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to grid_search_results.json")


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(line_buffering=True)  # 实时输出
    main()
