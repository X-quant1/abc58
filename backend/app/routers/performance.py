"""交易绩效分析路由

提供实盘交易绩效分析：
- 总体概览（总盈亏/胜率/夏普/最大回撤/手续费）
- 每日/月度收益统计
- 盈亏分布
- 策略维度对比
- 交易流水明细
"""
from fastapi import APIRouter, Query
from datetime import datetime, timedelta
from collections import defaultdict
import math

from app.database import SessionLocal
from app.models import Trade, Strategy

router = APIRouter(prefix="/api/performance", tags=["绩效分析"])


# ─── 工具函数 ───

def _get_fills_from_okx(inst_id: str = "", days: int = 90) -> list:
    """从 OKX 获取成交流水（含手续费）"""
    try:
        from app.services.trade_rest import get_trade_service
        fills = get_trade_service().get_swap_fills(inst_id)
        return fills if isinstance(fills, list) else []
    except Exception:
        return []


def _calc_max_drawdown(equity_curve: list) -> float:
    """从权益曲线计算最大回撤"""
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak * 100 if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd
    return round(max_dd, 2)


def _calc_sharpe(daily_returns: list) -> float:
    """计算年化夏普比率（无风险利率=0）"""
    if len(daily_returns) < 2:
        return 0.0
    avg = sum(daily_returns) / len(daily_returns)
    variance = sum((r - avg) ** 2 for r in daily_returns) / len(daily_returns)
    std = variance ** 0.5
    if std == 0:
        return 0.0
    sharpe = avg / std * (365 ** 0.5)
    return round(sharpe, 2)


# ─── API 接口 ───

@router.get("/overview")
async def get_performance_overview(days: int = Query(30, ge=1, le=365)):
    """绩效概览：总盈亏/胜率/夏普/最大回撤/手续费/交易次数"""
    db = SessionLocal()
    try:
        # 查询交易记录
        since = datetime.now() - timedelta(days=days)
        trades = db.query(Trade).filter(Trade.created_at >= since).order_by(Trade.created_at).all()

        if not trades:
            return {
                "ok": True, "has_data": False,
                "total_pnl": 0, "total_fee": 0, "trade_count": 0,
                "win_rate": 0, "win_count": 0, "lose_count": 0,
                "avg_pnl": 0, "max_win": 0, "max_loss": 0,
                "sharpe_ratio": 0, "max_drawdown": 0,
                "profit_factor": 0, "avg_holding_time": "",
                "long_count": 0, "short_count": 0,
                "long_pnl": 0, "short_pnl": 0,
                "daily_pnl": [],
            }

        # 基础统计
        total_pnl = sum(t.pnl or 0 for t in trades)
        total_fee = sum(t.fee or 0 for t in trades)
        trade_count = len(trades)

        pnl_list = [t.pnl or 0 for t in trades if t.pnl is not None]
        win_count = sum(1 for p in pnl_list if p > 0)
        lose_count = sum(1 for p in pnl_list if p < 0)
        win_rate = round(win_count / len(pnl_list) * 100, 2) if pnl_list else 0
        avg_pnl = round(total_pnl / trade_count, 4) if trade_count else 0
        max_win = round(max(pnl_list), 4) if pnl_list else 0
        max_loss = round(min(pnl_list), 4) if pnl_list else 0

        # 盈亏比 (profit factor)
        gross_profit = sum(p for p in pnl_list if p > 0)
        gross_loss = abs(sum(p for p in pnl_list if p < 0))
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else float('inf') if gross_profit > 0 else 0

        # 多空统计（基于 direction 字段）
        long_trades = [t for t in trades if t.direction in ('open_long', 'close_long') or (not t.direction and t.side == 'buy')]
        short_trades = [t for t in trades if t.direction in ('open_short', 'close_short') or (not t.direction and t.side == 'sell')]
        long_pnl = sum(t.pnl or 0 for t in long_trades)
        short_pnl = sum(t.pnl or 0 for t in short_trades)

        # 每日盈亏（用于计算夏普和最大回撤）
        daily_pnl_map = defaultdict(float)
        for t in trades:
            date_str = t.created_at.strftime("%Y-%m-%d") if t.created_at else "unknown"
            daily_pnl_map[date_str] += t.pnl or 0

        daily_pnl = []
        for date_str in sorted(daily_pnl_map.keys()):
            daily_pnl.append({"date": date_str, "pnl": round(daily_pnl_map[date_str], 4)})

        # 计算权益曲线（累计盈亏）
        equity_curve = [0]
        for dp in daily_pnl:
            equity_curve.append(equity_curve[-1] + dp["pnl"])

        max_drawdown = _calc_max_drawdown(equity_curve)

        # 夏普比率（基于每日收益率）
        daily_returns = []
        for i in range(1, len(equity_curve)):
            if equity_curve[i - 1] != 0:
                daily_returns.append(dp["pnl"] / abs(equity_curve[i - 1]) if i <= len(daily_pnl) else 0)

        # 更稳健的夏普计算
        if len(daily_pnl) >= 2:
            pnl_values = [dp["pnl"] for dp in daily_pnl]
            avg_daily = sum(pnl_values) / len(pnl_values)
            var_daily = sum((p - avg_daily) ** 2 for p in pnl_values) / len(pnl_values)
            std_daily = var_daily ** 0.5
            if std_daily > 0:
                sharpe = avg_daily / std_daily * (365 ** 0.5)
            else:
                sharpe = 0.0
        else:
            sharpe = 0.0

        return {
            "ok": True, "has_data": True,
            "total_pnl": round(total_pnl, 4),
            "total_fee": round(total_fee, 4),
            "net_pnl": round(total_pnl - total_fee, 4),
            "trade_count": trade_count,
            "win_count": win_count,
            "lose_count": lose_count,
            "win_rate": win_rate,
            "avg_pnl": avg_pnl,
            "max_win": max_win,
            "max_loss": max_loss,
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown": max_drawdown,
            "profit_factor": profit_factor if profit_factor != float('inf') else 999,
            "long_count": len(long_trades),
            "short_count": len(short_trades),
            "long_pnl": round(long_pnl, 4),
            "short_pnl": round(short_pnl, 4),
            "daily_pnl": daily_pnl,
        }
    finally:
        db.close()


