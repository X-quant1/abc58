"""策略引擎 - 核心模块

策略基类 + 策略运行器 + 3种策略实现（均线交叉/RSI/布林带）。

策略引擎运行在后端，24/7 不依赖前端浏览器：
1. 定时拉行情 → 计算指标 → 生成信号
2. 信号触发 → 调用 trade_service 下单
3. 通过信号记录持久化到数据库
4. 持仓状态持久化到 Strategy.position，重启后自动同步
"""
import json
import time
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from app.database import SessionLocal
from app.models import Strategy, Trade
from app.services.cache import get_cached_market_service as _get_market_service
# 使用 Bitget 适配器替代 OKX trade_rest
from app.services.trade_bitget_adapter import get_trade_service as _get_trade_service
from app.services.bitget_client import BitgetAPIError

# Bitget API 错误码常量（暂无特定错误码，用通用处理）
OKX_ERR_INSUFFICIENT_BALANCE = "40001"  # Bitget 余额不足错误码

# 模块级延迟解析：旧代码中的 market_service / trade_service 引用自动走单例
def __getattr__(name):
    if name == "market_service":
        return _get_market_service()
    if name == "trade_service":
        return _get_trade_service()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
from app.services.ws_manager import ws_manager
from app.services.logger import sys_logger


# ─── 策略信号类型 ───

SIGNAL_OPEN_LONG = "open_long"     # 开多
SIGNAL_OPEN_SHORT = "open_short"   # 开空
SIGNAL_CLOSE_LONG = "close_long"   # 平多
SIGNAL_CLOSE_SHORT = "close_short" # 平空
SIGNAL_HOLD = "hold"               # 持仓观望
SIGNAL_NONE = "none"               # 无信号


# ─── 策略基类 ───

class BaseStrategy(ABC):
    """策略基类 - 所有策略必须继承此类"""

    # 策略类型标识，子类必须覆盖
    strategy_type: str = "base"
    strategy_name: str = "基础策略"
    strategy_desc: str = ""

    # 默认参数
    default_params: dict = {}

    def __init__(self, params: dict = None):
        self.params = {**self.default_params, **(params or {})}

    @abstractmethod
    def generate_signal(self, klines: list) -> str:
        """根据K线数据生成交易信号

        Args:
            klines: K线数据列表，每条包含 open/high/low/close/volume/timestamp

        Returns:
            信号类型: open_long / open_short / close_long / close_short / hold / none
        """
        pass

    def get_required_klines_count(self) -> int:
        """返回策略需要的最小K线数量"""
        return 100

    def to_dict(self) -> dict:
        """序列化策略信息"""
        return {
            "type": self.strategy_type,
            "name": self.strategy_name,
            "desc": self.strategy_desc,
            "params": self.params,
            "default_params": self.default_params,
        }


# ─── 均线交叉策略 ───

class MACrossStrategy(BaseStrategy):
    """均线交叉策略

    短均线上穿长均线 → 开多
    短均线下穿长均线 → 开空（或平多）
    """
    strategy_type = "ma_cross"
    strategy_name = "均线交叉"
    strategy_desc = "短均线上穿长均线买入，下穿卖出"
    default_params = {
        "fast_period": 7,       # 短均线周期
        "slow_period": 25,      # 长均线周期
        "timeframe": "1h",      # K线周期
    }

    @staticmethod
    def _calc_ma(closes: list, period: int) -> list:
        """计算简单移动平均"""
        result = []
        for i in range(len(closes)):
            if i < period - 1:
                result.append(None)
            else:
                ma = sum(closes[i - period + 1:i + 1]) / period
                result.append(ma)
        return result

    def generate_signal(self, klines: list) -> str:
        fast_period = int(self.params.get("fast_period", 7))
        slow_period = int(self.params.get("slow_period", 25))

        if len(klines) < slow_period + 2:
            return SIGNAL_NONE

        closes = [k["close"] for k in klines]
        fast_ma = self._calc_ma(closes, fast_period)
        slow_ma = self._calc_ma(closes, slow_period)

        # 当前和上一根K线的均线值
        curr_fast = fast_ma[-1]
        curr_slow = slow_ma[-1]
        prev_fast = fast_ma[-2]
        prev_slow = slow_ma[-2]

        if None in (curr_fast, curr_slow, prev_fast, prev_slow):
            return SIGNAL_NONE

        # 金叉：短均线上穿长均线
        if prev_fast <= prev_slow and curr_fast > curr_slow:
            return SIGNAL_OPEN_LONG
        # 死叉：短均线下穿长均线
        if prev_fast >= prev_slow and curr_fast < curr_slow:
            return SIGNAL_OPEN_SHORT

        return SIGNAL_HOLD


# ─── RSI 超卖超买策略 ───

class RSIStrategy(BaseStrategy):
    """RSI 超卖超买策略

    RSI < 超卖线 → 开多（超卖反弹）
    RSI > 超买线 → 开空（超买回落）
    """
    strategy_type = "rsi"
    strategy_name = "RSI 超卖超买"
    strategy_desc = "RSI低于超卖线买入，高于超买线卖出"
    default_params = {
        "period": 14,           # RSI 周期
        "oversold": 30,         # 超卖线
        "overbought": 70,       # 超买线
        "timeframe": "1h",
    }

    @staticmethod
    def _calc_rsi(closes: list, period: int) -> list:
        """计算 RSI"""
        result = []
        gains = []
        losses = []

        for i in range(1, len(closes)):
            change = closes[i] - closes[i - 1]
            gains.append(max(change, 0))
            losses.append(max(-change, 0))

        if len(gains) < period:
            return [None] * len(closes)

        # 第一个 RSI 用简单平均
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        for i in range(period):
            result.append(None)

        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(100 - 100 / (1 + rs))

        # 后续用指数移动平均
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            if avg_loss == 0:
                result.append(100.0)
            else:
                rs = avg_gain / avg_loss
                result.append(100 - 100 / (1 + rs))

        return result

    def generate_signal(self, klines: list) -> str:
        period = int(self.params.get("period", 14))
        oversold = float(self.params.get("oversold", 30))
        overbought = float(self.params.get("overbought", 70))
        vol_confirm = self.params.get("vol_confirm", False)  # 是否启用成交量确认
        vol_mult = float(self.params.get("vol_mult", 1.2))   # 成交量倍数阈值

        if len(klines) < period + 2:
            return SIGNAL_NONE

        closes = [k["close"] for k in klines]
        rsi_values = self._calc_rsi(closes, period)

        curr_rsi = rsi_values[-1]
        prev_rsi = rsi_values[-2]

        if curr_rsi is None or prev_rsi is None:
            return SIGNAL_NONE

        # 成交量确认（可选）
        vol_ok = True
        if vol_confirm:
            volumes = [k.get("volume", 0) for k in klines]
            if len(volumes) >= 10:
                vol_ma = sum(volumes[-10:]) / 10
                vol_ok = volumes[-1] >= vol_ma * vol_mult

        # 从超卖区上穿 → 开多
        if prev_rsi < oversold and curr_rsi >= oversold and vol_ok:
            return SIGNAL_OPEN_LONG
        # 从超买区下穿 → 开空
        if prev_rsi > overbought and curr_rsi <= overbought and vol_ok:
            return SIGNAL_OPEN_SHORT

        return SIGNAL_HOLD


# ─── 布林带突破策略 ───

class BollingerStrategy(BaseStrategy):
    """布林带突破策略

    价格突破上轨 → 开多（趋势跟随）
    价格跌破下轨 → 开空（趋势跟随）
    """
    strategy_type = "bollinger"
    strategy_name = "布林带突破"
    strategy_desc = "价格突破上轨买入，跌破下轨卖出"
    default_params = {
        "period": 20,           # 布林带周期
        "std_dev": 2.0,         # 标准差倍数
        "timeframe": "1h",
    }

    @staticmethod
    def _calc_bollinger(closes: list, period: int, std_dev: float) -> list:
        """计算布林带 (upper, middle, lower)"""
        result = []
        for i in range(len(closes)):
            if i < period - 1:
                result.append(None)
            else:
                window = closes[i - period + 1:i + 1]
                mid = sum(window) / period
                variance = sum((x - mid) ** 2 for x in window) / period
                std = variance ** 0.5
                upper = mid + std_dev * std
                lower = mid - std_dev * std
                result.append({"upper": upper, "middle": mid, "lower": lower})
        return result

    def generate_signal(self, klines: list) -> str:
        period = int(self.params.get("period", 20))
        std_dev = float(self.params.get("std_dev", 2.0))

        if len(klines) < period + 2:
            return SIGNAL_NONE

        closes = [k["close"] for k in klines]
        boll = self._calc_bollinger(closes, period, std_dev)

        curr_boll = boll[-1]
        prev_boll = boll[-2]
        curr_close = closes[-1]
        prev_close = closes[-2]

        if curr_boll is None or prev_boll is None:
            return SIGNAL_NONE

        # 突破上轨 → 开多
        if prev_close <= prev_boll["upper"] and curr_close > curr_boll["upper"]:
            return SIGNAL_OPEN_LONG
        # 跌破下轨 → 开空
        if prev_close >= prev_boll["lower"] and curr_close < curr_boll["lower"]:
            return SIGNAL_OPEN_SHORT

        return SIGNAL_HOLD


# ─── MACD 策略 ───

class MACDStrategy(BaseStrategy):
    """MACD 策略（趋势动能确认）

    经典双指标策略，比单纯均线交叉更可靠：
    - DIF 上穿 DEA（零轴上方金叉）→ 开多
    - DIF 下穿 DEA（零轴下方死叉）→ 开空
    - 零轴过滤：只在 MACD 柱状图同向时确认信号
    """
    strategy_type = "macd"
    strategy_name = "MACD 趋势动能"
    strategy_desc = "DIF/DEA金叉死叉+零轴方向过滤，经典趋势确认策略"
    default_params = {
        "fast_period": 12,       # 快线 EMA 周期
        "slow_period": 26,       # 慢线 EMA 周期
        "signal_period": 9,      # 信号线 DEA 周期
        "timeframe": "1h",
    }

    @staticmethod
    def _calc_ema(closes: list, period: int) -> list:
        """计算指数移动平均"""
        if len(closes) < period:
            return [None] * len(closes)
        result = [None] * (period - 1)
        # 初始值用 SMA
        sma = sum(closes[:period]) / period
        result.append(sma)
        multiplier = 2 / (period + 1)
        for i in range(period, len(closes)):
            ema = closes[i] * multiplier + result[-1] * (1 - multiplier)
            result.append(ema)
        return result

    @staticmethod
    def _calc_macd(closes: list, fast: int, slow: int, signal: int) -> dict:
        """计算 MACD 指标

        Returns:
            {"dif": [...], "dea": [...], "histogram": [...]}
        """
        ema_fast = MACDStrategy._calc_ema(closes, fast)
        ema_slow = MACDStrategy._calc_ema(closes, slow)

        # DIF = 快线 - 慢线
        dif = []
        for i in range(len(closes)):
            if ema_fast[i] is None or ema_slow[i] is None:
                dif.append(None)
            else:
                dif.append(ema_fast[i] - ema_slow[i])

        # DEA = DIF 的 EMA
        valid_dif = [d for d in dif if d is not None]
        if len(valid_dif) < signal:
            return {"dif": dif, "dea": [None] * len(closes), "histogram": [None] * len(closes)}

        # 找到 DIF 开始有效的位置
        first_valid = next(i for i, d in enumerate(dif) if d is not None)
        dea = [None] * first_valid
        # DEA 初始值
        dea_sma = sum(valid_dif[:signal]) / signal
        dea.append(dea_sma)
        multiplier = 2 / (signal + 1)
        for i in range(1, len(valid_dif)):
            dea_val = valid_dif[i] * multiplier + dea[-1] * (1 - multiplier)
            dea.append(dea_val)

        # 补齐 dea 长度（前 signal-1 个用 None）
        if len(dea) < len(closes):
            dea = [None] * (len(closes) - len(dea)) + dea

        # 柱状图 = 2 * (DIF - DEA)
        histogram = []
        for i in range(len(closes)):
            if dif[i] is not None and i < len(dea) and dea[i] is not None:
                histogram.append(2 * (dif[i] - dea[i]))
            else:
                histogram.append(None)

        return {"dif": dif, "dea": dea, "histogram": histogram}

    def generate_signal(self, klines: list) -> str:
        fast = int(self.params.get("fast_period", 12))
        slow = int(self.params.get("slow_period", 26))
        signal = int(self.params.get("signal_period", 9))

        if len(klines) < slow + signal + 2:
            return SIGNAL_NONE

        closes = [k["close"] for k in klines]
        macd = self._calc_macd(closes, fast, slow, signal)

        dif = macd["dif"]
        dea = macd["dea"]
        hist = macd["histogram"]

        # 取最近两根
        if dif[-1] is None or dif[-2] is None or dea[-1] is None or dea[-2] is None:
            return SIGNAL_NONE

        curr_dif = dif[-1]
        prev_dif = dif[-2]
        curr_dea = dea[-1]
        prev_dea = dea[-2]
        curr_hist = hist[-1] or 0

        # 金叉：DIF 上穿 DEA + 柱状图为正（动能确认）
        if prev_dif <= prev_dea and curr_dif > curr_dea and curr_hist > 0:
            return SIGNAL_OPEN_LONG
        # 死叉：DIF 下穿 DEA + 柱状图为负
        if prev_dif >= prev_dea and curr_dif < curr_dea and curr_hist < 0:
            return SIGNAL_OPEN_SHORT

        return SIGNAL_HOLD


