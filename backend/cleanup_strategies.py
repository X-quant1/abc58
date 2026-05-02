"""清理所有 enabled=True 的策略"""
from app.database import SessionLocal
from app.models import Strategy

db = SessionLocal()
try:
    strategies = db.query(Strategy).filter(Strategy.enabled == True).all()
    print(f'清理前: {len(strategies)} 个策略 enabled=True')
    
    for s in strategies:
        print(f'  #{s.id} {s.name} -> enabled=False')
        s.enabled = False
    
    db.commit()
    print('\n清理完成')
    
    remaining = db.query(Strategy).filter(Strategy.enabled == True).count()
    print(f'剩余 enabled=True: {remaining} 个')
finally:
    db.close()
