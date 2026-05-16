"""策略实例路由"""
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List

from app.database import SessionLocal
from app.models import Strategy, StrategyInstance, User
from app.services.strategy import strategy_runner, get_strategy_class
from app.auth import get_current_user

router = APIRouter(prefix="/api/strategy-instance", tags=["策略实例"])


class CreateInstanceRequest(BaseModel):
    strategy_id: int
    name: Optional[str] = None
    params: dict = {}


@router.get("/list")
async def list_instances():
    """获取策略实例列表"""
    db = SessionLocal()
    try:
        instances = db.query(StrategyInstance).order_by(StrategyInstance.id.desc()).all()
        result = []
        for inst in instances:
            strategy = db.query(Strategy).filter(Strategy.id == inst.strategy_id).first()
            params = json.loads(inst.params) if inst.params else {}

            # 获取运行状态
            is_running = strategy_runner.is_running(inst.id)

            result.append({
                "id": inst.id,
                "strategy_id": inst.strategy_id,
                "name": inst.name,
                "params": params,
                "enabled": inst.enabled,
                "running": is_running,
                "position": inst.position,
                "type": strategy.type if strategy else "unknown",
                "type_name": get_strategy_class(strategy.type).strategy_name if strategy else "",
                "is_instance": True,
                "created_at": inst.created_at.isoformat() if inst.created_at else None,
            })
        return {"instances": result}
    finally:
        db.close()


@router.post("/create")
async def create_instance(req: CreateInstanceRequest, current_user: dict = Depends(get_current_user)):
    """基于策略模板创建实例"""
    db = SessionLocal()
    try:
        # 检查策略模板是否存在
        strategy = db.query(Strategy).filter(Strategy.id == req.strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="策略模板不存在")

        # 合并参数：模板参数 + 用户参数
        template_params = json.loads(strategy.params) if strategy.params else {}
        merged_params = {**template_params, **req.params}

        # 创建实例
        instance = StrategyInstance(
            strategy_id=req.strategy_id,
            name=req.name or f"{strategy.name}-实例",
            params=json.dumps(merged_params),
            enabled=False,
            position="none",
        )
        db.add(instance)
        db.commit()
        db.refresh(instance)

        return {"ok": True, "instance_id": instance.id}
    finally:
        db.close()


@router.post("/{instance_id}/start")
async def start_instance(instance_id: int, current_user: dict = Depends(get_current_user)):
    """启动策略实例"""
    db = SessionLocal()
    try:
        instance = db.query(StrategyInstance).filter(StrategyInstance.id == instance_id).first()
        if not instance:
            raise HTTPException(status_code=404, detail="实例不存在")

        # 更新状态
        instance.enabled = True
        db.commit()

        # 启动策略（暂时使用原有方式，后续需要改造strategy_runner支持实例）
        result = strategy_runner.start(instance_id)
        return result
    finally:
        db.close()


@router.post("/{instance_id}/stop")
async def stop_instance(instance_id: int, current_user: dict = Depends(get_current_user)):
    """停止策略实例"""
    db = SessionLocal()
    try:
        instance = db.query(StrategyInstance).filter(StrategyInstance.id == instance_id).first()
        if not instance:
            raise HTTPException(status_code=404, detail="实例不存在")

        # 更新状态
        instance.enabled = False
        db.commit()

        # 停止策略
        result = strategy_runner.stop(instance_id)
        return result
    finally:
        db.close()


@router.delete("/{instance_id}")
async def delete_instance(instance_id: int, current_user: dict = Depends(get_current_user)):
    """删除策略实例"""
    db = SessionLocal()
    try:
        instance = db.query(StrategyInstance).filter(StrategyInstance.id == instance_id).first()
        if not instance:
            raise HTTPException(status_code=404, detail="实例不存在")

        # 先停止
        if instance.enabled:
            strategy_runner.stop(instance_id)

        db.delete(instance)
        db.commit()
        return {"ok": True}
    finally:
        db.close()