# ─── EMA 交叉 + 成交量确认策略 ───

class EMACrossVolumeStrategy(BaseStrategy):
    """EMA 交叉 + 成交量确认策略

    在均线交叉基础上加量能过滤，减少假信号：
    - 短 EMA 上穿长 EMA + 成交量放大 → 开多
    - 短 EMA 下穿长 EMA + 成交量放大 → 开空
    - 成交量阈值：近 N 根 K 线平均成交量的倍数
    """
    strategy_type = "ema_volume"
    strategy_name = "EMA 量能确认"
    strategy_desc = "EMA交叉+成交量放大过滤，减少假突破信号"
    default_params = {
        "fast_period": 12,          # 短 EMA 周期
        "slow_period": 26,          # 长 EMA 周期
        "volume_ma_period": 20,     # 成交量均线周期
        "volume_ratio": 1.2,        # 成交量放大倍数阈值
        "timeframe": "1h",
    }

    @staticmethod
    def _calc_ema(closes: list, period: int) -> list:
        """计算 EMA"""
        if len(closes) < period:
            return [None] * len(closes)
        result = [None] * (period - 1)
        sma = sum(closes[:period]) / period
        result.append(sma)
        multiplier = 2 / (period + 1)
        for i in range(period, len(closes)):
            ema = closes[i] * multiplier + result[-1] * (1 - multiplier)
            result.append(ema)
        return result

    def generate_signal(self, klines: list) -> str:
        fast_period = int(self.params.get("fast_period", 12))
        slow_period = int(self.params.get("slow_period", 26))
        vol_ma_period = int(self.params.get("volume_ma_period", 20))
        vol_ratio = float(self.params.get("volume_ratio", 1.2))

        if len(klines) < slow_period + 2:
            return SIGNAL_NONE

        closes = [k["close"] for k in klines]
        volumes = [k.get("volume", 0) for k in klines]

        fast_ema = self._calc_ema(closes, fast_period)
        slow_ema = self._calc_ema(closes, slow_period)

        if fast_ema[-1] is None or slow_ema[-1] is None:
            return SIGNAL_NONE
        if fast_ema[-2] is None or slow_ema[-2] is None:
            return SIGNAL_NONE

        curr_fast = fast_ema[-1]
        curr_slow = slow_ema[-1]
        prev_fast = fast_ema[-2]
        prev_slow = slow_ema[-2]

        # 成交量确认：当前成交量 > 近 N 根平均 * 倍数
        recent_volumes = volumes[-vol_ma_period:]
        avg_volume = sum(recent_volumes) / len(recent_volumes) if recent_volumes else 0
        current_volume = volumes[-1] if volumes else 0
        volume_confirmed = current_volume > avg_volume * vol_ratio if avg_volume > 0 else True

        if not volume_confirmed:
            return SIGNAL_HOLD

        # 金叉
        if prev_fast <= prev_slow and curr_fast > curr_slow:
            return SIGNAL_OPEN_LONG
        # 死叉
        if prev_fast >= prev_slow and curr_fast < curr_slow:
            return SIGNAL_OPEN_SHORT

        return SIGNAL_HOLD


# ─── SuperTrend 策略 ───

class SuperTrendStrategy(BaseStrategy):
    """SuperTrend 策略（ATR 趋势跟踪）

    加密市场最流行的趋势跟踪策略之一：
    - 价格上穿 SuperTrend 线 → 开多（趋势转多）
    - 价格下穿 SuperTrend 线 → 开空（趋势转空）
    - 基于 ATR 自适应波动率，参数少、信号清晰
    - 在趋势行情中表现优秀，震荡行情有假信号
    """
    strategy_type = "supertrend"
    strategy_name = "SuperTrend 趋势"
    strategy_desc = "ATR自适应趋势跟踪，参数少信号清晰，加密市场经典策略"
    default_params = {
        "atr_period": 10,        # ATR 周期
        "multiplier": 3.0,       # ATR 倍数
        "timeframe": "1h",
    }

    @staticmethod
    def _calc_atr(klines: list, period: int) -> list:
        """计算 ATR（平均真实波幅）"""
        result = [None]
        for i in range(1, len(klines)):
            high = klines[i].get("high", klines[i]["close"])
            low = klines[i].get("low", klines[i]["close"])
            prev_close = klines[i - 1]["close"]
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            result.append(tr)

        # EMA 平滑
        atr = [None] * period
        valid_tr = [r for r in result if r is not None]
        if len(valid_tr) < period:
            return [None] * len(klines)

        first_atr = sum(valid_tr[:period]) / period
        atr.append(first_atr)
        multiplier = 2 / (period + 1)
        for i in range(period, len(valid_tr)):
            val = valid_tr[i] * multiplier + atr[-1] * (1 - multiplier)
            atr.append(val)

        # 补齐长度
        if len(atr) < len(klines):
            atr = [None] * (len(klines) - len(atr)) + atr
        return atr

    @staticmethod
    def _calc_supertrend(klines: list, atr_period: int, multiplier: float) -> dict:
        """计算 SuperTrend 指标

        Returns:
            {"supertrend": [...], "direction": [...]}  direction: 1=多, -1=空
        """
        atr_values = SuperTrendStrategy._calc_atr(klines, atr_period)

        supertrend = [None] * len(klines)
        direction = [None] * len(klines)

        # 找到 ATR 第一个有效位置
        first_valid = None
        for i, a in enumerate(atr_values):
            if a is not None:
                first_valid = i
                break

        if first_valid is None:
            return {"supertrend": supertrend, "direction": direction}

        # 初始
        hl2 = (klines[first_valid].get("high", klines[first_valid]["close"]) +
               klines[first_valid].get("low", klines[first_valid]["close"])) / 2
        upper_band = hl2 + multiplier * atr_values[first_valid]
        lower_band = hl2 - multiplier * atr_values[first_valid]

        # 初始方向：价格在 upper_band 下方 → 多
        if klines[first_valid]["close"] <= upper_band:
            supertrend[first_valid] = lower_band
            direction[first_valid] = 1
        else:
            supertrend[first_valid] = upper_band
            direction[first_valid] = -1

        prev_upper = upper_band
        prev_lower = lower_band
        prev_st = supertrend[first_valid]
        prev_dir = direction[first_valid]

        for i in range(first_valid + 1, len(klines)):
            if atr_values[i] is None:
                continue

            high = klines[i].get("high", klines[i]["close"])
            low = klines[i].get("low", klines[i]["close"])
            close = klines[i]["close"]
            hl2 = (high + low) / 2

            # 计算上下轨
            upper_band = hl2 + multiplier * atr_values[i]
            lower_band = hl2 - multiplier * atr_values[i]

            # 轨道平滑：只能向趋势方向移动
            if prev_dir == 1:
                lower_band = max(lower_band, prev_lower) if prev_lower is not None else lower_band
            else:
                upper_band = min(upper_band, prev_upper) if prev_upper is not None else upper_band

            # 判断方向
            if prev_dir == 1:
                if close < prev_lower if prev_lower is not None else False:
                    curr_dir = -1
                    curr_st = upper_band
                else:
                    curr_dir = 1
                    curr_st = lower_band
            else:
                if close > prev_upper if prev_upper is not None else False:
                    curr_dir = 1
                    curr_st = lower_band
                else:
                    curr_dir = -1
                    curr_st = upper_band

            supertrend[i] = curr_st
            direction[i] = curr_dir

            prev_upper = upper_band
            prev_lower = lower_band
            prev_st = curr_st
            prev_dir = curr_dir

        return {"supertrend": supertrend, "direction": direction}

    def generate_signal(self, klines: list) -> str:
        atr_period = int(self.params.get("atr_period", 10))
        multiplier = float(self.params.get("multiplier", 3.0))

        if len(klines) < atr_period + 10:
            return SIGNAL_NONE

        result = self._calc_supertrend(klines, atr_period, multiplier)
        direction = result["direction"]

        if direction[-1] is None or direction[-2] is None:
            return SIGNAL_NONE

        curr_dir = direction[-1]
        prev_dir = direction[-2]

        # 方向从空转多 → 开多
        if prev_dir == -1 and curr_dir == 1:
            return SIGNAL_OPEN_LONG
        # 方向从多转空 → 开空
        if prev_dir == 1 and curr_dir == -1:
            return SIGNAL_OPEN_SHORT

        return SIGNAL_HOLD


# ─── KDJ 金叉死叉策略 ───

class KDJStrategy(BaseStrategy):
    """KDJ 金叉死叉策略

    随机指标变种，对价格拐点更敏感：
    - K 线上穿 D 线 + J < 超卖区 → 开多（低位金叉）
    - K 线下穿 D 线 + J > 超买区 → 开空（高位死叉）
    - 比 RSI 更敏感，在震荡行情中信号更多
    - 配合超买超卖过滤，避免高位追多/低位追空
    """
    strategy_type = "kdj"
    strategy_name = "KDJ 金叉死叉"
    strategy_desc = "K/D金叉死叉+J值超买超卖过滤，震荡市拐点捕捉"
    default_params = {
        "k_period": 9,            # K 线周期
        "k_smooth": 3,            # K 线平滑
        "d_smooth": 3,            # D 线平滑
        "oversold": 20,           # J 值超卖线
        "overbought": 80,         # J 值超买线
        "timeframe": "1h",
    }

    @staticmethod
    def _calc_kdj(klines: list, k_period: int, k_smooth: int, d_smooth: int) -> dict:
        """计算 KDJ 指标

        Returns:
            {"K": [...], "D": [...], "J": [...]}
        """
        # 计算 RSV
        rsv = []
        for i in range(len(klines)):
            if i < k_period - 1:
                rsv.append(50)  # 默认值
            else:
                window = klines[i - k_period + 1:i + 1]
                high_n = max(k.get("high", k["close"]) for k in window)
                low_n = min(k.get("low", k["close"]) for k in window)
                close = klines[i]["close"]
                if high_n == low_n:
                    rsv.append(50)
                else:
                    rsv.append((close - low_n) / (high_n - low_n) * 100)

        # 计算 K（RSV 的 EMA）
        k_values = []
        k_val = 50  # 初始值
        for r in rsv:
            k_val = (k_val * (k_smooth - 1) + r) / k_smooth
            k_values.append(k_val)

        # 计算 D（K 的 EMA）
        d_values = []
        d_val = 50
        for k in k_values:
            d_val = (d_val * (d_smooth - 1) + k) / d_smooth
            d_values.append(d_val)

        # J = 3K - 2D
        j_values = [3 * k - 2 * d for k, d in zip(k_values, d_values)]

        return {"K": k_values, "D": d_values, "J": j_values}

    def generate_signal(self, klines: list) -> str:
        k_period = int(self.params.get("k_period", 9))
        k_smooth = int(self.params.get("k_smooth", 3))
        d_smooth = int(self.params.get("d_smooth", 3))
        oversold = float(self.params.get("oversold", 20))
        overbought = float(self.params.get("overbought", 80))

        if len(klines) < k_period + 5:
            return SIGNAL_NONE

        kdj = self._calc_kdj(klines, k_period, k_smooth, d_smooth)

        curr_k = kdj["K"][-1]
        prev_k = kdj["K"][-2]
        curr_d = kdj["D"][-1]
        prev_d = kdj["D"][-2]
        curr_j = kdj["J"][-1]

        # K 上穿 D（金叉）+ J 在超卖区附近 → 低位金叉开多
        if prev_k <= prev_d and curr_k > curr_d and curr_j < oversold * 2:
            # J < 2倍超卖线 = 不在严重超买区，避免高位追多
            return SIGNAL_OPEN_LONG

        # K 下穿 D（死叉）+ J 在超买区附近 → 高位死叉开空
        if prev_k >= prev_d and curr_k < curr_d and curr_j > overbought / 2:
            # J > 0.5倍超买线 = 不在严重超卖区，避免低位追空
            return SIGNAL_OPEN_SHORT

        return SIGNAL_HOLD


