"""交易相关 CRUD 操作"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.crud.base import CRUDBase
from app.models import Trade


class CRUDTrade(CRUDBase[Trade]):
    """交易 CRUD 操作"""
    
    def __init__(self):
        super().__init__(Trade)
    
    def get_by_strategy(
        self, 
        db: Session, 
        *, 
        strategy_id: int,
        limit: int = 100
    ) -> List[Trade]:
        """获取策略的交易记录"""
        return db.query(Trade).filter(
            Trade.strategy_id == strategy_id
        ).order_by(desc(Trade.created_at)).limit(limit).all()
    
    def get_open_trades(self, db: Session, *, strategy_id: int) -> List[Trade]:
        """获取策略的未平仓交易"""
        return db.query(Trade).filter(
            Trade.strategy_id == strategy_id,
            Trade.closed_at == None
        ).all()
    
    def get_recent_trades(
        self, 
        db: Session, 
        *, 
        limit: int = 100
    ) -> List[Trade]:
        """获取最近的交易记录"""
        return db.query(Trade).order_by(
            desc(Trade.created_at)
        ).limit(limit).all()
    
    def close_trade(
        self,
        db: Session,
        *,
        trade_id: int,
        exit_price: float,
        pnl: float,
        fee: float = 0
    ) -> Optional[Trade]:
        """平仓"""
        trade = self.get(db, trade_id)
        if trade:
            trade.exit_price = exit_price
            trade.pnl = pnl
            trade.fee = fee
            trade.closed_at = datetime.utcnow()
            db.commit()
            db.refresh(trade)
        return trade
    
    def calculate_pnl(
        self,
        db: Session,
        *,
        strategy_id: int
    ) -> float:
        """计算策略总盈亏"""
        trades = db.query(Trade).filter(
            Trade.strategy_id == strategy_id,
            Trade.closed_at != None
        ).all()
        return sum(t.pnl - t.fee for t in trades)
    
    def count_trades(
        self,
        db: Session,
        *,
        strategy_id: int,
        side: str = None
    ) -> int:
        """统计交易次数"""
        query = db.query(Trade).filter(Trade.strategy_id == strategy_id)
        if side:
            query = query.filter(Trade.side == side)
        return query.count()
