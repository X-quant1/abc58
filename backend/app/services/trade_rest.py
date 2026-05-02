"""交易执行服务 - OKX REST API

使用OKX REST API执行交易，无需依赖CLI工具。
支持高并发场景（1000+用户）。
"""
import asyncio
import aiohttp
from typing import Optional, Dict, Any, List

from app.services.okx_client import OKXClient, get_client
from app.services.logger import sys_logger


class TradeService:
    """OKX 合约交易服务（REST API版本）"""
    
    def __init__(self, client: OKXClient = None):
        """初始化交易服务
        
        Args:
            client: OKX客户端实例（不传则使用全局实例）
        """
        self.client = client or get_client()
    
    # ─── 杠杆设置 ───
    
    def set_leverage(
        self,
        inst_id: str,
        lever: int,
        mgn_mode: str = "cross",
        pos_side: str = ""
    ) -> Dict:
        """设置杠杆倍数
        
        Args:
            inst_id: 合约ID，如 BTC-USDT-SWAP
            lever: 杠杆倍数，如 100
            mgn_mode: 保证金模式 cross=全仓 isolated=逐仓
            pos_side: 持仓方向 net/long/short（逐仓必填）
        
        Returns:
            API响应数据
        """
        body = {
            "instId": inst_id,
            "lever": str(lever),
            "mgnMode": mgn_mode,
        }
        
        if pos_side:
            body["posSide"] = pos_side
        
        return self.client.post("/api/v5/account/set-leverage", body)
    
    def get_leverage(self, inst_id: str, mgn_mode: str = "cross") -> Dict:
        """获取当前杠杆设置
        
        Args:
            inst_id: 合约ID
            mgn_mode: 保证金模式
        
        Returns:
            杠杆设置信息
        """
        # 使用POST请求，不是GET
        body = {
            "instId": inst_id,
            "mgnMode": mgn_mode,
        }
        return self.client.post("/api/v5/account/leverage-info", body)
    
    # ─── 下单 ───
    
    def place_order(
        self,
        inst_id: str,
        side: str,              # buy / sell
        sz: str,                # 数量（合约张数）
        ord_type: str = "market",  # market / limit
        px: str = "",           # 限价价格
        pos_side: str = "net",  # net / long / short
        td_mode: str = "cross", # cross / isolated
        reduce_only: bool = False,
        tp_trigger_px: str = "",   # 止盈触发价
        tp_ord_px: str = "",       # 止盈委托价（-1=市价）
        sl_trigger_px: str = "",   # 止损触发价
        sl_ord_px: str = "",       # 止损委托价（-1=市价）
        cl_ord_id: str = "",       # 客户自定义订单ID
    ) -> Dict:
        """下合约订单
        
        Args:
            inst_id: 合约ID
            side: buy / sell
            sz: 数量
            ord_type: market / limit
            px: 限价价格
            pos_side: net / long / short
            td_mode: cross / isolated
            reduce_only: 是否只减仓
            tp_trigger_px: 止盈触发价
            tp_ord_px: 止盈委托价
            sl_trigger_px: 止损触发价
            sl_ord_px: 止损委托价
            cl_ord_id: 客户自定义订单ID
        
        Returns:
            订单信息
        """
        body = {
            "instId": inst_id,
            "tdMode": td_mode,
            "side": side,
            "posSide": pos_side,
            "ordType": ord_type,
            "sz": sz,
        }
        
        if px and ord_type == "limit":
            body["px"] = px
        
        if reduce_only:
            body["reduceOnly"] = "true"
        
        if cl_ord_id:
            body["clOrdId"] = cl_ord_id
        
        # 止盈止损（使用attachAlgoOrds）
        attach_algo_ords = []
        if tp_trigger_px or sl_trigger_px:
            algo_ord = {}
            if tp_trigger_px:
                algo_ord["tpTriggerPx"] = tp_trigger_px
                algo_ord["tpOrdPx"] = tp_ord_px or "-1"
                algo_ord["tpTriggerPxType"] = "last"
            if sl_trigger_px:
                algo_ord["slTriggerPx"] = sl_trigger_px
                algo_ord["slOrdPx"] = sl_ord_px or "-1"
                algo_ord["slTriggerPxType"] = "last"
            attach_algo_ords.append(algo_ord)
        
        if attach_algo_ords:
            body["attachAlgoOrds"] = attach_algo_ords
        
        result = self.client.post("/api/v5/trade/order", body)
        sys_logger.info("trade", f"Order placed: {result}")
        return result
    
    def open_long(
        self,
        inst_id: str = "BTC-USDT-SWAP",
        sz: str = "0.01",
        lever: int = None,
        td_mode: str = "cross",
        ord_type: str = "market",
        px: str = "",
        tp_trigger_px: str = "",
        sl_trigger_px: str = "",
    ) -> Dict:
        """开多单
        
        Args:
            inst_id: 合约ID
            sz: 数量
            lever: 杠杆（None表示不设置）
            td_mode: 保证金模式
            ord_type: 订单类型
            px: 限价价格
            tp_trigger_px: 止盈触发价
            sl_trigger_px: 止损触发价
        
        Returns:
            订单信息
        """
        # 设置杠杆
        if lever is not None:
            try:
                result = self.set_leverage(inst_id, lever, td_mode, pos_side="long")
                sys_logger.info("trade", f"Set leverage to {lever}X for long: {result}")
            except Exception as e:
                sys_logger.warn("trade", f"Set leverage failed (will continue): {e}")
        
        # 下单
        return self.place_order(
            inst_id=inst_id,
            side="buy",
            sz=sz,
            ord_type=ord_type,
            px=px,
            pos_side="long",
            td_mode=td_mode,
            tp_trigger_px=tp_trigger_px,
            tp_ord_px="-1" if tp_trigger_px else "",
            sl_trigger_px=sl_trigger_px,
            sl_ord_px="-1" if sl_trigger_px else "",
        )
    
    def open_short(
        self,
        inst_id: str = "BTC-USDT-SWAP",
        sz: str = "0.01",
        lever: int = None,
        td_mode: str = "cross",
        ord_type: str = "market",
        px: str = "",
        tp_trigger_px: str = "",
        sl_trigger_px: str = "",
    ) -> Dict:
        """开空单"""
        # 设置杠杆
        if lever is not None:
            try:
                self.set_leverage(inst_id, lever, td_mode, pos_side="short")
            except Exception as e:
                sys_logger.warn("trade", f"Set leverage failed (will continue): {e}")
        
        # 下单
        return self.place_order(
            inst_id=inst_id,
            side="sell",
            sz=sz,
            ord_type=ord_type,
            px=px,
            pos_side="short",
            td_mode=td_mode,
            tp_trigger_px=tp_trigger_px,
            tp_ord_px="-1" if tp_trigger_px else "",
            sl_trigger_px=sl_trigger_px,
            sl_ord_px="-1" if sl_trigger_px else "",
        )
    
    def close_position(
        self,
        inst_id: str = "BTC-USDT-SWAP",
        mgn_mode: str = "cross",
        pos_side: str = "net",
    ) -> Dict:
        """平仓（单个合约）
        
        Args:
            inst_id: 合约ID
            mgn_mode: 保证金模式
            pos_side: 持仓方向 net/long/short
        """
        body = {
            "instId": inst_id,
            "mgnMode": mgn_mode,
            "posSide": pos_side,
        }
        
        return self.client.post("/api/v5/trade/close-position", body)
    
    def close_all_positions(self) -> Dict:
        """一键平仓 — 平掉所有合约持仓"""
        # 获取所有持仓
        positions = self.client.get("/api/v5/account/positions")
        
        if not positions:
            return {"closed": 0, "results": [], "msg": "no positions to close"}
        
        results = []
        for pos in positions:
            inst_id = pos.get("instId", "")
            pos_side = pos.get("posSide", "")
            
            try:
                res = self.close_position(inst_id=inst_id, pos_side=pos_side)
                results.append({
                    "inst_id": inst_id,
                    "pos_side": pos_side,
                    "status": "success",
                    "result": res,
                })
            except Exception as e:
                results.append({
                    "inst_id": inst_id,
                    "pos_side": pos_side,
                    "status": "error",
                    "error": str(e)[:200],
                })
        
        success_count = sum(1 for r in results if r["status"] == "success")
        return {
            "closed": success_count,
            "total": len(positions),
            "results": results,
        }
    
    # ─── 撤单 ───
    
    def cancel_order(self, inst_id: str, ord_id: str = "", cl_ord_id: str = "") -> Dict:
        """撤销合约订单
        
        Args:
            inst_id: 合约ID
            ord_id: 订单ID
            cl_ord_id: 客户自定义订单ID
        """
        body = [{"instId": inst_id}]
        
        if ord_id:
            body[0]["ordId"] = ord_id
        if cl_ord_id:
            body[0]["clOrdId"] = cl_ord_id
        
        return self.client.post("/api/v5/trade/cancel-order", body)
    
    # ─── 算法订单 ───
    
    def place_algo_trailing(
        self,
        inst_id: str,
        side: str,
        sz: str,
        callback_pct: float = None,
        callback_points: float = None,
        activate_price: str = "",
        pos_side: str = "net",
        td_mode: str = "cross",
        reduce_only: bool = True,
    ) -> Dict:
        """下移动止损（追踪止损）算法单
        
        Args:
            inst_id: 合约ID
            side: buy / sell
            sz: 数量
            callback_pct: 回调比例（百分比）
            callback_points: 回调点数（优先级高于callback_pct）
            activate_price: 激活价格
            pos_side: 持仓方向
            td_mode: 保证金模式
            reduce_only: 是否只减仓
        
        Returns:
            算法订单信息
        """
        body = {
            "instId": inst_id,
            "tdMode": td_mode,
            "side": side,
            "posSide": pos_side,
            "sz": sz,
            "ordType": "move_order_stop",
        }
        
        # 回调参数
        if callback_points is not None and callback_points > 0:
            body["callbackSpread"] = str(callback_points)
        elif callback_pct is not None:
            ratio = callback_pct / 100
            body["callbackRatio"] = str(ratio)
        
        if activate_price:
            body["activePx"] = activate_price
        
        if reduce_only:
            body["reduceOnly"] = "true"
        
        sys_logger.info("trade", f"Placing trailing stop: {body}")
        return self.client.post("/api/v5/trade/order-algo", body)
    
    def cancel_algo_order(self, inst_id: str, algo_id: str) -> Dict:
        """撤销算法订单
        
        Args:
            inst_id: 合约ID
            algo_id: 算法订单ID
        """
        body = [{
            "instId": inst_id,
            "algoId": algo_id,
        }]
        
        return self.client.post("/api/v5/trade/cancel-algos", body)
    
    # ─── 止损止盈算法单 ───
    
    def place_algo_tp_sl(
        self,
        inst_id: str,
        side: str,
        sz: str,
        tp_trigger_px: str = "",
        tp_ord_px: str = "-1",
        sl_trigger_px: str = "",
        sl_ord_px: str = "-1",
        pos_side: str = "net",
        td_mode: str = "cross",
        reduce_only: bool = True,
    ) -> Dict:
        """下止损止盈算法单（OCO类型）
        
        Args:
            inst_id: 合约ID
            side: buy / sell
            sz: 数量
            tp_trigger_px: 止盈触发价
            tp_ord_px: 止盈委托价（-1=市价）
            sl_trigger_px: 止损触发价
            sl_ord_px: 止损委托价（-1=市价）
            pos_side: 持仓方向
            td_mode: 保证金模式
            reduce_only: 是否只减仓
        
        Returns:
            算法订单信息
        """
        body = {
            "instId": inst_id,
            "tdMode": td_mode,
            "side": side,
            "posSide": pos_side,
            "sz": sz,
            "ordType": "oco",
        }
        
        if tp_trigger_px:
            body["tpTriggerPx"] = tp_trigger_px
            body["tpOrdPx"] = tp_ord_px
            body["tpTriggerPxType"] = "last"
        if sl_trigger_px:
            body["slTriggerPx"] = sl_trigger_px
            body["slOrdPx"] = sl_ord_px
            body["slTriggerPxType"] = "last"
        if reduce_only:
            body["reduceOnly"] = "true"
        
        sys_logger.info("trade", f"Placing TP/SL algo order: {body}")
        return self.client.post("/api/v5/trade/order-algo", body)
    
    # ─── 查询 ───
    
    def get_swap_positions(self, inst_id: str = "") -> list:
        """获取合约持仓（兼容旧接口格式）
        
        Args:
            inst_id: 合约ID（可选）
        
        Returns:
            持仓列表（旧格式字段名）
        """
        endpoint = "/api/v5/account/positions"
        if inst_id:
            endpoint += f"?instId={inst_id}"
        
        data = self.client.get(endpoint)
        
        if not isinstance(data, list):
            return []
        
        results = []
        for p in data:
            if isinstance(p, dict):
                results.append({
                    "symbol": p.get("instId", ""),
                    "side": p.get("posSide", ""),
                    "size": safe_float(p.get("pos", 0)),
                    "avg_price": safe_float(p.get("avgPx", 0)),
                    "unrealized_pnl": safe_float(p.get("upl", 0)),
                    "unrealized_pnl_ratio": safe_float(p.get("uplRatio", 0)),
                    "leverage": p.get("lever", ""),
                    "margin": safe_float(p.get("margin", 0)),
                    "liq_price": safe_float(p.get("liqPx", 0)),
                    "mark_price": safe_float(p.get("markPx", 0)),
                    "mgn_mode": p.get("mgnMode", ""),
                })
        return results
    
    def get_swap_orders(self, inst_id: str = "", history: bool = False) -> list:
        """获取合约委托列表
        
        Args:
            inst_id: 合约ID（可选）
            history: 是否查询历史委托
        
        Returns:
            委托列表
        """
        if history:
            endpoint = "/api/v5/trade/orders-history-archive"
        else:
            endpoint = "/api/v5/trade/orders-pending"
        
        params = []
        if inst_id:
            params.append(f"instId={inst_id}")
        
        # 历史查询需要产品类型
        if history:
            params.append("instType=SWAP")
        
        if params:
            endpoint += "?" + "&".join(params)
        
        data = self.client.get(endpoint)
        return data if isinstance(data, list) else []
    
    def get_swap_fills(self, inst_id: str = "") -> list:
        """获取合约成交流水
        
        Args:
            inst_id: 合约ID（可选）
        
        Returns:
            成交列表
        """
        endpoint = "/api/v5/trade/fills?instType=SWAP"
        if inst_id:
            endpoint += f"&instId={inst_id}"
        
        data = self.client.get(endpoint)
        return data if isinstance(data, list) else []


