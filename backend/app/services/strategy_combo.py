"""策略组合管理器 - 多策略确认机制

支持：
1. 主策略 + 确认策略组合
2. 多策略投票机制
3. 市场状态过滤
4. 信号强度评估
"""
import threading
from datetime import datetime
from typing import List, Dict, Optional
from app.services.strategy import (
    BaseStrategy, get_strategy_class, 
    SIGNAL_OPEN_LONG, SIGNAL_OPEN_SHORT,
    SIGNAL_CLOSE_LONG, SIGNAL_CLOSE_SHORT,
    SIGNAL_HOLD, SIGNAL_NONE,
)
from app.services.market_regime import market_regime_detector
from app.services.logger import sys_logger


class SignalStrength:
    """信号强度评估"""
    WEAK = 1      # 单一策略
    MODERATE = 2  # 双策略确认
    STRONG = 3    # 三策略确认
    VERY_STRONG = 4  # 四策略确认


class ComboStrategy(BaseStrategy):
    """组合策略基类"""
    
    strategy_type = "combo"
    strategy_name = "组合策略"
    strategy_desc = "多策略确认，提高信号质量"
    
    default_params = {
        "primary_strategy": "trend_break",      # 主策略
        "confirm_strategies": ["rsi_macd"],     # 确认策略列表
        "confirm_threshold": 2,                  # 需要几个策略确认
        "regime_filter": True,                   # 是否启用市场状态过滤
        "min_signal_strength": SignalStrength.MODERATE,  # 最小信号强度
    }
    
    def __init__(self, params: dict = None):
        super().__init__(params)
        
        # 初始化策略实例
        self.primary_strategy = self._create_strategy(
            self.params.get("primary_strategy", "trend_break")
        )
        self.confirm_strategies = []
        for strategy_type in self.params.get("confirm_strategies", []):
            strategy = self._create_strategy(strategy_type)
            if strategy:
                self.confirm_strategies.append(strategy)
        
        self.confirm_threshold = self.params.get("confirm_threshold", 2)
        self.regime_filter = self.params.get("regime_filter", True)
        self.min_signal_strength = self.params.get("min_signal_strength", SignalStrength.MODERATE)
    
    def _create_strategy(self, strategy_type: str) -> Optional[BaseStrategy]:
        """创建策略实例"""
        strategy_cls = get_strategy_class(strategy_type)
        if strategy_cls:
            return strategy_cls(self.params)
        return None
    
    def generate_signal(self, klines: list) -> str:
        """生成组合信号"""
        if not self.primary_strategy:
            return SIGNAL_NONE
        
        # 1. 市场状态过滤
        if self.regime_filter:
            regime = market_regime_detector.detect(klines)
            if regime in ["ranging", "volatile"]:
                # 震荡市和高波动无方向市不开仓
                return SIGNAL_HOLD
        
        # 2. 主策略信号
        primary_signal = self.primary_strategy.generate_signal(klines)
        
        # 如果主策略没有信号，直接返回
        if primary_signal in [SIGNAL_NONE, SIGNAL_HOLD]:
            return primary_signal
        
        # 如果是平仓信号，直接执行（不需要确认）
        if primary_signal in [SIGNAL_CLOSE_LONG, SIGNAL_CLOSE_SHORT]:
            return primary_signal
        
        # 3. 确认策略投票
        confirm_votes = 0
        for strategy in self.confirm_strategies:
            confirm_signal = strategy.generate_signal(klines)
            
            # 同向信号才算确认
            if self._is_same_direction(primary_signal, confirm_signal):
                confirm_votes += 1
        
        # 4. 判断信号强度
        signal_strength = 1 + confirm_votes  # 主策略 + 确认票数
        
        # 5. 是否达到阈值
        if signal_strength >= self.confirm_threshold:
            # 记录信号强度
            self._log_signal(primary_signal, signal_strength, confirm_votes)
            return primary_signal
        else:
            # 未达到确认阈值，不执行
            return SIGNAL_HOLD
    
    def _is_same_direction(self, signal1: str, signal2: str) -> bool:
        """判断两个信号是否同向"""
        # 开多信号组
        long_signals = [SIGNAL_OPEN_LONG, SIGNAL_CLOSE_SHORT]
        # 开空信号组
        short_signals = [SIGNAL_OPEN_SHORT, SIGNAL_CLOSE_LONG]
        
        if signal1 in long_signals and signal2 in long_signals:
            return True
        if signal1 in short_signals and signal2 in short_signals:
            return True
        return False
    
    def _log_signal(self, signal: str, strength: int, confirm_votes: int):
        """记录信号日志"""
        signal_names = {
            SIGNAL_OPEN_LONG: "开多",
            SIGNAL_OPEN_SHORT: "开空",
            SIGNAL_CLOSE_LONG: "平多",
            SIGNAL_CLOSE_SHORT: "平空",
        }
        
        strength_names = {
            SignalStrength.WEAK: "弱",
            SignalStrength.MODERATE: "中等",
            SignalStrength.STRONG: "强",
            SignalStrength.VERY_STRONG: "极强",
        }
        
        sys_logger.info(
            "combo_strategy",
            f"[组合信号] {signal_names.get(signal, signal)} | "
            f"强度: {strength_names.get(strength, strength)} | "
            f"确认策略: {confirm_votes}/{len(self.confirm_strategies)}"
        )
    
    def get_required_klines_count(self) -> int:
        """返回需要的K线数量（取所有策略的最大值）"""
        max_count = self.primary_strategy.get_required_klines_count()
        for strategy in self.confirm_strategies:
            count = strategy.get_required_klines_count()
            if count > max_count:
                max_count = count
        return max_count


