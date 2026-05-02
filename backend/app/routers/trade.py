"""交易路由 - 合约交易 + 一键平仓（REST API版本）"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.cache import get_cached_market_service, invalidate_account_cache
from app.services.trade_rest import get_trade_service

router = APIRouter(prefix="/api/trade", tags=["交易"])


# ─── 请求模型 ───

class PlaceOrderRequest(BaseModel):
    inst_id: str = "BTC-USDT-SWAP"
    side: str                           # buy / sell
    sz: str = "0.01"                    # 合约张数
    ord_type: str = "market"            # market / limit
    px: str = ""                        # 限价价格
    lever: int = None                   # 杠杆（None=不设置）
    td_mode: str = "cross"             # cross / isolated
    pos_side: str = "net"              # net / long / short
    reduce_only: bool = False
    tp_trigger_px: str = ""
    sl_trigger_px: str = ""


class ClosePositionRequest(BaseModel):
    inst_id: str = "BTC-USDT-SWAP"
    mgn_mode: str = "cross"
    pos_side: str = "net"


class SetLeverageRequest(BaseModel):
    inst_id: str = "BTC-USDT-SWAP"
    lever: int = 10
    mgn_mode: str = "cross"
    pos_side: str = ""


# ─── 查询接口 ───

@router.get("/balance")
async def get_balance():
    """获取账户余额"""
    try:
        ms = get_cached_market_service()
        return ms.get_account_balance()
    except RuntimeError as e:
        if "API Key" in str(e) or "credentials" in str(e):
            raise HTTPException(status_code=403, detail="请先在设置中配置 OKX API Key")
        raise HTTPException(status_code=502, detail=str(e)[:300])


@router.get("/positions")
async def get_positions():
    """获取合约持仓"""
    try:
        ts = get_trade_service()
        data = ts.get_swap_positions()
        return {"positions": data}
    except RuntimeError as e:
        if "API Key" in str(e) or "credentials" in str(e):
            raise HTTPException(status_code=403, detail="请先在设置中配置 OKX API Key")
        raise HTTPException(status_code=502, detail=str(e)[:300])


@router.get("/orders")
async def get_pending_orders():
    """获取合约未成交委托"""
    try:
        ts = get_trade_service()
        data = ts.get_swap_orders()
        return {"orders": data}
    except RuntimeError as e:
        if "API Key" in str(e) or "credentials" in str(e):
            raise HTTPException(status_code=403, detail="请先在设置中配置 OKX API Key")
        raise HTTPException(status_code=502, detail=str(e)[:300])


@router.get("/fills")
async def get_fills(inst_id: str = ""):
    """获取合约成交流水"""
    try:
        ts = get_trade_service()
        data = ts.get_swap_fills(inst_id)
        return {"fills": data}
    except RuntimeError as e:
        if "API Key" in str(e) or "credentials" in str(e):
            raise HTTPException(status_code=403, detail="请先在设置中配置 OKX API Key")
        raise HTTPException(status_code=502, detail=str(e)[:300])


# ─── 交易接口 ───

@router.post("/open-long")
async def open_long(
    inst_id: str = "BTC-USDT-SWAP",
    sz: str = "0.01",
    lever: int = None,
    td_mode: str = "cross",
    tp_trigger_px: str = "",
    sl_trigger_px: str = "",
):
    """开多单"""
    try:
        ts = get_trade_service()
        result = ts.open_long(
            inst_id=inst_id, sz=sz, lever=lever, td_mode=td_mode,
            tp_trigger_px=tp_trigger_px, sl_trigger_px=sl_trigger_px,
        )
        invalidate_account_cache()
        return {"ok": True, "result": result}
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)[:300])


@router.post("/open-short")
async def open_short(
    inst_id: str = "BTC-USDT-SWAP",
    sz: str = "0.01",
    lever: int = None,
    td_mode: str = "cross",
    tp_trigger_px: str = "",
    sl_trigger_px: str = "",
):
    """开空单"""
    try:
        ts = get_trade_service()
        result = ts.open_short(
            inst_id=inst_id, sz=sz, lever=lever, td_mode=td_mode,
            tp_trigger_px=tp_trigger_px, sl_trigger_px=sl_trigger_px,
        )
        invalidate_account_cache()
        return {"ok": True, "result": result}
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)[:300])


@router.post("/close")
async def close_position(req: ClosePositionRequest):
    """平仓（单个合约）"""
    try:
        ts = get_trade_service()
        result = ts.close_position(
            inst_id=req.inst_id,
            mgn_mode=req.mgn_mode,
            pos_side=req.pos_side,
        )
        invalidate_account_cache()
        return {"ok": True, "result": result}
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)[:300])


@router.post("/close-all")
async def close_all_positions():
    """一键平仓 — 平掉所有合约持仓"""
    try:
        ts = get_trade_service()
        result = ts.close_all_positions()
        invalidate_account_cache()
        return {"ok": True, **result}
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)[:300])


@router.post("/cancel")
async def cancel_order(inst_id: str, ord_id: str = "", cl_ord_id: str = ""):
    """撤销合约订单"""
    try:
        ts = get_trade_service()
        result = ts.cancel_order(inst_id, ord_id, cl_ord_id)
        return {"ok": True, "result": result}
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)[:300])


@router.post("/leverage")
async def set_leverage(req: SetLeverageRequest):
    """设置杠杆"""
    try:
        ts = get_trade_service()
        result = ts.set_leverage(
            inst_id=req.inst_id,
            lever=req.lever,
            mgn_mode=req.mgn_mode,
            pos_side=req.pos_side,
        )
        return {"ok": True, "result": result}
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)[:300])


@router.get("/leverage")
async def get_leverage(inst_id: str = "BTC-USDT-SWAP", mgn_mode: str = "cross"):
    """获取当前杠杆设置"""
    try:
        ts = get_trade_service()
        result = ts.get_leverage(inst_id, mgn_mode)
        return {"result": result}
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)[:300])
