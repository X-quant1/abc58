"""数据模型"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Kline(Base):
    """K线数据"""
    __tablename__ = "klines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), index=True, nullable=False)       # BTC-USDT
    timeframe = Column(String(10), nullable=False)                # 1m/5m/1h/4h/1d
    timestamp = Column(DateTime, index=True, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)


class Strategy(Base):
    """策略配置"""
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    type = Column(String(30), nullable=False)                     # ma_cross/rsi/bollinger
    params = Column(Text, nullable=False)                         # JSON 参数
    enabled = Column(Boolean, default=False)
    position = Column(String(10), default="none")                 # 当前持仓方向: none/long/short（持久化）
    published = Column(Boolean, default=True, index=True)         # 是否上架（管理员控制）
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Trade(Base):
    """交易记录"""
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(Integer, nullable=False)
    symbol = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)                     # buy/sell
    direction = Column(String(20), default="")                    # open_long/open_short/close_long/close_short
    price = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    pnl = Column(Float, default=0)
    fee = Column(Float, default=0)
    order_id = Column(String(50))
    entry_price = Column(Float, nullable=True)                    # 开仓价格
    exit_price = Column(Float, nullable=True)                     # 平仓价格
    size = Column(Float, nullable=True)                           # 仓位大小
    opened_at = Column(DateTime, nullable=True)                   # 开仓时间
    closed_at = Column(DateTime, nullable=True)                   # 平仓时间
    created_at = Column(DateTime, server_default=func.now())


class SystemLog(Base):
    """系统日志"""
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    level = Column(String(10), nullable=False, index=True)         # info/warn/error
    module = Column(String(30), nullable=False)                     # strategy/trade/market/system
    message = Column(Text, nullable=False)
    detail = Column(Text)                                           # JSON 详情
    created_at = Column(DateTime, server_default=func.now(), index=True)


class BacktestResult(Base):
    """回测结果"""
    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_name = Column(String(50), nullable=False)
    symbol = Column(String(20), nullable=False)
    timeframe = Column(String(10), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    initial_capital = Column(Float, nullable=False)
    final_capital = Column(Float, nullable=False)
    total_return = Column(Float)
    max_drawdown = Column(Float)
    sharpe_ratio = Column(Float)
    win_rate = Column(Float)
    trade_count = Column(Integer)
    params = Column(Text)                                         # JSON 参数快照
    created_at = Column(DateTime, server_default=func.now())


class Notification(Base):
    """通知记录"""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    level = Column(String(10), nullable=False, index=True)        # info/warn/error
    category = Column(String(30), nullable=False)                 # trade/strategy/system/alert
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    detail = Column(Text)                                         # JSON 详情
    channels = Column(String(100))                                # email/webhook/push
    read = Column(Boolean, default=False, index=True)             # 是否已读
    strategy_id = Column(Integer, nullable=True)                  # 关联策略ID
    created_at = Column(DateTime, server_default=func.now(), index=True)


class User(Base):
    """用户账户"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=True, index=True)
    password_hash = Column(String(128), nullable=False)
    nickname = Column(String(50))
    avatar = Column(String(200), default="")                      # 头像路径
    role = Column(String(20), default="user")                    # user/admin
    active = Column(Boolean, default=True)
    okx_uid = Column(String(50), nullable=True, index=True)      # OKX 账户ID（用户绑定）
    is_subordinate = Column(Boolean, default=False)                # 是否下级用户
    created_at = Column(DateTime, server_default=func.now())
    last_login = Column(DateTime)


class SubordinateUID(Base):
    """下级用户 UID 列表（从 OKX 邀请记录抓取）"""
    __tablename__ = "subordinate_uids"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uid = Column(String(50), unique=True, nullable=False, index=True)  # OKX UID
    created_at = Column(DateTime, server_default=func.now())