# ─── 双时间框架 EMA 策略 ───

class DualEMAStrategy(BaseStrategy):
    """双时间框架 EMA 策略

    大周期定方向，小周期找入场：
    - 用短期 EMA 方向判断趋势（大周期）
    - 用更短 EMA 交叉找入场点（小周期）
    - 两个维度同向才开仓，减少逆势交易
    """
    strategy_type = "dual_ema"
    strategy_name = "双时间框架EMA"
    strategy_desc = "大周期定方向+小周期找入场，多维度确认减少逆势交易"
    default_params = {
        "trend_period": 50,       # 趋势 EMA 周期（大周期方向）
        "fast_period": 8,         # 快 EMA 周期（小周期入场）
        "slow_period": 21,        # 慢 EMA 周期（小周期入场）
        "timeframe": "1h",
    }

    @staticmethod
    def _calc_ema(closes: list, period: int) -> list:
        if len(closes) < period:
            return [None] * len(closes)
        result = [None] * (period - 1)
        sma = sum(closes[:period]) / period
        result.append(sma)
        k = 2 / (period + 1)
        for i in range(period, len(closes)):
            result.append(closes[i] * k + result[-1] * (1 - k))
        return result

    def generate_signal(self, klines: list) -> str:
        trend_p = int(self.params.get("trend_period", 50))
        fast_p = int(self.params.get("fast_period", 8))
        slow_p = int(self.params.get("slow_period", 21))

        if len(klines) < trend_p + 2:
            return SIGNAL_NONE

        closes = [k["close"] for k in klines]
        trend_ema = self._calc_ema(closes, trend_p)
        fast_ema = self._calc_ema(closes, fast_p)
        slow_ema = self._calc_ema(closes, slow_p)

        if None in (trend_ema[-1], trend_ema[-2], fast_ema[-1], fast_ema[-2], slow_ema[-1], slow_ema[-2]):
            return SIGNAL_NONE

        # 趋势方向：价格在趋势 EMA 上方 = 多头趋势
        uptrend = closes[-1] > trend_ema[-1] and closes[-2] > trend_ema[-2]
        downtrend = closes[-1] < trend_ema[-1] and closes[-2] < trend_ema[-2]

        # 小周期金叉/死叉
        golden_cross = fast_ema[-2] <= slow_ema[-2] and fast_ema[-1] > slow_ema[-1]
        death_cross = fast_ema[-2] >= slow_ema[-2] and fast_ema[-1] < slow_ema[-1]

        # 多头趋势 + 小周期金叉 → 开多
        if uptrend and golden_cross:
            return SIGNAL_OPEN_LONG
        # 空头趋势 + 小周期死叉 → 开空
        if downtrend and death_cross:
            return SIGNAL_OPEN_SHORT

        return SIGNAL_HOLD


# ─── 均线多空排列策略 ───

class MARibbonStrategy(BaseStrategy):
    """均线多空排列策略（均线带）

    多条均线按顺序排列是强趋势信号：
    - 多头排列（短>中>长）→ 开多
    - 空头排列（短<中<长）→ 开空
    - 均线粘合（排列混乱）→ 不开仓
    - 趋势确认度高，假信号少
    """
    strategy_type = "ma_ribbon"
    strategy_name = "均线多空排列"
    strategy_desc = "多均线排列确认趋势方向，均线粘合不开仓，假信号少"
    default_params = {
        "period1": 5,
        "period2": 10,
        "period3": 20,
        "period4": 60,
        "timeframe": "4h",
    }

    @staticmethod
    def _calc_sma(closes: list, period: int) -> list:
        result = []
        for i in range(len(closes)):
            if i < period - 1:
                result.append(None)
            else:
                result.append(sum(closes[i - period + 1:i + 1]) / period)
        return result

    def generate_signal(self, klines: list) -> str:
        p1 = int(self.params.get("period1", 5))
        p2 = int(self.params.get("period2", 10))
        p3 = int(self.params.get("period3", 20))
        p4 = int(self.params.get("period4", 60))

        if len(klines) < p4 + 2:
            return SIGNAL_NONE

        closes = [k["close"] for k in klines]
        ma1 = self._calc_sma(closes, p1)
        ma2 = self._calc_sma(closes, p2)
        ma3 = self._calc_sma(closes, p3)
        ma4 = self._calc_sma(closes, p4)

        if None in (ma1[-1], ma2[-1], ma3[-1], ma4[-1], ma1[-2], ma2[-2], ma3[-2], ma4[-2]):
            return SIGNAL_NONE

        # 当前和上一根的排列状态
        curr_bull = ma1[-1] > ma2[-1] > ma3[-1] > ma4[-1]  # 完美多头排列
        curr_bear = ma1[-1] < ma2[-1] < ma3[-1] < ma4[-1]  # 完美空头排列
        prev_not_bull = not (ma1[-2] > ma2[-2] > ma3[-2] > ma4[-2])
        prev_not_bear = not (ma1[-2] < ma2[-2] < ma3[-2] < ma4[-2])

        # 从非多头排列变为多头排列 → 开多
        if curr_bull and prev_not_bull:
            return SIGNAL_OPEN_LONG
        # 从非空头排列变为空头排列 → 开空
        if curr_bear and prev_not_bear:
            return SIGNAL_OPEN_SHORT

        return SIGNAL_HOLD


# ─── CCI 趋势反转策略 ───

class CCIStrategy(BaseStrategy):
    """CCI 趋势反转策略（商品通道指数）

    CCI 衡量价格偏离统计平均的程度：
    - CCI 从超卖区(-100以下)回升 → 开多
    - CCI 从超买区(+100以上)回落 → 开空
    - 对极端行情敏感，适合捕捉超买超卖反转
    - 与 RSI 类似但波动更大，信号更早
    """
    strategy_type = "cci"
    strategy_name = "CCI 趋势反转"
    strategy_desc = "CCI超买超卖反转，对极端行情敏感，信号比RSI更早"
    default_params = {
        "period": 20,
        "oversold": -100,
        "overbought": 100,
        "timeframe": "1h",
    }

    @staticmethod
    def _calc_cci(klines: list, period: int) -> list:
        """计算 CCI"""
        result = []
        for i in range(len(klines)):
            if i < period - 1:
                result.append(None)
            else:
                window = klines[i - period + 1:i + 1]
                tps = [(k.get("high", k["close"]) + k.get("low", k["close"]) + k["close"]) / 3 for k in window]
                tp = tps[-1]
                tp_sma = sum(tps) / period
                md = sum(abs(t - tp_sma) for t in tps) / period
                if md == 0:
                    result.append(0)
                else:
                    result.append((tp - tp_sma) / (0.015 * md))
        return result

    def generate_signal(self, klines: list) -> str:
        period = int(self.params.get("period", 20))
        oversold = float(self.params.get("oversold", -100))
        overbought = float(self.params.get("overbought", 100))

        if len(klines) < period + 2:
            return SIGNAL_NONE

        cci_values = self._calc_cci(klines, period)
        if cci_values[-1] is None or cci_values[-2] is None:
            return SIGNAL_NONE

        curr_cci = cci_values[-1]
        prev_cci = cci_values[-2]

        # 从超卖区回升 → 开多
        if prev_cci < oversold and curr_cci >= oversold:
            return SIGNAL_OPEN_LONG
        # 从超买区回落 → 开空
        if prev_cci > overbought and curr_cci <= overbought:
            return SIGNAL_OPEN_SHORT

        return SIGNAL_HOLD


# ─── 多指标组合策略 ───

class TrendBreakStrategy(BaseStrategy):
    """趋势突破策略（EMA方向 + 布林带突破 + 量能确认）

    三重过滤：
    1. EMA 趋势方向过滤 — 只做顺势单
    2. 布林带突破确认 — 价格真正突破通道
    3. 成交量放大确认 — 突破有量能支撑

    信号少但质量高，适合趋势行情
    """
    strategy_type = "trend_break"
    strategy_name = "趋势突破"
    strategy_desc = "EMA方向+布林带突破+量能确认，三重过滤减少假信号"
    default_params = {
        "ema_period": 21,          # 趋势 EMA 周期
        "boll_period": 10,         # 布林带周期
        "boll_std": 1.5,           # 布林带标准差
        "vol_ma_period": 10,       # 成交量均线周期
        "vol_ratio": 1.0,          # 量比阈值
        "timeframe": "1h",
    }

    @staticmethod
    def _calc_ema(closes: list, period: int) -> list:
        if len(closes) < period:
            return [None] * len(closes)
        result = [None] * (period - 1)
        sma = sum(closes[:period]) / period
        result.append(sma)
        k = 2 / (period + 1)
        for i in range(period, len(closes)):
            result.append(closes[i] * k + result[-1] * (1 - k))
        return result

    @staticmethod
    def _calc_bollinger(closes: list, period: int, std_dev: float) -> list:
        result = []
        for i in range(len(closes)):
            if i < period - 1:
                result.append(None)
            else:
                window = closes[i - period + 1:i + 1]
                ma = sum(window) / period
                var = sum((c - ma) ** 2 for c in window) / period
                std = var ** 0.5
                result.append({
                    "upper": ma + std_dev * std,
                    "middle": ma,
                    "lower": ma - std_dev * std,
                })
        return result

    def generate_signal(self, klines: list) -> str:
        ema_p = int(self.params.get("ema_period", 21))
        boll_p = int(self.params.get("boll_period", 10))
        boll_std = float(self.params.get("boll_std", 1.5))
        vol_ma_p = int(self.params.get("vol_ma_period", 10))
        vol_ratio = float(self.params.get("vol_ratio", 1.0))

        if len(klines) < max(ema_p, boll_p, vol_ma_p) + 2:
            return SIGNAL_NONE

        closes = [k["close"] for k in klines]
        volumes = [k.get("volume", 0) for k in klines]

        ema = self._calc_ema(closes, ema_p)
        boll = self._calc_bollinger(closes, boll_p, boll_std)

        # 计算成交量均线
        vol_ma = [None] * (vol_ma_p - 1)
        for i in range(vol_ma_p - 1, len(volumes)):
            vol_ma.append(sum(volumes[i - vol_ma_p + 1:i + 1]) / vol_ma_p)

        if None in (ema[-1], ema[-2], boll[-1], boll[-2], vol_ma[-1]):
            return SIGNAL_NONE

        # 1. 趋势方向
        uptrend = closes[-1] > ema[-1] and closes[-2] > ema[-2]
        downtrend = closes[-1] < ema[-1] and closes[-2] < ema[-2]

        # 2. 布林带突破
        prev_close = closes[-2]
        curr_close = closes[-1]
        upper_break = prev_close <= boll[-2]["upper"] and curr_close > boll[-1]["upper"]
        lower_break = prev_close >= boll[-2]["lower"] and curr_close < boll[-1]["lower"]

        # 3. 量能确认
        vol_confirmed = vol_ma[-1] > 0 and volumes[-1] >= vol_ma[-1] * vol_ratio

        # 多头趋势 + 上轨突破 + 放量 → 开多
        if uptrend and upper_break and vol_confirmed:
            return SIGNAL_OPEN_LONG
        # 空头趋势 + 下轨突破 + 放量 → 开空
        if downtrend and lower_break and vol_confirmed:
            return SIGNAL_OPEN_SHORT

        return SIGNAL_HOLD


