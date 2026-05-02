import sys
sys.path.insert(0, 'c:\\LH\\OKX\\backend')
from app.database import SessionLocal
from app.models import SubordinateUID

db = SessionLocal()
bad = db.query(SubordinateUID).filter(SubordinateUID.uid == 'list').all()
print(f"删除 {len(bad)} 条无效记录")
for r in bad:
    print(f"  删除 id={r.id}, uid={r.uid}")
    db.delete(r)
db.commit()

# 显示清理后的结果
results = db.query(SubordinateUID).all()
print(f"\n清理后共 {len(results)} 个下级UID:")
for r in results:
    print(f"  id={r.id}, uid={r.uid}")

db.close()
print("\n完成")
