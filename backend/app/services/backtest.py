"""回测引擎 - 历史K线模拟+收益计算

用历史K线数据模拟策略运行，计算：
- 总收益率
- 最大回撤
- 夏普比率
- 胜率
- 交易次数
- 收益曲线

改进点（v2）：
- 手续费：OKX VIP0 合约 maker 0.02% / taker 0.05%，回测用 taker 费率
- 滑点：可配置，默认 0.05%
- 仓位：支持固定张数和仓位百分比两种模式（与实盘策略对齐）
- 止盈止损：支持固定止盈/止损 + 移动止损
- 全仓模式保证金计算
"""
import json
from datetime import datetime
from typing import Optional

from app.database import SessionLocal
from app.models import BacktestResult
from app.services.cache import get_cached_market_service
from app.services.strategy import (
    BaseStrategy, get_strategy_class, list_available_strategies,
    SIGNAL_OPEN_LONG, SIGNAL_OPEN_SHORT, SIGNAL_CLOSE_LONG, SIGNAL_CLOSE_SHORT,
    SIGNAL_HOLD, SIGNAL_NONE,
)


# OKX 合约费率（VIP0）
TAKER_FEE_RATE = 0.0005     # taker 0.05%
MAKER_FEE_RATE = 0.0002     # maker 0.02%
DEFAULT_SLIPPAGE = 0.0005    # 滑点 0.05%

# 合约面值（1张合约代表多少币）
FACE_VALUE_MAP = {
    "BTC-USDT-SWAP": 0.01,
    "ETH-USDT-SWAP": 0.1,
    "SOL-USDT-SWAP": 1,
}