@router.get("/daily-pnl")
async def get_daily_pnl(days: int = Query(30, ge=1, le=365)):
    """每日盈亏统计"""
    db = SessionLocal()
    try:
        since = datetime.now() - timedelta(days=days)
        trades = db.query(Trade).filter(Trade.created_at >= since).order_by(Trade.created_at).all()

        daily_map = defaultdict(lambda: {"pnl": 0, "fee": 0, "count": 0, "win": 0, "lose": 0})
        for t in trades:
            date_str = t.created_at.strftime("%Y-%m-%d") if t.created_at else "unknown"
            entry = daily_map[date_str]
            entry["pnl"] += t.pnl or 0
            entry["fee"] += t.fee or 0
            entry["count"] += 1
            if (t.pnl or 0) > 0:
                entry["win"] += 1
            elif (t.pnl or 0) < 0:
                entry["lose"] += 1

        result = []
        cumulative = 0
        for date_str in sorted(daily_map.keys()):
            entry = daily_map[date_str]
            cumulative += entry["pnl"]
            result.append({
                "date": date_str,
                "pnl": round(entry["pnl"], 4),
                "fee": round(entry["fee"], 4),
                "count": entry["count"],
                "win": entry["win"],
                "lose": entry["lose"],
                "cumulative_pnl": round(cumulative, 4),
            })

        return {"data": result}
    finally:
        db.close()


@router.get("/monthly-pnl")
async def get_monthly_pnl(months: int = Query(12, ge=1, le=36)):
    """月度盈亏统计"""
    db = SessionLocal()
    try:
        since = datetime.now() - timedelta(days=months * 31)
        trades = db.query(Trade).filter(Trade.created_at >= since).order_by(Trade.created_at).all()

        monthly_map = defaultdict(lambda: {"pnl": 0, "fee": 0, "count": 0, "win": 0, "lose": 0})
        for t in trades:
            month_str = t.created_at.strftime("%Y-%m") if t.created_at else "unknown"
            entry = monthly_map[month_str]
            entry["pnl"] += t.pnl or 0
            entry["fee"] += t.fee or 0
            entry["count"] += 1
            if (t.pnl or 0) > 0:
                entry["win"] += 1
            elif (t.pnl or 0) < 0:
                entry["lose"] += 1

        result = []
        cumulative = 0
        for month_str in sorted(monthly_map.keys()):
            entry = monthly_map[month_str]
            cumulative += entry["pnl"]
            result.append({
                "month": month_str,
                "pnl": round(entry["pnl"], 4),
                "fee": round(entry["fee"], 4),
                "count": entry["count"],
                "win": entry["win"],
                "lose": entry["lose"],
                "win_rate": round(entry["win"] / entry["count"] * 100, 1) if entry["count"] > 0 else 0,
                "cumulative_pnl": round(cumulative, 4),
            })

        return {"data": result}
    finally:
        db.close()


