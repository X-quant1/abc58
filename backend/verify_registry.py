"""验证策略注册表"""
import sys
sys.path.insert(0, '.')

# 强制重新加载模块
import importlib
if 'app.services.strategy' in sys.modules:
    del sys.modules['app.services.strategy']
    del sys.modules['app.services.strategy']

from app.services.strategy import STRATEGY_REGISTRY

print('=== 策略注册表 ===\n')
print(f'策略总数: {len(STRATEGY_REGISTRY)}\n')

for type_key in sorted(STRATEGY_REGISTRY.keys()):
    cls = STRATEGY_REGISTRY[type_key]
    marker = ' [新]' if type_key in ('multi_tf_trend', 'funding_arb') else ''
    print(f'{type_key:<20} - {cls.strategy_name}{marker}')

print('\n检查新策略:')
if 'multi_tf_trend' in STRATEGY_REGISTRY:
    print('[OK] multi_tf_trend 已注册')
else:
    print('[X] multi_tf_trend 未注册')

if 'funding_arb' in STRATEGY_REGISTRY:
    print('[OK] funding_arb 已注册')
else:
    print('[X] funding_arb 未注册')