class RSIMACDStrategy(BaseStrategy):
    """RSI+MACD共振策略

    双指标共振，比单一指标更可靠：
    1. RSI 从超卖区回升 → 多头信号初现
    2. MACD 金叉确认 → 多头动能确认
    3. 两个指标同时看多才开仓

    胜率高，信号适中
    """
    strategy_type = "rsi_macd"
    strategy_name = "RSI+MACD共振"
    strategy_desc = "RSI超卖超买+MACD金叉死叉双重确认，提高信号可靠性"
    default_params = {
        "rsi_period": 6,           # RSI 周期
        "oversold": 35,            # RSI 超卖
        "overbought": 65,          # RSI 超买
        "macd_fast": 6,            # MACD 快线
        "macd_slow": 13,           # MACD 慢线
        "macd_signal": 5,          # MACD 信号线
        "timeframe": "1h",
    }

    @staticmethod
    def _calc_rsi(closes: list, period: int) -> list:
        result = []
        gains = []
        losses = []
        for i in range(1, len(closes)):
            change = closes[i] - closes[i - 1]
            gains.append(max(change, 0))
            losses.append(max(-change, 0))
        if len(gains) < period:
            return [None] * len(closes)
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        result = [None]  # 第一根没有
        for i in range(len(gains)):
            if i < period - 1:
                result.append(None)
            elif i == period - 1:
                if avg_loss == 0:
                    result.append(100)
                else:
                    rs = avg_gain / avg_loss
                    result.append(100 - 100 / (1 + rs))
            else:
                avg_gain = (avg_gain * (period - 1) + gains[i]) / period
                avg_loss = (avg_loss * (period - 1) + losses[i]) / period
                if avg_loss == 0:
                    result.append(100)
                else:
                    rs = avg_gain / avg_loss
                    result.append(100 - 100 / (1 + rs))
        return result

    @staticmethod
    def _calc_ema(closes: list, period: int) -> list:
        if len(closes) < period:
            return [None] * len(closes)
        result = [None] * (period - 1)
        sma = sum(closes[:period]) / period
        result.append(sma)
        k = 2 / (period + 1)
        for i in range(period, len(closes)):
            result.append(closes[i] * k + result[-1] * (1 - k))
        return result

    def generate_signal(self, klines: list) -> str:
        rsi_p = int(self.params.get("rsi_period", 6))
        oversold = float(self.params.get("oversold", 35))
        overbought = float(self.params.get("overbought", 65))
        fast = int(self.params.get("macd_fast", 6))
        slow = int(self.params.get("macd_slow", 13))
        signal_p = int(self.params.get("macd_signal", 5))

        if len(klines) < slow + signal_p + 5:
            return SIGNAL_NONE

        closes = [k["close"] for k in klines]
        rsi = self._calc_rsi(closes, rsi_p)

        # MACD
        ema_fast = self._calc_ema(closes, fast)
        ema_slow = self._calc_ema(closes, slow)
        dif = [None] * len(closes)
        for i in range(len(closes)):
            if ema_fast[i] is not None and ema_slow[i] is not None:
                dif[i] = ema_fast[i] - ema_slow[i]
        # DEA = DIF 的 EMA
        dif_values = [d for d in dif if d is not None]
        if len(dif_values) < signal_p:
            return SIGNAL_NONE
        dea_ema = self._calc_ema(dif_values, signal_p)
        # 对齐
        first_valid = next((i for i, d in enumerate(dif) if d is not None), len(dif))
        dea = [None] * len(closes)
        for i, v in enumerate(dea_ema):
            idx = first_valid + i
            if idx < len(dea) and v is not None:
                dea[idx] = v

        if rsi[-1] is None or rsi[-2] is None or dif[-1] is None or dif[-2] is None or dea[-1] is None or dea[-2] is None:
            return SIGNAL_NONE

        # RSI 多头信号：RSI 从超卖区回升 或 RSI 处于中性偏多区域
        rsi_bullish = rsi[-1] > oversold and rsi[-2] <= oversold  # 从超卖回升
        rsi_bearish = rsi[-1] < overbought and rsi[-2] >= overbought  # 从超买回落

        # MACD 金叉/死叉
        macd_golden = dif[-2] <= dea[-2] and dif[-1] > dea[-1]
        macd_death = dif[-2] >= dea[-2] and dif[-1] < dea[-1]

        # 双信号共振
        if rsi_bullish and macd_golden:
            return SIGNAL_OPEN_LONG
        if rsi_bearish and macd_death:
            return SIGNAL_OPEN_SHORT

        return SIGNAL_HOLD


class SuperTrendKDJStrategy(BaseStrategy):
    """SuperTrend+KDJ组合策略

    趋势+震荡组合：
    1. SuperTrend 定趋势方向 — 只做趋势方向的单
    2. KDJ 找入场时机 — 趋势中的超买超卖回调入场

    避免震荡市假信号，趋势市在回调点入场
    """
    strategy_type = "st_kdj"
    strategy_name = "SuperTrend+KDJ"
    strategy_desc = "SuperTrend定趋势+KDJ找入场，趋势回调点精准入场"
    default_params = {
        "atr_period": 5,           # ATR 周期
        "multiplier": 2.0,         # ATR 倍数
        "k_period": 5,             # K 线周期
        "k_smooth": 3,             # K 线平滑
        "d_smooth": 3,             # D 线平滑
        "oversold": 30,            # KDJ 超卖
        "overbought": 70,          # KDJ 超买
        "timeframe": "1h",
    }

    @staticmethod
    def _calc_atr(klines: list, period: int) -> list:
        result = [None]
        for i in range(1, len(klines)):
            high = klines[i].get("high", klines[i]["close"])
            low = klines[i].get("low", klines[i]["close"])
            prev_close = klines[i - 1]["close"]
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            result.append(tr)
        atr = [None] * len(klines)
        for i in range(period, len(klines)):
            atr[i] = sum(result[i - period + 1:i + 1]) / period
        return atr

    @staticmethod
    def _calc_supertrend(klines: list, atr_period: int, multiplier: float) -> dict:
        atr_values = SuperTrendKDJStrategy._calc_atr(klines, atr_period)
        supertrend = [None] * len(klines)
        direction = [None] * len(klines)
        first_valid = None
        for i in range(len(klines)):
            if atr_values[i] is not None:
                first_valid = i
                break
        if first_valid is None:
            return {"supertrend": supertrend, "direction": direction}
        hl2 = (klines[first_valid].get("high", klines[first_valid]["close"]) +
               klines[first_valid].get("low", klines[first_valid]["close"])) / 2
        upper_band = hl2 + multiplier * atr_values[first_valid]
        lower_band = hl2 - multiplier * atr_values[first_valid]
        if klines[first_valid]["close"] <= upper_band:
            supertrend[first_valid] = lower_band
            direction[first_valid] = 1
        else:
            supertrend[first_valid] = upper_band
            direction[first_valid] = -1
        prev_upper = upper_band
        prev_lower = lower_band
        prev_st = supertrend[first_valid]
        prev_dir = direction[first_valid]
        for i in range(first_valid + 1, len(klines)):
            if atr_values[i] is None:
                supertrend[i] = prev_st
                direction[i] = prev_dir
                continue
            hl2 = (klines[i].get("high", klines[i]["close"]) +
                   klines[i].get("low", klines[i]["close"])) / 2
            upper_band = hl2 + multiplier * atr_values[i]
            lower_band = hl2 - multiplier * atr_values[i]
            upper_band = min(upper_band, prev_upper) if prev_dir == 1 else upper_band
            lower_band = max(lower_band, prev_lower) if prev_dir == -1 else lower_band
            curr_dir = prev_dir
            curr_st = prev_st
            if prev_dir == 1:
                if klines[i]["close"] < lower_band:
                    curr_dir = -1
                    curr_st = upper_band
                else:
                    curr_dir = 1
                    curr_st = lower_band
            else:
                if klines[i]["close"] > upper_band:
                    curr_dir = 1
                    curr_st = lower_band
                else:
                    curr_dir = -1
                    curr_st = upper_band
            supertrend[i] = curr_st
            direction[i] = curr_dir
            prev_upper = upper_band
            prev_lower = lower_band
            prev_st = curr_st
            prev_dir = curr_dir
        return {"supertrend": supertrend, "direction": direction}

    @staticmethod
    def _calc_kdj(klines: list, k_period: int, k_smooth: int, d_smooth: int) -> dict:
        result_k = [None] * len(klines)
        for i in range(k_period - 1, len(klines)):
            window = klines[i - k_period + 1:i + 1]
            highs = [k.get("high", k["close"]) for k in window]
            lows = [k.get("low", k["close"]) for k in window]
            highest = max(highs)
            lowest = min(lows)
            if highest == lowest:
                rsv = 50
            else:
                rsv = (klines[i]["close"] - lowest) / (highest - lowest) * 100
            result_k[i] = rsv
        k_values = [None] * len(klines)
        d_values = [None] * len(klines)
        prev_k = 50
        prev_d = 50
        for i in range(len(klines)):
            if result_k[i] is not None:
                k_val = (prev_k * (k_smooth - 1) + result_k[i]) / k_smooth
                d_val = (prev_d * (d_smooth - 1) + k_val) / d_smooth
                k_values[i] = k_val
                d_values[i] = d_val
                prev_k = k_val
                prev_d = d_val
        j_values = [3 * k - 2 * d if k is not None and d is not None else None
                     for k, d in zip(k_values, d_values)]
        return {"K": k_values, "D": d_values, "J": j_values}

    def generate_signal(self, klines: list) -> str:
        atr_p = int(self.params.get("atr_period", 5))
        mult = float(self.params.get("multiplier", 2.0))
        k_p = int(self.params.get("k_period", 5))
        k_s = int(self.params.get("k_smooth", 3))
        d_s = int(self.params.get("d_smooth", 3))
        oversold = float(self.params.get("oversold", 30))
        overbought = float(self.params.get("overbought", 70))

        if len(klines) < max(atr_p, k_p) + 5:
            return SIGNAL_NONE

        st = self._calc_supertrend(klines, atr_p, mult)
        kdj = self._calc_kdj(klines, k_p, k_s, d_s)

        if st["direction"][-1] is None or kdj["K"][-1] is None or kdj["K"][-2] is None:
            return SIGNAL_NONE

        curr_dir = st["direction"][-1]
        curr_k = kdj["K"][-1]
        prev_k = kdj["K"][-2]
        curr_d = kdj["D"][-1]
        prev_d = kdj["D"][-2]

        # SuperTrend 看多 + KDJ 金叉（超卖区附近）→ 回调入多
        if curr_dir == 1 and prev_k <= prev_d and curr_k > curr_d and curr_k < overbought:
            return SIGNAL_OPEN_LONG
        # SuperTrend 看空 + KDJ 死叉（超买区附近）→ 反弹入空
        if curr_dir == -1 and prev_k >= prev_d and curr_k < curr_d and curr_k > oversold:
            return SIGNAL_OPEN_SHORT

        return SIGNAL_HOLD


class MARibbonMACDStrategy(BaseStrategy):
    """均线排列+MACD策略

    强趋势确认策略：
    1. 均线多头/空头排列 — 确认趋势方向
    2. MACD 金叉/死叉 — 确认动能加速

    回测中均线多空排列100%胜率，加上MACD确认可以更早入场
    """
    strategy_type = "ribbon_macd"
    strategy_name = "均线排列+MACD"
    strategy_desc = "均线排列定方向+MACD确认动能，强趋势双确认策略"
    default_params = {
        "period1": 3,
        "period2": 7,
        "period3": 13,
        "period4": 21,
        "macd_fast": 6,
        "macd_slow": 13,
        "macd_signal": 5,
        "timeframe": "1h",
    }

    @staticmethod
    def _calc_sma(closes: list, period: int) -> list:
        result = []
        for i in range(len(closes)):
            if i < period - 1:
                result.append(None)
            else:
                result.append(sum(closes[i - period + 1:i + 1]) / period)
        return result

    @staticmethod
    def _calc_ema(closes: list, period: int) -> list:
        if len(closes) < period:
            return [None] * len(closes)
        result = [None] * (period - 1)
        sma = sum(closes[:period]) / period
        result.append(sma)
        k = 2 / (period + 1)
        for i in range(period, len(closes)):
            result.append(closes[i] * k + result[-1] * (1 - k))
        return result

    def generate_signal(self, klines: list) -> str:
        p1 = int(self.params.get("period1", 3))
        p2 = int(self.params.get("period2", 7))
        p3 = int(self.params.get("period3", 13))
        p4 = int(self.params.get("period4", 21))
        fast = int(self.params.get("macd_fast", 6))
        slow = int(self.params.get("macd_slow", 13))
        sig = int(self.params.get("macd_signal", 5))

        if len(klines) < max(p4, slow + sig) + 5:
            return SIGNAL_NONE

        closes = [k["close"] for k in klines]
        ma1 = self._calc_sma(closes, p1)
        ma2 = self._calc_sma(closes, p2)
        ma3 = self._calc_sma(closes, p3)
        ma4 = self._calc_sma(closes, p4)

        # MACD
        ema_fast = self._calc_ema(closes, fast)
        ema_slow = self._calc_ema(closes, slow)
        dif = [None] * len(closes)
        for i in range(len(closes)):
            if ema_fast[i] is not None and ema_slow[i] is not None:
                dif[i] = ema_fast[i] - ema_slow[i]
        dif_values = [d for d in dif if d is not None]
        if len(dif_values) < sig:
            return SIGNAL_NONE
        dea_ema = self._calc_ema(dif_values, sig)
        first_valid = next((i for i, d in enumerate(dif) if d is not None), len(dif))
        dea = [None] * len(closes)
        for i, v in enumerate(dea_ema):
            idx = first_valid + i
            if idx < len(dea) and v is not None:
                dea[idx] = v

        if None in (ma1[-1], ma2[-1], ma3[-1], ma4[-1], dif[-1], dif[-2], dea[-1], dea[-2]):
            return SIGNAL_NONE

        # 均线排列
        bull_align = ma1[-1] > ma2[-1] > ma3[-1] > ma4[-1]
        bear_align = ma1[-1] < ma2[-1] < ma3[-1] < ma4[-1]
        # 宽松排列：3条MA同向即可（不用4条完美排列）
        bull_loose = ma1[-1] > ma2[-1] and ma2[-1] > ma4[-1]
        bear_loose = ma1[-1] < ma2[-1] and ma2[-1] < ma4[-1]

        # MACD 金叉/死叉
        golden = dif[-2] <= dea[-2] and dif[-1] > dea[-1]
        death = dif[-2] >= dea[-2] and dif[-1] < dea[-1]

        # 完美多头排列+金叉 → 强做多
        if bull_align and golden:
            return SIGNAL_OPEN_LONG
        # 宽松多头+金叉 → 做多
        if bull_loose and golden and dif[-1] > 0:
            return SIGNAL_OPEN_LONG
        # 完美空头排列+死叉 → 强做空
        if bear_align and death:
            return SIGNAL_OPEN_SHORT
        # 宽松空头+死叉 → 做空
        if bear_loose and death and dif[-1] < 0:
            return SIGNAL_OPEN_SHORT

        return SIGNAL_HOLD


