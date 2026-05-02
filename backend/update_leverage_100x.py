import json
import app.routers.settings  # 加载API密钥
from app.database import SessionLocal
from app.models import Strategy

db = SessionLocal()
strategies = db.query(Strategy).all()

print("更新策略杠杆为100X:")
for s in strategies:
    params = json.loads(s.params) if s.params else {}
    old_leverage = params.get("leverage", 10)
    params["leverage"] = 100
    s.params = json.dumps(params)
    print(f"#{s.id} {s.name}: {old_leverage}X -> 100X")

db.commit()
print("\n[OK] 所有策略杠杆已更新为100X")
db.close()
