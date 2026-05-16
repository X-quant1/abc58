"""交易路由 - 合约交易（Bitget异步版）"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.routers.settings import _load_bitget_config, _has_bitget_config
from app.services.bitget_client import BitgetClient, BitgetAPIError
from app.services.trade_bitget import BitgetTradeService

router = APIRouter(prefix="/api/trade", tags=["交易"])


def _get_trade_service():
    if not _has_bitget_config():
        raise HTTPException(status_code=403, detail="请先绑定 Bitget API")
    cfg = _load_bitget_config()
    if not cfg.get("key"):
        raise HTTPException(status_code=403, detail="Bitget API 未配置")
    client = BitgetClient(cfg["key"], cfg["secret"], cfg["passphrase"])
    return BitgetTradeService(client)


class PlaceOrderRequest(BaseModel):
    symbol: str = "BTCUSDT"
    side: str = "buy"
    size: str = "0.0001"
    order_type: str = "market"
    price: str = ""
    margin_mode: str = "crossed"
    tp_price: str = ""  # 止盈价格
    sl_price: str = ""  # 止损价格
    tpsl_visible: bool = False  # True=持仓可见(两次调用), False=仅生效(一次调用,默认)

class ClosePositionRequest(BaseModel):
    symbol: str = "BTCUSDT"
    hold_side: str = ""
    size: str = ""

class SetTPSLRequest(BaseModel):
    symbol: str = "BTCUSDT"
    hold_side: str = "long"
    tp_price: str = ""
    sl_price: str = ""


@router.get("/balance")
async def get_balance():
    ts = _get_trade_service()
    try:
        acc = await ts.client.get_mix_account()
        return {"accountEquity": acc.get("accountEquity"), "available": acc.get("available")}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)[:200])


@router.get("/positions")
async def get_positions():
    ts = _get_trade_service()
    try:
        return {"positions": await ts.get_positions()}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)[:200])


@router.get("/orders")
async def get_pending_orders(symbol: str = "BTCUSDT"):
    ts = _get_trade_service()
    try:
        data = await ts.client._request("GET", "/api/v2/mix/order/orders-pending",
                                         params={"symbol": symbol, "productType": "USDT-FUTURES"})
        return {"orders": data}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)[:200])


@router.post("/open-long")
async def open_long(req: PlaceOrderRequest):
    ts = _get_trade_service()
    try:
        result = await ts.open_long(req.symbol, req.size, tp_price=req.tp_price,
                                     sl_price=req.sl_price, order_type=req.order_type, price=req.price,
                                     tpsl_visible=req.tpsl_visible)
        return {"success": True, "data": result, "message": "开多成功"}
    except BitgetAPIError as e:
        raise HTTPException(status_code=400, detail=f"开多失败 [{e.code}]: {e.msg}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)[:200])


@router.post("/open-short")
async def open_short(req: PlaceOrderRequest):
    ts = _get_trade_service()
    try:
        result = await ts.open_short(req.symbol, req.size, tp_price=req.tp_price,
                                      sl_price=req.sl_price, order_type=req.order_type, price=req.price,
                                      tpsl_visible=req.tpsl_visible)
        return {"success": True, "data": result, "message": "开空成功"}
    except BitgetAPIError as e:
        raise HTTPException(status_code=400, detail=f"开空失败 [{e.code}]: {e.msg}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)[:200])


@router.post("/close")
async def close_position(req: ClosePositionRequest):
    ts = _get_trade_service()
    try:
        result = await ts.close_position(req.symbol, req.hold_side, req.size)
        return {"success": True, "data": result, "message": "平仓成功"}
    except BitgetAPIError as e:
        raise HTTPException(status_code=400, detail=f"平仓失败 [{e.code}]: {e.msg}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)[:200])


@router.post("/close-all")
async def close_all_positions():
    ts = _get_trade_service()
    try:
        positions = await ts.get_positions()
        results = []
        for pos in positions:
            if float(pos.get("total", "0")) > 0:
                result = await ts.close_position(pos.get("symbol"), pos.get("holdSide"))
                results.append(result)
        return {"success": True, "closed": len(results), "message": f"已平 {len(results)} 个仓位"}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)[:200])


@router.post("/set-tpsl")
async def set_tpsl(req: SetTPSLRequest):
    """为已有仓位设置止盈止损"""
    ts = _get_trade_service()
    try:
        result = await ts.set_position_tpsl(req.symbol, req.hold_side, req.tp_price, req.sl_price)
        return {"success": True, "data": result, "message": "止盈止损设置成功"}
    except BitgetAPIError as e:
        raise HTTPException(status_code=400, detail=f"止盈止损设置失败 [{e.code}]: {e.msg}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)[:200])
