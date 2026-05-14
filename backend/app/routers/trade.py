"""交易路由 - 合约交易（Bitget版本）"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.routers.settings import _load_bitget_config, _has_bitget_config
from app.services.bitget_client import BitgetClient, BitgetAPIError
from app.services.trade_bitget import BitgetTradeService

router = APIRouter(prefix="/api/trade", tags=["交易"])


def _get_trade_service():
    """获取已初始化的Bitget交易服务"""
    if not _has_bitget_config():
        raise HTTPException(status_code=403, detail="请先在个人中心绑定 Bitget API")
    cfg = _load_bitget_config()
    if not cfg.get("key"):
        raise HTTPException(status_code=403, detail="Bitget API 未配置")
    client = BitgetClient(cfg["key"], cfg["secret"], cfg["passphrase"])
    return BitgetTradeService(client)


# ─── 请求模型 ───

class PlaceOrderRequest(BaseModel):
    symbol: str = "BTCUSDT"
    side: str = "buy"                   # buy / sell
    size: str = "1"                     # 张数
    order_type: str = "market"          # market / limit
    price: str = ""                     # 限价价格
    hold_side: str = ""                 # long / short (双向持仓)
    margin_mode: str = "crossed"        # crossed / fixed
    reduce_only: bool = False

class ClosePositionRequest(BaseModel):
    symbol: str = "BTCUSDT"
    hold_side: str = ""                 # long / short，不传则全平
    size: str = ""                      # 不传则全平


# ─── 查询接口 ───

@router.get("/balance")
async def get_balance():
    """获取合约账户余额"""
    ts = _get_trade_service()
    try:
        acc = ts.client.get_mix_account()
        return {"accountEquity": acc.get("accountEquity"), "available": acc.get("available")}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)[:200])


@router.get("/positions")
async def get_positions():
    """获取合约持仓"""
    ts = _get_trade_service()
    try:
        return {"positions": ts.get_positions()}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)[:200])


@router.get("/orders")
async def get_pending_orders(symbol: str = "BTCUSDT"):
    """获取当前挂单"""
    ts = _get_trade_service()
    try:
        data = ts.client._request("GET", "/api/v2/mix/order/orders-pending",
                                   params={"symbol": symbol, "productType": "USDT-FUTURES"})
        return {"orders": data}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)[:200])


# ─── 交易接口 ───

@router.post("/open-long")
async def open_long(req: PlaceOrderRequest):
    """开多"""
    ts = _get_trade_service()
    try:
        result = ts.open_long(req.symbol, req.size, margin_mode=req.margin_mode)
        return {"success": True, "data": result, "message": "开多成功"}
    except BitgetAPIError as e:
        detail = f"开多失败 [{e.code}]: {e.msg}"
        raise HTTPException(status_code=400, detail=detail)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)[:200])


@router.post("/open-short")
async def open_short(req: PlaceOrderRequest):
    """开空"""
    ts = _get_trade_service()
    try:
        result = ts.open_short(req.symbol, req.size, margin_mode=req.margin_mode)
        return {"success": True, "data": result, "message": "开空成功"}
    except BitgetAPIError as e:
        detail = f"开空失败 [{e.code}]: {e.msg}"
        raise HTTPException(status_code=400, detail=detail)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)[:200])


@router.post("/close")
async def close_position(req: ClosePositionRequest):
    """平仓"""
    ts = _get_trade_service()
    try:
        result = ts.close_position(req.symbol, req.hold_side, req.size)
        return {"success": True, "data": result, "message": "平仓成功"}
    except BitgetAPIError as e:
        detail = f"平仓失败 [{e.code}]: {e.msg}"
        raise HTTPException(status_code=400, detail=detail)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)[:200])


@router.post("/close-all")
async def close_all_positions():
    """一键全平"""
    ts = _get_trade_service()
    try:
        positions = ts.get_positions()
        results = []
        for pos in positions:
            if float(pos.get("total", "0")) > 0:
                result = ts.close_position(pos.get("symbol"), pos.get("holdSide"))
                results.append(result)
        return {"success": True, "closed": len(results), "message": f"已平 {len(results)} 个仓位"}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)[:200])
