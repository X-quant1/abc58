"""回测路由"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.database import SessionLocal
from app.models import BacktestResult
from app.services.strategy import list_available_strategies, STRATEGY_REGISTRY
from app.services.backtest import backtest_engine, TAKER_FEE_RATE, DEFAULT_SLIPPAGE

router = APIRouter(prefix="/api/backtest", tags=["回测"])


# ─── 请求模型 ───

class RunBacktestRequest(BaseModel):
    strategy_type: str                      # ma_cross / rsi / bollinger
    params: dict = {}                        # 策略参数
    symbol: str = "BTC-USDT-SWAP"           # 交易对
    timeframe: str = "1h"                    # K线周期
    initial_capital: float = 10000           # 初始资金
    leverage: int = 10                       # 杠杆
    fee_rate: float = TAKER_FEE_RATE         # 手续费率
    slippage: float = DEFAULT_SLIPPAGE       # 滑点比例


# ─── 运行回测 ───

@router.post("/run")
async def run_backtest(req: RunBacktestRequest):
    """执行回测"""
    if req.strategy_type not in STRATEGY_REGISTRY:
        raise HTTPException(status_code=400, detail=f"unknown strategy type: {req.strategy_type}")

    try:
        # 合并止盈止损参数
        params = {**req.params}
        if "take_profit_pct" not in params:
            params["take_profit_pct"] = 0
        if "stop_loss_pct" not in params:
            params["stop_loss_pct"] = 5
        if "trailing_stop_pct" not in params:
            params["trailing_stop_pct"] = 0
        if "size_mode" not in params:
            params["size_mode"] = "fixed"
        if "size" not in params:
            params["size"] = 1
        if "size_pct" not in params:
            params["size_pct"] = 10
        if "td_mode" not in params:
            params["td_mode"] = "cross"
        if "inst_id" not in params:
            params["inst_id"] = req.symbol

        result = backtest_engine.run(
            strategy_type=req.strategy_type,
            params=params,
            symbol=req.symbol,
            timeframe=req.timeframe,
            initial_capital=req.initial_capital,
            leverage=req.leverage,
            fee_rate=req.fee_rate,
            slippage=req.slippage,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:300])


# ─── 回测历史 ───

@router.get("/results")
async def get_backtest_results(limit: int = 20):
    """获取回测结果列表"""
    db = SessionLocal()
    try:
        results = db.query(BacktestResult).order_by(
            BacktestResult.id.desc()
        ).limit(limit).all()
        data = []
        for r in results:
            cls = STRATEGY_REGISTRY.get(r.strategy_name)
            type_name = cls.strategy_name if cls else r.strategy_name

            data.append({
                "id": r.id,
                "strategy_name": r.strategy_name,
                "strategy_display_name": type_name,
                "symbol": r.symbol,
                "timeframe": r.timeframe,
                "start_date": r.start_date.isoformat() if r.start_date else "",
                "end_date": r.end_date.isoformat() if r.end_date else "",
                "initial_capital": r.initial_capital,
                "final_capital": r.final_capital,
                "total_return": r.total_return,
                "max_drawdown": r.max_drawdown,
                "sharpe_ratio": r.sharpe_ratio,
                "win_rate": r.win_rate,
                "trade_count": r.trade_count,
                "params": r.params,
                "created_at": r.created_at.isoformat() if r.created_at else "",
            })
        return {"results": data}
    finally:
        db.close()


@router.get("/result/{result_id}")
async def get_backtest_detail(result_id: int):
    """获取回测详情（含完整交易记录和收益曲线）"""
    db = SessionLocal()
    try:
        r = db.query(BacktestResult).filter(BacktestResult.id == result_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="result not found")

        cls = STRATEGY_REGISTRY.get(r.strategy_name)
        type_name = cls.strategy_name if cls else r.strategy_name

        return {
            "id": r.id,
            "strategy_name": r.strategy_name,
            "strategy_display_name": type_name,
            "symbol": r.symbol,
            "timeframe": r.timeframe,
            "start_date": r.start_date.isoformat() if r.start_date else "",
            "end_date": r.end_date.isoformat() if r.end_date else "",
            "initial_capital": r.initial_capital,
            "final_capital": r.final_capital,
            "total_return": r.total_return,
            "max_drawdown": r.max_drawdown,
            "sharpe_ratio": r.sharpe_ratio,
            "win_rate": r.win_rate,
            "trade_count": r.trade_count,
            "params": r.params,
            "created_at": r.created_at.isoformat() if r.created_at else "",
        }
    finally:
        db.close()


@router.delete("/result/{result_id}")
async def delete_backtest_result(result_id: int):
    """删除回测结果"""
    db = SessionLocal()
    try:
        r = db.query(BacktestResult).filter(BacktestResult.id == result_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="result not found")
        db.delete(r)
        db.commit()
        return {"ok": True, "msg": "deleted"}
    finally:
        db.close()


# ─── 策略回测统计 ───

@router.get("/strategy/{strategy_type}/stats")
async def get_strategy_backtest_stats(strategy_type: str):
    """获取策略类型的最优回测统计数据（按总收益率排序）"""
    from datetime import datetime, timedelta
    db = SessionLocal()
    try:
        # 查询该策略类型收益率最高的回测结果
        result = db.query(BacktestResult).filter(
            BacktestResult.strategy_name == strategy_type
        ).order_by(BacktestResult.total_return.desc()).first()
        
        if not result:
            return {
                "has_data": False,
                "message": "暂无回测数据",
                "strategy_type": strategy_type,
            }
        
        # 计算年化收益率（假设回测周期为30天）
        days = 30
        if result.start_date and result.end_date:
            days = (result.end_date - result.start_date).days or 30
        annual_return = 0
        if result.total_return and days > 0:
            annual_return = (result.total_return / days) * 365
        
        # 判断是否需要更新（超过3天）
        need_update = False
        if result.created_at:
            three_days_ago = datetime.utcnow() - timedelta(days=3)
            need_update = result.created_at < three_days_ago
        
        cls = STRATEGY_REGISTRY.get(strategy_type)
        type_name = cls.strategy_name if cls else strategy_type
        
        return {
            "has_data": True,
            "strategy_type": strategy_type,
            "strategy_display_name": type_name,
            "annual_return": round(annual_return, 2),
            "total_return": round(result.total_return or 0, 2),
            "win_rate": round(result.win_rate or 0, 2),
            "max_drawdown": round(result.max_drawdown or 0, 2),
            "trade_count": result.trade_count or 0,
            "sharpe_ratio": round(result.sharpe_ratio or 0, 2),
            "initial_capital": result.initial_capital,
            "final_capital": result.final_capital,
            "symbol": result.symbol,
            "timeframe": result.timeframe,
            "start_date": result.start_date.isoformat() if result.start_date else "",
            "end_date": result.end_date.isoformat() if result.end_date else "",
            "last_updated": result.created_at.isoformat() if result.created_at else "",
            "need_update": need_update,
        }
    finally:
        db.close()
