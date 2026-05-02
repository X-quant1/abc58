"""策略管理路由"""
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List

from app.database import SessionLocal
from app.models import Strategy, Trade, StrategyTemplate, User
from app.services.strategy import (
    strategy_runner, list_available_strategies, get_strategy_class,
    STRATEGY_REGISTRY,
)
from app.auth import get_current_user_optional, get_current_user

router = APIRouter(prefix="/api/strategy", tags=["策略"])


# ─── 请求模型 ───

class CreateStrategyRequest(BaseModel):
    name: str
    type: str                           # ma_cross / rsi / bollinger
    params: dict = {}
    inst_id: str = "BTC-USDT-SWAP"      # 交易对
    size_mode: str = "fixed"             # fixed=固定张数 / percent=仓位百分比
    size: float = 1                        # 每次下单合约张数（size_mode=fixed，支持0.01）
    size_pct: float = 10                 # 仓位百分比（size_mode=percent，如10=10%）
    leverage: int = 10                   # 杠杆倍数
    take_profit_pct: float = 3           # 固定止盈百分比（默认3%）
    stop_loss_pct: float = 5             # 固定止损百分比（默认5%）
    trailing_stop_pct: float = 1.5       # 移动止损回调比例（默认1.5%）
    trail_activate_pct: float = 0        # 移动止盈激活百分比
    trail_callback_points: float = 0     # 移动止盈回调点数
    cooldown_minutes: int = 0            # 冷却时间（分钟）
    td_mode: str = "cross"              # 保证金模式 cross/isolated（默认全仓）
    timeframes: List[str] = ["1h"]      # 运行周期（支持多选）
    use_regime_filter: bool = True      # 是否启用市场状态过滤
    description: str = ""               # 策略描述


class UpdateStrategyRequest(BaseModel):
    name: Optional[str] = None
    params: Optional[dict] = None
    inst_id: Optional[str] = None
    size_mode: Optional[str] = None
    size: Optional[float] = None
    size_pct: Optional[float] = None
    leverage: Optional[int] = None
    take_profit_pct: Optional[float] = None
    stop_loss_pct: Optional[float] = None
    trailing_stop_pct: Optional[float] = None
    trail_activate_pct: Optional[float] = None
    trail_callback_points: Optional[float] = None
    cooldown_minutes: Optional[int] = None
    td_mode: Optional[str] = None
    timeframes: Optional[List[str]] = None
    description: Optional[str] = None


# ─── 可用策略 ───

@router.get("/available")
async def get_available_strategies():
    """获取所有可用策略类型（只返回已上架的策略模板）"""
    db = SessionLocal()
    try:
        # 从数据库读取已上架的策略模板
        templates = db.query(StrategyTemplate).filter(
            StrategyTemplate.published == True
        ).order_by(StrategyTemplate.sort_order, StrategyTemplate.id).all()

        result = []
        for tpl in templates:
            # 从 STRATEGY_REGISTRY 获取默认参数
            cls = STRATEGY_REGISTRY.get(tpl.type)
            default_params = cls.default_params if cls else {}
            result.append({
                "type": tpl.type,
                "name": tpl.name,
                "desc": tpl.desc or "",
                "default_params": default_params,
            })
        return {"strategies": result}
    finally:
        db.close()


# ─── 策略 CRUD ───

@router.get("/list")
async def list_strategies(current_user: dict | None = Depends(get_current_user_optional)):
    """获取策略列表
    
    规则：
    - 已上架的策略：所有用户可见
    - 已下架的策略：仅对已启用/运行该策略的用户可见，并显示警告提示
    - 管理员在 Strategy 页面也遵循相同规则（Admin 页面有专门的策略管理）
    """
    db = SessionLocal()
    try:
        # 判断是否是管理员
        is_admin = False
        user_id = None
        if current_user:
            user = db.query(User).filter(User.id == current_user["user_id"]).first()
            is_admin = user and user.role == "admin"
            user_id = current_user["user_id"]

        # 查询所有策略
        strategies = db.query(Strategy).order_by(Strategy.id.desc()).all()

        result = []
        for s in strategies:
            # 跳过下架策略的判断逻辑（管理员和普通用户规则一致）
            if not s.published:
                # 只有已启用或运行中的策略才可见
                is_running = strategy_runner.is_running(s.id)
                if not s.enabled and not is_running:
                    continue  # 跳过未启用且未运行的下架策略

            params = json.loads(s.params) if s.params else {}
            # 获取策略类型信息
            cls = get_strategy_class(s.type)
            type_name = cls.strategy_name if cls else s.type
            type_desc = cls.strategy_desc if cls else ""

            # 判断是否需要显示下架警告
            unpublished_warning = None
            if not s.published:
                unpublished_warning = "该策略已被管理员下架，请谨慎运行"

            result.append({
                "id": s.id,
                "name": s.name,
                "type": s.type,
                "type_name": type_name,
                "type_desc": type_desc,
                "params": params,
                "enabled": s.enabled,
                "running": strategy_runner.is_running(s.id),
                "position": s.position or "none",
                "published": s.published,
                "unpublished_warning": unpublished_warning,
                "created_at": s.created_at.isoformat() if s.created_at else "",
                "updated_at": s.updated_at.isoformat() if s.updated_at else "",
            })
        
        # 排序：运行中的策略在前，未启动的在后
        result.sort(key=lambda x: (not x["running"], not x["enabled"], -x["id"]))
        
        return {"strategies": result, "is_admin": is_admin}
    finally:
        db.close()