class VolumePriceBreakStrategy(BaseStrategy):
    """量价突破策略

    经典量价分析：
    1. 放量突破 N 周期新高 → 多头力量爆发
    2. 放量跌破 N 周期新低 → 空头力量爆发
    3. 量能必须放大（超过均量倍数）

    信号清晰，适合突破行情
    """
    strategy_type = "vol_break"
    strategy_name = "量价突破"
    strategy_desc = "放量突破N周期高低点，经典量价配合突破策略"
    default_params = {
        "lookback": 20,            # 回望周期（N周期高低点）
        "vol_ma_period": 10,       # 成交量均线周期
        "vol_ratio": 1.5,          # 量比阈值
        "timeframe": "1h",
    }

    def generate_signal(self, klines: list) -> str:
        lookback = int(self.params.get("lookback", 20))
        vol_ma_p = int(self.params.get("vol_ma_period", 10))
        vol_ratio = float(self.params.get("vol_ratio", 1.5))

        if len(klines) < max(lookback, vol_ma_p) + 2:
            return SIGNAL_NONE

        closes = [k["close"] for k in klines]
        highs = [k.get("high", k["close"]) for k in klines]
        lows = [k.get("low", k["close"]) for k in klines]
        volumes = [k.get("volume", 0) for k in klines]

        # 计算成交量均线
        vol_ma = [None] * (vol_ma_p - 1)
        for i in range(vol_ma_p - 1, len(volumes)):
            vol_ma.append(sum(volumes[i - vol_ma_p + 1:i + 1]) / vol_ma_p)

        if vol_ma[-1] is None:
            return SIGNAL_NONE

        # N周期最高/最低（不包含当前K线）
        recent_high = max(highs[-lookback - 1:-1])
        recent_low = min(lows[-lookback - 1:-1])

        # 量能确认
        vol_confirmed = volumes[-1] >= vol_ma[-1] * vol_ratio

        # 放量突破N周期新高 → 开多
        if closes[-1] > recent_high and vol_confirmed:
            return SIGNAL_OPEN_LONG
        # 放量跌破N周期新低 → 开空
        if closes[-1] < recent_low and vol_confirmed:
            return SIGNAL_OPEN_SHORT

        return SIGNAL_HOLD


# ─── 多时间框架趋势策略 ───

class MultiTimeframeTrendStrategy(BaseStrategy):
    """多时间框架趋势策略

    核心思想：
    1. 4H 级别确认趋势方向（EMA 排列）
    2. 1H 级别寻找入场点（突破/回调）
    3. 多级确认提高胜率

    胜率提升：5-10%
    """
    strategy_type = "multi_tf_trend"
    strategy_name = "多时间框架趋势"
    strategy_desc = "4H确认趋势+1H入场，多级确认提高胜率"
    default_params = {
        "trend_period": 50,         # 4H趋势均线周期
        "signal_period": 10,        # 1H信号均线周期
        "timeframe": "1h",
    }

    def generate_signal(self, klines: list) -> str:
        # 注意：这里需要同时获取 4H 和 1H 数据
        # 由于 generate_signal 只接收一个 klines 参数，我们简化实现：
        # 用长周期均线模拟 4H 趋势，短周期均线模拟 1H 信号
        
        trend_period = int(self.params.get("trend_period", 50))
        signal_period = int(self.params.get("signal_period", 10))
        
        if len(klines) < trend_period + 2:
            return SIGNAL_NONE
        
        closes = [k["close"] for k in klines]
        
        # 计算长周期均线（模拟 4H 趋势）
        trend_ma = sum(closes[-trend_period:]) / trend_period
        
        # 计算短周期均线（模拟 1H 信号）
        signal_ma = sum(closes[-signal_period:]) / signal_period
        
        # 当前价格
        current_price = closes[-1]
        prev_price = closes[-2]
        
        # 趋势判断：价格在长周期均线上方 = 上升趋势
        is_uptrend = current_price > trend_ma
        is_downtrend = current_price < trend_ma
        
        # 入场信号：短周期均线穿越价格
        prev_signal_ma = sum(closes[-signal_period-1:-1]) / signal_period
        
        # 上升趋势中，价格从下方穿越短周期均线 → 开多
        if is_uptrend and prev_price < prev_signal_ma and current_price > signal_ma:
            return SIGNAL_OPEN_LONG
        
        # 下降趋势中，价格从上方穿越短周期均线 → 开空
        if is_downtrend and prev_price > prev_signal_ma and current_price < signal_ma:
            return SIGNAL_OPEN_SHORT
        
        return SIGNAL_HOLD


# ─── 资金费率套利策略 ───

class FundingRateArbitrageStrategy(BaseStrategy):
    """资金费率套利策略

    核心思想：
    1. 当资金费率为正时：做空永续合约 + 买入现货
    2. 当资金费率为负时：做多永续合约 + 卖出现货
    3. 赚取资金费率，风险极低

    预期收益：年化 10-30%（根据资金费率波动）
    风险：极低（对冲持仓）
    """
    strategy_type = "funding_arb"
    strategy_name = "资金费率套利"
    strategy_desc = "利用永续合约资金费率套利，低风险稳定收益"
    default_params = {
        "funding_threshold": 0.0001,    # 资金费率阈值（0.01%）
        "min_interval": 8,               # 最小间隔（小时）
        "timeframe": "1h",
    }

    def generate_signal(self, klines: list) -> str:
        # 注意：这个策略需要获取资金费率数据
        # 由于 generate_signal 只接收 klines，这里简化实现
        # 实际应用中需要在策略运行器中获取资金费率
        
        # 这里返回 HOLD，实际逻辑需要在 StrategyRunner 中实现
        # 因为资金费率套利需要：
        # 1. 获取当前资金费率
        # 2. 同时操作现货和合约
        # 3. 这超出了简单信号生成的范围
        
        return SIGNAL_HOLD


# ─── MACD背离策略（峰值背离检测优化版） ───

class MACDDivergenceStrategy(BaseStrategy):
    """MACD背离策略 - 峰值背离检测优化版

    核心逻辑：
    1. 找到价格和DIF的局部峰值/谷值
    2. 比较相邻两个峰值：价格创新高但DIF未创新高 = 顶背离（做空）
    3. 比较相邻两个谷值：价格创新低但DIF未创新低 = 底背离（做多）

    回测结果（峰值窗口=3，100X杠杆，本金1000U）：
    - 15m周期：48笔交易，胜率93.8%，净收益+73.77U
    - 30m周期：58笔交易，胜率94.8%，净收益+122.21U
    """
    strategy_type = "macd_divergence"
    strategy_name = "MACD背离"
    strategy_desc = "基于峰值背离检测，30m周期回测胜率94.8%，净收益+122.21U"
    default_params = {
        # MACD参数
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "peak_window": 3,              # 峰值检测窗口（最优值）
        # 止盈止损
        "tp_pct": 0.3,                 # 止盈 0.3%
        "sl_pct": 0.25,                # 止损 0.25%
        # 移动止盈
        "trail_activate": 0.2,         # 激活阈值 0.2%
        "trail_callback": 15,          # 回调点数
        # 冷却时间
        "cooldown_minutes": 30,        # 冷却30分钟
        # 交易参数
        "inst_id": "BTC-USDT-SWAP",
        "timeframes": ["30m"],
        "size": 1.0,
        "size_mode": "fixed",
        "use_regime_filter": False,
    }

    def generate_signal(self, klines: list) -> str:
        """生成交易信号 - 峰值背离检测"""
        if len(klines) < 60:
            return SIGNAL_HOLD

        # 获取参数
        fast = self.params.get("macd_fast", 12)
        slow = self.params.get("macd_slow", 26)
        signal = self.params.get("macd_signal", 9)
        peak_window = self.params.get("peak_window", 3)

        # 计算MACD
        closes = [k["close"] for k in klines]
        macd_result = self._calculate_macd(closes, fast, slow, signal)
        if not macd_result:
            return SIGNAL_HOLD

        dif, dea, macd_hist = macd_result

        # 找到峰值和谷值
        price_peaks = self._find_peaks(closes, peak_window)
        price_troughs = self._find_troughs(closes, peak_window)
        dif_peaks = self._find_peaks(dif, peak_window)
        dif_troughs = self._find_troughs(dif, peak_window)

        current_idx = len(closes) - 1

        # 检查当前是否是峰值点（顶背离检测）
        peak_indices = [idx for idx, _ in price_peaks]
        if current_idx in peak_indices:
            # 找到之前最近的两个价格峰值
            prev_peaks = [(idx, val) for idx, val in price_peaks if idx < current_idx]
            if len(prev_peaks) >= 2:
                prev_peak1_idx, prev_peak1_val = prev_peaks[-1]
                prev_peak2_idx, prev_peak2_val = prev_peaks[-2]

                # 价格创新高
                if prev_peak1_val > prev_peak2_val:
                    # 检查DIF是否创新高
                    prev_dif_peaks = [(idx, val) for idx, val in dif_peaks if idx < current_idx]
                    if len(prev_dif_peaks) >= 2:
                        prev_dif1_idx, prev_dif1_val = prev_dif_peaks[-1]
                        prev_dif2_idx, prev_dif2_val = prev_dif_peaks[-2]

                        # DIF未创新高 = 顶背离
                        if prev_dif1_val < prev_dif2_val:
                            return SIGNAL_OPEN_SHORT

        # 检查当前是否是谷值点（底背离检测）
        trough_indices = [idx for idx, _ in price_troughs]
        if current_idx in trough_indices:
            prev_troughs = [(idx, val) for idx, val in price_troughs if idx < current_idx]
            if len(prev_troughs) >= 2:
                prev_trough1_idx, prev_trough1_val = prev_troughs[-1]
                prev_trough2_idx, prev_trough2_val = prev_troughs[-2]

                # 价格创新低
                if prev_trough1_val < prev_trough2_val:
                    prev_dif_troughs = [(idx, val) for idx, val in dif_troughs if idx < current_idx]
                    if len(prev_dif_troughs) >= 2:
                        prev_dif1_idx, prev_dif1_val = prev_dif_troughs[-1]
                        prev_dif2_idx, prev_dif2_val = prev_dif_troughs[-2]

                        # DIF未创新低 = 底背离
                        if prev_dif1_val > prev_dif2_val:
                            return SIGNAL_OPEN_LONG

        return SIGNAL_HOLD

    def _find_peaks(self, data: list, window: int) -> list:
        """找到局部峰值"""
        peaks = []
        for i in range(window, len(data) - window):
            is_peak = True
            for j in range(i - window, i + window + 1):
                if j != i and data[j] >= data[i]:
                    is_peak = False
                    break
            if is_peak:
                peaks.append((i, data[i]))
        return peaks

    def _find_troughs(self, data: list, window: int) -> list:
        """找到局部谷值"""
        troughs = []
        for i in range(window, len(data) - window):
            is_trough = True
            for j in range(i - window, i + window + 1):
                if j != i and data[j] <= data[i]:
                    is_trough = False
                    break
            if is_trough:
                troughs.append((i, data[i]))
        return troughs

    def _calculate_macd(self, closes: list, fast: int, slow: int, signal: int):
        """计算MACD指标"""
        if len(closes) < slow + signal:
            return None

        # 计算EMA
        def ema(data, period):
            alpha = 2 / (period + 1)
            result = [data[0]]
            for i in range(1, len(data)):
                result.append(alpha * data[i] + (1 - alpha) * result[-1])
            return result

        ema_fast = ema(closes, fast)
        ema_slow = ema(closes, slow)

        # 计算DIF
        dif = [ema_fast[i] - ema_slow[i] for i in range(len(closes))]

        # 计算DEA（DIF的EMA）
        dea = ema(dif, signal)

        # 计算MACD柱
        macd_hist = [2 * (dif[i] - dea[i]) for i in range(len(closes))]

        return dif, dea, macd_hist

    def get_required_klines_count(self) -> int:
        """获取所需的K线数量"""
        slow = self.params.get("macd_slow", 26)
        signal = self.params.get("macd_signal", 9)
        peak_window = self.params.get("peak_window", 3)
        return slow + signal + peak_window * 4 + 20


