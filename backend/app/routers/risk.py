"""风控管理路由"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.database import SessionLocal
from app.models import RiskControl, RiskEvent, User
from app.services.risk import risk_control_service
from app.auth import get_current_user

router = APIRouter(prefix="/api/risk", tags=["风控"])


# ─── 请求模型 ───

class CreateRuleRequest(BaseModel):
    name: str
    rule_type: str  # daily_loss / consecutive_loss / max_positions / balance_warning
    threshold: float
    enabled: bool = True


class UpdateRuleRequest(BaseModel):
    name: Optional[str] = None
    threshold: Optional[float] = None
    enabled: Optional[bool] = None


# ─── 风控规则 API ───

@router.get("/rules")
async def get_rules(current_user: dict = Depends(get_current_user)):
    """获取所有风控规则"""
    db = SessionLocal()
    try:
        rules = db.query(RiskControl).order_by(RiskControl.id).all()
        return {
            "rules": [
                {
                    "id": r.id,
                    "name": r.name,
                    "rule_type": r.rule_type,
                    "threshold": r.threshold,
                    "enabled": r.enabled,
                    "triggered_at": r.triggered_at.isoformat() if r.triggered_at else None,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rules
            ]
        }
    finally:
        db.close()


@router.post("/rules")
async def create_rule(req: CreateRuleRequest, current_user: dict = Depends(get_current_user)):
    """创建风控规则（仅管理员）"""
    db = SessionLocal()
    try:
        # 检查权限
        user = db.query(User).filter(User.id == current_user["user_id"]).first()
        if not user or user.role != "admin":
            raise HTTPException(status_code=403, detail="只有管理员能创建风控规则")
        
        # 验证规则类型
        valid_types = ["daily_loss", "consecutive_loss", "max_positions", "balance_warning"]
        if req.rule_type not in valid_types:
            raise HTTPException(status_code=400, detail=f"无效的规则类型，可选: {valid_types}")
        
        # 创建规则
        rule = RiskControl(
            name=req.name,
            rule_type=req.rule_type,
            threshold=req.threshold,
            enabled=req.enabled,
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)
        
        return {
            "id": rule.id,
            "name": rule.name,
            "rule_type": rule.rule_type,
            "threshold": rule.threshold,
            "enabled": rule.enabled,
        }
    finally:
        db.close()


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: int, req: UpdateRuleRequest, current_user: dict = Depends(get_current_user)):
    """更新风控规则"""
    db = SessionLocal()
    try:
        # 检查权限
        user = db.query(User).filter(User.id == current_user["user_id"]).first()
        if not user or user.role != "admin":
            raise HTTPException(status_code=403, detail="只有管理员能修改风控规则")
        
        # 查找规则
        rule = db.query(RiskControl).filter(RiskControl.id == rule_id).first()
        if not rule:
            raise HTTPException(status_code=404, detail="规则不存在")
        
        # 更新字段
        if req.name is not None:
            rule.name = req.name
        if req.threshold is not None:
            rule.threshold = req.threshold
        if req.enabled is not None:
            rule.enabled = req.enabled
        
        db.commit()
        db.refresh(rule)
        
        return {
            "id": rule.id,
            "name": rule.name,
            "rule_type": rule.rule_type,
            "threshold": rule.threshold,
            "enabled": rule.enabled,
        }
    finally:
        db.close()


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: int, current_user: dict = Depends(get_current_user)):
    """删除风控规则"""
    db = SessionLocal()
    try:
        # 检查权限
        user = db.query(User).filter(User.id == current_user["user_id"]).first()
        if not user or user.role != "admin":
            raise HTTPException(status_code=403, detail="只有管理员能删除风控规则")
        
        # 查找并删除
        rule = db.query(RiskControl).filter(RiskControl.id == rule_id).first()
        if not rule:
            raise HTTPException(status_code=404, detail="规则不存在")
        
        db.delete(rule)
        db.commit()
        
        return {"ok": True, "msg": "规则已删除"}
    finally:
        db.close()


# ─── 风控事件 API ───

@router.get("/events")
async def get_events(limit: int = 100, current_user: dict = Depends(get_current_user)):
    """获取风控事件日志"""
    db = SessionLocal()
    try:
        events = db.query(RiskEvent).order_by(RiskEvent.created_at.desc()).limit(limit).all()
        return {
            "events": [
                {
                    "id": e.id,
                    "rule_id": e.rule_id,
                    "strategy_id": e.strategy_id,
                    "event_type": e.event_type,
                    "description": e.description,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in events
            ]
        }
    finally:
        db.close()


@router.post("/check")
async def check_rules(current_user: dict = Depends(get_current_user)):
    """手动触发风控检查"""
    db = SessionLocal()
    try:
        # 检查权限
        user = db.query(User).filter(User.id == current_user["user_id"]).first()
        if not user or user.role != "admin":
            raise HTTPException(status_code=403, detail="只有管理员能触发风控检查")
        
        # 执行检查
        triggered = risk_control_service.check_all_rules()
        
        return {
            "ok": True,
            "triggered_count": len(triggered),
            "triggered_rules": [
                {
                    "id": r.id,
                    "name": r.name,
                    "rule_type": r.rule_type,
                }
                for r in triggered
            ]
        }
    finally:
        db.close()
