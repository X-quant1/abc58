"""通知路由 - 通知历史查询与标记已读"""
from fastapi import APIRouter, Query
from typing import Optional

from app.services.notification import notification_service

router = APIRouter(prefix="/api/notifications", tags=["通知"])


@router.get("")
async def get_notifications(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    category: Optional[str] = None,
    unread_only: bool = False,
):
    """查询通知历史"""
    return notification_service.get_notifications(
        limit=limit, offset=offset, category=category, unread_only=unread_only
    )


@router.get("/unread-count")
async def get_unread_count():
    """获取未读通知数"""
    return {"count": notification_service.get_unread_count()}


@router.post("/read")
async def mark_read(id: Optional[int] = None, all: bool = False):
    """标记通知已读"""
    return notification_service.mark_read(notification_id=id, mark_all=all)
