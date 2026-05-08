"""热门活动公开接口（Dashboard 使用，无需认证）"""
import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import HotActivity, SiteConfig

router = APIRouter(prefix="/api/activities", tags=["activities"])


@router.get("")
async def get_public_activities(db: Session = Depends(get_db)):
    """获取热门活动（公开，无需认证）"""
    config = db.query(SiteConfig).filter(SiteConfig.key == "activity_banners").first()
    banners = []
    if config and config.value:
        try:
            banners = json.loads(config.value)
        except:
            banners = []

    activities = db.query(HotActivity).filter(
        HotActivity.active == True
    ).order_by(HotActivity.sort_order).all()

    return {
        "banners": banners,
        "activities": [
            {
                "id": a.id,
                "icon_url": a.icon_url,
                "title": a.title,
                "desc": a.description,
                "status": a.status_text,
                "status_type": "status-active" if "进行中" in a.status_text else (
                    "status-upcoming" if "即将" in a.status_text else "status-active"
                ),
                "badge": a.badge_label,
                "badge_type": a.badge_type,
            }
            for a in activities
        ]
    }
