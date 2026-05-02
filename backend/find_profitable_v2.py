"""
寻找盈利策略：优化策略参数 + 更合理的止盈止损比例
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

# 止盈止损：止盈要大于止损（风险收益比>1）
TP_SL_PAIRS = [
    (30, 15),  # 止盈30%, 止损15% (2:1)
    (40, 20),  # 止盈40%, 止损20% (2:1)
    (50, 25),  # 止盈50%, 止损25% (2:1)
    (60, 30),  # 止盈60%, 止损30% (2:1)
    (40, 15),  # 止盈40%, 止损15% (2.67:1)
    (50, 20),  # 止盈50%, 止损20% (2.5:1)
    (60, 20),  # 止盈60%, 止损20% (3:1)
    (80, 30),  # 止盈80%, 止损30% (2.67:1)
]

# 策略参数范围
STRATEGY_PARAMS = {
    "rsi": [
        {"period": 6, "oversold": 25, "overbought": 75},
        {"period": 9, "oversold": 30, "overbought": 70},
        {"period": 14, "oversold": 30, "overbought": 70},
        {"period": 14, "oversold": 25, "overbought": 75},
        {"period": 21, "oversold": 30, "overbought": 70},
    ],
    "kdj": [
        {"k_period": 9, "oversold": 20, "overbought": 80},
        {"k_period": 14, "oversold": 20, "overbought": 80},
    ],
    "cci": [
        {"period": 14, "oversold": -100, "overbought": 100},
        {"period": 20, "oversold": -100, "overbought": 100},
    ],
    "macd": [
        {"fast": 12, "slow": 26, "signal": 9},
        {"fast": 8, "slow": 21, "signal": 7},
    ],
    "bollinger": [
        {"period": 20, "std_dev": 2.0},
        {"period": 20, "std_dev": 2.5},
    ],
    "ema_cross": [
        {"fast_period": 7, "slow_period": 21},
        {"fast_period": 9, "slow_period": 26},
        {"fast_period": 12, "slow_period": 26},
    ],
}

# 获取K线
print("获取K线数据...")
klines = market_service.get_klines(symbol="BTC-USDT", timeframe=TIMEFRAME, limit=600)
print(f"获取到 {len(klines)} 根K线\n")

engine = BacktestEngine()

# 获取所有策略
db = SessionLocal()
strategies = db.query(Strategy).all()

results = []

for s in strategies:
    print(f"\n测试策略 #{s.id} {s.name}...", flush=True)

    params = json.loads(s.params) if s.params else {}
    strategy_type = s.type

    # 获取该策略的参数组合
    param_combos = STRATEGY_PARAMS.get(strategy_type, [{}])

    best_result = None
    best_params_all = None

    test_count = 0
    for strategy_param in param_combos:
        for tp, sl in TP_SL_PAIRS:
            for trailing in [10, 15, 20, 25]:
                test_params = params.copy()
                test_params.update(strategy_param)
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

                    if trade_count >= 1:
                        if best_result is None or total_return > best_result["total_return"]:
                            best_result = {
                                "total_return": total_return,
                                "win_rate": win_rate,
                                "trade_count": trade_count,
                                "max_drawdown": result.get("max_drawdown", 0),
                                "tp": tp,
                                "sl": sl,
                                "trailing": trailing,
                            }
                            best_params_all = strategy_param.copy()

    if best_result:
        print(f"  最优: TP={best_result['tp']}% SL={best_result['sl']}% Trailing={best_result['trailing']}%", flush=True)
        print(f"  策略参数: {best_params_all}", flush=True)
        print(f"  结果: 收益={best_result['total_return']:.2f}% 胜率={best_result['win_rate']:.1f}% 交易={best_result['trade_count']}", flush=True)

        results.append({
            "id": s.id,
            "name": s.name,
            "type": strategy_type,
            "best_params": best_result,
            "strategy_params": best_params_all,
        })
    else:
        print(f"  无交易（测试{test_count}组）", flush=True)

db.close()

# 按收益率排序
results.sort(key=lambda x: x["best_params"]["total_return"], reverse=True)

# 输出汇总
print("\n" + "=" * 100)
print("策略收益率排名（从高到低）")
print("=" * 100)
print(f"{'排名':<6} {'策略':<25} {'收益率%':<10} {'胜率%':<8} {'交易次数':<8} {'止盈%':<8} {'止损%':<8} {'盈亏比':<8}")
print("-" * 100)

for i, r in enumerate(results, 1):
    bp = r["best_params"]
    ratio = bp['tp'] / bp['sl'] if bp['sl'] > 0 else 0
    print(f"{i:<6} #{r['id']} {r['name']:<20} {bp['total_return']:<10.2f} {bp['win_rate']:<8.1f} {bp['trade_count']:<8} {bp['tp']:<8} {bp['sl']:<8} {ratio:<8.1f}")

# 输出盈利策略
profitable = [r for r in results if r["best_params"]["total_return"] > 0]
print(f"\n盈利策略数量: {len(profitable)}/{len(results)}")

if profitable:
    print("\n[OK] 盈利策略详细参数：")
    for r in profitable:
        bp = r["best_params"]
        sp = r["strategy_params"]
        print(f"\n#{r['id']} {r['name']}:")
        print(f"  策略参数: {sp}")
        print(f"  止盈={bp['tp']}%, 止损={bp['sl']}%, 移动止损={bp['trailing']}%")
        print(f"  收益率={bp['total_return']:.2f}%, 胜率={bp['win_rate']:.1f}%, 交易={bp['trade_count']}次")
        print(f"  盈亏比={bp['tp']/bp['sl']:.1f}")
else:
    print("\n[X] 未找到盈利策略")

# 保存结果
with open("profitable_strategies_v2.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print("\n结果已保存到 profitable_strategies_v2.json")