@router.get("/strategy-comparison")
async def get_strategy_comparison():
    """策略维度对比"""
    db = SessionLocal()
    try:
        trades = db.query(Trade).order_by(Trade.created_at).all()

        strategy_map = defaultdict(lambda: {"pnl": 0, "fee": 0, "count": 0, "win": 0, "lose": 0})
        for t in trades:
            sid = t.strategy_id or 0
            entry = strategy_map[sid]
            entry["pnl"] += t.pnl or 0
            entry["fee"] += t.fee or 0
            entry["count"] += 1
            if (t.pnl or 0) > 0:
                entry["win"] += 1
            elif (t.pnl or 0) < 0:
                entry["lose"] += 1

        result = []
        for sid, entry in strategy_map.items():
            # 查策略名
            strategy_name = f"Strategy #{sid}"
            if sid > 0:
                s = db.query(Strategy).filter(Strategy.id == sid).first()
                if s:
                    strategy_name = s.name

            result.append({
                "strategy_id": sid,
                "strategy_name": strategy_name,
                "pnl": round(entry["pnl"], 4),
                "fee": round(entry["fee"], 4),
                "count": entry["count"],
                "win": entry["win"],
                "lose": entry["lose"],
                "win_rate": round(entry["win"] / entry["count"] * 100, 1) if entry["count"] > 0 else 0,
                "avg_pnl": round(entry["pnl"] / entry["count"], 4) if entry["count"] > 0 else 0,
            })

        return {"data": result}
    finally:
        db.close()


@router.get("/pnl-distribution")
async def get_pnl_distribution():
    """盈亏分布（按区间统计交易笔数）"""
    db = SessionLocal()
    try:
        trades = db.query(Trade).order_by(Trade.created_at).all()

        # 定义区间
        bins = [
            ("<-5%", -999999, -0.05),
            ("-5%~-2%", -0.05, -0.02),
            ("-2%~0%", -0.02, 0),
            ("0%~2%", 0, 0.02),
            ("2%~5%", 0.02, 0.05),
            (">5%", 0.05, 999999),
        ]

        result = []
        for label, low, high in bins:
            count = 0
            for t in trades:
                pnl = t.pnl or 0
                if pnl >= low and pnl < high:
                    count += 1
            result.append({"range": label, "count": count})

        return {"data": result}
    finally:
        db.close()


@router.get("/trades")
async def get_performance_trades(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(100, ge=1, le=500),
    strategy_id: int = Query(0, ge=0),
):
    """交易流水明细（带策略名称和盈亏）"""
    db = SessionLocal()
    try:
        since = datetime.now() - timedelta(days=days)
        query = db.query(Trade).filter(Trade.created_at >= since)

        if strategy_id > 0:
            query = query.filter(Trade.strategy_id == strategy_id)

        trades = query.order_by(Trade.created_at.desc()).limit(limit).all()

        result = []
        for t in trades:
            # 策略名
            strategy_name = f"Strategy #{t.strategy_id}"
            if t.strategy_id:
                s = db.query(Strategy).filter(Strategy.id == t.strategy_id).first()
                if s:
                    strategy_name = s.name

            result.append({
                "id": t.id,
                "strategy_id": t.strategy_id,
                "strategy_name": strategy_name,
                "symbol": t.symbol,
                "side": t.side,
                "price": t.price,
                "amount": t.amount,
                "pnl": t.pnl or 0,
                "fee": t.fee or 0,
                "net_pnl": round((t.pnl or 0) - (t.fee or 0), 4),
                "order_id": t.order_id,
                "created_at": t.created_at.isoformat() if t.created_at else "",
            })

        return {"trades": result, "total": len(result)}
    finally:
        db.close()


@router.get("/equity-curve")
async def get_equity_curve(days: int = Query(30, ge=1, le=365)):
    """权益曲线（基于累计盈亏）"""
    db = SessionLocal()
    try:
        since = datetime.now() - timedelta(days=days)
        trades = db.query(Trade).filter(Trade.created_at >= since).order_by(Trade.created_at).all()

        if not trades:
            return {"data": [], "has_data": False}

        # 累计盈亏曲线
        cumulative = 0
        curve = []
        for t in trades:
            cumulative += (t.pnl or 0) - (t.fee or 0)
            curve.append({
                "time": t.created_at.isoformat() if t.created_at else "",
                "equity": round(cumulative, 4),
                "pnl": round((t.pnl or 0) - (t.fee or 0), 4),
            })

        return {"data": curve, "has_data": True}
    finally:
        db.close()


@router.get("/okx-fills")
async def get_okx_fills(days: int = Query(7, ge=1, le=90)):
    """从 OKX 获取真实成交流水（含手续费和盈亏）"""
    try:
        from app.services.trade_rest import get_trade_service
        fills = get_trade_service().get_swap_fills()
        return {"fills": fills if isinstance(fills, list) else [], "count": len(fills) if isinstance(fills, list) else 0}
    except Exception as e:
        return {"fills": [], "count": 0, "error": str(e)[:200]}