class TrendBreakComboStrategy(ComboStrategy):
    """趋势突破组合策略
    
    主策略：趋势突破（EMA + 布林带 + 成交量）
    确认策略：RSI+MACD共振
    过滤：市场状态检测
    """
    
    strategy_type = "trend_break_combo"
    strategy_name = "趋势突破组合"
    strategy_desc = "趋势突破为主，RSI+MACD确认，市场状态过滤"
    
    default_params = {
        "primary_strategy": "trend_break",
        "confirm_strategies": ["rsi_macd"],
        "confirm_threshold": 2,
        "regime_filter": True,
        "min_signal_strength": SignalStrength.MODERATE,
        
        # 主策略参数
        "ema_period": 21,
        "boll_period": 10,
        "boll_std": 1.5,
        "vol_ma_period": 10,
        
        # 确认策略参数
        "rsi_period": 6,
        "macd_fast": 6,
        "macd_slow": 26,
        "macd_signal": 9,
        
        # 止盈止损
        "take_profit_pct": 60,
        "stop_loss_pct": 35,
        "trailing_activation_pct": 50,
        "trailing_callback_pct": 25,
    }


class MultiConfirmComboStrategy(ComboStrategy):
    """多策略确认组合
    
    主策略：趋势突破
    确认策略：RSI+MACD + 均线多空排列 + SuperTrend
    需要3个策略确认才开仓
    """
    
    strategy_type = "multi_confirm_combo"
    strategy_name = "多策略确认组合"
    strategy_desc = "趋势突破为主，3个策略确认，高胜率低频交易"
    
    default_params = {
        "primary_strategy": "trend_break",
        "confirm_strategies": ["rsi_macd", "ma_ribbon", "supertrend"],
        "confirm_threshold": 3,  # 需要3个策略确认
        "regime_filter": True,
        "min_signal_strength": SignalStrength.STRONG,
        
        # 主策略参数
        "ema_period": 21,
        "boll_period": 10,
        "boll_std": 1.5,
        "vol_ma_period": 10,
        
        # 确认策略参数
        "rsi_period": 6,
        "macd_fast": 6,
        "macd_slow": 26,
        "macd_signal": 9,
        "ma_periods": "3,7,13,21",
        "st_period": 10,
        "st_multiplier": 3,
        
        # 止盈止损
        "take_profit_pct": 80,
        "stop_loss_pct": 40,
        "trailing_activation_pct": 60,
        "trailing_callback_pct": 30,
    }


class ConservativeComboStrategy(ComboStrategy):
    """保守型组合策略
    
    主策略：均线多空排列
    确认策略：RSI+MACD + 趋势突破
    只在强趋势时开仓
    """
    
    strategy_type = "conservative_combo"
    strategy_name = "保守型组合"
    strategy_desc = "均线排列为主，双重确认，只做强趋势"
    
    default_params = {
        "primary_strategy": "ma_ribbon",
        "confirm_strategies": ["rsi_macd", "trend_break"],
        "confirm_threshold": 2,
        "regime_filter": True,
        "min_signal_strength": SignalStrength.MODERATE,
        
        # 主策略参数
        "ma_periods": "3,7,13,21",
        
        # 确认策略参数
        "rsi_period": 6,
        "macd_fast": 6,
        "macd_slow": 26,
        "macd_signal": 9,
        "ema_period": 21,
        "boll_period": 10,
        "boll_std": 1.5,
        
        # 止盈止损（保守）
        "take_profit_pct": 50,
        "stop_loss_pct": 30,
        "trailing_activation_pct": 40,
        "trailing_callback_pct": 20,
    }


# 注册组合策略
COMBO_STRATEGY_REGISTRY = {
    "trend_break_combo": TrendBreakComboStrategy,
    "multi_confirm_combo": MultiConfirmComboStrategy,
    "conservative_combo": ConservativeComboStrategy,
}


def get_combo_strategy(strategy_type: str) -> Optional[type]:
    """获取组合策略类"""
    return COMBO_STRATEGY_REGISTRY.get(strategy_type)


def list_combo_strategies() -> list:
    """列出所有组合策略"""
    result = []
    for type_key, cls in COMBO_STRATEGY_REGISTRY.items():
        result.append({
            "type": type_key,
            "name": cls.strategy_name,
            "desc": cls.strategy_desc,
            "default_params": cls.default_params,
        })
    return result