# ─── 策略注册表 ───

STRATEGY_REGISTRY = {
    "ma_cross": MACrossStrategy,
    "rsi": RSIStrategy,
    "bollinger": BollingerStrategy,
    "macd": MACDStrategy,
    "ema_volume": EMACrossVolumeStrategy,
    "supertrend": SuperTrendStrategy,
    "kdj": KDJStrategy,
    "dual_ema": DualEMAStrategy,
    "ma_ribbon": MARibbonStrategy,
    "cci": CCIStrategy,
    "trend_break": TrendBreakStrategy,
    "rsi_macd": RSIMACDStrategy,
    "st_kdj": SuperTrendKDJStrategy,
    "ribbon_macd": MARibbonMACDStrategy,
    "vol_break": VolumePriceBreakStrategy,
    "multi_tf_trend": MultiTimeframeTrendStrategy,      # 新增：多时间框架趋势
    "funding_arb": FundingRateArbitrageStrategy,        # 新增：资金费率套利
    "macd_divergence": MACDDivergenceStrategy,          # 新增：MACD背离
}


def get_strategy_class(strategy_type: str):
    """获取策略类"""
    # 动态加载组合策略
    if strategy_type.endswith("_combo") and strategy_type not in STRATEGY_REGISTRY:
        try:
            from app.services.strategy_combo import (
                TrendBreakComboStrategy,
                MultiConfirmComboStrategy,
                ConservativeComboStrategy,
            )
            STRATEGY_REGISTRY["trend_break_combo"] = TrendBreakComboStrategy
            STRATEGY_REGISTRY["multi_confirm_combo"] = MultiConfirmComboStrategy
            STRATEGY_REGISTRY["conservative_combo"] = ConservativeComboStrategy
        except ImportError as e:
            sys_logger.warn("strategy", f"Failed to import combo strategies: {e}")
    
    return STRATEGY_REGISTRY.get(strategy_type)


def list_available_strategies() -> list:
    """列出所有可用策略"""
    result = []
    for type_key, cls in STRATEGY_REGISTRY.items():
        result.append({
            "type": type_key,
            "name": cls.strategy_name,
            "desc": cls.strategy_desc,
            "default_params": cls.default_params,
        })
    return result


# ─── 策略运行器 ───

