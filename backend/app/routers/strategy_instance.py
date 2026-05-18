"""策略实例路由"""
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List

from app.database import SessionLocal
from app.models import Strategy, StrategyInstance, User
from app.services.strategy import strategy_runner, get_strategy_class
from app.services.logger import sys_logger
from app.auth import get_current_user

router = APIRouter(prefix="/api/strategy-instance", tags=["策略实例"])


class CreateInstanceRequest(BaseModel):
    strategy_id: int
    name: Optional[str] = None
    params: dict = {}


class UpdateInstanceRequest(BaseModel):
    """更新策略实例参数"""
    name: Optional[str] = None
    platform: Optional[str] = None
    inst_id: Optional[str] = None
    leverage: Optional[int] = None
    size_mode: Optional[str] = None
    size: Optional[float] = None
    size_pct: Optional[float] = None
    position_mode: Optional[str] = None
    timeframes: Optional[List[str]] = None
    run_days: Optional[List[int]] = None
    run_start_time: Optional[str] = None
    run_end_time: Optional[str] = None
    tp_mode: Optional[str] = None
    take_profit_pct: Optional[float] = None
    take_profit_points: Optional[float] = None
    sl_mode: Optional[str] = None
    stop_loss_pct: Optional[float] = None
    stop_loss_points: Optional[float] = None
    trail_mode: Optional[str] = None
    trailing_stop_pct: Optional[float] = None
    trailing_stop_points: Optional[float] = None
    trail_activate_mode: Optional[str] = None
    trail_activate_pct: Optional[float] = None
    trail_activate_points: Optional[float] = None
    trail_callback_points: Optional[float] = None
    cooldown_minutes: Optional[int] = None
    td_mode: Optional[str] = None
    description: Optional[str] = None
    settings_mode: Optional[str] = None  # 简易版/专业版模式
    params: Optional[dict] = None


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


@router.put("/{instance_id}")
async def update_instance(instance_id: int, req: UpdateInstanceRequest, current_user: dict = Depends(get_current_user)):
    """更新策略实例参数"""
    print(f"[DEBUG] update_instance called: id={instance_id}, req={req.dict(exclude_unset=True)}")
    db = SessionLocal()
    try:
        instance = db.query(StrategyInstance).filter(StrategyInstance.id == instance_id).first()
        if not instance:
            raise HTTPException(status_code=404, detail="实例不存在")

        # 解析现有参数
        params = json.loads(instance.params) if instance.params else {}

        # 更新名称
        if req.name is not None:
            instance.name = req.name

        # 更新参数
        if req.platform is not None:
            params["platform"] = req.platform
        if req.inst_id is not None:
            params["inst_id"] = req.inst_id
        if req.timeframes is not None:
            params["timeframes"] = req.timeframes
        if req.leverage is not None:
            params["leverage"] = req.leverage
        if req.size_mode is not None:
            params["size_mode"] = req.size_mode
        if req.size is not None:
            params["size"] = req.size
        if req.size_pct is not None:
            params["size_pct"] = req.size_pct
        if req.position_mode is not None:
            params["position_mode"] = req.position_mode
        if req.run_days is not None:
            params["run_days"] = req.run_days
        if req.run_start_time is not None:
            params["run_start_time"] = req.run_start_time
        if req.run_end_time is not None:
            params["run_end_time"] = req.run_end_time
        if req.tp_mode is not None:
            params["tp_mode"] = req.tp_mode
        if req.take_profit_pct is not None:
            params["take_profit_pct"] = req.take_profit_pct
        if req.take_profit_points is not None:
            params["take_profit_points"] = req.take_profit_points
        if req.sl_mode is not None:
            params["sl_mode"] = req.sl_mode
        if req.stop_loss_pct is not None:
            params["stop_loss_pct"] = req.stop_loss_pct
        if req.stop_loss_points is not None:
            params["stop_loss_points"] = req.stop_loss_points
        if req.trail_mode is not None:
            params["trail_mode"] = req.trail_mode
        if req.trailing_stop_pct is not None:
            params["trailing_stop_pct"] = req.trailing_stop_pct
        if req.trailing_stop_points is not None:
            params["trailing_stop_points"] = req.trailing_stop_points
        if req.trail_activate_mode is not None:
            params["trail_activate_mode"] = req.trail_activate_mode
        if req.trail_activate_pct is not None:
            params["trail_activate_pct"] = req.trail_activate_pct
        if req.trail_activate_points is not None:
            params["trail_activate_points"] = req.trail_activate_points
        if req.trail_callback_points is not None:
            params["trail_callback_points"] = req.trail_callback_points
        if req.cooldown_minutes is not None:
            params["cooldown_minutes"] = req.cooldown_minutes
        if req.td_mode is not None:
            params["td_mode"] = req.td_mode
        if req.description is not None:
            params["description"] = req.description
        if req.settings_mode is not None:
            params["settings_mode"] = req.settings_mode
            instance.version = req.settings_mode  # 同步版本字段
        if req.params is not None:
            params.update(req.params)

        instance.params = json.dumps(params)
        db.commit()
        sys_logger.info("strategy", f"策略参数已修改: {instance.name}", strategy_id=instance_id)
        return {"ok": True, "msg": "实例参数已更新"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
