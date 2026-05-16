"""Bitget 行情数据服务

提供与 OKX MarketService 相同的同步接口，底层调用 Bitget REST API。
供 CachedMarketService (cache.py) 和策略系统使用。
"""
import asyncio
from typing import List, Dict, Any, Optional

from app.services.bitget_client import BitgetClient, get_client, BitgetAPIError
from app.services.logger import sys_logger
from app.routers.settings import _load_bitget_config, _has_bitget_config


def _get_or_create_client() -> BitgetClient:
    """获取或创建 Bitget 客户端"""
    client = get_client()
    if client is not None:
        return client
    if not _has_bitget_config():
        raise RuntimeError("Bitget API 未配置")
    cfg = _load_bitget_config()
    from app.services.bitget_client import init_client
    return init_client(cfg["key"], cfg["secret"], cfg["passphrase"])


def _run_async(coro):
    """运行异步协程

    如果已在 asyncio 事件循环中（如 FastAPI async 路由），使用 nest_asyncio 或
    简单地用 loop.run_until_complete。但在已有 loop 的线程中需要用 run_in_executor。
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None:
        # 已在事件循环中（如 FastAPI async 路由），用新线程执行
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            # 在新线程中创建新的事件循环来运行协程
            def run_in_new_loop():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(coro)
                finally:
                    new_loop.close()
            return pool.submit(run_in_new_loop).result()
    else:
        # 不在事件循环中，直接运行
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError("closed")
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)


class BitgetMarketService:
    """Bitget 行情数据服务（同步接口，兼容 OKX MarketService）

    返回值格式尽量与 OKX MarketService 保持一致，减少调用方修改量。
    """

    def __init__(self, client: BitgetClient = None):
        self.client = client  # 可注入，便于测试

    def _client(self) -> BitgetClient:
        return self.client or _get_or_create_client()

    # ─── 公开接口 ───

    def get_ticker(self, symbol: str = "BTC-USDT") -> dict:
        """获取单个交易对最新行情

        Args:
            symbol: 交易对。兼容两种格式:
                    - OKX 风格: "BTC-USDT" 或 "BTC-USDT-SWAP"
                    - Bitget 风格: "BTCUSDT"

        Returns:
            统一格式 dict，包含 price / open / high / low / volume 等
        """
        bitget_symbol = self._to_bitget_symbol(symbol)
        client = self._client()

        async def _do():
            return await client.get_ticker(bitget_symbol)

        data = _run_async(_do())
        if not data or not isinstance(data, dict):
            return {"symbol": bitget_symbol, "price": 0, "last": "0", "bidPx": "0", "askPx": "0"}

        last = float(data.get("lastPr", 0))
        high = float(data.get("high24h", 0))
        low = float(data.get("low24h", 0))
        open_24h = float(data.get("openUtc0", 0))
        volume = float(data.get("baseVolume", 0))
        quote_volume = float(data.get("quoteVolume", 0))
        change_pct = round((last - open_24h) / open_24h * 100, 2) if open_24h > 0 else 0

        return {
            # Bitget 原始字段（兼容前端直接读取）
            "symbol": bitget_symbol,
            "last": data.get("lastPr", "0"),
            "bidPx": data.get("bidPr", "0"),
            "askPx": data.get("askPr", "0"),
            "high24h": data.get("high24h", "0"),
            "low24h": data.get("low24h", "0"),
            # 统一字段（兼容 OKX MarketService 接口）
            "price": last,
            "open": open_24h,
            "high": high,
            "low": low,
            "volume": volume,
            "quote_volume": quote_volume,
            "change_24h": change_pct,
            "best_bid": float(data.get("bidPr", 0)),
            "best_ask": float(data.get("askPr", 0)),
            "timestamp": int(data.get("ts", 0)),
        }

    def get_tickers(self, inst_type: str = "SPOT") -> list:
        """获取所有交易对行情

        Args:
            inst_type: Bitget productType, 如 "USDT-FUTURES"
                       也兼容 OKX 风格 "SWAP" -> "USDT-FUTURES"
        """
        product_type = self._to_product_type(inst_type)
        client = self._client()

        async def _do():
            return await client.get_tickers(product_type)

        data = _run_async(_do())
        if not isinstance(data, list):
            return []

        results = []
        for item in data:
            if not isinstance(item, dict):
                continue
            last = float(item.get("lastPr", 0))
            open_24h = float(item.get("openUtc0", 0))
            change_pct = round((last - open_24h) / open_24h * 100, 2) if open_24h > 0 else 0
            results.append({
                "symbol": item.get("symbol", ""),
                "price": last,
                "open": open_24h,
                "high": float(item.get("high24h", 0)),
                "low": float(item.get("low24h", 0)),
                "volume": float(item.get("baseVolume", 0)),
                "quote_volume": float(item.get("quoteVolume", 0)),
                "change_24h": change_pct,
                "timestamp": int(item.get("ts", 0)),
            })
        return results

    def get_klines(
        self,
        symbol: str = "BTC-USDT-SWAP",
        interval: str = "1H",
        limit: int = 100,
        timeframe: str = None,
    ) -> list:
        """获取K线数据

        Args:
            symbol: 交易对（兼容 OKX "BTC-USDT-SWAP" 和 Bitget "BTCUSDT"）
            interval: K线周期 1m/5m/15m/30m/1H/4H/1D/1W
            limit: 数量
            timeframe: 别名（兼容旧代码），优先级低于 interval
        """
        # 兼容旧代码的 timeframe 参数
        if interval == "1H" and timeframe is not None:
            interval = timeframe
        # Bitget K线 interval 必须大写：1h -> 1H, 4h -> 4H, 1d -> 1D
        interval = interval.upper()
        bitget_symbol = self._to_bitget_symbol(symbol)
        # Bitget 使用 granularity，和 OKX interval 基本一致
        granularity = interval
        client = self._client()

        async def _do():
            return await client.get_klines(bitget_symbol, granularity, limit)

        data = _run_async(_do())
        if not isinstance(data, list):
            return []

        results = []
        for item in data:
            if not isinstance(item, list) or len(item) < 6:
                continue
            # Bitget K线: [ts, open, high, low, close, volume, ...]
            results.append({
                "timestamp": int(item[0]) if item[0] else 0,
                "open": float(item[1]) if item[1] else 0,
                "high": float(item[2]) if item[2] else 0,
                "low": float(item[3]) if item[3] else 0,
                "close": float(item[4]) if item[4] else 0,
                "volume": float(item[5]) if item[5] else 0,
                "quote_volume": float(item[6]) if len(item) > 6 and item[6] else 0,
            })

        # Bitget 返回正序（时间升序），与 OKX 一致（反转后）
        results.reverse()
        return results

    def get_multi_tickers(self, symbols: list = None) -> list:
        """批量获取行情

        Args:
            symbols: 交易对列表（兼容 OKX 和 Bitget 格式）
        """
        if symbols is None:
            symbols = [
                "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT",
                "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "SUIUSDT",
            ]

        results = []
        for sym in symbols:
            bitget_sym = self._to_bitget_symbol(sym)
            try:
                ticker = self.get_ticker(bitget_sym)
                if ticker and ticker.get("price", 0) > 0:
                    results.append(ticker)
            except Exception:
                continue
        return results

    def get_symbols(self, inst_type: str = "SPOT") -> list:
        """获取交易对列表

        Args:
            inst_type: 兼容 OKX "SPOT"/"SWAP" 和 Bitget "USDT-FUTURES"
        """
        product_type = self._to_product_type(inst_type)
        client = self._client()

        async def _do():
            return await client.get_contracts(product_type)

        data = _run_async(_do())
        if not isinstance(data, list):
            return []

        results = []
        for item in data:
            if not isinstance(item, dict):
                continue
            results.append({
                "symbol": item.get("symbol", ""),
                "base": item.get("baseCoin", ""),
                "name": item.get("symbolName", ""),
                "min_size": item.get("minTradeNum", ""),
                "tick_size": item.get("pricePlace", ""),
                "instId": item.get("symbol", ""),  # 兼容 OKX
                "baseCcy": item.get("baseCoin", ""),  # 兼容 OKX
            })
        return results

    def get_orderbook(self, symbol: str = "BTC-USDT", depth: int = 20) -> dict:
        """获取订单簿"""
        bitget_symbol = self._to_bitget_symbol(symbol)
        client = self._client()

        async def _do():
            path = f"/api/v2/mix/market/orderbook?symbol={bitget_symbol}&productType=USDT-FUTURES&limit={depth}"
            return await client._request("GET", path)

        data = _run_async(_do())
        if not isinstance(data, dict):
            return {"bids": [], "asks": [], "timestamp": 0}

        bids = [[float(p), float(s)] for p, s in data.get("bids", [])]
        asks = [[float(p), float(s)] for p, s in data.get("asks", [])]
        return {"bids": bids, "asks": asks, "timestamp": int(data.get("ts", 0))}

    # ─── 私有接口（需要 API Key）───

    def get_positions(self, inst_id: str = None) -> list:
        """获取持仓列表

        Args:
            inst_id: 合约ID（可选）。兼容 OKX "BTC-USDT-SWAP"

        Returns:
            兼容 OKX 格式的持仓列表
        """
        from app.services.trade_bitget import BitgetTradeService

        client = self._client()
        service = BitgetTradeService(client)

        async def _do():
            positions = await service.get_positions()
            result = []
            for pos in positions:
                if not isinstance(pos, dict):
                    continue
                symbol = pos.get("symbol", "")
                # 如果指定了 inst_id，过滤
                if inst_id:
                    okx_symbol = symbol.replace("USDT", "-USDT-SWAP")
                    if okx_symbol != inst_id and symbol != inst_id:
                        continue

                total = float(pos.get("total", 0))
                if total <= 0:
                    continue

                hold_side = pos.get("holdSide", "")

                result.append({
                    # OKX 兼容字段
                    "instId": symbol.replace("USDT", "-USDT-SWAP"),
                    "instType": "SWAP",
                    "mgnMode": "cross",
                    "posSide": hold_side,  # long / short
                    "pos": pos.get("total", "0"),
                    "avgPx": pos.get("openPriceAvg", ""),
                    "upl": pos.get("unrealizedPL", "0"),
                    "uplRatio": pos.get("unrealizedPLR", ""),
                    "lever": pos.get("leverage", "10"),
                    "margin": pos.get("margin", ""),
                    "liqPx": pos.get("liqPrice", ""),
                    "markPx": pos.get("markPrice", ""),
                    "timestamp": int(pos.get("ts", 0)),
                    # Bitget 原始字段
                    "symbol": symbol,
                    "side": hold_side,
                    "size": pos.get("total", "0"),
                })
            return result

        return _run_async(_do())

    def get_account_balance(self, ccy: str = None) -> dict:
        """获取账户余额

        Args:
            ccy: 币种，如 "USDT"

        Returns:
            兼容 OKX 格式的余额信息
            {
                "total_equity": float,
                "total_margin": float,
                "total_unrealized_pnl": float,
                "details": [...]
            }
        """
        client = self._client()

        async def _do():
            return await client.get_mix_account(symbol="BTCUSDT", margin_coin="USDT")

        data = _run_async(_do())
        if not isinstance(data, dict):
            return {"total_equity": 0, "total_margin": 0, "total_unrealized_pnl": 0, "details": []}

        # Bitget V2 API 字段名：accountEquity（非 totalEquity）
        total_eq = float(data.get("accountEquity", 0) or data.get("totalEquity", 0))
        total_margin = float(data.get("totalMargin", 0))
        unrealized_pnl = float(data.get("unrealizedPL", 0))
        available = float(data.get("available", 0))

        return {
            "total_equity": total_eq,
            "total_margin": total_margin,
            "total_unrealized_pnl": unrealized_pnl,
            "available": available,
            "details": [{
                "currency": "USDT",
                "equity": total_eq,
                "available": available,
                "frozen": total_margin - available if total_margin > available else 0,
            }],
        }

    def get_funding_balance(self) -> dict:
        """获取资金账户余额（现货账户）"""
        client = self._client()

        async def _do():
            return await client.get_assets()

        data = _run_async(_do())
        if not isinstance(data, list):
            return {"total_equity": 0, "details": []}

        details = []
        total = 0.0
        for item in data:
            if not isinstance(item, dict):
                continue
            bal = float(item.get("available", 0))
            if bal <= 0:
                continue
            coin = item.get("coin", "")
            frozen = float(item.get("frozen", 0))
            details.append({
                "currency": coin,
                "balance": bal + frozen,
                "available": bal,
                "frozen": frozen,
            })
            total += bal + frozen

        return {"total_equity": total, "details": details}

    def get_bills(self, limit: int = 20, inst_type: str = "") -> list:
        """获取账户账单流水"""
        client = self._client()

        async def _do():
            path = "/api/v2/mix/account/bills"
            params = {"productType": "USDT-FUTURES", "limit": str(limit)}
            return await client._request("GET", path, params=params)

        data = _run_async(_do())
        if not isinstance(data, list):
            return []

        results = []
        for b in data:
            if not isinstance(b, dict):
                continue
            results.append({
                "bill_id": b.get("billId", ""),
                "symbol": b.get("symbol", ""),
                "type": b.get("businessType", ""),
                "side": b.get("side", ""),
                "currency": b.get("marginCoin", ""),
                "amount": float(b.get("change", 0) or 0),
                "pnl": float(b.get("pnl", 0) or 0),
                "fee": float(b.get("fee", 0) or 0),
                "px": float(b.get("price", 0) or 0),
                "sz": float(b.get("size", 0) or 0),
                "fill_px": float(b.get("fillPrice", 0) or 0),
                "fill_sz": float(b.get("fillSize", 0) or 0),
                "account_equity": float(b.get("accountEquity", 0) or 0),
                "timestamp": int(b.get("cTime", 0) or 0),
            })
        return results

    # ─── 辅助方法 ───

    @staticmethod
    def _to_bitget_symbol(symbol: str) -> str:
        """将 OKX 格式交易对转为 Bitget 格式

        BTC-USDT-SWAP -> BTCUSDT
        BTC-USDT -> BTCUSDT
        BTCUSDT -> BTCUSDT (不变)
        """
        if "-" in symbol:
            # OKX 格式: BTC-USDT-SWAP 或 BTC-USDT
            return symbol.replace("-USDT-SWAP", "USDT").replace("-USDT", "USDT")
        return symbol

    @staticmethod
    def _to_product_type(inst_type: str) -> str:
        """将 OKX instType 转为 Bitget productType

        SWAP -> USDT-FUTURES
        FUTURES -> USDT-FUTURES
        SPOT -> SPOT
        """
        mapping = {
            "SWAP": "USDT-FUTURES",
            "FUTURES": "USDT-FUTURES",
            "SPOT": "SPOT",
        }
        return mapping.get(inst_type.upper(), inst_type)


# ─── 全局单例 ───

_market_service: Optional[BitgetMarketService] = None


def get_bitget_market_service() -> BitgetMarketService:
    """获取全局 Bitget 行情服务实例"""
    global _market_service
    if _market_service is None:
        _market_service = BitgetMarketService()
    return _market_service


def reset_bitget_market_service():
    """重置全局实例（API 配置变更后调用）"""
    global _market_service
    _market_service = None