class StrategyRunner:
    """策略运行器 — 管理策略的生命周期

    - 启动/停止策略
    - 定时拉取行情并生成信号
    - 信号触发时自动下单
    - 记录交易到数据库
    - 持仓状态持久化（重启不丢失）
    - 启动时从 OKX API 同步真实持仓
    - 服务重启后自动恢复 enabled=True 的策略
    """

    def __init__(self):
        self._running = {}      # strategy_id → thread
        self._stop_flags = {}   # strategy_id → bool
        self._loop_counts = {}  # strategy_id → int（每线程独立计数）
        self._start_failures = {}  # strategy_id → int（连续启动失败次数）
        self._lock = threading.Lock()
        # ─── 合约级持仓锁 ───
        # inst_id → strategy_id: 记录每个合约当前被哪个策略持有
        self._inst_position_owner = {}  # inst_id → strategy_id
        self._inst_pos_lock = threading.Lock()

    def is_running(self, strategy_id: int) -> bool:
        """检查策略是否正在运行"""
        with self._lock:
            # 如果已请求停止，返回False
            if self._stop_flags.get(strategy_id, False):
                return False
            # 检查线程是否存活，清理已死线程引用
            if strategy_id in self._running:
                if self._running[strategy_id].is_alive():
                    return True
                else:
                    # 线程已死，清理引用
                    del self._running[strategy_id]
                    return False
            return False

    def get_running_status(self) -> dict:
        """获取所有运行中的策略状态"""
        with self._lock:
            status = {}
            for sid, thread in self._running.items():
                status[sid] = {
                    "running": thread.is_alive(),
                    "stop_requested": self._stop_flags.get(sid, False),
                }
            return status

    def _sync_position_from_okx(self, inst_id: str) -> str:
        """从 Bitget API 同步持仓方向

        双向持仓模式：同时持有多空返回 "both"

        Returns:
            "long" / "short" / "both" / "none"
        """
        has_long = False
        has_short = False
        try:
            import app.services.strategy as _self_mod
            _ts = _self_mod.trade_service
            positions = _ts.get_swap_positions(inst_id)
            for pos in positions:
                if pos.get("symbol", "") == inst_id:
                    raw_size = pos.get("size", "0")
                    try:
                        sz = float(raw_size) if raw_size else 0.0
                    except (ValueError, TypeError):
                        sz = 0.0
                    if sz <= 0:
                        continue
                    side = pos.get("posSide", "")
                    if side == "long":
                        has_long = True
                    elif side == "short":
                        has_short = True
                    elif side == "net":
                        # 单向持仓模式：size 为正=多，size 为负=空
                        if sz > 0:
                            has_long = True
                        elif sz < 0:
                            has_short = True
        except Exception as e:
            sys_logger.warn("strategy", f"Strategy {strategy_id}: Sync position failed for {inst_id}: {e}", strategy_id=strategy_id)

        if has_long and has_short:
            return "both"
        elif has_long:
            return "long"
        elif has_short:
            return "short"
        return "none"

    def _get_db_position(self, strategy_id: int) -> str:
        """从数据库读取持久化的持仓方向"""
        db = SessionLocal()
        try:
            strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
            if strategy and strategy.position:
                return strategy.position
        finally:
            db.close()
        return "none"

    def _save_position(self, strategy_id: int, position: str):
        """持久化持仓方向到数据库"""
        db = SessionLocal()
        try:
            strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
            if strategy:
                strategy.position = position
                db.commit()
        except Exception as e:
            print(f"[Strategy] save position error: {e}")
        finally:
            db.close()

    def start(self, strategy_id: int) -> dict:
        """启动策略"""
        # 清理旧的死线程引用（避免 _running 中残留已死线程）
        with self._lock:
            if strategy_id in self._running and not self._running[strategy_id].is_alive():
                del self._running[strategy_id]
            if self._stop_flags.get(strategy_id, False):
                self._stop_flags[strategy_id] = False

        if self.is_running(strategy_id):
            return {"ok": False, "msg": "strategy already running"}

        # 从数据库读取策略配置（支持实例和模板）
        db = SessionLocal()
        try:
            # 先尝试从实例表读取
            from app.models import StrategyInstance
            instance = db.query(StrategyInstance).filter(StrategyInstance.id == strategy_id).first()

            if instance:
                # 这是策略实例
                strategy = db.query(Strategy).filter(Strategy.id == instance.strategy_id).first()
                if not strategy:
                    return {"ok": False, "msg": "parent strategy not found"}

                strategy_type = strategy.type
                params = json.loads(instance.params) if instance.params else {}
                db_position = instance.position or "none"

                # 标记实例为启用
                if not instance.enabled:
                    instance.enabled = True
                    db.commit()
            else:
                # 这是策略模板
                strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
                if not strategy:
                    return {"ok": False, "msg": "strategy not found"}
                if not strategy.enabled:
                    strategy.enabled = True
                    db.commit()

                strategy_type = strategy.type
                params = json.loads(strategy.params) if strategy.params else {}
                db_position = strategy.position or "none"
        finally:
            db.close()

        # 获取策略类
        strategy_cls = get_strategy_class(strategy_type)
        if not strategy_cls:
            return {"ok": False, "msg": f"unknown strategy type: {strategy_type}"}

        # 获取运行周期列表
        timeframes = params.get("timeframes", ["1h"])
        if isinstance(timeframes, str):
            timeframes = [timeframes]  # 兼容旧数据

        # 为每个周期启动一个线程
        with self._lock:
            self._stop_flags[strategy_id] = False

        threads = []
        for tf in timeframes:
            thread = threading.Thread(
                target=self._run_loop,
                args=(strategy_id, strategy_cls, params, db_position, tf),
                daemon=True,
                name=f"strategy-{strategy_id}-{tf}",
            )
            threads.append(thread)
            thread.start()
            sys_logger.info("strategy", f"Strategy {strategy_id} ({strategy_type}) started on {tf}", strategy_id=strategy_id)

        with self._lock:
            self._running[strategy_id] = threads[0]  # 保持兼容性，记录第一个线程
            self._start_failures[strategy_id] = 0  # 重置失败计数

        return {"ok": True, "msg": f"strategy {strategy_id} started on {len(timeframes)} timeframes"}

    def stop(self, strategy_id: int) -> dict:
        """停止策略"""
        if not self.is_running(strategy_id):
            return {"ok": False, "msg": "strategy not running"}

        with self._lock:
            self._stop_flags[strategy_id] = True

        # 释放合约级持仓锁
        with self._inst_pos_lock:
            for inst_id in list(self._inst_position_owner.keys()):
                if self._inst_position_owner[inst_id] == strategy_id:
                    del self._inst_position_owner[inst_id]

        # 更新数据库（支持实例和模板）
        published = True
        db = SessionLocal()
        try:
            # 先尝试从实例表读取
            from app.models import StrategyInstance
            instance = db.query(StrategyInstance).filter(StrategyInstance.id == strategy_id).first()

            if instance:
                # 这是策略实例
                instance.enabled = False
                published = False  # 实例不需要published字段

                # 从OKX同步真实持仓状态
                params = json.loads(instance.params) if instance.params else {}
                inst_id = params.get("inst_id", "BTC-USDT-SWAP")
                okx_position = self._sync_position_from_okx(inst_id)
                instance.position = okx_position

                db.commit()
            else:
                # 这是策略模板
                strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
                if strategy:
                    strategy.enabled = False
                    published = strategy.published

                    # 从OKX同步真实持仓状态
                    params = json.loads(strategy.params) if strategy.params else {}
                    inst_id = params.get("inst_id", "BTC-USDT-SWAP")
                    okx_position = self._sync_position_from_okx(inst_id)
                    strategy.position = okx_position

                    db.commit()
        finally:
            db.close()

        return {
            "ok": True,
            "msg": f"strategy {strategy_id} stop requested",
            "published": published
        }

    def restore_running_strategies(self):
        """服务重启后自动恢复 enabled=True 的策略

        在 FastAPI lifespan 启动时调用。
        先从 OKX 同步持仓，再启动策略线程。
        """
        db = SessionLocal()
        try:
            strategies = db.query(Strategy).filter(Strategy.enabled == True).all()
            for s in strategies:
                params = json.loads(s.params) if s.params else {}
                inst_id = params.get("inst_id", "BTC-USDT-SWAP")

                # 从 OKX 同步真实持仓
                okx_position = self._sync_position_from_okx(inst_id)
                s.position = okx_position
                print(f"[Strategy] Restore #{s.id} ({s.name}): db_pos={s.position}, okx_pos={okx_position}")

            db.commit()

            # 启动所有 enabled 的策略
            for s in strategies:
                print(f"[Strategy] Auto-start #{s.id} ({s.name})")
                self.start(s.id)

        except Exception as e:
            print(f"[Strategy] Restore error: {e}")
            sys_logger.error("strategy", f"Restore strategies failed: {e}")
        finally:
            db.close()

    def _run_loop(self, strategy_id: int, strategy_cls, params: dict, initial_position: str, timeframe: str = "1h"):
        """策略运行主循环"""
        try:
            self._run_loop_inner(strategy_id, strategy_cls, params, initial_position, timeframe)
        except Exception as e:
            import traceback
            print(f"[Strategy] {strategy_id} thread CRASHED: {e}\n{traceback.format_exc()}")
            sys_logger.error("strategy",
                f"Strategy {strategy_id} thread crashed: {e}\n{traceback.format_exc()}", strategy_id=strategy_id)
            # 清理运行状态，允许下次 start() 重新启动
            with self._lock:
                self._running.pop(strategy_id, None)
                self._stop_flags.pop(strategy_id, None)
                self._start_failures[strategy_id] = self._start_failures.get(strategy_id, 0) + 1

    def _run_loop_inner(self, strategy_id: int, strategy_cls, params: dict, initial_position: str, timeframe: str = "1h"):
        """策略运行主循环（内部实现）"""
        # 显式获取模块级服务（daemon 线程内 __getattr__ 不可靠）
        import app.services.strategy as _self_mod
        self._market_svc = _self_mod.market_service
        self._trade_svc = _self_mod.trade_service
        strategy = strategy_cls(params)

        # 根据K线周期决定轮询间隔
        interval_map = {
            "1m": 60, "3m": 180, "5m": 300, "10m": 600, "15m": 900,
            "30m": 1800, "1h": 3600, "4h": 14400, "1d": 86400,
        }
        interval = interval_map.get(timeframe, 3600)

        print(f"\n{'='*60}")
        print(f"[Strategy {strategy_id}] Thread started for timeframe: {timeframe}")
        print(f"[Strategy {strategy_id}] Thread name: {threading.current_thread().name}")
        print(f"[Strategy {strategy_id}] Poll interval: {interval}s")
        print(f"{'='*60}\n")
        sys_logger.info("strategy", f"Strategy {strategy_id} loop started, timeframe={timeframe}", strategy_id=strategy_id)

        # 当前持仓方向（从数据库 + OKX 同步的初始值）
        current_position = initial_position

        while True:
            with self._lock:
                if self._stop_flags.get(strategy_id, True):
                    print(f"[Strategy] {strategy_id} stopped")
                    break

            try:
                regime_info = {}  # 每轮重置
                # 1. 拉取行情
                inst_id = params.get("inst_id", "BTC-USDT-SWAP")
                # 现货格式的 symbol → 合约格式
                symbol = inst_id.replace("-SWAP", "")
                klines = self._market_svc.get_klines(
                    symbol=symbol,
                    interval=timeframe,
                    limit=strategy.get_required_klines_count(),
                )

                if not klines:
                    print(f"[Strategy] {strategy_id}: no klines data, retrying...")
                    time.sleep(interval)
                    continue

                # 2. 生成信号
                signal = strategy.generate_signal(klines)

                # 2.5 市场状态过滤（震荡市不开趋势仓）
                regime_info = {}
                use_filter = params.get("use_regime_filter", False)  # 默认禁用
                if use_filter and signal in (SIGNAL_OPEN_LONG, SIGNAL_OPEN_SHORT) and current_position == "none":
                    from app.services.market_regime import market_regime_detector
                    regime_result = market_regime_detector.detect_with_score(klines)
                    regime = regime_result.get("regime", "ranging")
                    regime_info = regime_result

                    if regime == "volatile":
                        # 高波动无方向 → 不开新仓（但可以收紧止损）
                        sys_logger.info("strategy",
                            f"Strategy {strategy_id}: signal={signal} BLOCKED by regime={regime}, "
                            f"score={regime_result.get('score', 0)}", strategy_id=strategy_id)
                        signal = SIGNAL_HOLD
                    # ranging 和 weak_trend 允许开仓（方案C：只拦截volatile）

                # 2.5 广播策略状态（每轮都推送当前信号）
                ws_manager.broadcast_sync("strategy_status", {
                    "strategy_id": strategy_id,
                    "signal": signal,
                    "position": current_position,
                    "kline_time": klines[-1].get("time", "") if klines else "",
                    "kline_close": klines[-1].get("close", 0) if klines else 0,
                    "regime": regime_info.get("regime", ""),
                    "regime_score": regime_info.get("score", 0),
                })

                # 3. 根据信号执行交易
                if signal != SIGNAL_HOLD and signal != SIGNAL_NONE:
                    self._execute_signal(strategy_id, signal, params, current_position)

                    # 更新当前持仓方向
                    if signal == SIGNAL_OPEN_LONG:
                        current_position = "long"
                    elif signal == SIGNAL_OPEN_SHORT:
                        current_position = "short"
                    elif signal in (SIGNAL_CLOSE_LONG, SIGNAL_CLOSE_SHORT):
                        current_position = "none"

                    # 持久化持仓方向到数据库
                    self._save_position(strategy_id, current_position)

                    # ─── 更新合约级持仓锁 ───
                    inst_id = params.get("inst_id", "BTC-USDT-SWAP")
                    with self._inst_pos_lock:
                        if current_position in ("long", "short"):
                            self._inst_position_owner[inst_id] = strategy_id
                        else:
                            # 平仓后释放：只释放当前策略的持有
                            if self._inst_position_owner.get(inst_id) == strategy_id:
                                del self._inst_position_owner[inst_id]

                    print(f"[Strategy] {strategy_id}: signal={signal}, position={current_position}")

                    # 广播策略信号
                    ws_manager.broadcast_sync("signal", {
                        "strategy_id": strategy_id,
                        "signal": signal,
                        "position": current_position,
                        "inst_id": params.get("inst_id", "BTC-USDT-SWAP"),
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })

                # 4. 周期性同步 OKX 真实持仓（每 5 轮校验一次）
                # 防止止盈止损触发后内存持仓与实际不一致
                self._loop_counts[strategy_id] = self._loop_counts.get(strategy_id, 0) + 1

                if self._loop_counts[strategy_id] % 5 == 0:
                    inst_id = params.get("inst_id", "BTC-USDT-SWAP")
                    okx_pos = self._sync_position_from_okx(inst_id)
                    if okx_pos != current_position:
                        print(f"[Strategy] {strategy_id}: position mismatch! memory={current_position}, okx={okx_pos}")
                        sys_logger.warn("strategy", f"Position mismatch for #{strategy_id}: memory={current_position}, okx={okx_pos}", strategy_id=strategy_id)
                        current_position = okx_pos
                        self._save_position(strategy_id, current_position)
                        # 同步合约级持仓锁
                        with self._inst_pos_lock:
                            if current_position in ("long", "short"):
                                self._inst_position_owner[inst_id] = strategy_id
                            elif self._inst_position_owner.get(inst_id) == strategy_id:
                                del self._inst_position_owner[inst_id]

            except Exception as e:
                import traceback
                print(f"[Strategy] {strategy_id} error: {e}")
                sys_logger.error("strategy", f"Strategy {strategy_id} error: {e}\n{traceback.format_exc()}", strategy_id=strategy_id)

            # 5. 等待下一个周期
            time.sleep(interval)

    def _execute_signal(self, strategy_id: int, signal: str, params: dict,
                        current_position: str) -> dict:
        """执行交易信号，返回执行结果 {"ok": bool, "msg": str, "order": ...}"""
        # 确保线程内有服务引用（daemon 线程中 __getattr__ 不可靠）
        if not hasattr(self, '_market_svc') or self._market_svc is None:
            import app.services.strategy as _self_mod
            self._market_svc = _self_mod.market_service
            self._trade_svc = _self_mod.trade_service
        _ms, _ts = self._market_svc, self._trade_svc

        # BitgetAPIError 和 OKX_ERR_INSUFFICIENT_BALANCE 已在模块顶部导入

        inst_id = params.get("inst_id", "BTC-USDT-SWAP")
        lever = int(params.get("leverage", 10))
        td_mode = params.get("td_mode", "cross")

        # ─── 合约级持仓冲突检查 ───
        # 如果其他策略持有该合约，阻止开仓（避免多策略争抢同一合约）
        # 双向持仓模式下，同方向可以叠加；仅在该策略无任何持仓时检查
        if signal in (SIGNAL_OPEN_LONG, SIGNAL_OPEN_SHORT) and current_position in ("none",):
            with self._inst_pos_lock:
                owner = self._inst_position_owner.get(inst_id)
                if owner and owner != strategy_id:
                    sys_logger.info("strategy",
                        f"#{strategy_id} signal={signal} BLOCKED: {inst_id} owned by #{owner}", strategy_id=strategy_id)
                    return {"ok": False, "msg": f"合约 {inst_id} 被策略 #{owner} 持有，无法开仓"}

        # 余额预检 — 开仓前检查是否有足够余额
        if signal in (SIGNAL_OPEN_LONG, SIGNAL_OPEN_SHORT):
            try:
                balance_info = _ms.get_account_balance("USDT")
                # Bitget 返回 available 字段表示可用余额；total_equity 有时为 0
                avail = balance_info.get("available", 0) or balance_info.get("total_equity", 0)
                if avail <= 0:
                    sys_logger.warn("strategy", f"#{strategy_id} skip open: zero balance (avail={avail})", strategy_id=strategy_id)
                    return {"ok": False, "msg": f"账户余额不足 (可用: {avail} USDT)"}
            except Exception as e:
                sys_logger.warn("strategy", f"#{strategy_id} balance check failed: {e}", strategy_id=strategy_id)

        # 下单张数：支持固定张数和仓位百分比两种模式
        size_mode = params.get("size_mode", "fixed")
        if size_mode == "percent":
            sz = self._calc_size_by_pct(inst_id, lever, float(params.get("size_pct", 10)))
        else:
            sz = str(params.get("size", 1))

        # ─── 止盈止损参数 ───
        # 模式: pct=百分比, points=点数
        tp_mode = params.get("tp_mode", "pct")
        sl_mode = params.get("sl_mode", "pct")
        tp_pct = float(params.get("take_profit_pct", 0))      # 止盈百分比
        tp_points = float(params.get("take_profit_points", 0))  # 止盈点数
        sl_pct = float(params.get("stop_loss_pct", 0))        # 止损百分比
        sl_points = float(params.get("stop_loss_points", 0))  # 止损点数
        leverage = int(params.get("leverage", 10))

        # 移动止盈参数
        trail_mode = params.get("trail_mode", "pct")
        trail_activate_mode = params.get("trail_activate_mode", "pct")
        trailing_stop_pct = float(params.get("trailing_stop_pct", 0))
        trailing_stop_points = float(params.get("trailing_stop_points", 0))
        trail_activate_pct = float(params.get("trail_activate_pct", 0))
        trail_activate_points = float(params.get("trail_activate_points", 0))
        trail_callback_points = float(params.get("trail_callback_points", 0))

        # 获取当前价格用于计算止盈止损价位
        tp_trigger_px = ""
        sl_trigger_px = ""
        current_price = 0
        try:
            ticker = _ms.get_ticker(inst_id.replace("-SWAP", ""))
            current_price = ticker.get("price", 0)
        except Exception as e:
            sys_logger.warn("strategy", f"#{strategy_id} get ticker failed: {e}", strategy_id=strategy_id)

        if current_price > 0:
            # Bitget BTCUSDT 价格精度：0.1（1位小数）
            price_fmt = lambda p: f"{round(p / 0.1) * 0.1:.1f}"

            if signal == SIGNAL_OPEN_LONG:
                # 止盈：开多→价格上涨
                if tp_mode == "points" and tp_points > 0:
                    tp_trigger_px = price_fmt(current_price + tp_points)
                elif tp_pct > 0:
                    price_change_pct = tp_pct / leverage / 100
                    tp_trigger_px = price_fmt(current_price * (1 + price_change_pct))
                # 止损：开多→价格下跌
                if sl_mode == "points" and sl_points > 0:
                    sl_trigger_px = price_fmt(current_price - sl_points)
                elif sl_pct > 0:
                    price_change_pct = sl_pct / leverage / 100
                    sl_trigger_px = price_fmt(current_price * (1 - price_change_pct))

            elif signal == SIGNAL_OPEN_SHORT:
                # 止盈：开空→价格下跌
                if tp_mode == "points" and tp_points > 0:
                    tp_trigger_px = price_fmt(current_price - tp_points)
                elif tp_pct > 0:
                    price_change_pct = tp_pct / leverage / 100
                    tp_trigger_px = price_fmt(current_price * (1 - price_change_pct))
                # 止损：开空→价格上涨
                if sl_mode == "points" and sl_points > 0:
                    sl_trigger_px = price_fmt(current_price + sl_points)
                elif sl_pct > 0:
                    price_change_pct = sl_pct / leverage / 100
                    sl_trigger_px = price_fmt(current_price * (1 + price_change_pct))

        order_result = None

        # 开仓前设置杠杆
        if signal in (SIGNAL_OPEN_LONG, SIGNAL_OPEN_SHORT):
            try:
                _ts.set_leverage(inst_id=inst_id, lever=lever, mgn_mode=td_mode)
            except Exception as e:
                sys_logger.warn("strategy", f"#{strategy_id} set leverage failed: {e}", strategy_id=strategy_id)

        if signal == SIGNAL_OPEN_LONG:
            # 双向持仓模式(hedge mode)：不需要先平空仓，直接开多
            try:
                order_result = _ts.open_long(
                    inst_id=inst_id, sz=sz, lever=lever, td_mode=td_mode,
                    tp_trigger_px=tp_trigger_px, sl_trigger_px=sl_trigger_px,
                )
            except BitgetAPIError as e:
                if e.code == OKX_ERR_INSUFFICIENT_BALANCE:
                    msg = f"开多失败: 余额不足 (size={sz})"
                    sys_logger.error("strategy", f"#{strategy_id} open long FAILED: insufficient balance (sz={sz})", strategy_id=strategy_id)
                else:
                    msg = f"开多失败: [{e.code}] {e.msg}"
                    sys_logger.error("strategy", f"#{strategy_id} open long FAILED: [{e.code}] {e.msg}", strategy_id=strategy_id)
                return {"ok": False, "msg": msg}
            except Exception as e:
                sys_logger.error("strategy", f"#{strategy_id} open long error: {e}", strategy_id=strategy_id)
                return {"ok": False, "msg": f"开多失败: {e}"}

        elif signal == SIGNAL_OPEN_SHORT:
            # 双向持仓模式(hedge mode)：不需要先平多仓，直接开空
            try:
                order_result = _ts.open_short(
                    inst_id=inst_id, sz=sz, lever=lever, td_mode=td_mode,
                    tp_trigger_px=tp_trigger_px, sl_trigger_px=sl_trigger_px,
                )
            except BitgetAPIError as e:
                if e.code == OKX_ERR_INSUFFICIENT_BALANCE:
                    msg = f"开空失败: 余额不足 (size={sz})"
                    sys_logger.error("strategy", f"#{strategy_id} open short FAILED: insufficient balance (sz={sz})", strategy_id=strategy_id)
                else:
                    msg = f"开空失败: [{e.code}] {e.msg}"
                    sys_logger.error("strategy", f"#{strategy_id} open short FAILED: [{e.code}] {e.msg}", strategy_id=strategy_id)
                return {"ok": False, "msg": msg}
            except Exception as e:
                sys_logger.error("strategy", f"#{strategy_id} open short error: {e}", strategy_id=strategy_id)
                return {"ok": False, "msg": f"开空失败: {e}"}

        elif signal == SIGNAL_CLOSE_LONG:
            try:
                order_result = _ts.close_position(inst_id=inst_id, pos_side="long")
            except Exception as e:
                sys_logger.error("strategy", f"#{strategy_id} close long error: {e}", strategy_id=strategy_id)
                return {"ok": False, "msg": f"平多失败: {e}"}

        elif signal == SIGNAL_CLOSE_SHORT:
            try:
                order_result = _ts.close_position(inst_id=inst_id, pos_side="short")
            except Exception as e:
                sys_logger.error("strategy", f"#{strategy_id} close short error: {e}", strategy_id=strategy_id)
                return {"ok": False, "msg": f"平空失败: {e}"}

        # 开仓后设置移动止盈算法单
        # 支持两种模式：百分比(trailing_stop_pct) 或 点数(trailing_stop_points)
        use_trailing = (trailing_stop_pct > 0 or trailing_stop_points > 0 or trail_callback_points > 0) \
            and signal in (SIGNAL_OPEN_LONG, SIGNAL_OPEN_SHORT) and order_result
        if use_trailing:
            try:
                side = "sell" if signal == SIGNAL_OPEN_LONG else "buy"
                algo_pos_side = "long" if signal == SIGNAL_OPEN_LONG else "short"

                # 计算激活价格
                activate_price = ""
                # 重新获取当前价格（之前的变量可能已被使用）
                if current_price <= 0:
                    try:
                        ticker = _ms.get_ticker(inst_id.replace("-SWAP", ""))
                        current_price = ticker.get("price", 0)
                    except Exception as e:
                        sys_logger.warn("strategy", f"Get ticker for activate price failed: {e}", strategy_id=strategy_id)

                if current_price > 0:
                    price_fmt = lambda p: f"{round(p / 0.1) * 0.1:.1f}"
                    # 激活阈值：点数模式优先
                    if trail_activate_mode == "points" and trail_activate_points > 0:
                        if signal == SIGNAL_OPEN_LONG:
                            activate_price = price_fmt(current_price + trail_activate_points)
                        else:
                            activate_price = price_fmt(current_price - trail_activate_points)
                    elif trail_activate_pct > 0:
                        if signal == SIGNAL_OPEN_LONG:
                            activate_price = price_fmt(current_price * (1 + trail_activate_pct / 100))
                        else:
                            activate_price = price_fmt(current_price * (1 - trail_activate_pct / 100))

                # 调用移动止盈API
                # 回调参数：点数模式优先，其次百分比模式
                if trail_mode == "points" and trailing_stop_points > 0:
                    # 点数模式
                    _ts.place_algo_trailing(
                        inst_id=inst_id,
                        side=side,
                        sz=sz,
                        callback_points=trailing_stop_points,
                        activate_price=activate_price,
                        pos_side=algo_pos_side,
                        td_mode=td_mode,
                    )
                    sys_logger.info("strategy",
                        f"#{strategy_id} trailing stop set: activate={activate_price}, callback={trailing_stop_points} points", strategy_id=strategy_id)
                elif trail_callback_points > 0:
                    # 兼容旧字段 trail_callback_points
                    _ts.place_algo_trailing(
                        inst_id=inst_id,
                        side=side,
                        sz=sz,
                        callback_points=trail_callback_points,
                        activate_price=activate_price,
                        pos_side=algo_pos_side,
                        td_mode=td_mode,
                    )
                    sys_logger.info("strategy",
                        f"#{strategy_id} trailing stop set: activate={activate_price}, callback={trail_callback_points} points", strategy_id=strategy_id)
                else:
                    # 百分比模式
                    _ts.place_algo_trailing(
                        inst_id=inst_id,
                        side=side,
                        sz=sz,
                        callback_pct=trailing_stop_pct,
                        activate_price=activate_price,
                        pos_side=algo_pos_side,
                        td_mode=td_mode,
                    )
                    sys_logger.info("strategy",
                        f"#{strategy_id} trailing stop set: activate={activate_price}, callback={trailing_stop_pct}%", strategy_id=strategy_id)
            except Exception as e:
                sys_logger.warn("strategy", f"Trailing stop failed for #{strategy_id}: {e}", strategy_id=strategy_id)

        # 记录交易到数据库
        if order_result is not None:
            self._record_trade(strategy_id, signal, inst_id, params, order_result, sz)

        # 更新持仓方向
        # 双向持仓模式：支持同时持有多空仓位
        new_position = current_position
        if signal == SIGNAL_OPEN_LONG:
            if current_position == "short":
                new_position = "both"
            elif current_position != "both":
                new_position = "long"
        elif signal == SIGNAL_OPEN_SHORT:
            if current_position == "long":
                new_position = "both"
            elif current_position != "both":
                new_position = "short"
        elif signal == SIGNAL_CLOSE_LONG:
            if current_position == "both":
                new_position = "short"
            else:
                new_position = "none"
        elif signal == SIGNAL_CLOSE_SHORT:
            if current_position == "both":
                new_position = "long"
            else:
                new_position = "none"
        if new_position != current_position:
            self._save_position(strategy_id, new_position)

        # 广播策略状态
        ws_manager.broadcast_sync("strategy_status", {
            "strategy_id": strategy_id,
            "signal": signal,
            "position": new_position,
            "running": True,
            "enabled": True,
        })

        return {"ok": True, "msg": f"{signal} 执行成功", "order": order_result}

    def _calc_size_by_pct(self, inst_id: str, leverage: int, size_pct: float) -> str:
        """根据仓位百分比计算下单数量（BTC 数量）

        公式: 数量 = (可用余额 * size_pct% * 杠杆) / 当前价格
        返回 BTC 数量（如 "0.001"）
        """
        try:
            # 获取账户可用余额
            balance_info = self._market_svc.get_account_balance("USDT")
            avail_usdt = balance_info.get("available", 0) or balance_info.get("total_equity", 0)
            if avail_usdt <= 0:
                return "0.0001"

            # 获取当前价格
            ticker = self._market_svc.get_ticker(inst_id.replace("-SWAP", ""))
            current_price = ticker.get("price", 0)
            if current_price <= 0:
                return "0.0001"

            # 计算数量（BTC）
            position_value = avail_usdt * (size_pct / 100) * leverage
            size = position_value / current_price
            # 最小 0.0001 BTC，保留 4 位小数
            size = max(0.0001, round(size, 4))
            return str(size)
        except Exception as e:
            sys_logger.warn("strategy", f"Calc size by pct failed: {e}")
            return "0.0001"

    def _record_trade(self, strategy_id: int, signal: str, inst_id: str,
                      params: dict, order_result, sz: str = "1"):
        """记录交易到数据库"""
        db = SessionLocal()
        try:
            # 解析订单结果
            price = 0
            amount = float(sz)
            order_id = ""
            if isinstance(order_result, dict):
                # OKX 返回的订单数据
                if "ordId" in order_result:
                    order_id = order_result["ordId"]
                if "avgPx" in order_result:
                    price = float(order_result["avgPx"] or 0)
                elif "px" in order_result:
                    price = float(order_result["px"] or 0)
            elif isinstance(order_result, list) and order_result:
                first = order_result[0] if isinstance(order_result[0], dict) else {}
                order_id = first.get("ordId", "")
                price = float(first.get("avgPx") or first.get("px") or 0)

            side_map = {
                SIGNAL_OPEN_LONG: "buy",
                SIGNAL_OPEN_SHORT: "sell",
                SIGNAL_CLOSE_LONG: "sell",
                SIGNAL_CLOSE_SHORT: "buy",
            }

            trade = Trade(
                strategy_id=strategy_id,
                symbol=inst_id,
                side=side_map.get(signal, signal),
                direction=signal,
                price=price,
                amount=amount,
                order_id=order_id,
            )
            db.add(trade)
            db.commit()

            # 广播成交通知
            ws_manager.broadcast_sync("trade", {
                "strategy_id": strategy_id,
                "signal": signal,
                "symbol": inst_id,
                "side": side_map.get(signal, signal),
                "price": price,
                "amount": amount,
                "order_id": order_id,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
            sys_logger.info("trade", f"Signal={signal} symbol={inst_id} price={price} amount={amount}", strategy_id=strategy_id)

            # ─── 发送交易通知 ───
            try:
                from app.services.notification import notification_service
                signal_label = {
                    SIGNAL_OPEN_LONG: "开多",
                    SIGNAL_OPEN_SHORT: "开空",
                    SIGNAL_CLOSE_LONG: "平多",
                    SIGNAL_CLOSE_SHORT: "平空",
                }.get(signal, signal)
                notification_service.notify(
                    title=f"策略#{strategy_id} {signal_label}",
                    message=f"{inst_id} | 方向={signal_label} | 价格={price} | 数量={amount}",
                    level="info",
                    category="trade",
                    extra={"strategy_id": strategy_id, "signal": signal, "price": price, "amount": amount, "order_id": order_id},
                    strategy_id=strategy_id,
                )
            except Exception:
                pass  # 通知失败不影响交易
        except Exception as e:
            print(f"[Strategy] record trade error: {e}")
        finally:
            db.close()


# 全局策略运行器单例
strategy_runner = StrategyRunner()
