"""市场状态识别器 — 判断当前市场是趋势还是震荡

核心思想：
1. BTC 1h 级别，简单技术指标策略之所以亏钱，是因为趋势策略在震荡市里反复假突破
2. 如果能过滤掉震荡市中的开仓信号，只在趋势市开仓，胜率会显著提升
3. 本模块提供 MarketRegimeDetector 类，输出 "trending" / "ranging" / "volatile" 三种状态

实现方法（多维度综合评分）：
- ADX（平均方向指数）：衡量趋势强度，ADX>25 为趋势市
- 波动率压缩：近期波动率 vs 远期波动率的比值，压缩后容易爆发趋势
- 价格位置：价格偏离均线的程度，偏离大说明趋势强
- ATR 变化率：ATR 快速扩大通常意味着趋势启动

使用方式：
    detector = MarketRegimeDetector()
    regime = detector.detect(klines)
    # regime = "trending" / "ranging" / "volatile"

    # 在策略引擎中：
    if regime == "ranging":
        signal = SIGNAL_HOLD  # 震荡市不开趋势仓
"""

from typing import Literal

RegimeType = Literal["strong_trend", "trending", "weak_trend", "ranging", "volatile"]


class MarketRegimeDetector:
    """市场状态识别器

    状态定义：
    - "strong_trend": 强趋势，ADX高+价格偏离大+ATR扩大 → 最佳开仓窗口
    - "trending": 趋势市，有方向性 → 可以开仓
    - "weak_trend": 弱趋势/过渡 → 可以缩小仓位开仓
    - "ranging": 震荡市，无方向 → 不开新趋势仓
    - "volatile": 高波动无方向 → 不开仓，已有仓收紧止损
    """

    def __init__(self, params: dict = None):
        p = params or {}
        # ADX 参数（BTC 1h 的 ADX 通常在 12-40 之间，阈值需要偏低）
        self.adx_period = int(p.get("adx_period", 14))
        self.adx_threshold = float(p.get("adx_threshold", 20))   # ADX > 20 为趋势（降低阈值）
        self.adx_strong = float(p.get("adx_strong", 30))          # ADX > 30 为强趋势
        self.adx_weak = float(p.get("adx_weak", 15))              # ADX < 15 明确震荡

        # 波动率参数
        self.vol_short = int(p.get("vol_short_period", 10))    # 短期波动率周期
        self.vol_long = int(p.get("vol_long_period", 50))      # 长期波动率周期
        self.vol_squeeze_threshold = float(p.get("vol_squeeze", 0.7))  # 短/长 < 此值为压缩

        # 均线偏离参数
        self.ma_period = int(p.get("ma_period", 50))
        self.deviation_threshold = float(p.get("deviation_threshold", 0.02))  # 偏离2%以上

        # ATR 变化率参数
        self.atr_period = int(p.get("atr_period", 14))
        self.atr_change_threshold = float(p.get("atr_change_threshold", 0.3))  # ATR变化率>30%

    def detect(self, klines: list) -> RegimeType:
        """识别当前市场状态

        Args:
            klines: K线数据（需要至少 vol_long + 10 根）

        Returns:
            "strong_trend" — 强趋势，最佳开仓窗口
            "trending"     — 趋势市，可以开仓
            "weak_trend"   — 弱趋势/过渡，可缩小仓位开仓
            "ranging"      — 震荡市，不开趋势仓
            "volatile"     — 高波动无方向，不开仓
        """
        if len(klines) < self.vol_long + 10:
            return "ranging"  # 数据不足，默认震荡

        closes = [k["close"] for k in klines]
        highs = [k["high"] for k in klines]
        lows = [k["low"] for k in klines]

        # 计算各维度得分（0~1，越高越倾向趋势）
        scores = []

        # 1. ADX 评分
        adx_score = self._adx_score(closes, highs, lows)
        if adx_score is not None:
            scores.append(("adx", adx_score, 0.40))  # ADX 权重提高到 40%

        # 2. 波动率压缩评分
        vol_score = self._volatility_score(closes)
        if vol_score is not None:
            scores.append(("vol", vol_score, 0.20))

        # 3. 均线偏离评分
        dev_score = self._deviation_score(closes)
        if dev_score is not None:
            scores.append(("dev", dev_score, 0.25))

        # 4. ATR 变化率评分
        atr_score = self._atr_change_score(highs, lows, closes)
        if atr_score is not None:
            scores.append(("atr", atr_score, 0.15))

        if not scores:
            return "ranging"

        # 加权综合得分
        total_weight = sum(w for _, _, w in scores)
        weighted_score = sum(s * w for _, s, w in scores) / total_weight

        # 阈值判断（5级分类）
        if weighted_score >= 0.75:
            return "strong_trend"
        elif weighted_score >= 0.55:
            return "trending"
        elif weighted_score >= 0.40:
            return "weak_trend"
        elif weighted_score >= 0.25:
            return "volatile"
        else:
            return "ranging"

    def detect_with_score(self, klines: list) -> dict:
        """识别市场状态并返回详细评分

        Returns:
            {
                "regime": "trending"/"ranging"/"volatile",
                "score": float,  # 0~1 综合得分
                "details": {
                    "adx": {"value": float, "score": float},
                    "vol_ratio": {"value": float, "score": float},
                    "deviation": {"value": float, "score": float},
                    "atr_change": {"value": float, "score": float},
                }
            }
        """
        if len(klines) < self.vol_long + 10:
            return {
                "regime": "ranging",
                "score": 0,
                "details": {},
                "reason": "insufficient data"
            }

        closes = [k["close"] for k in klines]
        highs = [k["high"] for k in klines]
        lows = [k["low"] for k in klines]

        details = {}
        scores = []

        # ADX
        adx_val, adx_sc = self._adx_score_raw(closes, highs, lows)
        if adx_val is not None:
            details["adx"] = {"value": round(adx_val, 2), "score": round(adx_sc, 3)}
            scores.append(("adx", adx_sc, 0.35))

        # 波动率
        vol_val, vol_sc = self._volatility_score_raw(closes)
        if vol_val is not None:
            details["vol_ratio"] = {"value": round(vol_val, 3), "score": round(vol_sc, 3)}
            scores.append(("vol", vol_sc, 0.20))

        # 偏离度
        dev_val, dev_sc = self._deviation_score_raw(closes)
        if dev_val is not None:
            details["deviation"] = {"value": round(dev_val, 4), "score": round(dev_sc, 3)}
            scores.append(("dev", dev_sc, 0.25))

        # ATR变化
        atr_val, atr_sc = self._atr_change_score_raw(highs, lows, closes)
        if atr_val is not None:
            details["atr_change"] = {"value": round(atr_val, 3), "score": round(atr_sc, 3)}
            scores.append(("atr", atr_sc, 0.20))

        if not scores:
            return {"regime": "ranging", "score": 0, "details": details}

        total_weight = sum(w for _, _, w in scores)
        weighted_score = sum(s * w for _, s, w in scores) / total_weight

        if weighted_score >= 0.75:
            regime = "strong_trend"
        elif weighted_score >= 0.55:
            regime = "trending"
        elif weighted_score >= 0.40:
            regime = "weak_trend"
        elif weighted_score >= 0.25:
            regime = "volatile"
        else:
            regime = "ranging"

        return {
            "regime": regime,
            "score": round(weighted_score, 3),
            "details": details,
        }

    # ─── ADX（平均方向指数）───

    def _calc_adx(self, highs: list, lows: list, closes: list, period: int = 14) -> float:
        """计算 ADX 值"""
        n = len(closes)
        if n < period * 2 + 1:
            return None

        # 计算 +DM 和 -DM
        plus_dm_list = []
        minus_dm_list = []
        for i in range(1, n):
            high_diff = highs[i] - highs[i - 1]
            low_diff = lows[i - 1] - lows[i]
            plus_dm = high_diff if high_diff > low_diff and high_diff > 0 else 0
            minus_dm = low_diff if low_diff > high_diff and low_diff > 0 else 0
            plus_dm_list.append(plus_dm)
            minus_dm_list.append(minus_dm)

        # 计算 TR (True Range)
        tr_list = []
        for i in range(1, n):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            tr_list.append(tr)

        # 平滑处理（Wilder 方法）
        def wilder_smooth(data, period):
            result = [sum(data[:period])]
            for i in range(period, len(data)):
                result.append(result[-1] - result[-1] / period + data[i])
            return result

        if len(tr_list) < period or len(plus_dm_list) < period:
            return None

        atr = wilder_smooth(tr_list, period)
        plus_dm_smooth = wilder_smooth(plus_dm_list, period)
        minus_dm_smooth = wilder_smooth(minus_dm_list, period)

        # 计算 +DI 和 -DI
        dx_list = []
        for i in range(len(atr)):
            if atr[i] == 0:
                continue
            plus_di = 100 * plus_dm_smooth[i] / atr[i]
            minus_di = 100 * minus_dm_smooth[i] / atr[i]
            di_sum = plus_di + minus_di
            if di_sum == 0:
                dx_list.append(0)
            else:
                dx_list.append(100 * abs(plus_di - minus_di) / di_sum)

        # ADX = DX 的平滑
        if len(dx_list) < period:
            return None

        adx = sum(dx_list[-period:]) / period
        return adx

    def _adx_score(self, closes, highs, lows):
        adx = self._calc_adx(highs, lows, closes, self.adx_period)
        if adx is None:
            return None
        if adx >= self.adx_strong:
            return 1.0
        elif adx >= self.adx_threshold:
            return 0.5 + 0.5 * (adx - self.adx_threshold) / (self.adx_strong - self.adx_threshold)
        elif adx >= self.adx_weak:
            return 0.2 + 0.3 * (adx - self.adx_weak) / (self.adx_threshold - self.adx_weak)
        else:
            return 0.2 * adx / max(self.adx_weak, 1)

    def _adx_score_raw(self, closes, highs, lows):
        adx = self._calc_adx(highs, lows, closes, self.adx_period)
        if adx is None:
            return None, None
        score = self._adx_score(closes, highs, lows)
        return adx, score

    # ─── 波动率压缩 ───

    def _volatility_score(self, closes):
        val, sc = self._volatility_score_raw(closes)
        return sc

    def _volatility_score_raw(self, closes):
        n = len(closes)
        if n < self.vol_long + 5:
            return None, None

        # 短期波动率（收益率标准差）
        short_returns = [(closes[i] - closes[i-1]) / closes[i-1]
                         for i in range(n - self.vol_short, n)]
        short_vol = (sum(r**2 for r in short_returns) / len(short_returns)) ** 0.5

        # 长期波动率
        long_returns = [(closes[i] - closes[i-1]) / closes[i-1]
                        for i in range(n - self.vol_long, n)]
        long_vol = (sum(r**2 for r in long_returns) / len(long_returns)) ** 0.5

        if long_vol == 0:
            return None, None

        ratio = short_vol / long_vol

        # 波动率压缩（ratio < squeeze_threshold）→ 预示趋势即将爆发
        # 但还在压缩中，先不开仓
        # ratio > 1 → 短期波动率扩大，趋势已经启动
        if ratio < self.vol_squeeze_threshold:
            # 压缩中，趋势未启动
            score = 0.3
        elif ratio > 1.3:
            # 短期波动显著扩大，趋势确认
            score = 1.0
        elif ratio > 1.0:
            # 短期波动略大于长期，趋势可能启动
            score = 0.5 + 0.5 * (ratio - 1.0) / 0.3
        else:
            # 正常范围
            score = 0.3 + 0.2 * (ratio - self.vol_squeeze_threshold) / (1.0 - self.vol_squeeze_threshold)

        return ratio, max(0, min(1, score))

    # ─── 均线偏离度 ───

    def _deviation_score(self, closes):
        val, sc = self._deviation_score_raw(closes)
        return sc

    def _deviation_score_raw(self, closes):
        n = len(closes)
        if n < self.ma_period:
            return None, None

        ma = sum(closes[-self.ma_period:]) / self.ma_period
        current = closes[-1]
        deviation = abs(current - ma) / ma

        # 偏离越大，趋势越强
        if deviation > self.deviation_threshold * 2:
            score = 1.0
        elif deviation > self.deviation_threshold:
            score = 0.5 + 0.5 * (deviation - self.deviation_threshold) / self.deviation_threshold
        else:
            score = deviation / self.deviation_threshold * 0.5

        return deviation, score

    # ─── ATR 变化率 ───

    def _calc_atr(self, highs, lows, closes, period=14):
        """计算 ATR"""
        n = len(closes)
        if n < period + 1:
            return None

        tr_list = []
        for i in range(1, n):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            tr_list.append(tr)

        if len(tr_list) < period:
            return None

        # 简单移动平均 ATR
        atr = sum(tr_list[-period:]) / period
        return atr

    def _atr_change_score(self, highs, lows, closes):
        val, sc = self._atr_change_score_raw(highs, lows, closes)
        return sc

    def _atr_change_score_raw(self, highs, lows, closes):
        n = len(closes)
        half = self.atr_period * 2
        if n < half + self.atr_period:
            return None, None

        # 当前 ATR
        current_atr = self._calc_atr(highs[-half:], lows[-half:], closes[-half:], self.atr_period)

        # 之前的 ATR
        prev_atr = self._calc_atr(
            highs[-(half + self.atr_period):-self.atr_period],
            lows[-(half + self.atr_period):-self.atr_period],
            closes[-(half + self.atr_period):-self.atr_period],
            self.atr_period,
        )

        if current_atr is None or prev_atr is None or prev_atr == 0:
            return None, None

        change_rate = (current_atr - prev_atr) / prev_atr

        # ATR 扩大 → 趋势启动
        if change_rate > self.atr_change_threshold:
            score = 1.0
        elif change_rate > 0:
            score = 0.5 + 0.5 * change_rate / self.atr_change_threshold
        elif change_rate > -self.atr_change_threshold:
            score = 0.5 * (1 + change_rate / self.atr_change_threshold)
        else:
            score = 0

        return change_rate, max(0, min(1, score))


# ─── 全局实例 ───
market_regime_detector = MarketRegimeDetector()
