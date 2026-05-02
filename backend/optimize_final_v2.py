"""
完整优化：策略参数 + 止盈止损参数（修正版）
"""
import json
import app.routers.settings
from app.database import SessionLocal
from app.models import Strategy
from app.services.backtest import BacktestEngine
from app.services.market import market_service

INITIAL_CAPITAL = 10000
LEVERAGE = 100
TIMEFRAME = "1h"
SYMBOL = "BTC-USDT-SWAP"

# 止盈止损范围（至少20%）
TP_RANGE = [20, 25, 30, 35, 40, 50]
SL_RANGE = [20, 25, 30, 35, 40]
TRAILING_RANGE = [10, 15, 20, 25]

# 策略参数范围
STRATEGY_PARAM_RANGES = {
    "rsi": {
        "period": [4, 6, 8, 10],
        "oversold": [20, 25, 30, 35],
        "overbought": [65, 70, 75, 80],
    },
    "kdj": {
        "k_period": [7, 9, 11],
        "oversold": [15, 20, 25],
        "overbought": [75, 80, 85],
    },
    "cci": {
        "period": [14, 20],
        "oversold": [-100, -150],
        "overbought": [100, 150],
    },
    "macd": {
        "fast": [10, 12],
        "slow": [24, 26],
        "signal": [8, 9],
    },
}

# 获取K线
print("获取K线数据...")
klines = market_service.get_klines(symbol="BTC-USDT", timeframe=TIMEFRAME, limit=600)
print(f"获取到 {len(klines)} 根K线\n")

engine = BacktestEngine()

# 获取所有策略
db = SessionLocal()
strategies = db.query(Strategy).filter(Strategy.id.in_([3, 4, 5, 6])).all()  # 只优化前4个策略

results = []

for s in strategies:
    print(f"\n优化策略 #{s.id} {s.name}...", flush=True)

    params = json.loads(s.params) if s.params else {}
    strategy_type = s.type

    param_ranges = STRATEGY_PARAM_RANGES.get(strategy_type, {})
    if not param_ranges:
        print(f"  未定义参数范围，跳过", flush=True)
        continue

    best_result = None
    best_all_params = None

    # 生成参数组合
    strategy_param_combos = [{}]
    for key, values in param_ranges.items():
        new_combos = []
        for combo in strategy_param_combos:
            for val in values:
                new_combo = combo.copy()
                new_combo[key] = val
                new_combos.append(new_combo)
        strategy_param_combos = new_combos

    print(f"  参数组合: {len(strategy_param_combos)} × {len(TP_RANGE)}×{len(SL_RANGE)}×{len(TRAILING_RANGE)} = {len(strategy_param_combos)*len(TP_RANGE)*len(SL_RANGE)*len(TRAILING_RANGE)}组", flush=True)

    test_count = 0
    for strategy_params in strategy_param_combos:
        for tp in TP_RANGE:
            for sl in SL_RANGE:
                for trailing in TRAILING_RANGE:
                    test_params = params.copy()
                    test_params.update(strategy_params)
                    test_params["take_profit_pct"] = tp
                    test_params["stop_loss_pct"] = sl
                    test_params["trailing_stop_pct"] = trailing

                    result = engine.run(
                        strategy_type=strategy_type,
                        params=test_params,
                        symbol=SYMBOL,
                        timeframe=TIMEFRAME,
                        klines=klines,
                        initial_capital=INITIAL_CAPITAL,
                        leverage=LEVERAGE,
                    )

                    test_count += 1

                    if result.get("ok"):
                        total_return = result.get("total_return", 0)
                        win_rate = result.get("win_rate", 0)
                        trade_count = result.get("trade_count", 0)

                        # 至少10次交易，胜率至少30%
                        if trade_count >= 10 and win_rate >= 30:
                            score = total_return * (win_rate / 100) * (trade_count / 10)

                            if best_result is None or score > best_result["score"]:
                                best_result = {
                                    "score": score,
                                    "total_return": total_return,
                                    "win_rate": win_rate,
                                    "trade_count": trade_count,
                                    "max_drawdown": result.get("max_drawdown", 0),
                                    "tp": tp,
                                    "sl": sl,
                                    "trailing": trailing,
                                }
                                best_all_params = strategy_params.copy()

    if best_result:
        print(f"  最优参数:", flush=True)
        print(f"    策略: {best_all_params}", flush=True)
        print(f"    TP={best_result['tp']}% SL={best_result['sl']}% Trailing={best_result['trailing']}%", flush=True)
        print(f"  结果: 收益={best_result['total_return']:.2f}% 胜率={best_result['win_rate']:.1f}% 交易={best_result['trade_count']}", flush=True)

        results.append({
            "id": s.id,
            "name": s.name,
            "type": strategy_type,
            "strategy_params": best_all_params,
            "best_params": best_result,
        })
    else:
        print(f"  未找到合适参数（测试{test_count}组，要求交易>=10，胜率>=30%）", flush=True)

db.close()

# 输出汇总
print("\n" + "=" * 100)
print("优化结果汇总")
print("=" * 100)
print(f"{'策略':<25} {'止盈%':<8} {'止损%':<8} {'移动止损%':<10} {'收益率%':<10} {'胜率%':<8} {'交易次数':<8}")
print("-" * 100)
for r in results:
    bp = r["best_params"]
    print(f"#{r['id']} {r['name']:<20} {bp['tp']:<8} {bp['sl']:<8} {bp['trailing']:<10} {bp['total_return']:<10.2f} {bp['win_rate']:<8.1f} {bp['trade_count']:<8}")

print("\n详细参数：")
for r in results:
    bp = r["best_params"]
    sp = r["strategy_params"]
    print(f"\n#{r['id']} {r['name']}:")
    print(f"  策略参数: {sp}")
    print(f"  止盈={bp['tp']}%, 止损={bp['sl']}%, 移动止损={bp['trailing']}%")

# 保存结果
with open("optimize_final_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print("\n结果已保存到 optimize_final_results.json")
