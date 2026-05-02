"""更新策略#12的止盈止损参数"""
import sys
sys.path.insert(0, '.')
from app.database import SessionLocal
from app.models import Strategy
import json

db = SessionLocal()
s = db.query(Strategy).filter(Strategy.id == 12).first()

if s:
    params = json.loads(s.params) if s.params else {}
    
    print("更新前参数:")
    print(f"  止盈: {params.get('take_profit_pct', 0)}%")
    print(f"  止损: {params.get('stop_loss_pct', 0)}%")
    print(f"  移动止损: {params.get('trailing_stop_pct', 0)}%")
    
    # 更新参数
    params['take_profit_pct'] = 3.0
    params['stop_loss_pct'] = 5.0
    params['trailing_stop_pct'] = 1.5
    
    s.params = json.dumps(params)
    db.commit()
    
    print("\n更新后参数:")
    print(f"  止盈: {params['take_profit_pct']}%")
    print(f"  止损: {params['stop_loss_pct']}%")
    print(f"  移动止损: {params['trailing_stop_pct']}%")
    print("\n策略#12参数已更新！")
else:
    print("策略#12不存在")

db.close()
