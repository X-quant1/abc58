"""
测试单个策略的完整优化
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

# 止盈止损范围
TP_RANGE = [20, 30, 40, 50]
SL_RANGE = [20, 30, 40]
TRAILING_RANGE = [10, 15, 20]

# RSI参数范围
RSI_PERIODS = [4, 6, 8, 10]
OVERSOLD = [20, 25, 30, 35]
OVERBOUGHT = [65, 70, 75, 80]

# 获取K线
print("获取K线数据...")
klines = market_service.get_klines(symbol="BTC-USDT", timeframe=TIMEFRAME, limit=600)
print(f"获取到 {len(klines)} 根K线\n")

engine = BacktestEngine()

# 获取RSI策略
db = SessionLocal()
s = db.query(Strategy).filter(Strategy.id == 3).first()
db.close()

params = json.loads(s.params) if s.params else {}

print(f"优化策略 #{s.id} {s.name}")
print(f"原始参数: {params}\n")

best_result = None
best_all_params = None

test_count = 0

for period in RSI_PERIODS:
    for oversold in OVERSOLD:
        for overbought in OVERBOUGHT:
            for tp in TP_RANGE:
                for sl in SL_RANGE:
                    for trailing in TRAILING_RANGE:
                        test_params = params.copy()
                        test_params["period"] = period
                        test_params["oversold"] = oversold
                        test_params["overbought"] = overbought
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

                            # 至少5次交易，胜率至少40%
                            if trade_count >= 5 and win_rate >= 40:
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
                                    best_all_params = {
                                        "period": period,
                                        "oversold": oversold,
                                        "overbought": overbought,
                                    }

print(f"测试了 {test_count} 组参数\n")

if best_result:
    print(f"最优参数:")
    print(f"  RSI周期: {best_all_params['period']}")
    print(f"  超卖阈值: {best_all_params['oversold']}")
    print(f"  超买阈值: {best_all_params['overbought']}")
    print(f"  止盈: {best_result['tp']}%")
    print(f"  止损: {best_result['sl']}%")
    print(f"  移动止损: {best_result['trailing']}%")
    print(f"\n回测结果:")
    print(f"  总收益: {best_result['total_return']:.2f}%")
    print(f"  胜率: {best_result['win_rate']:.1f}%")
    print(f"  交易次数: {best_result['trade_count']}")
    print(f"  最大回撤: {best_result['max_drawdown']:.2f}%")
    print(f"  综合得分: {best_result['score']:.2f}")
else:
    print("未找到符合条件的参数组合（交易>=5次，胜率>=40%）")
