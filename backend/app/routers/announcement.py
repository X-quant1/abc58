"""公告管理 API"""
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.models import Announcement
from app.crud.announcement import CRUDAnnouncement

router = APIRouter(prefix="/api/announcements", tags=["announcements"])

crud_announcement = CRUDAnnouncement()


# ─── Pydantic 模型 ───

class AnnouncementCreate(BaseModel):
    """创建公告"""
    title: str = Field(..., min_length=1, max_length=100, description="公告标题")
    content: str = Field(..., min_length=1, max_length=500, description="公告内容")
    color: str = Field(default="#3b82f6", description="文字颜色（十六进制）")
    bold: bool = Field(default=False, description="是否加粗")
    sort_order: int = Field(default=1, description="排序（越小越靠前）")
    is_active: bool = Field(default=True, description="是否启用")
    start_time: Optional[datetime] = Field(default=None, description="开始时间")
    end_time: Optional[datetime] = Field(default=None, description="结束时间")


class AnnouncementUpdate(BaseModel):
    """更新公告"""
    title: Optional[str] = Field(default=None, max_length=100)
    content: Optional[str] = Field(default=None, max_length=500)
    color: Optional[str] = None
    bold: Optional[bool] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


# ─── 公开接口 ───

@router.get("/active")
async def get_active_announcements(
    db: Session = Depends(get_db),
    limit: int = 10
):
    """获取当前有效的公告（公开接口，用于轮播）"""
    announcements = crud_announcement.get_active(db, limit=limit)
    return [
        {
            "id": a.id,
            "title": a.title,
            "content": a.content,
            "color": a.color,
            "bold": a.bold,
        }
        for a in announcements
    ]


# ─── 管理接口 ───

@router.get("")
async def list_announcements(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取所有公告（管理员）"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作")

    announcements = crud_announcement.get_all_ordered(db)
    return [
        {
            "id": a.id,
            "title": a.title,
            "content": a.content,
            "color": a.color,
            "bold": a.bold,
            "sort_order": a.sort_order,
            "is_active": a.is_active,
            "start_time": a.start_time.isoformat() if a.start_time else None,
            "end_time": a.end_time.isoformat() if a.end_time else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in announcements
    ]


@router.post("")
async def create_announcement(
    data: AnnouncementCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建公告（管理员）"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作")

    announcement = crud_announcement.create_announcement(
        db,
        title=data.title,
        content=data.content,
        color=data.color,
        bold=data.bold,
        sort_order=data.sort_order,
        is_active=data.is_active,
        start_time=data.start_time,
        end_time=data.end_time,
    )
    return {"code": 0, "message": "创建成功", "data": {"id": announcement.id}}


@router.put("/{announcement_id}")
async def update_announcement(
    announcement_id: int,
    data: AnnouncementUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新公告（管理员）"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作")

    announcement = crud_announcement.get(db, announcement_id)
    if not announcement:
        raise HTTPException(status_code=404, detail="公告不存在")

    update_data = {}
    if data.title is not None:
        update_data["title"] = data.title
    if data.content is not None:
        update_data["content"] = data.content
    if data.color is not None:
        update_data["color"] = data.color
    if data.bold is not None:
        update_data["bold"] = data.bold
    if data.sort_order is not None:
        update_data["sort_order"] = data.sort_order
    if data.is_active is not None:
        update_data["is_active"] = data.is_active
    if data.start_time is not None:
        update_data["start_time"] = data.start_time
    if data.end_time is not None:
        update_data["end_time"] = data.end_time

    if update_data:
        crud_announcement.update(db, db_obj=announcement, obj_in=update_data)

    return {"code": 0, "message": "更新成功"}


@router.delete("/{announcement_id}")
async def delete_announcement(
    announcement_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除公告（管理员）"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作")

    crud_announcement.delete(db, id=announcement_id)
    return {"code": 0, "message": "删除成功"}


@router.post("/{announcement_id}/toggle")
async def toggle_announcement(
    announcement_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """切换公告启用状态（管理员）"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作")

    announcement = crud_announcement.toggle_active(db, announcement_id=announcement_id)
    if not announcement:
        raise HTTPException(status_code=404, detail="公告不存在")

    return {
        "code": 0,
        "message": f"已{'启用' if announcement.is_active else '禁用'}",
        "data": {"is_active": announcement.is_active}
    }
