"""启动所有启用的策略"""
import sys
sys.path.insert(0, '.')
from app.database import SessionLocal
from app.models import Strategy
from app.services.strategy import strategy_runner
import json

db = SessionLocal()

print('=== 启动所有启用的策略 ===\n')

# 获取所有启用的策略
strategies = db.query(Strategy).filter(Strategy.enabled == True).all()
print(f'找到 {len(strategies)} 个启用的策略\n')

for s in strategies:
    if not strategy_runner.is_running(s.id):
        print(f'启动策略 #{s.id} {s.name}...')
        try:
            strategy_runner.start(s.id)
            print(f'  [OK] 已启动')
        except Exception as e:
            print(f'  [错误] {e}')
    else:
        print(f'策略 #{s.id} {s.name} 已在运行中')

db.close()

print('\n=== 启动完成 ===')
print('\n提示: 请在前端刷新策略列表查看运行状态')
