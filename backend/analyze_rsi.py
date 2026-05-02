"""分析RSI指标"""
import sys
sys.path.insert(0, '.')
from app.services.market import market_service
from app.services.strategy import RSIStrategy
import json

# 获取K线数据
symbol = "BTC-USDT"
timeframe = "1h"
klines = market_service.get_klines(symbol, timeframe, limit=150)

print('=' * 70)
print('RSI指标分析')
print('=' * 70)
print()

# 使用优化后的参数
params = {"period": 6, "oversold": 40, "overbought": 60}
strategy = RSIStrategy(params)

# 计算RSI
closes = [k["close"] for k in klines]
rsi_values = strategy._calc_rsi(closes, params["period"])

# 显示最近10根K线的RSI值
print('最近10根K线的RSI值:')
print(f'参数: period={params["period"]}, oversold={params["oversold"]}, overbought={params["overbought"]}')
print()

for i in range(-10, 0):
    time_str = klines[i].get('time', '')
    close = klines[i].get('close', 0)
    rsi = rsi_values[i] if i < len(rsi_values) else None

    if rsi is not None:
        # 判断是否触发信号
        prev_rsi = rsi_values[i-1] if i-1 >= -len(rsi_values) else None
        signal = ''
        if prev_rsi is not None:
            if prev_rsi < params["oversold"] and rsi >= params["oversold"]:
                signal = ' [开多信号]'
            elif prev_rsi > params["overbought"] and rsi <= params["overbought"]:
                signal = ' [开空信号]'

        print(f'{time_str} | 价格: {close:10.2f} | RSI: {rsi:6.2f}{signal}')
    else:
        print(f'{time_str} | 价格: {close:10.2f} | RSI: N/A')

print()
print('=' * 70)
print('结论:')
print(f'  RSI范围: {min([r for r in rsi_values[-10:] if r is not None]):.2f} - {max([r for r in rsi_values[-10:] if r is not None]):.2f}')
print(f'  超卖线: {params["oversold"]}')
print(f'  超买线: {params["overbought"]}')
print()

# 检查是否有触发
recent_rsi = [r for r in rsi_values[-10:] if r is not None]
if any(r < params["oversold"] for r in recent_rsi):
    print('  [OK] 有RSI低于超卖线')
else:
    print('  [X] 没有RSI低于超卖线')

if any(r > params["overbought"] for r in recent_rsi):
    print('  [OK] 有RSI高于超买线')
else:
    print('  [X] 没有RSI高于超买线')

print('=' * 70)
