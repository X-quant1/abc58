"""策略监控路由 - 实时监控策略表现"""
from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
from sqlalchemy import func

from app.database import SessionLocal
from app.models import Strategy, Trade
from app.services.strategy import strategy_runner
from app.auth import get_current_user

router = APIRouter(prefix="/api/monitor", tags=["监控"])


@router.get("/dashboard")
async def get_monitor_dashboard(current_user: dict = Depends(get_current_user)):
    """获取监控面板数据
    
    返回：
    - 策略概览：总数、运行中、已停止
    - 今日盈亏
    - 总盈亏
    - 胜率统计
    - 持仓统计
    """
    db = SessionLocal()
    try:
        # 策略统计
        total_strategies = db.query(Strategy).filter(Strategy.published == True).count()
        running_strategies = db.query(Strategy).filter(
            Strategy.published == True,
            Strategy.enabled == True
        ).count()
        
        # 今日交易统计
        today = datetime.now().date()
        start_of_day = datetime.combine(today, datetime.min.time())
        
        today_trades = db.query(Trade).filter(
            Trade.closed_at >= start_of_day,
            Trade.pnl.isnot(None)
        ).all()
        
        today_pnl = sum(t.pnl for t in today_trades if t.pnl)
        today_trades_count = len(today_trades)
        today_win_count = len([t for t in today_trades if t.pnl and t.pnl > 0])
        today_win_rate = (today_win_count / today_trades_count * 100) if today_trades_count > 0 else 0
        
        # 总交易统计
        all_trades = db.query(Trade).filter(Trade.pnl.isnot(None)).all()
        total_pnl = sum(t.pnl for t in all_trades if t.pnl)
        total_trades_count = len(all_trades)
        total_win_count = len([t for t in all_trades if t.pnl and t.pnl > 0])
        total_win_rate = (total_win_count / total_trades_count * 100) if total_trades_count > 0 else 0
        
        # 持仓统计
        positions = []
        strategies = db.query(Strategy).filter(
            Strategy.published == True,
            Strategy.position != "none"
        ).all()
        
        for s in strategies:
            if s.position and s.position != "none":
                positions.append({
                    "strategy_id": s.id,
                    "strategy_name": s.name,
                    "position": s.position,
                    "running": strategy_runner.is_running(s.id),
                })
        
        return {
            "strategies": {
                "total": total_strategies,
                "running": running_strategies,
                "stopped": total_strategies - running_strategies,
            },
            "today": {
                "pnl": round(today_pnl, 2),
                "trades": today_trades_count,
                "win_rate": round(today_win_rate, 1),
            },
            "total": {
                "pnl": round(total_pnl, 2),
                "trades": total_trades_count,
                "win_rate": round(total_win_rate, 1),
            },
            "positions": positions,
            "position_count": len(positions),
        }
    finally:
        db.close()


@router.get("/strategies/performance")
async def get_strategies_performance(current_user: dict = Depends(get_current_user)):
    """获取所有策略的表现数据
    
    返回：
    - 策略ID、名称、状态
    - 总盈亏
    - 交易次数
    - 胜率
    - 平均持仓时间
    - 最大回撤
    """
    db = SessionLocal()
    try:
        strategies = db.query(Strategy).filter(Strategy.published == True).all()
        
        result = []
        for s in strategies:
            # 查询该策略的所有交易
            trades = db.query(Trade).filter(
                Trade.strategy_id == s.id,
                Trade.pnl.isnot(None)
            ).all()
            
            if trades:
                pnl = sum(t.pnl for t in trades if t.pnl)
                trades_count = len(trades)
                win_count = len([t for t in trades if t.pnl and t.pnl > 0])
                win_rate = (win_count / trades_count * 100) if trades_count > 0 else 0
                
                # 计算平均持仓时间
                holding_times = []
                for t in trades:
                    if t.opened_at and t.closed_at:
                        holding_time = (t.closed_at - t.opened_at).total_seconds() / 3600  # 小时
                        holding_times.append(holding_time)
                
                avg_holding_time = sum(holding_times) / len(holding_times) if holding_times else 0
                
                # 计算最大回撤（简化版：最大单笔亏损）
                max_loss = min([t.pnl for t in trades if t.pnl]) if trades else 0
            else:
                pnl = 0
                trades_count = 0
                win_rate = 0
                avg_holding_time = 0
                max_loss = 0
            
            result.append({
                "id": s.id,
                "name": s.name,
                "type": s.type,
                "enabled": s.enabled,
                "running": strategy_runner.is_running(s.id),
                "position": s.position or "none",
                "pnl": round(pnl, 2),
                "trades": trades_count,
                "win_rate": round(win_rate, 1),
                "avg_holding_time": round(avg_holding_time, 1),  # 小时
                "max_loss": round(max_loss, 2),
            })
        
        # 按盈亏排序
        result.sort(key=lambda x: x["pnl"], reverse=True)
        
        return {"strategies": result}
    finally:
        db.close()


@router.get("/strategies/{strategy_id}/trades")
async def get_strategy_trades(
    strategy_id: int,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """获取单个策略的交易记录"""
    db = SessionLocal()
    try:
        trades = db.query(Trade).filter(
            Trade.strategy_id == strategy_id
        ).order_by(Trade.created_at.desc()).limit(limit).all()
        
        return {
            "trades": [
                {
                    "id": t.id,
                    "side": t.side,
                    "size": t.size,
                    "entry_price": t.entry_price,
                    "exit_price": t.exit_price,
                    "pnl": t.pnl,
                    "opened_at": t.opened_at.isoformat() if t.opened_at else None,
                    "closed_at": t.closed_at.isoformat() if t.closed_at else None,
                }
                for t in trades
            ]
        }
    finally:
        db.close()
