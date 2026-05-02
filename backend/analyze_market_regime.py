"""分析过去12小时的市场状态"""
import sys
sys.path.insert(0, '.')
from app.services.market import market_service
from app.services.market_regime import market_regime_detector

# 获取过去12小时的K线
symbol = "BTC-USDT"
timeframe = "1h"
klines = market_service.get_klines(symbol, timeframe, limit=150)

print('=' * 70)
print('过去12小时市场状态分析')
print('=' * 70)
print()

# 分析最近12根K线的市场状态
regime_counts = {}
for i in range(12):
    # 使用前100根K线作为历史数据
    historical_klines = klines[:-(12-i)] if i > 0 else klines
    regime_result = market_regime_detector.detect_with_score(historical_klines)
    regime = regime_result.get('regime', 'unknown')
    score = regime_result.get('score', 0)

    regime_counts[regime] = regime_counts.get(regime, 0) + 1

    kline_time = historical_klines[-1].get('time', '')
    close = historical_klines[-1].get('close', 0)

    print(f'{kline_time} | 价格: {close:10.2f} | 状态: {regime:15s} | 得分: {score:.3f}')

print()
print('=' * 70)
print('市场状态分布:')
for regime, count in sorted(regime_counts.items()):
    pct = count / 12 * 100
    print(f'  {regime:15s}: {count:2d} 次 ({pct:5.1f}%)')

print()
print('结论:')
if regime_counts.get('ranging', 0) > 6:
    print('  [!] 市场持续震荡，策略会被拦截')
elif regime_counts.get('volatile', 0) > 6:
    print('  [!] 市场高波动无方向，策略会被拦截')
else:
    print('  [OK] 市场有趋势，策略应该能开仓')

print('=' * 70)
