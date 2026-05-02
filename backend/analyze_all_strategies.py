"""
检查所有策略的交易次数
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

# 获取所有策略
db = SessionLocal()
strategies = db.query(Strategy).all()

print("各策略交易次数分析:\n")
print(f"{'策略':<30} {'交易次数':<10} {'胜率%':<10} {'收益%':<10}")
print("-" * 60)

for s in strategies:
    params = json.loads(s.params) if s.params else {}

    # 设置默认止盈止损
    params["take_profit_pct"] = 30
    params["stop_loss_pct"] = 30
    params["trailing_stop_pct"] = 15

    result = engine.run(
        strategy_type=s.type,
        params=params,
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        klines=klines,
        initial_capital=INITIAL_CAPITAL,
        leverage=LEVERAGE,
    )

    if result.get("ok"):
        print(f"#{s.id} {s.name:<25} {result['trade_count']:<10} {result['win_rate']:<10.1f} {result['total_return']:<10.2f}")

db.close()
