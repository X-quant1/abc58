"""量化机器人管理 API"""
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import QuantRobot, RobotTrade
from app.auth import get_current_user

router = APIRouter(prefix="/api/robots", tags=["robots"])


async def get_current_user_optional(request: Request):
    """可选认证：有 token 则解析，无 token 返回 None"""
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    try:
        return get_current_user(type("C", (), {"credentials": auth_header[7:]})())
    except:
        return None


# ─── Pydantic Schema ───

class RobotCreate(BaseModel):
    name: str = ""
    description: str = ""
    initial_capital: float = 10000.0
    size_mode: str = "fixed"
    size: float = 1.0
    size_pct: float = 10.0
    leverage: int = 10
    strategies: List = []  # 策略配置数组 [{type, params}]
    is_running: bool = False
    sort_order: int = 0


class RobotUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    initial_capital: Optional[float] = None
    size_mode: Optional[str] = None
    size: Optional[float] = None
    size_pct: Optional[float] = None
    leverage: Optional[int] = None
    strategies: Optional[List] = None
    is_running: Optional[bool] = None
    sort_order: Optional[int] = None
    active: Optional[bool] = None


class RobotToggle(BaseModel):
    is_running: bool


# ─── 辅助函数 ───

def parse_strategies(strategies_json: str) -> List[str]:
    """解析策略 JSON"""
    try:
        return json.loads(strategies_json) if strategies_json else []
    except:
        return []