class SiteConfig(Base):
    """站点配置（key-value）"""
    __tablename__ = "site_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(50), unique=True, nullable=False, index=True)
    value = Column(Text, default="")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class StrategyTemplate(Base):
    """策略模板（管理员控制上架/下架，用户看到的策略列表）

    启动时从 STRATEGY_REGISTRY 自动同步：
    - 新增策略类型 → 自动插入模板记录
    - 已有模板 → 保留管理员编辑的名称/描述/上架状态
    """
    __tablename__ = "strategy_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(30), unique=True, nullable=False, index=True)   # 对应 STRATEGY_REGISTRY 的 key
    name = Column(String(50), nullable=False)                            # 显示名称（管理员可编辑）
    desc = Column(Text, default="")                                      # 策略描述（管理员可编辑）
    category = Column(String(20), default="single")                      # single / combined
    published = Column(Boolean, default=True, index=True)                # 是否上架
    sort_order = Column(Integer, default=0)                              # 排序（越小越靠前）
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class RiskControl(Base):
    """风控规则"""
    __tablename__ = "risk_controls"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # 规则名称
    rule_type = Column(String(50), nullable=False)  # daily_loss / consecutive_loss / max_positions / balance_warning
    threshold = Column(Float, nullable=False)  # 阈值
    enabled = Column(Boolean, default=True)  # 是否启用
    triggered_at = Column(DateTime, nullable=True)  # 最后触发时间
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 关联风控事件
    events = relationship("RiskEvent", back_populates="rule")


class RiskEvent(Base):
    """风控事件日志"""
    __tablename__ = "risk_events"
    
    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("risk_controls.id"), nullable=True)  # 关联规则
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=True)  # 关联策略
    event_type = Column(String(50), nullable=False)  # 事件类型
    description = Column(Text, nullable=False)  # 事件描述
    created_at = Column(DateTime, server_default=func.now())
    
    # 关联
    rule = relationship("RiskControl", back_populates="events")


class QuantRobot(Base):
    """量化机器人（展示用模拟账户）"""
    __tablename__ = "quant_robots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, default="")            # 机器人名称（可修改）
    description = Column(Text, default="")                            # 描述
    initial_capital = Column(Float, nullable=False, default=10000.0)  # 模拟资金(U)
    size_mode = Column(String(20), default="fixed")                   # fixed/percent
    size = Column(Float, default=1.0)                                 # 下单张数
    size_pct = Column(Float, default=10.0)                            # 仓位百分比
    leverage = Column(Integer, default=10)                            # 杠杆倍数
    strategies = Column(Text, default="[]")                            # 策略列表 JSON 数组
    is_running = Column(Boolean, default=False)                       # 是否运行中
    total_pnl = Column(Float, default=0)                              # 累计盈亏
    current_equity = Column(Float, default=10000.0)                   # 当前权益
    win_rate = Column(Float, default=0)                               # 胜率(%)
    trade_count = Column(Integer, default=0)                          # 交易次数
    max_drawdown = Column(Float, default=0)                           # 最大回撤(%)
    sort_order = Column(Integer, default=0, index=True)               # 排序
    active = Column(Boolean, default=True)                            # 是否启用
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class RobotTrade(Base):
    """机器人交易记录"""
    __tablename__ = "robot_trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    robot_id = Column(Integer, ForeignKey("quant_robots.id"), index=True, nullable=False)
    strategy_type = Column(String(30), nullable=False)                # 策略类型
    side = Column(String(10), nullable=False)                         # long/short
    entry_price = Column(Float, nullable=False)                       # 开仓价格
    exit_price = Column(Float, nullable=True)                         # 平仓价格（未平仓为 null）
    size = Column(Float, nullable=False, default=1.0)                 # 仓位大小(张)
    pnl = Column(Float, default=0)                                    # 盈亏
    status = Column(String(20), default="open")                       # open/closed
    close_reason = Column(String(20), default="")                     # 平仓原因: fixed_tp/fixed_sl/trailing/timeout/manual
    opened_at = Column(DateTime, server_default=func.now())
    closed_at = Column(DateTime, nullable=True)

    # 关联
    robot = relationship("QuantRobot", backref="trades")


class HotActivity(Base):
    """热门活动卡片（管理后台配置，Dashboard 展示）"""
    __tablename__ = "hot_activities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sort_order = Column(Integer, default=0, index=True)
    icon_url = Column(String(500), default="")
    title = Column(String(100), nullable=False, default="")
    description = Column(Text, default="")
    status_text = Column(String(50), default="")
    badge_label = Column(String(20), default="")
    badge_type = Column(String(10), default="none")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
