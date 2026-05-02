"""重置 admin 账户密码"""
import sys
sys.path.insert(0, 'c:/LH/OKX/backend')
from app.database import SessionLocal
from app.models import User
from app.auth import hash_password

db = SessionLocal()
user = db.query(User).filter(User.username == 'admin').first()
if user:
    user.password_hash = hash_password('btc2026')
    db.commit()
    print("Admin password reset to: btc2026")
else:
    print("Admin user not found")
db.close()