@router.post("/create")
async def create_strategy(req: CreateStrategyRequest, current_user: dict = Depends(get_current_user)):
    """创建策略（仅管理员）"""
    db = SessionLocal()
    try:
        # 检查是否是管理员
        user = db.query(User).filter(User.id == current_user["user_id"]).first()
        if not user or user.role != "admin":
            raise HTTPException(status_code=403, detail="只有管理员能创建策略")

        # 验证策略类型
        if req.type not in STRATEGY_REGISTRY:
            raise HTTPException(status_code=400, detail=f"unknown strategy type: {req.type}")

        # 合并参数：策略参数 + 交易参数
        full_params = {
            **req.params,
            "inst_id": req.inst_id,
            "size_mode": req.size_mode,
            "size": req.size,
            "size_pct": req.size_pct,
            "leverage": req.leverage,
            "take_profit_pct": req.take_profit_pct,
            "stop_loss_pct": req.stop_loss_pct,
            "trailing_stop_pct": req.trailing_stop_pct,
            "trail_activate_pct": req.trail_activate_pct,
            "trail_callback_points": req.trail_callback_points,
            "cooldown_minutes": req.cooldown_minutes,
            "td_mode": req.td_mode,
            "timeframes": req.timeframes,
            "use_regime_filter": req.use_regime_filter,
            "description": req.description,
        }

        strategy = Strategy(
            name=req.name,
            type=req.type,
            params=json.dumps(full_params),
            enabled=False,
            position="none",
            published=True,  # 管理员创建的策略默认上架
        )
        db.add(strategy)
        db.commit()
        db.refresh(strategy)
        return {"ok": True, "id": strategy.id, "msg": "strategy created"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.put("/{strategy_id}")
async def update_strategy(strategy_id: int, req: UpdateStrategyRequest):
    """更新策略配置"""
    db = SessionLocal()
    try:
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="strategy not found")

        params = json.loads(strategy.params) if strategy.params else {}

        if req.name is not None:
            strategy.name = req.name
        if req.params is not None:
            params.update(req.params)
        if req.inst_id is not None:
            params["inst_id"] = req.inst_id
        if req.size_mode is not None:
            params["size_mode"] = req.size_mode
        if req.size is not None:
            params["size"] = req.size
        if req.size_pct is not None:
            params["size_pct"] = req.size_pct
        if req.leverage is not None:
            params["leverage"] = req.leverage
        if req.take_profit_pct is not None:
            params["take_profit_pct"] = req.take_profit_pct
        if req.stop_loss_pct is not None:
            params["stop_loss_pct"] = req.stop_loss_pct
        if req.trailing_stop_pct is not None:
            params["trailing_stop_pct"] = req.trailing_stop_pct
        if req.trail_activate_pct is not None:
            params["trail_activate_pct"] = req.trail_activate_pct
        if req.trail_callback_points is not None:
            params["trail_callback_points"] = req.trail_callback_points
        if req.cooldown_minutes is not None:
            params["cooldown_minutes"] = req.cooldown_minutes
        if req.td_mode is not None:
            params["td_mode"] = req.td_mode
        if req.timeframes is not None:
            params["timeframes"] = req.timeframes
        if req.description is not None:
            params["description"] = req.description

        strategy.params = json.dumps(params)
        db.commit()
        return {"ok": True, "msg": "strategy updated"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.delete("/{strategy_id}")
async def delete_strategy(strategy_id: int):
    """删除策略"""
    if strategy_runner.is_running(strategy_id):
        raise HTTPException(status_code=400, detail="cannot delete running strategy, stop it first")

    db = SessionLocal()
    try:
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="strategy not found")
        db.delete(strategy)
        db.commit()
        return {"ok": True, "msg": "strategy deleted"}
    finally:
        db.close()


# ─── 策略运行控制 ───

@router.post("/{strategy_id}/start")
async def start_strategy(strategy_id: int):
    """启动策略"""
    result = strategy_runner.start(strategy_id)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["msg"])
    return result


@router.post("/{strategy_id}/stop")
async def stop_strategy(strategy_id: int):
    """停止策略"""
    result = strategy_runner.stop(strategy_id)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["msg"])
    
    # WebSocket推送策略状态更新
    from app.services.ws_manager import ws_manager
    from app.database import SessionLocal
    from app.models import Strategy
    
    db = SessionLocal()
    try:
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if strategy:
            ws_manager.broadcast_sync("strategy_status", {
                "strategy_id": strategy_id,
                "running": False,
                "enabled": False,
                "published": strategy.published,
                "position": strategy.position,
            })
    finally:
        db.close()
    
    return result


@router.get("/status")
async def get_running_status():
    """获取所有运行中策略的状态"""
    return {"status": strategy_runner.get_running_status()}


# ─── 策略交易记录 ───

@router.get("/{strategy_id}/trades")
async def get_strategy_trades(strategy_id: int, limit: int = 50):
    """获取策略的交易记录"""
    db = SessionLocal()
    try:
        trades = db.query(Trade).filter(
            Trade.strategy_id == strategy_id
        ).order_by(Trade.id.desc()).limit(limit).all()
        result = []
        for t in trades:
            result.append({
                "id": t.id,
                "symbol": t.symbol,
                "side": t.side,
                "direction": t.direction or "",
                "price": t.price,
                "amount": t.amount,
                "pnl": t.pnl,
                "fee": t.fee,
                "order_id": t.order_id,
                "created_at": t.created_at.isoformat() if t.created_at else "",
            })
        return {"trades": result}
    finally:
        db.close()
