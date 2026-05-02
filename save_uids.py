import sys
sys.path.insert(0, 'backend')
from app.database import SessionLocal
from app.models import SubordinateUID

uids = sys.argv[1].split(',') if len(sys.argv) > 1 else []
db = SessionLocal()
new_count = 0
for uid in uids:
    if uid and not db.query(SubordinateUID).filter(SubordinateUID.uid == uid).first():
        db.add(SubordinateUID(uid=uid))
        new_count += 1
db.commit()

# 更新用户状态
from app.models import User
subordinate_uids = set(uid[0] for uid in db.query(SubordinateUID.uid).all())
for user in db.query(User).filter(User.okx_uid != None).all():
    user.is_subordinate = user.okx_uid in subordinate_uids
db.commit()
db.close()
print(f'保存了 {new_count} 个新 UID，共 {len(uids)} 个')
