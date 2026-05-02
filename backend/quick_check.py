import sys
sys.path.insert(0, '.')
from app.database import SessionLocal
from app.models import Strategy
import json

db = SessionLocal()
s = db.query(Strategy).filter(Strategy.id == 3).first()
params = json.loads(s.params) if s.params else {}
print(f'Strategy #3 params length: {len(s.params) if s.params else 0}')
print(f'Has period: {"period" in params}')
print(f'Period value: {params.get("period", "NOT SET")}')
db.close()
