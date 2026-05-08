"""策略相关 CRUD 操作"""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models import Strategy, StrategyTemplate


class CRUDStrategy(CRUDBase[Strategy]):
    """策略 CRUD 操作"""
    
    def __init__(self):
        super().__init__(Strategy)
    
    def get_by_name(self, db: Session, *, name: str) -> Optional[Strategy]:
        """根据名称获取策略"""
        return db.query(Strategy).filter(Strategy.name == name).first()
    
    def get_enabled(self, db: Session) -> List[Strategy]:
        """获取所有启用的策略"""
        return db.query(Strategy).filter(Strategy.enabled == True).all()
    
    def get_by_type(self, db: Session, *, type: str) -> List[Strategy]:
        """根据类型获取策略"""
        return db.query(Strategy).filter(Strategy.type == type).all()
    
    def set_enabled(self, db: Session, *, strategy_id: int, enabled: bool) -> Optional[Strategy]:
        """启用/禁用策略"""
        strategy = self.get(db, strategy_id)
        if strategy:
            strategy.enabled = enabled
            db.commit()
            db.refresh(strategy)
        return strategy
    
    def set_position(self, db: Session, *, strategy_id: int, position: str) -> Optional[Strategy]:
        """设置策略持仓状态"""
        strategy = self.get(db, strategy_id)
        if strategy:
            strategy.position = position
            db.commit()
            db.refresh(strategy)
        return strategy
    
    def update_params(self, db: Session, *, strategy_id: int, params: str) -> Optional[Strategy]:
        """更新策略参数"""
        strategy = self.get(db, strategy_id)
        if strategy:
            strategy.params = params
            db.commit()
            db.refresh(strategy)
        return strategy


class CRUDStrategyTemplate(CRUDBase[StrategyTemplate]):
    """策略模板 CRUD 操作"""
    
    def __init__(self):
        super().__init__(StrategyTemplate)
    
    def get_by_type(self, db: Session, *, type: str) -> Optional[StrategyTemplate]:
        """根据类型获取模板"""
        return db.query(StrategyTemplate).filter(StrategyTemplate.type == type).first()
    
    def get_published(self, db: Session) -> List[StrategyTemplate]:
        """获取所有已发布的模板"""
        return db.query(StrategyTemplate).filter(
            StrategyTemplate.published == True
        ).order_by(StrategyTemplate.sort_order).all()
    
    def set_published(self, db: Session, *, template_id: int, published: bool) -> Optional[StrategyTemplate]:
        """设置发布状态"""
        template = self.get(db, template_id)
        if template:
            template.published = published
            db.commit()
            db.refresh(template)
        return template
