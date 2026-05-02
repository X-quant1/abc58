"""
寻找盈利策略：放宽条件，只关注收益率
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

# 更宽的止盈止损范围
TP_RANGE = [15, 20, 25, 30, 40, 50, 60, 80]
SL_RANGE = [10, 15, 20, 25, 30, 40]
TRAILING_RANGE = [5, 10, 15, 20, 30]

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

    best_result = None
    best_params_all = None

    test_count = 0
    for tp in TP_RANGE:
        for sl in SL_RANGE:
            for trailing in TRAILING_RANGE:
                test_params = params.copy()
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

                    # 只要有交易，就记录
                    if trade_count >= 1:
                        # 只看收益率，不看胜率
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
                            best_params_all = test_params.copy()

    if best_result:
        print(f"  最优: TP={best_result['tp']}% SL={best_result['sl']}% Trailing={best_result['trailing']}%", flush=True)
        print(f"  结果: 收益={best_result['total_return']:.2f}% 胜率={best_result['win_rate']:.1f}% 交易={best_result['trade_count']}", flush=True)

        results.append({
            "id": s.id,
            "name": s.name,
            "type": strategy_type,
            "best_params": best_result,
            "all_params": best_params_all,
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
print(f"{'排名':<6} {'策略':<25} {'收益率%':<10} {'胜率%':<8} {'交易次数':<8} {'止盈%':<8} {'止损%':<8}")
print("-" * 100)

for i, r in enumerate(results, 1):
    bp = r["best_params"]
    print(f"{i:<6} #{r['id']} {r['name']:<20} {bp['total_return']:<10.2f} {bp['win_rate']:<8.1f} {bp['trade_count']:<8} {bp['tp']:<8} {bp['sl']:<8}")

# 输出盈利策略
profitable = [r for r in results if r["best_params"]["total_return"] > 0]
print(f"\n盈利策略数量: {len(profitable)}/{len(results)}")

if profitable:
    print("\n盈利策略详细参数：")
    for r in profitable:
        bp = r["best_params"]
        print(f"\n#{r['id']} {r['name']}:")
        print(f"  止盈={bp['tp']}%, 止损={bp['sl']}%, 移动止损={bp['trailing']}%")
        print(f"  收益率={bp['total_return']:.2f}%, 胜率={bp['win_rate']:.1f}%, 交易={bp['trade_count']}次")

# 保存结果
with open("profitable_strategies.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print("\n结果已保存到 profitable_strategies.json")