def robot_to_dict(r: QuantRobot, db: Session = None) -> dict:
    """机器人对象转字典"""
    # 计算平均持仓时间
    avg_holding_hours = 0
    if db and r.trade_count > 0:
        from app.models import RobotTrade
        from datetime import datetime
        closed_trades = db.query(RobotTrade).filter(
            RobotTrade.robot_id == r.id,
            RobotTrade.status == 'closed',
            RobotTrade.opened_at.isnot(None),
            RobotTrade.closed_at.isnot(None)
        ).all()
        if closed_trades:
            total_hours = 0
            for t in closed_trades:
                delta = t.closed_at - t.opened_at
                total_hours += delta.total_seconds() / 3600
            avg_holding_hours = total_hours / len(closed_trades)

    return {
        "id": r.id,
        "name": r.name,
        "description": r.description,
        "initial_capital": r.initial_capital,
        "size_mode": r.size_mode or "fixed",
        "size": r.size or 1.0,
        "size_pct": r.size_pct or 10.0,
        "leverage": r.leverage or 10,
        "strategies": parse_strategies(r.strategies),
        "strategy_count": len(parse_strategies(r.strategies)),
        "is_running": r.is_running,
        "total_pnl": r.total_pnl,
        "current_equity": r.current_equity,
        "win_rate": r.win_rate,
        "trade_count": r.trade_count,
        "max_drawdown": r.max_drawdown,
        "avg_holding_hours": round(avg_holding_hours, 1),
        "sort_order": r.sort_order,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


# ─── API 端点 ───

@router.get("")
def list_robots(current_user: dict = Depends(get_current_user_optional), db: Session = Depends(get_db)):
    """获取所有机器人列表（公开，可选认证）"""
    robots = db.query(QuantRobot).filter(QuantRobot.active == True).order_by(QuantRobot.sort_order, QuantRobot.id).all()
    return [robot_to_dict(r, db) for r in robots]


@router.get("/{robot_id}")
def get_robot(robot_id: int, current_user: dict = Depends(get_current_user_optional), db: Session = Depends(get_db)):
    """获取单个机器人详情（公开，可选认证）"""
    robot = db.query(QuantRobot).filter(QuantRobot.id == robot_id, QuantRobot.active == True).first()
    if not robot:
        raise HTTPException(status_code=404, detail="机器人不存在")
    return robot_to_dict(robot, db)


@router.post("")
def create_robot(data: RobotCreate, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """创建机器人（仅管理员）"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可创建机器人")

    robot = QuantRobot(
        name=data.name,
        description=data.description,
        initial_capital=data.initial_capital,
        strategies=json.dumps(data.strategies),
        is_running=data.is_running,
        current_equity=data.initial_capital,
        sort_order=data.sort_order,
    )
    db.add(robot)
    db.commit()
    db.refresh(robot)
    return {"id": robot.id, "message": "创建成功"}


@router.put("/{robot_id}")
def update_robot(robot_id: int, data: RobotUpdate, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """更新机器人（仅管理员）"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可编辑机器人")

    robot = db.query(QuantRobot).filter(QuantRobot.id == robot_id).first()
    if not robot:
        raise HTTPException(status_code=404, detail="机器人不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "strategies":
            setattr(robot, key, json.dumps(value))
        else:
            setattr(robot, key, value)

    # 如果更新了初始资金且当前权益等于旧初始资金，同步更新权益
    if "initial_capital" in update_data:
        robot.current_equity = robot.initial_capital

    db.commit()
    return {"message": "更新成功"}


@router.delete("/{robot_id}")
def delete_robot(robot_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """删除机器人（软删除，仅管理员）"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可删除机器人")

    robot = db.query(QuantRobot).filter(QuantRobot.id == robot_id).first()
    if not robot:
        raise HTTPException(status_code=404, detail="机器人不存在")

    robot.active = False
    db.commit()
    return {"message": "删除成功"}


@router.post("/{robot_id}/toggle")
def toggle_robot(robot_id: int, data: RobotToggle, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """启停机器人（仅管理员）"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作机器人")

    robot = db.query(QuantRobot).filter(QuantRobot.id == robot_id).first()
    if not robot:
        raise HTTPException(status_code=404, detail="机器人不存在")

    robot.is_running = data.is_running
    db.commit()
    return {"message": f"机器人已{'启动' if data.is_running else '停止'}"}


# ─── 交易记录 API ───

@router.get("/{robot_id}/trades")
def get_robot_trades(robot_id: int, current_user: dict = Depends(get_current_user_optional), db: Session = Depends(get_db)):
    """获取机器人的交易记录（公开，可选认证）"""
    robot = db.query(QuantRobot).filter(QuantRobot.id == robot_id, QuantRobot.active == True).first()
    if not robot:
        raise HTTPException(status_code=404, detail="机器人不存在")

    trades = db.query(RobotTrade).filter(RobotTrade.robot_id == robot_id).order_by(RobotTrade.opened_at.desc()).limit(20).all()
    return [
        {
            "id": t.id,
            "strategy_type": t.strategy_type,
            "side": t.side,
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "size": t.size,
            "pnl": t.pnl,
            "status": t.status,
            "close_reason": t.close_reason or "",
            "opened_at": t.opened_at.isoformat() if t.opened_at else None,
            "closed_at": t.closed_at.isoformat() if t.closed_at else None,
        }
        for t in trades
    ]


# ─── Dashboard 专用：简要机器人数据 ───

@router.get("/dashboard/summary")
def dashboard_robot_summary(db: Session = Depends(get_db)):
    """Dashboard 专用：返回机器人简要数据（公开接口）"""
    robots = db.query(QuantRobot).filter(QuantRobot.active == True).order_by(QuantRobot.sort_order, QuantRobot.id).all()
    return [robot_to_dict(r) for r in robots]


def seed_default_robots(db: Session):
    """首次启动时创建默认的 3 个机器人"""
    from app.models import StrategyTemplate

    count = db.query(QuantRobot).count()
    if count > 0:
        return

    # 获取可用的策略类型
    templates = db.query(StrategyTemplate).filter(StrategyTemplate.published == True).order_by(StrategyTemplate.sort_order).all()
    template_types = [t.type for t in templates]

    defaults = [
        {
            "name": "趋势先锋",
            "description": "MACD背离策略，30分钟周期，高胜率趋势跟踪",
            "strategies": json.dumps([template_types[0]] if len(template_types) > 0 else ["macd_divergence"]),
            "total_pnl": 122.21,
            "current_equity": 10122.21,
            "win_rate": 94.8,
            "trade_count": 48,
            "max_drawdown": 3.2,
            "is_running": True,
            "sort_order": 1,
        },
        {
            "name": "均值猎手",
            "description": "布林带突破策略，15分钟周期，捕捉均值回归机会",
            "strategies": json.dumps([template_types[1]] if len(template_types) > 1 else ["bollinger_breakout"]),
            "total_pnl": 87.56,
            "current_equity": 10087.56,
            "win_rate": 82.3,
            "trade_count": 63,
            "max_drawdown": 5.8,
            "is_running": True,
            "sort_order": 2,
        },
        {
            "name": "动量之王",
            "description": "RSI超买超卖策略，1小时周期，捕捉大级别动量",
            "strategies": json.dumps([template_types[2]] if len(template_types) > 2 else ["rsi"]),
            "total_pnl": -23.40,
            "current_equity": 9976.60,
            "win_rate": 65.1,
            "trade_count": 35,
            "max_drawdown": 8.5,
            "is_running": False,
            "sort_order": 3,
        },
    ]

    for d in defaults:
        robot = QuantRobot(**d)
        db.add(robot)
    db.commit()
    print(f"[OK] Seeded {len(defaults)} default quant robots")
