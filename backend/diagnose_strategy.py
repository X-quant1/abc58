"""诊断策略信号生成"""
import sys
sys.path.insert(0, '.')
from app.services.market import market_service
from app.services.strategy import RSIStrategy, KDJStrategy, CCIStrategy
from app.services.market_regime import market_regime_detector
import json

# 1. 获取最近的K线数据
symbol = "BTC-USDT"
timeframe = "1h"
klines = market_service.get_klines(symbol, timeframe, limit=150)

print('=' * 70)
print('策略信号诊断')
print('=' * 70)
print(f'K线数量: {len(klines)}')
print(f'最新K线时间: {klines[-1].get("time", "") if klines else "N/A"}')
print(f'最新价格: {klines[-1].get("close", 0) if klines else 0}')
print()

# 2. 检查市场状态
regime_result = market_regime_detector.detect_with_score(klines)
regime = regime_result.get('regime', 'unknown')
score = regime_result.get('score', 0)
print(f'市场状态: {regime}')
print(f'市场得分: {score:.3f}')
print()

# 3. 测试各个策略的信号生成
strategies = [
    ('RSI', RSIStrategy, {"period": 6, "oversold": 40, "overbought": 60}),
    ('KDJ', KDJStrategy, {"k_period": 7, "d_period": 3, "j_smooth": 3, "overbought": 70, "oversold": 30}),
    ('CCI', CCIStrategy, {"period": 10, "overbought": 80, "oversold": -80}),
]

print('策略信号测试:')
print('-' * 70)

for name, strategy_cls, params in strategies:
    strategy = strategy_cls(params)
    signal = strategy.generate_signal(klines)

    print(f'{name:10s} | 信号: {signal:15s} | 参数: {json.dumps(params, ensure_ascii=False)}')

    # 如果是开仓信号，检查是否会被市场状态过滤器拦截
    if signal in ('open_long', 'open_short'):
        if regime == 'ranging':
            print(f'           | ⚠️  会被拦截（震荡市）')
        elif regime == 'volatile':
            print(f'           | ⚠️  会被拦截（高波动无方向）')
        else:
            print(f'           | ✅ 不会被拦截')

print()
print('=' * 70)
