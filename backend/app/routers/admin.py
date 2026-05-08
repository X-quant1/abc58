"""管理后台路由 — 运营统计 / 用户管理 / 策略管理 / 站点配置"""
import json
import uuid
import os
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text, func, desc

from app.database import SessionLocal
from app.models import User, Strategy, Trade, SystemLog, BacktestResult, Notification, SiteConfig, StrategyTemplate, HotActivity
from app.auth import get_current_user
from app.config import BASE_DIR

router = APIRouter(prefix="/api/admin", tags=["admin"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_admin(current_user: dict = Depends(get_current_user)):
    """管理员权限校验依赖"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == current_user["user_id"]).first()
        if not user or user.role != "admin":
            raise HTTPException(status_code=403, detail="需要管理员权限")
        return current_user
    finally:
        db.close()


# ═══════════════════════════════════════
# 一、运营概览
# ═══════════════════════════════════════

@router.get("/overview")
async def get_overview(_admin: dict = Depends(require_admin), db: Session = Depends(get_db)):
    """管理后台 — 运营概览"""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    # 用户统计
    total_users = db.query(func.count(User.id)).scalar() or 0
    today_new_users = db.query(func.count(User.id)).filter(
        User.created_at >= today_start
    ).scalar() or 0
    active_users_7d = db.query(func.count(User.id)).filter(
        User.last_login >= week_ago
    ).scalar() or 0
    admin_count = db.query(func.count(User.id)).filter(User.role == "admin").scalar() or 0

    # 用户列表（最近10个）
    recent_users = db.query(User).order_by(desc(User.created_at)).limit(10).all()
    users_list = [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email or "",
            "nickname": u.nickname or "",
            "role": u.role,
            "active": u.active,
            "last_login": u.last_login.isoformat() if u.last_login else "",
            "created_at": u.created_at.isoformat() if u.created_at else "",
        }
        for u in recent_users
    ]

    # 策略统计
    total_strategies = db.query(func.count(Strategy.id)).scalar() or 0
    running_strategies = db.query(func.count(Strategy.id)).filter(
        Strategy.enabled == True
    ).scalar() or 0

    # 交易统计
    total_trades = db.query(func.count(Trade.id)).scalar() or 0
    today_trades = db.query(func.count(Trade.id)).filter(
        Trade.created_at >= today_start
    ).scalar() or 0

    # 盈亏统计（所有交易）
    total_pnl = db.query(func.coalesce(func.sum(Trade.pnl), 0)).scalar() or 0
    total_fee = db.query(func.coalesce(func.sum(Trade.fee), 0)).scalar() or 0

    # 今日盈亏
    today_pnl = db.query(func.coalesce(func.sum(Trade.pnl), 0)).filter(
        Trade.created_at >= today_start
    ).scalar() or 0
    today_fee = db.query(func.coalesce(func.sum(Trade.fee), 0)).filter(
        Trade.created_at >= today_start
    ).scalar() or 0

    # 错误日志（最近24小时）
    error_count = db.query(func.count(SystemLog.id)).filter(
        SystemLog.level == "error",
        SystemLog.created_at >= now - timedelta(hours=24),
    ).scalar() or 0

    # 通知统计
    unread_notifications = db.query(func.count(Notification.id)).filter(
        Notification.read == False
    ).scalar() or 0

    return {
        "users": {
            "total": total_users,
            "today_new": today_new_users,
            "active_7d": active_users_7d,
            "admin_count": admin_count,
        },
        "strategies": {
            "total": total_strategies,
            "running": running_strategies,
        },
        "trades": {
            "total": total_trades,
            "today": today_trades,
        },
        "finance": {
            "total_pnl": round(float(total_pnl), 4),
            "total_fee": round(float(total_fee), 4),
            "today_pnl": round(float(today_pnl), 4),
            "today_fee": round(float(today_fee), 4),
        },
        "system": {
            "error_count_24h": error_count,
            "unread_notifications": unread_notifications,
        },
        "recent_users": users_list,
    }


# ═══════════════════════════════════════
# 二、用户管理
# ═══════════════════════════════════════

@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: str = Query("", description="搜索用户名/邮箱/OKX ID"),
    role: str = Query("", description="按角色过滤"),
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """管理后台 — 用户列表"""
    q = db.query(User)

    if search:
        q = q.filter(
            (User.username.contains(search)) | 
            (User.email.contains(search)) |
            (User.okx_uid.contains(search))
        )
    if role:
        q = q.filter(User.role == role)

    total = q.count()
    users = q.order_by(desc(User.created_at)).offset((page - 1) * size).limit(size).all()

    return {
        "total": total,
        "page": page,
        "size": size,
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email or "",
                "nickname": u.nickname or "",
                "role": u.role,
                "active": u.active,
                "okx_uid": u.okx_uid or "",
                "is_subordinate": getattr(u, 'is_subordinate', False),
                "last_login": u.last_login.isoformat() if u.last_login else None,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
    }


class ToggleUserRequest(BaseModel):
    user_id: int
    active: bool


@router.post("/users/toggle")
async def toggle_user(
    req: ToggleUserRequest,
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """启用/禁用用户"""
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.role == "admin":
        raise HTTPException(status_code=400, detail="不能禁用管理员")
    user.active = req.active
    db.commit()
    return {"message": f"用户已{'启用' if req.active else '禁用'}"}


class SetRoleRequest(BaseModel):
    user_id: int
    role: str = Field(..., pattern=r"^(user|admin)$")


@router.post("/users/role")
async def set_user_role(
    req: SetRoleRequest,
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """修改用户角色"""
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.role = req.role
    db.commit()
    return {"message": f"已将 {user.username} 角色设为 {req.role}"}


class SetOkxUidRequest(BaseModel):
    user_id: int
    okx_uid: str = Field(..., max_length=50)


@router.post("/users/okx-uid")
async def set_user_okx_uid(
    req: SetOkxUidRequest,
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """设置用户 OKX UID"""
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.okx_uid = req.okx_uid if req.okx_uid else None
    db.commit()
    return {"message": f"已设置 {user.username} 的 OKX UID 为 {req.okx_uid}"}


# ═══════════════════════════════════════
# 三、站点配置
# ═══════════════════════════════════════

class UpdateConfigRequest(BaseModel):
    configs: dict[str, str]  # key-value 对


@router.get("/config")
async def get_site_config(
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """获取站点配置"""
    configs = db.query(SiteConfig).all()
    result = {}
    # 预定义所有可配置项的默认值
    defaults = {
        "site_name": "BTC Quant",
        "site_slogan": "专业量化交易策略管理平台",
        "brand_headline": "专业量化交易策略管理平台",
        "brand_desc": "连接 OKX 交易所，多策略自动执行",
        "brand_footer": "© 2026 BTC Quant · 专业 · 稳定 · 安全",
        "logo_url": "",
        "allow_register": "true",
        "announcement_title": "",
        "announcement_content": "",
        "contact_email": "",
        "contact_telegram": "",
        "okx_register_url": "",
        "bitget_register_url": "",
        "htx_register_url": "",
        "agreement_title": "用户协议",
        "agreement_content": "",
    }
    for c in configs:
        result[c.key] = c.value
    # 填充缺失的默认值
    for k, v in defaults.items():
        if k not in result:
            result[k] = v
    return {"configs": result}


@router.post("/config")
async def update_site_config(
    req: UpdateConfigRequest,
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """更新站点配置"""
    updated = 0
    for key, value in req.configs.items():
        config = db.query(SiteConfig).filter(SiteConfig.key == key).first()
        if config:
            config.value = value
            config.updated_at = datetime.now(timezone.utc)
        else:
            config = SiteConfig(key=key, value=value)
            db.add(config)
        updated += 1
    db.commit()
    return {"message": f"已更新 {updated} 项配置"}


# ═══════════════════════════════════════
# 四、交易记录（管理视角）
# ═══════════════════════════════════════

@router.get("/trades")
async def admin_trades(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    days: int = Query(30, ge=1, le=365, description="最近N天"),
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """管理后台 — 交易记录"""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    q = db.query(Trade).filter(Trade.created_at >= since)
    total = q.count()

    trades = q.order_by(desc(Trade.created_at)).offset((page - 1) * size).limit(size).all()

    # 聚合统计
    stats = db.query(
        func.count(Trade.id).label("count"),
        func.coalesce(func.sum(Trade.pnl), 0).label("total_pnl"),
        func.coalesce(func.sum(Trade.fee), 0).label("total_fee"),
        func.coalesce(func.sum(Trade.amount), 0).label("total_amount"),
    ).filter(Trade.created_at >= since).first()

    return {
        "total": total,
        "page": page,
        "size": size,
        "stats": {
            "count": stats.count or 0,
            "total_pnl": round(float(stats.total_pnl), 4),
            "total_fee": round(float(stats.total_fee), 4),
            "total_amount": round(float(stats.total_amount), 4),
        },
        "trades": [
            {
                "id": t.id,
                "strategy_id": t.strategy_id,
                "symbol": t.symbol,
                "side": t.side,
                "direction": t.direction,
                "price": t.price,
                "amount": t.amount,
                "pnl": t.pnl,
                "fee": t.fee,
                "order_id": t.order_id,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in trades
        ],
    }


# ═══════════════════════════════════════
# 五、系统日志（管理视角）
# ═══════════════════════════════════════

@router.get("/logs")
async def admin_logs(
    level: str = Query("", description="info/warn/error"),
    module: str = Query("", description="strategy/trade/market/system"),
    hours: int = Query(24, ge=1, le=720, description="最近N小时"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """管理后台 — 系统日志"""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    q = db.query(SystemLog).filter(SystemLog.created_at >= since)
    if level:
        q = q.filter(SystemLog.level == level)
    if module:
        q = q.filter(SystemLog.module == module)

    total = q.count()
    logs = q.order_by(desc(SystemLog.created_at)).offset((page - 1) * size).limit(size).all()

    return {
        "total": total,
        "page": page,
        "size": size,
        "logs": [
            {
                "id": log.id,
                "level": log.level,
                "module": log.module,
                "message": log.message,
                "detail": log.detail,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
    }


# ═══════════════════════════════════════
# 六、策略实例管理（上架/下架）
# ═══════════════════════════════════════

@router.get("/strategies/list")
async def admin_list_strategies(
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """管理后台 — 策略实例列表（全部策略）"""
    from app.services.strategy import strategy_runner

    strategies = db.query(Strategy).order_by(Strategy.id).all()

    result = [
        {
            "id": s.id,
            "name": s.name,
            "type": s.type,
            "params": json.loads(s.params) if s.params else {},
            "enabled": s.enabled,
            "running": strategy_runner.is_running(s.id),
            "published": s.published,
            "position": s.position,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in strategies
    ]

    # 排序：运行中的策略在前，未启动的在后
    result.sort(key=lambda x: (not x["running"], not x["enabled"], -x["id"]))

    return {
        "strategies": result,
        "total": len(strategies),
        "published_count": sum(1 for s in strategies if s.published),
    }


class ToggleStrategyPublishRequest(BaseModel):
    strategy_id: int
    published: bool


@router.post("/strategies/publish")
async def toggle_strategy_publish(
    req: ToggleStrategyPublishRequest,
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """上架/下架策略实例
    
    - 上架时：策略保持停止状态（enabled=False）
    - 下架时：自动停止运行中的策略实例
    """
    from app.services.strategy import strategy_runner
    from app.services.ws_manager import ws_manager
    
    s = db.query(Strategy).filter(Strategy.id == req.strategy_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="策略不存在")
    
    # 如果是上架操作，确保策略是停止状态
    if req.published:
        # 上架时策略默认停止
        s.enabled = False
    
    # 如果是下架操作，不停止运行中的策略，让它继续运行
    # 用户在Strategy页面可以看到运行中的已下架策略，手动停止后才会消失
    
    s.published = req.published
    db.commit()
    
    # WebSocket推送策略状态更新
    ws_manager.broadcast_sync("strategy_status", {
        "strategy_id": req.strategy_id,
        "running": strategy_runner.is_running(req.strategy_id),
        "enabled": s.enabled,
        "published": s.published,
    })
    
    action = "上架" if req.published else "下架"
    still_running = "（策略仍在运行，需手动停止）" if not req.published and strategy_runner.is_running(req.strategy_id) else ""
    return {"message": f"策略「{s.name}」已{action}{still_running}"}


@router.post("/strategies/publish-all")
async def publish_all_strategies(
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """全部上架（策略默认停止状态）"""
    db.query(Strategy).update({Strategy.published: True, Strategy.enabled: False})
    db.commit()
    return {"message": "已全部上架（策略默认停止）"}


@router.post("/strategies/unpublish-all")
async def unpublish_all_strategies(
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """全部下架（会自动停止所有运行中的策略）"""
    from app.services.strategy import strategy_runner
    import time
    
    # 获取所有运行中的策略
    running_status = strategy_runner.get_running_status()
    stopped_count = 0
    
    # 停止所有运行中的策略
    for strategy_id, status in running_status.items():
        if status["running"]:
            strategy_runner.stop(strategy_id)
            stopped_count += 1
    
    # 等待所有策略停止（最多等待10秒）
    if stopped_count > 0:
        for _ in range(100):
            still_running = sum(1 for s in strategy_runner.get_running_status().values() if s["running"])
            if still_running == 0:
                break
            time.sleep(0.1)
    
    # 批量下架并禁用
    db.query(Strategy).update({Strategy.published: False, Strategy.enabled: False})
    db.commit()
    
    msg = "已全部下架"
    if stopped_count > 0:
        msg += f"（已停止 {stopped_count} 个运行中的策略）"
    return {"message": msg}


# ═══════════════════════════════════════
# 八、热门活动管理
# ═══════════════════════════════════════

@router.get("/activities")
async def get_activities(
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """获取热门活动配置"""
    banner = db.query(SiteConfig).filter(SiteConfig.key == "activity_banners").first()
    banners = []
    if banner and banner.value:
        try:
            import json
            banners = json.loads(banner.value)
        except:
            banners = []
    
    activities = db.query(HotActivity).order_by(HotActivity.sort_order).all()
    return {
        "banners": banners,
        "activities": [
            {
                "id": a.id,
                "sort_order": a.sort_order,
                "icon_url": a.icon_url,
                "title": a.title,
                "description": a.description,
                "status_text": a.status_text,
                "badge_label": a.badge_label,
                "badge_type": a.badge_type,
                "active": a.active,
            }
            for a in activities
        ]
    }


class ActivityCardData(BaseModel):
    id: int | None = None
    sort_order: int = 0
    icon_url: str = ""
    title: str = ""
    description: str = ""
    status_text: str = ""
    badge_label: str = ""
    badge_type: str = "none"
    active: bool = True


class BannerItem(BaseModel):
    url: str = ""
    link: str = ""


class SaveActivitiesRequest(BaseModel):
    banners: list[BannerItem] = []
    activities: list[ActivityCardData]


@router.post("/activities/save")
async def save_activities(
    req: SaveActivitiesRequest,
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """保存热门活动配置"""
    import json
    # 保存横幅列表
    banners_json = json.dumps([b.model_dump() for b in req.banners], ensure_ascii=False)
    banner = db.query(SiteConfig).filter(SiteConfig.key == "activity_banners").first()
    if banner:
        banner.value = banners_json
        banner.updated_at = datetime.now(timezone.utc)
    else:
        db.add(SiteConfig(key="activity_banners", value=banners_json))

    # 保存活动卡片
    for card_data in req.activities:
        if card_data.id:
            card = db.query(HotActivity).filter(HotActivity.id == card_data.id).first()
        else:
            card = None
        if card:
            card.sort_order = card_data.sort_order
            card.icon_url = card_data.icon_url
            card.title = card_data.title
            card.description = card_data.description
            card.status_text = card_data.status_text
            card.badge_label = card_data.badge_label
            card.badge_type = card_data.badge_type
            card.active = card_data.active
            card.updated_at = datetime.now(timezone.utc)
        else:
            db.add(HotActivity(
                sort_order=card_data.sort_order,
                icon_url=card_data.icon_url,
                title=card_data.title,
                description=card_data.description,
                status_text=card_data.status_text,
                badge_label=card_data.badge_label,
                badge_type=card_data.badge_type,
                active=card_data.active,
            ))

    db.commit()
    return {"message": "活动配置已保存"}


@router.post("/activities/upload")
async def upload_activity_image(
    file: UploadFile = File(...),
    _admin: dict = Depends(require_admin),
):
    """上传活动图片"""
    # 验证文件类型
    allowed_types = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="仅支持 PNG/JPEG/GIF/WEBP/SVG 图片格式")

    # 生成唯一文件名
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "png"
    filename = f"{uuid.uuid4().hex}.{ext}"

    # 保存文件
    upload_dir = BASE_DIR / "static" / "uploads" / "activities"
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / filename
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="图片大小不能超过 5MB")
    with open(file_path, "wb") as f:
        f.write(content)

    url = f"/static/uploads/activities/{filename}"
    return {"url": url, "filename": filename}
