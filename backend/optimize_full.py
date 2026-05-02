"""
完整优化：策略参数 + 止盈止损参数
目标：提高交易频率，止盈止损至少20%
"""
import json
import sys
import app.routers.settings
from app.database import SessionLocal
from app.models import Strategy
from app.services.backtest import BacktestEngine
from app.services.market import market_service

# 回测参数
INITIAL_CAPITAL = 10000
LEVERAGE = 100
TIMEFRAME = "1h"
SYMBOL = "BTC-USDT-SWAP"

# 止盈止损搜索范围（至少20%）
TP_RANGE = [20, 25, 30, 35, 40, 50, 60, 80, 100]  # 止盈：20%-100%
SL_RANGE = [20, 25, 30, 35, 40, 50]               # 止损：20%-50%
TRAILING_RANGE = [10, 15, 20, 25, 30]             # 移动止损：10%-30%

# 策略参数搜索范围（根据策略类型）
STRATEGY_PARAM_RANGES = {
    "rsi": {
        "period": [4, 6, 8, 10, 12, 14],
        "oversold": [20, 25, 30, 35, 40],
        "overbought": [60, 65, 70, 75, 80],
    },
    "kdj": {
        "n": [5, 7, 9, 11, 14],
        "m1": [3, 5, 7],
        "m2": [3, 5, 7],
    },
    "cci": {
        "period": [10, 14, 20, 28],
        "constant": [0.015, 0.02, 0.025],
    },
    "macd": {
        "fast": [8, 10, 12],
        "slow": [20, 24, 26],
        "signal": [7, 8, 9],
    },
    "bollinger": {
        "period": [15, 20, 25],
        "std_dev": [1.5, 2.0, 2.5],
    },
    "ema_cross": {
        "fast_period": [5, 7, 9, 12],
        "slow_period": [20, 26, 30, 50],
    },
    "supertrend": {
        "period": [7, 10, 14],
        "multiplier": [2.0, 2.5, 3.0, 3.5],
    },
    "volume_breakout": {
        "volume_ma_period": [10, 15, 20],
        "price_change_pct": [0.5, 1.0, 1.5],
    },
    "trend_breakout": {
        "ema_period": [15, 21, 30],
        "boll_period": [10, 15, 20],
        "boll_std": [1.5, 2.0, 2.5],
    },
    "ma_alignment": {
        "ma_periods": ["3,7,13,21", "5,10,20,30", "7,14,21,28"],
    },
    "rsi_macd": {
        "rsi_period": [4, 6, 8],
        "macd_fast": [8, 10, 12],
        "macd_slow": [20, 24, 26],
        "macd_signal": [7, 8, 9],
    },
    "dual_timeframe": {
        "fast_period": [5, 7, 9],
        "slow_period": [20, 26, 30],
    },
    "multi_timeframe": {
        "ema_period": [15, 21, 30],
        "volume_ma": [10, 15, 20],
    },
}

# 获取K线
print("获取K线数据...")
spot_symbol = SYMBOL.replace("-SWAP", "")
klines = market_service.get_klines(symbol=spot_symbol, timeframe=TIMEFRAME, limit=600)
print(f"获取到 {len(klines)} 根K线\n")

engine = BacktestEngine()

# 获取所有策略
db = SessionLocal()
strategies = db.query(Strategy).all()

results = []

for s in strategies:
    print(f"\n优化策略 #{s.id} {s.name}...", flush=True)

    params = json.loads(s.params) if s.params else {}
    strategy_type = s.type

    # 获取该策略的参数搜索范围
    param_ranges = STRATEGY_PARAM_RANGES.get(strategy_type, {})

    if not param_ranges:
        print(f"  未定义参数搜索范围，跳过", flush=True)
        continue

    best_result = None
    best_all_params = None

    test_count = 0

    # 策略参数组合
    strategy_param_combos = [{}]
    for key, values in param_ranges.items():
        new_combos = []
        for combo in strategy_param_combos:
            for val in values:
                new_combo = combo.copy()
                new_combo[key] = val
                new_combos.append(new_combo)
        strategy_param_combos = new_combos

    print(f"  策略参数组合: {len(strategy_param_combos)}组", flush=True)

    # 遍历所有参数组合
    for strategy_params in strategy_param_combos:
        for tp in TP_RANGE:
            for sl in SL_RANGE:
                for trailing in TRAILING_RANGE:
                    # 合并参数
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

                        # 至少5次交易，胜率至少40%
                        if trade_count >= 5 and win_rate >= 40:
                            # 综合得分：收益率 × 胜率 × 交易频率
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
        print(f"    策略参数: {best_all_params}", flush=True)
        print(f"    止盈={best_result['tp']}% 止损={best_result['sl']}% 移动止损={best_result['trailing']}%", flush=True)
        print(f"  回测结果:", flush=True)
        print(f"    收益={best_result['total_return']:.2f}% 胜率={best_result['win_rate']:.1f}% 交易={best_result['trade_count']}", flush=True)

        results.append({
            "id": s.id,
            "name": s.name,
            "type": strategy_type,
            "strategy_params": best_all_params,
            "best_params": best_result,
        })
    else:
        print(f"  未找到合适参数（测试了{test_count}组，要求交易>=5次，胜率>=40%）", flush=True)

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
with open("optimize_full_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print("\n结果已保存到 optimize_full_results.json")
