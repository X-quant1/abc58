"""
分析各参数组合的交易次数
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

# 获取K线
klines = market_service.get_klines(symbol="BTC-USDT", timeframe=TIMEFRAME, limit=600)
print(f"K线数量: {len(klines)}\n")

engine = BacktestEngine()

# 获取RSI策略
db = SessionLocal()
s = db.query(Strategy).filter(Strategy.id == 3).first()
db.close()

params = json.loads(s.params) if s.params else {}

print(f"测试不同RSI参数的交易次数:\n")

# 测试不同RSI周期
for period in [4, 6, 8, 10, 12, 14]:
    test_params = params.copy()
    test_params["period"] = period
    test_params["take_profit_pct"] = 30
    test_params["stop_loss_pct"] = 30
    test_params["trailing_stop_pct"] = 15

    result = engine.run(
        strategy_type=s.type,
        params=test_params,
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        klines=klines,
        initial_capital=INITIAL_CAPITAL,
        leverage=LEVERAGE,
    )

    if result.get("ok"):
        print(f"period={period}: 交易={result['trade_count']}次, 胜率={result['win_rate']:.1f}%, 收益={result['total_return']:.2f}%")

print("\n测试不同超卖超买阈值:\n")

# 测试不同阈值
for oversold in [20, 25, 30, 35, 40]:
    for overbought in [60, 65, 70, 75, 80]:
        test_params = params.copy()
        test_params["period"] = 6
        test_params["oversold"] = oversold
        test_params["overbought"] = overbought
        test_params["take_profit_pct"] = 30
        test_params["stop_loss_pct"] = 30
        test_params["trailing_stop_pct"] = 15

        result = engine.run(
            strategy_type=s.type,
            params=test_params,
            symbol=SYMBOL,
            timeframe=TIMEFRAME,
            klines=klines,
            initial_capital=INITIAL_CAPITAL,
            leverage=LEVERAGE,
        )

        if result.get("ok") and result['trade_count'] >= 2:
            print(f"oversold={oversold}, overbought={overbought}: 交易={result['trade_count']}次, 胜率={result['win_rate']:.1f}%, 收益={result['total_return']:.2f}%")
