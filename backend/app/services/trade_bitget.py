"""Bitget 合约交易服务（异步版）"""
from typing import Dict, List, Optional
from app.services.bitget_client import BitgetClient, BitgetAPIError
from app.services.logger import sys_logger


class BitgetTradeService:
    """Bitget合约交易（异步）
    
    止盈止损策略：
    1. 只需TP/SL生效（默认）：place-order 一次调用，带 presetStopSurplusPrice/presetStopLossPrice
       - 优点：一次API调用，零延迟
       - 缺点：仓位列表不可见，触发类型固定 fill_price
    2. 需持仓列表可见：开仓后调 place-pos-tpsl
       - 优点：仓位可见，触发类型可选 mark_price
       - 缺点：两次API调用，有短暂窗口期
    """
    
    def __init__(self, client: BitgetClient = None):
        self.client = client
    
    async def set_leverage(
        self, symbol: str = "BTCUSDT", leverage: int = 10,
        margin_mode: str = "crossed", margin_coin: str = "USDT",
        hold_side: str = ""
    ) -> Dict:
        """设置杠杆倍数

        Args:
            symbol: 交易对
            leverage: 杠杆倍数
            margin_mode: 保证金模式 crossed/isolated
            margin_coin: 保证金币种
            hold_side: 持仓方向（逐仓模式需要）
        """
        body = {
            "symbol": symbol,
            "productType": "USDT-FUTURES",
            "marginCoin": margin_coin,
            "marginMode": margin_mode,
            "leverage": str(leverage),
        }
        if hold_side:
            body["holdSide"] = hold_side
        return await self.client._request("POST", "/api/v2/mix/account/set-leverage", body=body)
    
    async def place_order(
        self, symbol: str, side: str, size: str,
        trade_side: str = "Open", order_type: str = "market",
        price: str = "", margin_mode: str = "crossed",
        margin_coin: str = "USDT", reduce_only: bool = False,
        preset_tp_price: str = "",
        preset_sl_price: str = "",
        hold_side: str = "",
    ) -> Dict:
        """下单

        Args:
            preset_tp_price: 预设止盈价（一次调用方案，仓位不可见）
            preset_sl_price: 预设止损价（一次调用方案，仓位不可见）
            hold_side: 持仓方向 "long"/"short"（双向持仓模式下必填）
        """
        body = {
            "symbol": symbol, "marginCoin": margin_coin,
            "productType": "USDT-FUTURES", "side": side,
            "orderType": order_type, "size": size,
            "marginMode": margin_mode, "force": "GTC",
            "tradeSide": trade_side,
        }
        if price and order_type == "limit":
            body["price"] = price
        if reduce_only:
            body["reduceOnly"] = True
        if hold_side:
            body["holdSide"] = hold_side
        # 预设止盈止损（一次调用方案，仓位不可见）
        if preset_tp_price:
            body["presetStopSurplusPrice"] = preset_tp_price
        if preset_sl_price:
            body["presetStopLossPrice"] = preset_sl_price
        return await self.client._request("POST", "/api/v2/mix/order/place-order", body=body)
    
    async def set_position_tpsl(
        self, symbol: str = "BTCUSDT", hold_side: str = "long",
        tp_price: str = "", sl_price: str = "",
        margin_coin: str = "USDT",
    ) -> List[Dict]:
        """设置仓位止盈止损（place-pos-tpsl）
        
        Args:
            hold_side: 持仓方向 "long"/"short"
            tp_price: 止盈触发价（空单应低于开仓价，多单应高于开仓价）
            sl_price: 止损触发价（空单应高于开仓价，多单应低于开仓价）
        """
        body = {
            "symbol": symbol,
            "productType": "USDT-FUTURES",
            "marginCoin": margin_coin,
            "holdSide": hold_side,
            "stopSurplusTriggerType": "mark_price",
            "stopLossTriggerType": "mark_price",
        }
        if tp_price:
            body["stopSurplusTriggerPrice"] = tp_price
        if sl_price:
            body["stopLossTriggerPrice"] = sl_price
        if not tp_price and not sl_price:
            raise ValueError("止盈价和止损价至少设置一个")
        return await self.client._request("POST", "/api/v2/mix/order/place-pos-tpsl", body=body)
    
    async def open_long(self, symbol: str = "BTCUSDT", size: str = "0.0001",
                        tp_price: str = "", sl_price: str = "",
                        order_type: str = "market", price: str = "",
                        tpsl_visible: bool = False,
                        margin_mode: str = "crossed") -> Dict:
        """开多仓

        Args:
            tp_price: 止盈价
            sl_price: 止损价
            tpsl_visible: True=持仓可见(两次调用), False=仅生效(一次调用,默认)
            margin_mode: 保证金模式 crossed/isolated
        """
        if tpsl_visible and (tp_price or sl_price):
            # 两次调用：开仓 + place-pos-tpsl（仓位可见，mark_price触发）
            result = await self.place_order(symbol, "buy", size, trade_side="Open",
                                             order_type=order_type, price=price,
                                             margin_mode=margin_mode,
                                             hold_side="long")
            try:
                await self.set_position_tpsl(symbol, "long", tp_price, sl_price)
            except Exception as e:
                sys_logger.warning(f"开多后设置止盈止损失败: {e}")
                result["tpsl_warning"] = str(e)[:200]
        else:
            # 一次调用：带 preset TP/SL（仓位不可见，fill_price触发）
            result = await self.place_order(symbol, "buy", size, trade_side="Open",
                                             order_type=order_type, price=price,
                                             margin_mode=margin_mode,
                                             preset_tp_price=tp_price, preset_sl_price=sl_price,
                                             hold_side="long")
        
        # 返回止盈止损价格，方便前端显示
        if tp_price:
            result["tp_price"] = tp_price
        if sl_price:
            result["sl_price"] = sl_price
        return result
    
    async def open_short(self, symbol: str = "BTCUSDT", size: str = "0.0001",
                         tp_price: str = "", sl_price: str = "",
                         order_type: str = "market", price: str = "",
                         tpsl_visible: bool = False,
                         margin_mode: str = "crossed") -> Dict:
        """开空仓

        Args:
            tp_price: 止盈价
            sl_price: 止损价
            tpsl_visible: True=持仓可见(两次调用), False=仅生效(一次调用,默认)
            margin_mode: 保证金模式 crossed/isolated
        """
        if tpsl_visible and (tp_price or sl_price):
            # 两次调用：开仓 + place-pos-tpsl（仓位可见，mark_price触发）
            result = await self.place_order(symbol, "sell", size, trade_side="Open",
                                             order_type=order_type, price=price,
                                             margin_mode=margin_mode,
                                             hold_side="short")
            try:
                await self.set_position_tpsl(symbol, "short", tp_price, sl_price)
            except Exception as e:
                sys_logger.warning(f"开空后设置止盈止损失败: {e}")
                result["tpsl_warning"] = str(e)[:200]
        else:
            # 一次调用：带 preset TP/SL（仓位不可见，fill_price触发）
            result = await self.place_order(symbol, "sell", size, trade_side="Open",
                                             order_type=order_type, price=price,
                                             margin_mode=margin_mode,
                                             preset_tp_price=tp_price, preset_sl_price=sl_price,
                                             hold_side="short")
        
        # 返回止盈止损价格，方便前端显示
        if tp_price:
            result["tp_price"] = tp_price
        if sl_price:
            result["sl_price"] = sl_price
        return result
    
    async def close_long(self, symbol: str = "BTCUSDT", size: str = "") -> Dict:
        return await self.place_order(symbol, "sell", size or "0", trade_side="Close", hold_side="long")

    async def close_short(self, symbol: str = "BTCUSDT", size: str = "") -> Dict:
        return await self.place_order(symbol, "buy", size or "0", trade_side="Close", hold_side="short")
    
    async def close_position(self, symbol: str = "BTCUSDT", hold_side: str = "",
                              size: str = "", margin_coin: str = "USDT") -> Dict:
        body = {"symbol": symbol, "marginCoin": margin_coin, "productType": "USDT-FUTURES"}
        if hold_side:
            body["holdSide"] = hold_side
        if size:
            body["size"] = size
        return await self.client._request("POST", "/api/v2/mix/order/close-positions", body=body)
    
    async def get_positions(self, product_type: str = "USDT-FUTURES") -> List[Dict]:
        return await self.client._request("GET", "/api/v2/mix/position/all-position",
                                          params={"productType": product_type})
    
    async def place_trailing_stop(
        self, symbol: str = "BTCUSDT", hold_side: str = "long",
        trigger_price: str = "", range_rate: str = "0.01",
        size: str = "", margin_coin: str = "USDT",
    ) -> Dict:
        """设置追踪止损/移动止盈（place-tpsl-order with planType=moving_plan）
        
        Args:
            symbol: 交易对
            hold_side: 持仓方向 "long"/"short"
            trigger_price: 触发价格（追踪止损的初始触发价）
            range_rate: 回撤比例（如 "0.01" = 1%，即价格回撤1%触发平仓）
            size: 数量（如 "0.0001"）
        """
        body = {
            "symbol": symbol,
            "productType": "USDT-FUTURES",
            "marginCoin": margin_coin,
            "planType": "moving_plan",
            "holdSide": hold_side,
            "triggerPrice": trigger_price,
            "rangeRate": range_rate,
            "size": size,
        }
        return await self.client._request("POST", "/api/v2/mix/order/place-tpsl-order", body=body)