class BacktestEngine:
    """回测引擎"""

    def run(
        self,
        strategy_type: str,
        params: dict,
        symbol: str = "BTC-USDT-SWAP",
        timeframe: str = "1h",
        klines: list = None,
        initial_capital: float = 10000,
        leverage: int = 10,
        fee_rate: float = TAKER_FEE_RATE,
        slippage: float = DEFAULT_SLIPPAGE,
        regime_filter: bool = False,
    ) -> dict:
        """执行回测

        Args:
            strategy_type: 策略类型 ma_cross/rsi/bollinger
            params: 策略参数（含 size_mode/size/size_pct/tp/sl/trailing 等）
            symbol: 交易对
            timeframe: K线周期
            klines: K线数据（如果为None则从API获取）
            initial_capital: 初始资金
            leverage: 杠杆倍数
            fee_rate: 手续费率，默认 taker 0.05%
            slippage: 滑点比例，默认 0.05%
            regime_filter: 是否启用市场状态过滤

        Returns:
            回测结果字典
        """
        # 获取策略类
        strategy_cls = get_strategy_class(strategy_type)
        if not strategy_cls:
            return {"ok": False, "msg": f"unknown strategy: {strategy_type}"}

        strategy = strategy_cls(params)

        # 获取K线数据
        if klines is None:
            spot_symbol = symbol.replace("-SWAP", "")
            klines = get_cached_market_service().get_klines(
                symbol=spot_symbol,
                timeframe=timeframe,
                limit=300,
            )

        if not klines or len(klines) < 50:
            return {"ok": False, "msg": "insufficient kline data"}

        # 合并参数
        params["timeframe"] = timeframe
        params["inst_id"] = symbol

        # 运行回测
        result = self._simulate(
            strategy, klines, initial_capital, leverage,
            fee_rate=fee_rate, slippage=slippage,
            regime_filter=regime_filter,
        )

        # 保存到数据库
        self._save_result(
            strategy_type=strategy_type,
            params=params,
            symbol=symbol,
            timeframe=timeframe,
            klines=klines,
            initial_capital=initial_capital,
            result=result,
        )

        return result

    def _simulate(
        self,
        strategy: BaseStrategy,
        klines: list,
        initial_capital: float,
        leverage: int,
        fee_rate: float = TAKER_FEE_RATE,
        slippage: float = DEFAULT_SLIPPAGE,
        regime_filter: bool = False,
    ) -> dict:
        """模拟策略运行

        Args:
            regime_filter: 是否启用市场状态过滤（震荡市不开趋势仓）
        """
        capital = initial_capital      # 可用资金
        position = None                # {"side": "long"/"short", "entry_price": float, "sz": int, "margin": float, "highest": float, "lowest": float}
        trades = []                    # 交易记录
        equity_curve = []              # 权益曲线
        peak_equity = initial_capital
        max_drawdown = 0
        total_fees = 0                 # 累计手续费
        regime_stats = {"strong_trend": 0, "trending": 0, "weak_trend": 0, "ranging": 0, "volatile": 0, "filtered": 0}  # 状态统计

        # 从策略参数读取风控配置（与实盘策略对齐）
        params = strategy.params
        tp_pct = float(params.get("take_profit_pct", 0))
        sl_pct = float(params.get("stop_loss_pct", 0))
        trailing_pct = float(params.get("trailing_stop_pct", 0))
        trailing_activation_pct = float(params.get("trailing_activation_pct", 0))  # 移动止盈激活阈值(%)
        trailing_callback_points = float(params.get("trailing_callback_points", 0))  # 移动止盈回调点数
        size_mode = params.get("size_mode", "fixed")
        fixed_sz = float(params.get("size", 1))
        size_pct = float(params.get("size_pct", 10))
        inst_id = params.get("inst_id", "BTC-USDT-SWAP")
        face_value = FACE_VALUE_MAP.get(inst_id, 0.01)

        # 滑动窗口遍历K线
        min_klines = strategy.get_required_klines_count()

        for i in range(min_klines, len(klines)):
            window = klines[:i + 1]
            current_price = klines[i]["close"]
            current_high = klines[i].get("high", current_price)
            current_low = klines[i].get("low", current_price)
            current_time = klines[i].get("timestamp", i)

            # ── 1. 检查止损止盈 / 移动止损 ──
            if position:
                closed = self._check_sl_tp_trailing(
                    position, current_price, current_high, current_low,
                    tp_pct, sl_pct, trailing_pct, trailing_activation_pct,
                    trailing_callback_points,
                )
                if closed:
                    # 平仓（考虑滑点）
                    if position["side"] == "long":
                        fill_price = current_price * (1 - slippage)
                    else:
                        fill_price = current_price * (1 + slippage)

                    # 计算盈亏
                    pnl = self._calc_pnl(position, fill_price, face_value)
                    # 平仓手续费
                    close_fee = abs(position["sz"]) * face_value * fill_price * fee_rate
                    total_fees += close_fee

                    capital += position["margin"] + pnl - close_fee

                    trades.append({
                        "time": current_time,
                        "side": "close_" + position["side"],
                        "price": round(fill_price, 2),
                        "sz": position["sz"],
                        "pnl": round(pnl - close_fee, 4),
                        "fee": round(close_fee, 4),
                        "reason": closed,
                    })
                    position = None

            # ── 2. 生成信号 ──
            signal = strategy.generate_signal(window)

            # ── 2.5 市场状态过滤（可选）──
            if regime_filter and signal in (SIGNAL_OPEN_LONG, SIGNAL_OPEN_SHORT) and position is None:
                from app.services.market_regime import market_regime_detector
                regime = market_regime_detector.detect(window)
                regime_stats[regime] += 1
                if regime == "ranging":
                    # 震荡市不开趋势仓
                    regime_stats["filtered"] += 1
                    signal = SIGNAL_HOLD
                elif regime == "volatile":
                    # 高波动无方向，不开仓
                    regime_stats["filtered"] += 1
                    signal = SIGNAL_HOLD
                elif regime == "weak_trend":
                    # 弱趋势：可以开仓但减半仓位（通过调整 params 中的 size）
                    # 回测中暂不做仓位调整，只在实盘引擎中处理
                    pass  # 允许开仓

            # ── 3. 执行信号 ──
            if signal == SIGNAL_OPEN_LONG and position is None:
                sz, margin = self._calc_position_size(
                    size_mode, fixed_sz, size_pct, capital, leverage,
                    current_price, face_value,
                )
                # 开仓滑点
                fill_price = current_price * (1 + slippage)
                # 开仓手续费
                open_fee = sz * face_value * fill_price * fee_rate
                total_fees += open_fee

                position = {
                    "side": "long",
                    "entry_price": fill_price,
                    "sz": sz,
                    "margin": margin,
                    "highest": fill_price,    # 移动止损追踪最高价
                    "lowest": fill_price,
                    "leverage": leverage,     # 保存杠杆倍数
                }
                capital -= (margin + open_fee)

                trades.append({
                    "time": current_time,
                    "side": "open_long",
                    "price": round(fill_price, 2),
                    "sz": sz,
                    "margin": round(margin, 2),
                    "fee": round(open_fee, 4),
                })

            elif signal == SIGNAL_OPEN_SHORT and position is None:
                sz, margin = self._calc_position_size(
                    size_mode, fixed_sz, size_pct, capital, leverage,
                    current_price, face_value,
                )
                # 开仓滑点
                fill_price = current_price * (1 - slippage)
                # 开仓手续费
                open_fee = sz * face_value * fill_price * fee_rate
                total_fees += open_fee

                position = {
                    "side": "short",
                    "entry_price": fill_price,
                    "sz": sz,
                    "margin": margin,
                    "highest": fill_price,
                    "lowest": fill_price,
                    "leverage": leverage,     # 保存杠杆倍数
                }
                capital -= (margin + open_fee)

                trades.append({
                    "time": current_time,
                    "side": "open_short",
                    "price": round(fill_price, 2),
                    "sz": sz,
                    "margin": round(margin, 2),
                    "fee": round(open_fee, 4),
                })

            elif signal == SIGNAL_CLOSE_LONG and position and position["side"] == "long":
                fill_price = current_price * (1 - slippage)
                pnl = self._calc_pnl(position, fill_price, face_value)
                close_fee = abs(position["sz"]) * face_value * fill_price * fee_rate
                total_fees += close_fee

                capital += position["margin"] + pnl - close_fee

                trades.append({
                    "time": current_time,
                    "side": "close_long",
                    "price": round(fill_price, 2),
                    "sz": position["sz"],
                    "pnl": round(pnl - close_fee, 4),
                    "fee": round(close_fee, 4),
                    "reason": "signal",
                })
                position = None

            elif signal == SIGNAL_CLOSE_SHORT and position and position["side"] == "short":
                fill_price = current_price * (1 + slippage)
                pnl = self._calc_pnl(position, fill_price, face_value)
                close_fee = abs(position["sz"]) * face_value * fill_price * fee_rate
                total_fees += close_fee

                capital += position["margin"] + pnl - close_fee

                trades.append({
                    "time": current_time,
                    "side": "close_short",
                    "price": round(fill_price, 2),
                    "sz": position["sz"],
                    "pnl": round(pnl - close_fee, 4),
                    "fee": round(close_fee, 4),
                    "reason": "signal",
                })
                position = None

            # 更新移动止损追踪价
            if position:
                if current_high > position["highest"]:
                    position["highest"] = current_high
                if current_low < position["lowest"]:
                    position["lowest"] = current_low

            # ── 4. 计算当前权益 ──
            unrealized_pnl = self._calc_pnl(position, current_price, face_value) if position else 0
            current_equity = capital + (position["margin"] if position else 0) + unrealized_pnl

            equity_curve.append({
                "time": current_time,
                "equity": round(current_equity, 2),
            })

            # ── 5. 更新最大回撤 ──
            if current_equity > peak_equity:
                peak_equity = current_equity
            drawdown = (peak_equity - current_equity) / peak_equity * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # 最后如果还有持仓，按最后价格平仓
        if position:
            final_price = klines[-1]["close"]
            if position["side"] == "long":
                fill_price = final_price * (1 - slippage)
            else:
                fill_price = final_price * (1 + slippage)

            pnl = self._calc_pnl(position, fill_price, face_value)
            close_fee = abs(position["sz"]) * face_value * fill_price * fee_rate
            total_fees += close_fee

            capital += position["margin"] + pnl - close_fee

            trades.append({
                "time": klines[-1].get("timestamp", len(klines) - 1),
                "side": "close_" + position["side"],
                "price": round(fill_price, 2),
                "sz": position["sz"],
                "pnl": round(pnl - close_fee, 4),
                "fee": round(close_fee, 4),
                "reason": "backtest_end",
            })

        final_capital = capital

        # ── 计算统计指标 ──
        total_return = (final_capital - initial_capital) / initial_capital * 100

        # 胜率
        win_trades = [t for t in trades if t.get("pnl", 0) > 0]
        lose_trades = [t for t in trades if t.get("pnl", 0) < 0]
        close_trades = [t for t in trades if "close" in t.get("side", "")]
        win_rate = len(win_trades) / len(close_trades) * 100 if close_trades else 0

        # 盈亏比
        avg_win = sum(t["pnl"] for t in win_trades) / len(win_trades) if win_trades else 0
        avg_loss = abs(sum(t["pnl"] for t in lose_trades) / len(lose_trades)) if lose_trades else 1
        profit_factor = avg_win / avg_loss if avg_loss > 0 else 0

        # 夏普比率（简化版）
        daily_returns = []
        for i in range(1, len(equity_curve)):
            prev_eq = equity_curve[i - 1]["equity"]
            curr_eq = equity_curve[i]["equity"]
            if prev_eq > 0:
                daily_returns.append((curr_eq - prev_eq) / prev_eq)

        sharpe = 0
        if len(daily_returns) > 1:
            avg_ret = sum(daily_returns) / len(daily_returns)
            variance = sum((r - avg_ret) ** 2 for r in daily_returns) / len(daily_returns)
            std_ret = variance ** 0.5
            if std_ret > 0:
                sharpe = avg_ret / std_ret * (365 ** 0.5)

        return {
            "ok": True,
            "initial_capital": initial_capital,
            "final_capital": round(final_capital, 2),
            "total_return": round(total_return, 2),
            "max_drawdown": round(max_drawdown, 2),
            "sharpe_ratio": round(sharpe, 2),
            "win_rate": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2),
            "trade_count": len(close_trades),
            "win_count": len(win_trades),
            "lose_count": len(lose_trades),
            "total_fees": round(total_fees, 2),
            "trades": trades,
            "equity_curve": equity_curve,
            "leverage": leverage,
            "fee_rate": fee_rate,
            "slippage": slippage,
            "regime_stats": regime_stats,
        }

    def _calc_position_size(
        self, size_mode: str, fixed_sz: float, size_pct: float,
        capital: float, leverage: int, current_price: float, face_value: float,
    ) -> tuple:
        """计算开仓张数和保证金

        Returns:
            (sz: float, margin: float)
        """
        if size_mode == "percent":
            # 仓位百分比模式
            position_value = capital * (size_pct / 100) * leverage
            sz = max(0.01, position_value / (face_value * current_price))
        else:
            sz = fixed_sz

        # 保证金 = 张数 * 面值 * 价格 / 杠杆
        margin = sz * face_value * current_price / leverage
        # 不超过可用资金
        if margin > capital:
            sz = max(1, int(capital * leverage / (face_value * current_price)))
            margin = sz * face_value * current_price / leverage

        return sz, margin

    def _calc_pnl(self, position: dict, current_price: float, face_value: float) -> float:
        """计算持仓盈亏

        Args:
            position: 持仓信息
            current_price: 当前价格
            face_value: 合约面值

        Returns:
            盈亏金额（USDT）
        """
        if not position:
            return 0
        entry = position["entry_price"]
        sz = position["sz"]
        if position["side"] == "long":
            return (current_price - entry) * sz * face_value
        else:  # short
            return (entry - current_price) * sz * face_value

    def _check_sl_tp_trailing(
        self, position: dict, current_price: float,
        current_high: float, current_low: float,
        tp_pct: float, sl_pct: float, trailing_pct: float,
        trailing_activation_pct: float = 0,
        trailing_callback_points: float = 0,
    ) -> str:
        """检查是否触发止损/止盈/移动止损

        Args:
            tp_pct: 止盈百分比（杠杆收益）
            sl_pct: 止损百分比（杠杆亏损）
            trailing_pct: 移动止损回调比例（杠杆收益）
            trailing_activation_pct: 移动止盈激活阈值(%)，盈利达到此比例才启动移动止损
            trailing_callback_points: 移动止盈回调点数（固定点数，如40点）

        Returns:
            触发原因字符串，未触发返回空字符串
        """
        entry = position["entry_price"]
        side = position["side"]
        leverage = position.get("leverage", 10)  # 从持仓获取杠杆倍数

        # 计算价格变动百分比
        if side == "long":
            price_change_pct = (current_price - entry) / entry * 100
        else:
            price_change_pct = (entry - current_price) / entry * 100

        # 计算杠杆收益百分比 = 价格变动 × 杠杆倍数
        pnl_pct = price_change_pct * leverage

        if tp_pct > 0 and pnl_pct >= tp_pct:
            return "take_profit"
        if sl_pct > 0 and pnl_pct <= -sl_pct:
            return "stop_loss"

        # 移动止盈（需先达到激活阈值）
        if trailing_pct > 0 or trailing_callback_points > 0:
            # 检查是否已达到移动止盈激活阈值
            activated = True  # 默认激活
            if trailing_activation_pct > 0:
                activated = pnl_pct >= trailing_activation_pct

            if activated:
                if side == "long":
                    # 多仓：从最高价回落
                    highest = position.get("highest", entry)
                    if highest > entry:
                        # 方式1：固定点数回调
                        if trailing_callback_points > 0:
                            price_drawdown = highest - current_price
                            if price_drawdown >= trailing_callback_points:
                                return "trailing_stop"
                        # 方式2：百分比回调
                        elif trailing_pct > 0:
                            # 价格回撤百分比
                            price_drawdown_pct = (highest - current_price) / highest * 100
                            # 杠杆收益回撤 = 价格回撤 × 杠杆
                            leverage_drawdown_pct = price_drawdown_pct * leverage
                            if leverage_drawdown_pct >= trailing_pct:
                                return "trailing_stop"
                else:
                    # 空仓：从最低价回升
                    lowest = position.get("lowest", entry)
                    if lowest < entry:
                        # 方式1：固定点数回调
                        if trailing_callback_points > 0:
                            price_bounce = current_price - lowest
                            if price_bounce >= trailing_callback_points:
                                return "trailing_stop"
                        # 方式2：百分比回调
                        elif trailing_pct > 0:
                            # 价格反弹百分比
                            price_bounce_pct = (current_price - lowest) / lowest * 100
                            # 杠杆收益回撤 = 价格反弹 × 杠杆
                            leverage_bounce_pct = price_bounce_pct * leverage
                            if leverage_bounce_pct >= trailing_pct:
                                return "trailing_stop"

        return ""

    def _save_result(self, strategy_type: str, params: dict, symbol: str,
                     timeframe: str, klines: list, initial_capital: float,
                     result: dict):
        """保存回测结果到数据库"""
        if not result.get("ok"):
            return

        db = SessionLocal()
        try:
            start_date = datetime.fromtimestamp(klines[0]["timestamp"] / 1000) if klines else datetime.now()
            end_date = datetime.fromtimestamp(klines[-1]["timestamp"] / 1000) if klines else datetime.now()

            bt = BacktestResult(
                strategy_name=strategy_type,
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                final_capital=result["final_capital"],
                total_return=result["total_return"],
                max_drawdown=result["max_drawdown"],
                sharpe_ratio=result["sharpe_ratio"],
                win_rate=result["win_rate"],
                trade_count=result["trade_count"],
                params=json.dumps(params),
            )
            db.add(bt)
            db.commit()
        except Exception as e:
            print(f"[Backtest] save error: {e}")
        finally:
            db.close()


# 单例
backtest_engine = BacktestEngine()
