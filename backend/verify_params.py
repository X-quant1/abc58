"""验证策略参数更新"""
import sys
sys.path.insert(0, '.')
from app.database import SessionLocal
from app.models import Strategy
import json

db = SessionLocal()
strategies = db.query(Strategy).filter(Strategy.id.in_([3, 5, 10])).all()

print('=== 验证策略参数更新 ===\n')
for s in strategies:
    params = json.loads(s.params) if isinstance(s.params, str) else s.params
    print(f'#{s.id} {s.name}')
    if s.id == 3:
        print(f'  period: {params.get("period")} (应为6)')
        print(f'  oversold: {params.get("oversold")} (应为40)')
        print(f'  overbought: {params.get("overbought")} (应为60)')
    elif s.id == 5:
        print(f'  period: {params.get("period")} (应为10)')
        print(f'  overbought: {params.get("overbought")} (应为80)')
    elif s.id == 10:
        print(f'  period1: {params.get("period1")} (应为3)')
        print(f'  period2: {params.get("period2")} (应为7)')
        print(f'  period3: {params.get("period3")} (应为13)')
        print(f'  period4: {params.get("period4")} (应为21)')
    print()

db.close()
