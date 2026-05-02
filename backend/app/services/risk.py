"""风控服务 - 账户级风险控制

风控规则：
1. 日亏损上限：当日亏损超过阈值时，停止所有策略
2. 连续亏损停止：连续N次亏损后，停止该策略
3. 最大持仓数限制：同时最多持有N个仓位
4. 账户余额预警：余额低于阈值时发送通知
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import RiskControl, RiskEvent, Strategy, Trade
from app.services.trade_rest import get_trade_service
from app.services.logger import sys_logger


class RiskControlService:
    """风控服务"""
    
    def __init__(self):
        self._consecutive_losses = {}  # strategy_id → 连续亏损次数
        self._daily_pnl = {}  # date → 当日盈亏
        self._last_check_date = None
    
    # ─── 风控检查 ───
    
    def check_all_rules(self) -> list:
        """检查所有风控规则，返回触发的规则列表"""
        db = SessionLocal()
        triggered = []
        
        try:
            # 获取所有启用的风控规则
            rules = db.query(RiskControl).filter(RiskControl.enabled == True).all()
            
            for rule in rules:
                if self._check_rule(db, rule):
                    triggered.append(rule)
                    # 记录风控事件
                    self._log_event(db, rule.id, None, rule.rule_type, f"风控规则触发: {rule.name}")
            
            db.commit()
        finally:
            db.close()
        
        return triggered
    
    def _check_rule(self, db: Session, rule: RiskControl) -> bool:
        """检查单个规则，返回是否触发"""
        if rule.rule_type == "daily_loss":
            return self._check_daily_loss(db, rule.threshold)
        elif rule.rule_type == "consecutive_loss":
            return self._check_consecutive_loss(db, int(rule.threshold))
        elif rule.rule_type == "max_positions":
            return self._check_max_positions(db, int(rule.threshold))
        elif rule.rule_type == "balance_warning":
            return self._check_balance_warning(db, rule.threshold)
        return False
    
    # ─── 具体规则检查 ───
    
    def _check_daily_loss(self, db: Session, threshold: float) -> bool:
        """检查日亏损上限
        
        Args:
            threshold: 日亏损上限（USDT），负数表示亏损
        """
        # 计算当日盈亏
        today = datetime.now().date()
        if self._last_check_date != today:
            self._daily_pnl = {}
            self._last_check_date = today
        
        # 查询当日所有已平仓交易
        start_of_day = datetime.combine(today, datetime.min.time())
        trades = db.query(Trade).filter(
            Trade.closed_at >= start_of_day,
            Trade.pnl.isnot(None)
        ).all()
        
        daily_pnl = sum(t.pnl for t in trades if t.pnl)
        self._daily_pnl[today] = daily_pnl
        
        # 检查是否超过阈值
        if daily_pnl < -abs(threshold):  # 亏损超过阈值
            sys_logger.warning(f"风控触发: 日亏损 {daily_pnl:.2f} USDT 超过阈值 {threshold:.2f} USDT")
            # 停止所有策略
            self._stop_all_strategies(db, f"日亏损超过阈值: {daily_pnl:.2f} USDT")
            return True
        
        return False
    
    def _check_consecutive_loss(self, db: Session, max_losses: int) -> bool:
        """检查连续亏损次数
        
        Args:
            max_losses: 最大连续亏损次数
        """
        # 更新连续亏损计数
        strategies = db.query(Strategy).filter(Strategy.enabled == True).all()
        
        for strategy in strategies:
            # 查询最近的交易
            last_trade = db.query(Trade).filter(
                Trade.strategy_id == strategy.id,
                Trade.pnl.isnot(None)
            ).order_by(Trade.closed_at.desc()).first()
            
            if last_trade and last_trade.pnl and last_trade.pnl < 0:
                # 亏损
                self._consecutive_losses[strategy.id] = self._consecutive_losses.get(strategy.id, 0) + 1
            else:
                # 盈利或无交易，重置计数
                self._consecutive_losses[strategy.id] = 0
            
            # 检查是否超过阈值
            if self._consecutive_losses[strategy.id] >= max_losses:
                sys_logger.warning(f"风控触发: 策略 {strategy.name} 连续亏损 {self._consecutive_losses[strategy.id]} 次")
                # 停止该策略
                strategy.enabled = False
                self._log_event(db, None, strategy.id, "consecutive_loss", 
                              f"连续亏损 {self._consecutive_losses[strategy.id]} 次，已停止策略")
                return True
        
        return False
    
    def _check_max_positions(self, db: Session, max_positions: int) -> bool:
        """检查最大持仓数
        
        Args:
            max_positions: 最大持仓数
        """
        # 统计当前持仓数
        positions = get_trade_service().get_swap_positions()
        position_count = len([p for p in positions if p.get("pos") and float(p.get("pos", 0)) != 0])
        
        if position_count > max_positions:
            sys_logger.warning(f"风控触发: 当前持仓数 {position_count} 超过阈值 {max_positions}")
            # 记录事件，但不停止策略（由交易服务拒绝新开仓）
            return True
        
        return False
    
    def _check_balance_warning(self, db: Session, threshold: float) -> bool:
        """检查账户余额预警
        
        Args:
            threshold: 余额预警阈值（USDT）
        """
        # 获取账户余额
        from app.services.cache import get_cached_market_service
        balance_info = get_cached_market_service().get_account_balance("USDT")
        balance = balance_info.get("total_equity", 0) if balance_info else 0
        if balance and balance < threshold:
            sys_logger.warning(f"风控触发: 账户余额 {balance:.2f} USDT 低于阈值 {threshold:.2f} USDT")
            # 发送通知（TODO: 集成通知服务）
            return True
        
        return False
    
    # ─── 辅助方法 ───
    
    def _stop_all_strategies(self, db: Session, reason: str):
        """停止所有策略"""
        from app.services.strategy import strategy_runner
        
        strategies = db.query(Strategy).filter(Strategy.enabled == True).all()
        for strategy in strategies:
            strategy.enabled = False
            strategy_runner.stop(strategy.id)
            sys_logger.info(f"已停止策略 {strategy.name}: {reason}")
    
    def _log_event(self, db: Session, rule_id: Optional[int], strategy_id: Optional[int], 
                   event_type: str, description: str):
        """记录风控事件"""
        event = RiskEvent(
            rule_id=rule_id,
            strategy_id=strategy_id,
            event_type=event_type,
            description=description,
        )
        db.add(event)
    
    # ─── 规则管理 ───
    
    def create_rule(self, name: str, rule_type: str, threshold: float, enabled: bool = True) -> RiskControl:
        """创建风控规则"""
        db = SessionLocal()
        try:
            rule = RiskControl(
                name=name,
                rule_type=rule_type,
                threshold=threshold,
                enabled=enabled,
            )
            db.add(rule)
            db.commit()
            db.refresh(rule)
            return rule
        finally:
            db.close()
    
    def get_rules(self) -> list:
        """获取所有风控规则"""
        db = SessionLocal()
        try:
            return db.query(RiskControl).order_by(RiskControl.id).all()
        finally:
            db.close()
    
    def get_events(self, limit: int = 100) -> list:
        """获取风控事件日志"""
        db = SessionLocal()
        try:
            return db.query(RiskEvent).order_by(RiskEvent.created_at.desc()).limit(limit).all()
        finally:
            db.close()


# 全局风控服务实例
risk_control_service = RiskControlService()
