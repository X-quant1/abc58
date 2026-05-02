"""
优化每个策略的止盈止损参数
网格搜索：测试不同的止盈止损组合，找出最优参数
"""
import json
import app.routers.settings  # 加载API密钥
from app.database import SessionLocal
from app.models import Strategy
from app.services.backtest import BacktestEngine
from app.services.market import market_service

# 回测参数
INITIAL_CAPITAL = 10000  # 初始资金
LEVERAGE = 100           # 杠杆倍数
TIMEFRAME = "1h"         # K线周期
SYMBOL = "BTC-USDT-SWAP" # 交易对

# 止盈止损搜索范围（杠杆收益%）
TP_RANGE = [10, 15, 20, 25, 30, 35, 40, 50]      # 止盈：10%-50%
SL_RANGE = [10, 15, 20, 25, 30]                   # 止损：10%-30%
TRAILING_RANGE = [5, 10, 15, 20]                  # 移动止损：5%-20%

# 获取K线数据
print("获取K线数据...")
spot_symbol = SYMBOL.replace("-SWAP", "")
klines = market_service.get_klines(symbol=spot_symbol, timeframe=TIMEFRAME, limit=600)
print(f"获取到 {len(klines)} 根K线")

# 初始化回测引擎
engine = BacktestEngine()

# 获取所有策略
db = SessionLocal()
strategies = db.query(Strategy).all()

print("\n" + "=" * 80)
print("策略止盈止损参数优化（100X杠杆）")
print("=" * 80)

results = []

for s in strategies:
    print(f"\n优化策略 #{s.id} {s.name}...")

    # 获取策略参数
    params = json.loads(s.params) if s.params else {}
    strategy_type = s.type

    # 保存原始参数
    original_params = params.copy()

    best_result = None
    best_params = {}

    # 网格搜索
    test_count = 0
    for tp in TP_RANGE:
        for sl in SL_RANGE:
            for trailing in TRAILING_RANGE:
                # 设置止盈止损参数
                test_params = original_params.copy()
                test_params["take_profit_pct"] = tp
                test_params["stop_loss_pct"] = sl
                test_params["trailing_stop_pct"] = trailing

                # 执行回测
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
                    # 评估指标：收益率 × 胜率（平衡盈利和稳定性）
                    total_return = result.get("total_return", 0)
                    win_rate = result.get("win_rate", 0)
                    trade_count = result.get("trade_count", 0)

                        # 只考虑有足够交易的组合（至少2次交易）
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
        print(f"  最优参数:")
        print(f"    止盈: {best_result['tp']}% (杠杆收益)")
        print(f"    止损: {best_result['sl']}% (杠杆亏损)")
        print(f"    移动止损: {best_result['trailing']}% (回调比例)")
        print(f"  回测结果:")
        print(f"    总收益: {best_result['total_return']:.2f}%")
        print(f"    胜率: {best_result['win_rate']:.1f}%")
        print(f"    交易次数: {best_result['trade_count']}")
        print(f"    最大回撤: {best_result['max_drawdown']:.2f}%")
        print(f"    综合得分: {best_result['score']:.2f}")

        results.append({
            "id": s.id,
            "name": s.name,
            "type": strategy_type,
            "best_params": best_result,
        })
    else:
        print(f"  未找到合适的参数组合（测试了{test_count}组）")

db.close()

# 输出汇总结果
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
