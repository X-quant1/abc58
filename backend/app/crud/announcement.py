"""公告 CRUD 操作"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models import Announcement


class CRUDAnnouncement(CRUDBase[Announcement]):
    """公告 CRUD 操作"""

    def __init__(self):
        super().__init__(Announcement)

    def get_active(
        self,
        db: Session,
        *,
        limit: int = 10
    ) -> List[Announcement]:
        """获取当前有效的公告（启用 + 未过期）"""
        now = datetime.utcnow()
        query = db.query(Announcement).filter(
            Announcement.is_active == True
        )
        # 过滤时间范围
        query = query.filter(
            (Announcement.start_time == None) | (Announcement.start_time <= now)
        )
        query = query.filter(
            (Announcement.end_time == None) | (Announcement.end_time >= now)
        )
        return query.order_by(Announcement.sort_order, Announcement.id).limit(limit).all()

    def get_all_ordered(
        self,
        db: Session
    ) -> List[Announcement]:
        """获取所有公告（按排序）"""
        return db.query(Announcement).order_by(Announcement.sort_order, Announcement.id).all()

    def create_announcement(
        self,
        db: Session,
        *,
        title: str,
        content: str,
        color: str = "#3b82f6",
        bold: bool = False,
        sort_order: int = 1,
        is_active: bool = True,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> Announcement:
        """创建公告"""
        return self.create(db, obj_in={
            "title": title,
            "content": content,
            "color": color,
            "bold": bold,
            "sort_order": sort_order,
            "is_active": is_active,
            "start_time": start_time,
            "end_time": end_time,
        })

    def toggle_active(
        self,
        db: Session,
        *,
        announcement_id: int
    ) -> Optional[Announcement]:
        """切换启用状态"""
        ann = self.get(db, announcement_id)
        if ann:
            ann.is_active = not ann.is_active
            db.commit()
            db.refresh(ann)
        return ann
