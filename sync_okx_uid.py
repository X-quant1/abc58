import sys
sys.path.insert(0, 'c:/LH/OKX/backend')
from app.database import SessionLocal
from app.models import User
from app.routers.settings import _load_config

saved = _load_config()
uid = saved.get("okx_uid", "")

db = SessionLocal()
admin = db.query(User).filter(User.username == "admin").first()
if admin:
    admin.okx_uid = uid
    db.commit()
    print(f"Synced: admin.okx_uid = '{uid}'")
else:
    print("Admin not found")
db.close()
