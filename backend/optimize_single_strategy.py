"""
优化单个策略的止盈止损参数（测试）
"""
import json
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
klines = market_service.get_klines(symbol=spot_symbol, timeframe=TIMEFRAME, limit=1000)
print(f"获取到 {len(klines)} 根K线\n")

# 获取策略#3
db = SessionLocal()
s = db.query(Strategy).filter(Strategy.id == 3).first()
db.close()

params = json.loads(s.params) if s.params else {}
print(f"优化策略 #{s.id} {s.name}")
print(f"类型: {s.type}\n")

engine = BacktestEngine()
best_result = None
best_params = {}

test_count = 0
for tp in TP_RANGE:
    for sl in SL_RANGE:
        for trailing in TRAILING_RANGE:
            test_params = params.copy()
            test_params["take_profit_pct"] = tp
            test_params["stop_loss_pct"] = sl
            test_params["trailing_stop_pct"] = trailing

            result = engine.run(
                strategy_type=s.type,
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
                        print(f"[{test_count}] TP={tp}% SL={sl}% Trailing={trailing}% → 收益={total_return:.2f}% 胜率={win_rate:.1f}% 交易={trade_count} 得分={score:.2f}")

if best_result:
    print(f"\n最优参数:")
    print(f"  止盈: {best_result['tp']}%")
    print(f"  止损: {best_result['sl']}%")
    print(f"  移动止损: {best_result['trailing']}%")
    print(f"  总收益: {best_result['total_return']:.2f}%")
    print(f"  胜率: {best_result['win_rate']:.1f}%")
    print(f"  交易次数: {best_result['trade_count']}")
    print(f"  最大回撤: {best_result['max_drawdown']:.2f}%")
else:
    print(f"\n未找到合适的参数组合（测试了{test_count}组）")
