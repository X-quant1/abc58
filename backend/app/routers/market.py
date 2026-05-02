"""行情数据路由 - OKX（带缓存）"""
from fastapi import APIRouter, Query, HTTPException

from app.services.cache import get_cached_market_service

router = APIRouter(prefix="/api/market", tags=["行情"])


@router.get("/kline")
async def get_kline(
    symbol: str = Query("BTC-USDT", description="交易对 (如 BTC-USDT)"),
    timeframe: str = Query("1h", description="K线周期: 1m/5m/15m/1h/4h/1d"),
    limit: int = Query(200, description="数量", le=300),
):
    """获取K线数据（带缓存，30秒TTL）"""
    try:
        ms = get_cached_market_service()
        data = ms.get_klines(symbol, timeframe, limit)
        return {"symbol": symbol, "timeframe": timeframe, "count": len(data), "data": data}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OKX API error: {str(e)}")


@router.get("/ticker")
async def get_ticker(symbol: str = Query("BTC-USDT", description="交易对")):
    """获取最新行情（带缓存，2秒TTL）"""
    try:
        ms = get_cached_market_service()
        return ms.get_ticker(symbol)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OKX API error: {str(e)}")


@router.get("/tickers")
async def get_multi_tickers():
    """批量获取主流币种行情（带缓存，5秒TTL）"""
    try:
        ms = get_cached_market_service()
        data = ms.get_multi_tickers()
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OKX API error: {str(e)}")


@router.get("/symbols")
async def get_symbols(inst_type: str = Query("SPOT", description="SPOT/SWAP/FUTURES")):
    """获取支持的交易对列表（带缓存，1小时TTL）"""
    try:
        ms = get_cached_market_service()
        data = ms.get_symbols(inst_type)
        return {"count": len(data), "symbols": data}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OKX API error: {str(e)}")


@router.get("/positions")
async def get_positions(inst_id: str = Query(None, description="合约ID")):
    """获取持仓列表（不缓存，实时数据）"""
    try:
        ms = get_cached_market_service()
        data = ms.get_positions(inst_id)
        return {"count": len(data), "positions": data}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OKX API error: {str(e)}")


@router.get("/balance")
async def get_balance(ccy: str = Query(None, description="币种")):
    """获取账户余额（不缓存，实时数据）"""
    try:
        ms = get_cached_market_service()
        data = ms.get_account_balance(ccy)
        return data
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OKX API error: {str(e)}")
