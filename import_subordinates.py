"""
手动导入下级 UID
用法：直接运行此脚本，粘贴从浏览器复制的下级 UID（一行一个）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.database import SessionLocal
from app.models import SubordinateUID, User


def import_uids():
    print("请粘贴下级 UID（一行一个），输入空行结束:")
    uids = []
    while True:
        line = input().strip()
        if not line:
            break
        # 提取纯数字 UID（支持粘贴完整 URL 或纯数字）
        if "inviteeUid=" in line:
            import re
            match = re.search(r"inviteeUid=(\d+)", line)
            if match:
                uids.append(match.group(1))
        elif line.isdigit():
            uids.append(line)

    if not uids:
        print("未输入任何 UID")
        return

    db = SessionLocal()
    try:
        new_count = 0
        for uid in uids:
            existing = db.query(SubordinateUID).filter(SubordinateUID.uid == uid).first()
            if not existing:
                db.add(SubordinateUID(uid=uid))
                new_count += 1
        db.commit()
        print(f"导入了 {new_count} 个新 UID，共 {len(uids)} 个")

        # 更新用户状态
        subordinate_uids = set(uid[0] for uid in db.query(SubordinateUID.uid).all())
        users = db.query(User).filter(User.okx_uid != None).all()
        updated = 0
        for user in users:
            is_sub = user.okx_uid in subordinate_uids
            if user.is_subordinate != is_sub:
                user.is_subordinate = is_sub
                updated += 1
        db.commit()
        print(f"更新了 {updated} 个用户的下级状态")
    finally:
        db.close()


if __name__ == "__main__":
    import_uids()
