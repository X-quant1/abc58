"""行情数据服务 - OKX REST API

使用OKX REST API获取行情数据，无需依赖CLI工具。
支持高并发场景（1000+用户）。
"""
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.services.okx_client import OKXClient, get_client
from app.services.logger import sys_logger


class MarketService:
    """OKX 行情数据服务（REST API版本）"""
    
    def __init__(self, client: OKXClient = None):
        """初始化行情服务
        
        Args:
            client: OKX客户端实例（不传则使用全局实例）
        """
        self.client = client or get_client()
    
    # ─── 公开接口（无需 API Key）───
    
    def get_ticker(self, symbol: str = "BTC-USDT") -> dict:
        """获取单个交易对最新行情
        
        Args:
            symbol: 交易对，如 BTC-USDT
        
        Returns:
            行情数据字典
        """
        inst_id = symbol.replace("/", "-").upper()
        data = self.client.get(f"/api/v5/market/ticker?instId={inst_id}")
        
        if isinstance(data, list) and len(data) > 0:
            data = data[0]
        else:
            raise RuntimeError(f"No data for {inst_id}")
        
        last = float(data.get("last", 0))
        open_24h = float(data.get("open24h", 0))
        change_pct = round((last - open_24h) / open_24h * 100, 2) if open_24h else 0
        
        return {
            "symbol": inst_id,
            "price": last,
            "open": open_24h,
            "high": float(data.get("high24h", 0)),
            "low": float(data.get("low24h", 0)),
            "volume": float(data.get("vol24h", 0)),
            "quote_volume": float(data.get("volCcy24h", 0)),
            "change_24h": change_pct,
            "best_bid": float(data.get("bidPx", 0)) if data.get("bidPx") else None,
            "best_ask": float(data.get("askPx", 0)) if data.get("askPx") else None,
            "timestamp": int(data.get("ts", 0)),
        }
    
    def get_tickers(self, inst_type: str = "SPOT") -> List[dict]:
        """获取所有交易对行情
        
        Args:
            inst_type: 产品类型 SPOT/SWAP/FUTURES/OPTION
        
        Returns:
            行情列表
        """
        data = self.client.get(f"/api/v5/market/tickers?instType={inst_type}")
        
        results = []
        for item in data:
            last = float(item.get("last", 0))
            open_24h = float(item.get("open24h", 0))
            change_pct = round((last - open_24h) / open_24h * 100, 2) if open_24h else 0
            
            results.append({
                "symbol": item.get("instId", ""),
                "price": last,
                "open": open_24h,
                "high": float(item.get("high24h", 0)),
                "low": float(item.get("low24h", 0)),
                "volume": float(item.get("vol24h", 0)),
                "quote_volume": float(item.get("volCcy24h", 0)),
                "change_24h": change_pct,
                "timestamp": int(item.get("ts", 0)),
            })
        
        return results
    
    def get_klines(
        self,
        symbol: str = "BTC-USDT-SWAP",
        interval: str = "1H",
        limit: int = 100,
    ) -> List[dict]:
        """获取K线数据
        
        Args:
            symbol: 交易对
            interval: K线周期 1m/5m/15m/30m/1H/4H/1D/1W/1M
            limit: 数量（最大300）
        
        Returns:
            K线列表
        """
        inst_id = symbol.replace("/", "-").upper()
        
        # OKX API的bar参数
        bar_map = {
            "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
            "1H": "1H", "4H": "4H", "1D": "1D", "1W": "1W", "1M": "1M",
        }
        bar = bar_map.get(interval, "1H")
        
        data = self.client.get(
            f"/api/v5/market/candles?instId={inst_id}&bar={bar}&limit={limit}"
        )
        
        # OKX返回格式: [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
        results = []
        for item in data:
            results.append({
                "timestamp": int(item[0]),
                "open": float(item[1]),
                "high": float(item[2]),
                "low": float(item[3]),
                "close": float(item[4]),
                "volume": float(item[5]),
                "quote_volume": float(item[6]),
            })
        
        # OKX返回倒序（最新在前），需要反转
        results.reverse()
        return results
    
    def get_orderbook(self, symbol: str = "BTC-USDT", depth: int = 20) -> dict:
        """获取订单簿
        
        Args:
            symbol: 交易对
            depth: 深度（最大400）
        
        Returns:
            订单簿数据
        """
        inst_id = symbol.replace("/", "-").upper()
        data = self.client.get(
            f"/api/v5/market/books?instId={inst_id}&sz={depth}"
        )
        
        if isinstance(data, list) and len(data) > 0:
            data = data[0]
        
        return {
            "bids": [[float(p), float(s)] for p, s in data.get("bids", [])],
            "asks": [[float(p), float(s)] for p, s in data.get("asks", [])],
            "timestamp": int(data.get("ts", 0)),
        }
    
    # ─── 私有接口（需要 API Key）───
    
    def get_positions(self, inst_id: str = None) -> List[dict]:
        """获取持仓列表
        
        Args:
            inst_id: 合约ID（可选，不传则返回所有）
        
        Returns:
            持仓列表
        """
        endpoint = "/api/v5/account/positions"
        if inst_id:
            endpoint += f"?instId={inst_id}"
        
        data = self.client.get(endpoint)
        
        results = []
        for pos in data:
            results.append({
                "instId": pos.get("instId", ""),
                "instType": pos.get("instType", ""),
                "mgnMode": pos.get("mgnMode", ""),
                "posSide": pos.get("posSide", ""),
                "pos": pos.get("pos", "0"),
                "avgPx": pos.get("avgPx", ""),
                "upl": pos.get("upl", ""),
                "uplRatio": pos.get("uplRatio", ""),
                "lever": pos.get("lever", ""),
                "margin": pos.get("margin", ""),
                "liqPx": pos.get("liqPx", ""),
                "markPx": pos.get("markPx", ""),
                "timestamp": int(pos.get("uTime", 0)),
            })
        
        return results
    
    def get_account_balance(self, ccy: str = None) -> dict:
        """获取账户余额
        
        Args:
            ccy: 币种（可选，如USDT）
        
        Returns:
            余额信息
        """
        endpoint = "/api/v5/account/balance"
        if ccy:
            endpoint += f"?ccy={ccy}"
        
        data = self.client.get(endpoint)
        
        if isinstance(data, list) and len(data) > 0:
            data = data[0]
        
        # 解析余额数据
        total_eq = float(data.get("totalEq", 0))
        
        details = []
        for detail in data.get("details", []):
            eq = float(detail.get("eq", 0))
            if eq > 0:
                details.append({
                    "currency": detail.get("ccy", ""),
                    "equity": eq,
                    "available": float(detail.get("availBal", 0)),
                    "frozen": float(detail.get("frozenBal", 0)),
                })
        
        return {
            "total_equity": total_eq,
            "total_margin": float(data.get("totalMargin", 0)),
            "total_unrealized_pnl": float(data.get("totalUTwProfit", 0)),
            "details": details,
        }
    
    def get_orders(self, inst_id: str = None, ord_type: str = None) -> List[dict]:
        """获取订单列表
        
        Args:
            inst_id: 合约ID（可选）
            ord_type: 订单类型（可选）
        
        Returns:
            订单列表
        """
        endpoint = "/api/v5/trade/orders-pending"
        params = []
        if inst_id:
            params.append(f"instId={inst_id}")
        if ord_type:
            params.append(f"ordType={ord_type}")
        
        if params:
            endpoint += "?" + "&".join(params)
        
        return self.client.get(endpoint)
    
    def get_algo_orders(self, inst_id: str = None) -> List[dict]:
        """获取算法订单列表
        
        Args:
            inst_id: 合约ID（可选）
        
        Returns:
            算法订单列表
        """
        endpoint = "/api/v5/trade/orders-algo-pending"
        if inst_id:
            endpoint += f"?instId={inst_id}"
        
        return self.client.get(endpoint)
    
    def get_symbols(self, inst_type: str = "SPOT") -> List[dict]:
        """获取支持的交易对列表
        
        Args:
            inst_type: 产品类型 SPOT/SWAP/FUTURES/OPTION
        
        Returns:
            交易对列表
        """
        data = self.client.get(f"/api/v5/public/instruments?instType={inst_type}")
        
        results = []
        for item in data:
            if item.get("state") == "live":
                results.append({
                    "symbol": item.get("instId", ""),
                    "base": item.get("baseCcy", ""),
                    "name": item.get("baseCcy", ""),
                    "min_size": item.get("minSz", ""),
                    "tick_size": item.get("tickSz", ""),
                })
        
        return results
    
    def get_multi_tickers(self, symbols: List[str] = None) -> List[dict]:
        """批量获取行情
        
        Args:
            symbols: 交易对列表（可选，不传则返回主流币种）
        
        Returns:
            行情列表
        """
        # 主流币种
        popular_symbols = [
            "BTC-USDT", "ETH-USDT", "SOL-USDT", "XRP-USDT", "DOGE-USDT",
            "ADA-USDT", "AVAX-USDT", "DOT-USDT", "LINK-USDT", "SUI-USDT",
        ]
        
        if symbols is None:
            symbols = popular_symbols
        
        # 获取所有SPOT行情
        data = self.client.get("/api/v5/market/tickers?instType=SPOT")
        
        # 构建symbol -> ticker映射
        ticker_map = {}
        for t in data:
            if isinstance(t, dict):
                ticker_map[t.get("instId", "")] = t
        
        results = []
        for sym in symbols:
            inst_id = sym.replace("/", "-").upper()
            t = ticker_map.get(inst_id)
            if not t:
                continue
            
            last = float(t.get("last", 0))
            open_24h = float(t.get("open24h", 0))
            change_pct = round((last - open_24h) / open_24h * 100, 2) if open_24h else 0
            
            results.append({
                "symbol": inst_id,
                "price": last,
                "open": open_24h,
                "high": float(t.get("high24h", 0)),
                "low": float(t.get("low24h", 0)),
                "volume": float(t.get("vol24h", 0)),
                "quote_volume": float(t.get("volCcy24h", 0)),
                "change_24h": change_pct,
                "timestamp": int(t.get("ts", 0)),
            })
        
        return results
    
    def get_funding_balance(self) -> dict:
        """获取资金账户余额"""
        data = self.client.get("/api/v5/asset/balances")
        
        if isinstance(data, list) and data:
            details = []
            for d in data:
                if isinstance(d, dict):
                    bal = float(d.get("bal", 0))
                    avail = float(d.get("availBal", 0))
                    if bal > 0 or avail > 0:
                        details.append({
                            "currency": d.get("ccy", ""),
                            "balance": bal,
                            "available": avail,
                            "frozen": float(d.get("frozenBal", 0)),
                        })
            # 计算总权益
            total = sum(d.get("balance", 0) for d in details)
            return {
                "total_equity": total,
                "details": details,
            }
        return {"total_equity": 0, "details": []}
    
    def get_bills(self, limit: int = 20, inst_type: str = "") -> list:
        """获取账户账单流水
        
        Args:
            limit: 返回条数
            inst_type: 产品类型（可选）
        
        Returns:
            账单列表
        """
        endpoint = f"/api/v5/account/bills?limit={limit}"
        if inst_type:
            endpoint += f"&instType={inst_type}"
        
        data = self.client.get(endpoint)
        
        if not isinstance(data, list):
            return []
        
        results = []
        for b in data:
            if isinstance(b, dict):
                results.append({
                    "bill_id": b.get("billId", ""),
                    "symbol": b.get("instId", ""),
                    "type": b.get("type", ""),
                    "side": b.get("side", ""),
                    "currency": b.get("ccy", ""),
                    "amount": float(b.get("balChg", 0) or 0),
                    "pnl": float(b.get("pnl", 0) or 0),
                    "fee": float(b.get("fee", 0) or 0),
                    "px": float(b.get("px", 0) or 0),
                    "sz": float(b.get("sz", 0) or 0),
                    "fill_px": float(b.get("fillPx", 0) or 0),
                    "fill_sz": float(b.get("fillSz", 0) or 0),
                    "account_equity": float(b.get("accountEq", 0) or 0),
                    "timestamp": int(b.get("ts", 0) or 0),
                })
        return results
    
    # ─── 异步方法（高并发场景）───
    
    async def async_get_ticker(self, symbol: str = "BTC-USDT", session: aiohttp.ClientSession = None) -> dict:
        """异步获取单个交易对最新行情
        
        Args:
            symbol: 交易对
            session: aiohttp会话（复用连接池）
        """
        inst_id = symbol.replace("/", "-").upper()
        data = await self.client.async_request("GET", f"/api/v5/market/ticker?instId={inst_id}", session=session)
        
        if isinstance(data, list) and len(data) > 0:
            data = data[0]
        else:
            raise RuntimeError(f"No data for {inst_id}")
        
        last = float(data.get("last", 0))
        open_24h = float(data.get("open24h", 0))
        change_pct = round((last - open_24h) / open_24h * 100, 2) if open_24h else 0
        
        return {
            "symbol": inst_id,
            "price": last,
            "open": open_24h,
            "high": float(data.get("high24h", 0)),
            "low": float(data.get("low24h", 0)),
            "volume": float(data.get("vol24h", 0)),
            "quote_volume": float(data.get("volCcy24h", 0)),
            "change_24h": change_pct,
            "best_bid": float(data.get("bidPx", 0)) if data.get("bidPx") else None,
            "best_ask": float(data.get("askPx", 0)) if data.get("askPx") else None,
            "timestamp": int(data.get("ts", 0)),
        }
    
    async def async_get_klines(
        self,
        symbol: str = "BTC-USDT-SWAP",
        interval: str = "1H",
        limit: int = 100,
        session: aiohttp.ClientSession = None,
    ) -> List[dict]:
        """异步获取K线数据"""
        inst_id = symbol.replace("/", "-").upper()
        
        bar_map = {
            "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
            "1H": "1H", "4H": "4H", "1D": "1D", "1W": "1W", "1M": "1M",
        }
        bar = bar_map.get(interval, "1H")
        
        data = await self.client.async_request(
            "GET",
            f"/api/v5/market/candles?instId={inst_id}&bar={bar}&limit={limit}",
            session=session,
        )
        
        results = []
        for item in data:
            results.append({
                "timestamp": int(item[0]),
                "open": float(item[1]),
                "high": float(item[2]),
                "low": float(item[3]),
                "close": float(item[4]),
                "volume": float(item[5]),
                "quote_volume": float(item[6]),
            })
        
        results.reverse()
        return results
    
    async def async_get_positions(self, inst_id: str = None, session: aiohttp.ClientSession = None) -> List[dict]:
        """异步获取持仓列表"""
        endpoint = "/api/v5/account/positions"
        if inst_id:
            endpoint += f"?instId={inst_id}"
        
        data = await self.client.async_request("GET", endpoint, session=session)
        
        results = []
        for pos in data:
            results.append({
                "instId": pos.get("instId", ""),
                "instType": pos.get("instType", ""),
                "mgnMode": pos.get("mgnMode", ""),
                "posSide": pos.get("posSide", ""),
                "pos": pos.get("pos", "0"),
                "avgPx": pos.get("avgPx", ""),
                "upl": pos.get("upl", ""),
                "uplRatio": pos.get("uplRatio", ""),
                "lever": pos.get("lever", ""),
                "margin": pos.get("margin", ""),
                "liqPx": pos.get("liqPx", ""),
                "markPx": pos.get("markPx", ""),
                "timestamp": int(pos.get("uTime", 0)),
            })
        
        return results
    
    async def async_get_account_balance(self, ccy: str = None, session: aiohttp.ClientSession = None) -> dict:
        """异步获取账户余额"""
        endpoint = "/api/v5/account/balance"
        if ccy:
            endpoint += f"?ccy={ccy}"
        
        data = await self.client.async_request("GET", endpoint, session=session)
        
        if isinstance(data, list) and len(data) > 0:
            data = data[0]
        
        total_eq = float(data.get("totalEq", 0))
        
        details = []
        for detail in data.get("details", []):
            details.append({
                "ccy": detail.get("ccy", ""),
                "bal": float(detail.get("bal", 0)),
                "availBal": float(detail.get("availBal", 0)),
                "frozenBal": float(detail.get("frozenBal", 0)),
                "eq": float(detail.get("eq", 0)),
            })
        
        return {
            "total_equity": total_eq,
            "details": details,
        }
    
    async def async_batch_get_tickers(self, symbols: List[str], session: aiohttp.ClientSession = None) -> List[dict]:
        """批量异步获取行情（高并发场景）
        
        Args:
            symbols: 交易对列表
            session: aiohttp会话
        
        Returns:
            行情列表
        """
        # 并发获取所有行情
        tasks = [self.async_get_ticker(sym, session) for sym in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤掉错误
        output = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                sys_logger.warn("market", f"Failed to get ticker for {symbols[i]}: {result}")
            else:
                output.append(result)
        
        return output


# ─── 全局实例 ───

_market_service: Optional[MarketService] = None

def get_market_service() -> MarketService:
    """获取全局行情服务实例"""
    global _market_service
    if _market_service is None:
        _market_service = MarketService()
    return _market_service