def safe_float(val, default=0.0):
    """安全转换为 float，处理 OKX API 返回空字符串的情况"""
    try:
        return float(val) if val not in (None, "", "None") else default
    except (ValueError, TypeError):
        return default
    
    # ─── 异步方法（高并发场景）───
    
    async def async_place_order(
        self,
        inst_id: str,
        side: str,
        sz: str,
        ord_type: str = "market",
        px: str = "",
        pos_side: str = "net",
        td_mode: str = "cross",
        reduce_only: bool = False,
        tp_trigger_px: str = "",
        tp_ord_px: str = "",
        sl_trigger_px: str = "",
        sl_ord_px: str = "",
        cl_ord_id: str = "",
        session: aiohttp.ClientSession = None,
    ) -> Dict:
        """异步下单（高并发场景）
        
        Args:
            session: aiohttp会话（复用连接池）
            其他参数同 place_order
        """
        body = {
            "instId": inst_id,
            "tdMode": td_mode,
            "side": side,
            "posSide": pos_side,
            "ordType": ord_type,
            "sz": sz,
        }
        
        if px and ord_type == "limit":
            body["px"] = px
        
        if reduce_only:
            body["reduceOnly"] = "true"
        
        if cl_ord_id:
            body["clOrdId"] = cl_ord_id
        
        # 止盈止损
        attach_algo_ords = []
        if tp_trigger_px or sl_trigger_px:
            algo_ord = {}
            if tp_trigger_px:
                algo_ord["tpTriggerPx"] = tp_trigger_px
                algo_ord["tpOrdPx"] = tp_ord_px or "-1"
                algo_ord["tpTriggerPxType"] = "last"
            if sl_trigger_px:
                algo_ord["slTriggerPx"] = sl_trigger_px
                algo_ord["slOrdPx"] = sl_ord_px or "-1"
                algo_ord["slTriggerPxType"] = "last"
            attach_algo_ords.append(algo_ord)
        
        if attach_algo_ords:
            body["attachAlgoOrds"] = attach_algo_ords
        
        result = await self.client.async_request("POST", "/api/v5/trade/order", body, session)
        sys_logger.info("trade", f"Async order placed: {result}")
        return result
    
    async def async_open_long(
        self,
        inst_id: str = "BTC-USDT-SWAP",
        sz: str = "0.01",
        lever: int = None,
        td_mode: str = "cross",
        ord_type: str = "market",
        px: str = "",
        tp_trigger_px: str = "",
        sl_trigger_px: str = "",
        session: aiohttp.ClientSession = None,
    ) -> Dict:
        """异步开多单"""
        # 设置杠杆
        if lever is not None:
            try:
                result = await self.client.async_request(
                    "POST",
                    "/api/v5/account/set-leverage",
                    {
                        "instId": inst_id,
                        "lever": str(lever),
                        "mgnMode": td_mode,
                        "posSide": "long",
                    },
                    session,
                )
                sys_logger.info("trade", f"Async set leverage to {lever}X for long: {result}")
            except Exception as e:
                sys_logger.warn("trade", f"Async set leverage failed (will continue): {e}")
        
        # 下单
        return await self.async_place_order(
            inst_id=inst_id,
            side="buy",
            sz=sz,
            ord_type=ord_type,
            px=px,
            pos_side="long",
            td_mode=td_mode,
            tp_trigger_px=tp_trigger_px,
            tp_ord_px="-1" if tp_trigger_px else "",
            sl_trigger_px=sl_trigger_px,
            sl_ord_px="-1" if sl_trigger_px else "",
            session=session,
        )
    
    async def async_open_short(
        self,
        inst_id: str = "BTC-USDT-SWAP",
        sz: str = "0.01",
        lever: int = None,
        td_mode: str = "cross",
        ord_type: str = "market",
        px: str = "",
        tp_trigger_px: str = "",
        sl_trigger_px: str = "",
        session: aiohttp.ClientSession = None,
    ) -> Dict:
        """异步开空单"""
        # 设置杠杆
        if lever is not None:
            try:
                await self.client.async_request(
                    "POST",
                    "/api/v5/account/set-leverage",
                    {
                        "instId": inst_id,
                        "lever": str(lever),
                        "mgnMode": td_mode,
                        "posSide": "short",
                    },
                    session,
                )
            except Exception as e:
                sys_logger.warn("trade", f"Async set leverage failed (will continue): {e}")
        
        # 下单
        return await self.async_place_order(
            inst_id=inst_id,
            side="sell",
            sz=sz,
            ord_type=ord_type,
            px=px,
            pos_side="short",
            td_mode=td_mode,
            tp_trigger_px=tp_trigger_px,
            tp_ord_px="-1" if tp_trigger_px else "",
            sl_trigger_px=sl_trigger_px,
            sl_ord_px="-1" if sl_trigger_px else "",
            session=session,
        )
    
    async def async_close_position(
        self,
        inst_id: str = "BTC-USDT-SWAP",
        mgn_mode: str = "cross",
        pos_side: str = "net",
        session: aiohttp.ClientSession = None,
    ) -> Dict:
        """异步平仓"""
        body = {
            "instId": inst_id,
            "mgnMode": mgn_mode,
            "posSide": pos_side,
        }
        
        return await self.client.async_request("POST", "/api/v5/trade/close-position", body, session)
    
    async def async_batch_open_long(
        self,
        users: List[Dict],
        inst_id: str = "BTC-USDT-SWAP",
        sz: str = "0.01",
        lever: int = 100,
    ) -> List[Dict]:
        """批量异步开多单（1000+用户场景）
        
        Args:
            users: 用户列表，每个用户包含 {client: OKXClient, ...}
            inst_id: 合约ID
            sz: 数量
            lever: 杠杆
        
        Returns:
            每个用户的开单结果
        """
        async with aiohttp.ClientSession(trust_env=True) as session:
            tasks = []
            for user in users:
                # 为每个用户创建独立的TradeService实例
                ts = TradeService(client=user.get("client"))
                task = ts.async_open_long(
                    inst_id=inst_id,
                    sz=sz,
                    lever=lever,
                    session=session,
                )
                tasks.append(task)
            
            # 并发执行所有任务
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            output = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    output.append({
                        "user_index": i,
                        "status": "error",
                        "error": str(result)[:200],
                    })
                else:
                    output.append({
                        "user_index": i,
                        "status": "success",
                        "result": result,
                    })
            
            return output


# ─── 全局实例 ───

_trade_service: Optional[TradeService] = None

def get_trade_service() -> TradeService:
    """获取全局交易服务实例"""
    global _trade_service
    if _trade_service is None:
        _trade_service = TradeService()
    return _trade_service
