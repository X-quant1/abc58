"""
优化所有策略的止盈止损参数
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

# 止盈止损搜索范围
TP_RANGE = [10, 15, 20, 25, 30, 35, 40, 50]
SL_RANGE = [10, 15, 20, 25, 30]
TRAILING_RANGE = [5, 10, 15, 20]

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
    original_params = params.copy()

    best_result = None

    test_count = 0
    for tp in TP_RANGE:
        for sl in SL_RANGE:
            for trailing in TRAILING_RANGE:
                test_params = original_params.copy()
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

                    if trade_count >= 2:
                        score = total_return * (win_rate / 100) if win_rate > 0 else 0

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

    if best_result:
        print(f"  最优: TP={best_result['tp']}% SL={best_result['sl']}% Trailing={best_result['trailing']}%")
        print(f"  收益={best_result['total_return']:.2f}% 胜率={best_result['win_rate']:.1f}% 交易={best_result['trade_count']}", flush=True)

        results.append({
            "id": s.id,
            "name": s.name,
            "type": strategy_type,
            "best_params": best_result,
        })
    else:
        print(f"  未找到合适参数（测试了{test_count}组）", flush=True)

db.close()

# 输出汇总
print("\n" + "=" * 80)
print("优化结果汇总")
print("=" * 80)
print(f"{'策略':<30} {'止盈%':<8} {'止损%':<8} {'移动止损%':<10} {'收益率%':<10} {'胜率%':<8}")
print("-" * 80)
for r in results:
    bp = r["best_params"]
    print(f"#{r['id']} {r['name']:<25} {bp['tp']:<8} {bp['sl']:<8} {bp['trailing']:<10} {bp['total_return']:<10.2f} {bp['win_rate']:<8.1f}")

print("\n建议更新参数：")
for r in results:
    bp = r["best_params"]
    print(f"#{r['id']}: 止盈={bp['tp']}%, 止损={bp['sl']}%, 移动止损={bp['trailing']}%")

# 保存结果到文件
with open("optimize_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print("\n结果已保存到 optimize_results.json")
