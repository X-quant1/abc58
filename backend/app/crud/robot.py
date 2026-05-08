"""机器人相关 CRUD 操作"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.crud.base import CRUDBase
from app.models import QuantRobot, RobotTrade


class CRUDRobot(CRUDBase[QuantRobot]):
    """量化机器人 CRUD 操作"""
    
    def __init__(self):
        super().__init__(QuantRobot)
    
    def get_active(self, db: Session) -> List[QuantRobot]:
        """获取所有活跃的机器人"""
        return db.query(QuantRobot).filter(
            QuantRobot.active == True
        ).order_by(QuantRobot.sort_order).all()
    
    def get_running(self, db: Session) -> List[QuantRobot]:
        """获取所有运行中的机器人"""
        return db.query(QuantRobot).filter(
            QuantRobot.is_running == True
        ).all()
    
    def set_running(self, db: Session, *, robot_id: int, running: bool) -> Optional[QuantRobot]:
        """设置运行状态"""
        robot = self.get(db, robot_id)
        if robot:
            robot.is_running = running
            db.commit()
            db.refresh(robot)
        return robot
    
    def update_stats(
        self,
        db: Session,
        *,
        robot_id: int,
        total_pnl: float = None,
        current_equity: float = None,
        win_rate: float = None,
        trade_count: int = None,
        max_drawdown: float = None
    ) -> Optional[QuantRobot]:
        """更新机器人统计数据"""
        robot = self.get(db, robot_id)
        if robot:
            if total_pnl is not None:
                robot.total_pnl = total_pnl
            if current_equity is not None:
                robot.current_equity = current_equity
            if win_rate is not None:
                robot.win_rate = win_rate
            if trade_count is not None:
                robot.trade_count = trade_count
            if max_drawdown is not None:
                robot.max_drawdown = max_drawdown
            db.commit()
            db.refresh(robot)
        return robot


class CRUDRobotTrade(CRUDBase[RobotTrade]):
    """机器人交易记录 CRUD 操作"""
    
    def __init__(self):
        super().__init__(RobotTrade)
    
    def get_by_robot(
        self,
        db: Session,
        *,
        robot_id: int,
        limit: int = 100
    ) -> List[RobotTrade]:
        """获取机器人的交易记录"""
        return db.query(RobotTrade).filter(
            RobotTrade.robot_id == robot_id
        ).order_by(desc(RobotTrade.opened_at)).limit(limit).all()
    
    def get_open_trades(self, db: Session, *, robot_id: int) -> List[RobotTrade]:
        """获取未平仓交易"""
        return db.query(RobotTrade).filter(
            RobotTrade.robot_id == robot_id,
            RobotTrade.status == "open"
        ).all()
    
    def close_trade(
        self,
        db: Session,
        *,
        trade_id: int,
        exit_price: float,
        pnl: float,
        close_reason: str = "manual"
    ) -> Optional[RobotTrade]:
        """平仓"""
        from datetime import datetime
        trade = self.get(db, trade_id)
        if trade:
            trade.exit_price = exit_price
            trade.pnl = pnl
            trade.status = "closed"
            trade.close_reason = close_reason
            trade.closed_at = datetime.utcnow()
            db.commit()
            db.refresh(trade)
        return trade
    
    def calculate_stats(self, db: Session, *, robot_id: int) -> dict:
        """计算机器人统计数据"""
        trades = self.get_by_robot(db, robot_id=robot_id, limit=1000)
        closed_trades = [t for t in trades if t.status == "closed"]
        
        if not closed_trades:
            return {
                "total_pnl": 0,
                "win_rate": 0,
                "trade_count": 0,
                "max_drawdown": 0
            }
        
        total_pnl = sum(t.pnl for t in closed_trades)
        win_count = sum(1 for t in closed_trades if t.pnl > 0)
        win_rate = (win_count / len(closed_trades)) * 100 if closed_trades else 0
        
        # 计算最大回撤
        equity_curve = []
        current_equity = 0
        for t in closed_trades:
            current_equity += t.pnl
            equity_curve.append(current_equity)
        
        max_drawdown = 0
        peak = 0
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            drawdown = ((peak - equity) / peak * 100) if peak > 0 else 0
            max_drawdown = max(max_drawdown, drawdown)
        
        return {
            "total_pnl": total_pnl,
            "win_rate": win_rate,
            "trade_count": len(closed_trades),
            "max_drawdown": max_drawdown
        }


# 实例化（由 __init__.py 统一管理）
# crud_robot = CRUDRobot()
# crud_robot_trade = CRUDRobotTrade()
