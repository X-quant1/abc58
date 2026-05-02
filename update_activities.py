import sys
sys.path.insert(0, 'c:/LH/OKX/backend')
from app.database import SessionLocal
from app.models import HotActivity

db = SessionLocal()
try:
    db.query(HotActivity).filter(HotActivity.id == 1).update({'icon_url': '/images/jiangbei.webp'})
    db.query(HotActivity).filter(HotActivity.id == 2).update({'icon_url': '/images/fuli.webp'})
    db.query(HotActivity).filter(HotActivity.id == 3).update({'icon_url': '/images/jiaocheng.webp'})
    db.commit()
    print('Updated 3 activities')
finally:
    db.close()
