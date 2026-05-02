import sys
sys.path.insert(0, 'c:/LH/OKX/backend')
from app.database import SessionLocal
from app.models import User
from app.routers.settings import _load_config

saved = _load_config()
okx_uid = saved.get("okx_uid", "")
print(f"Config okx_uid: {okx_uid}")

if okx_uid:
    db = SessionLocal()
    admin = db.query(User).filter(User.username == "admin").first()
    if admin and not admin.okx_uid:
        admin.okx_uid = okx_uid
        db.commit()
        print(f"Synced okx_uid={okx_uid} to admin user")
    else:
        print(f"Admin already has okx_uid={admin.okx_uid}" if admin else "Admin not found")
    db.close()
