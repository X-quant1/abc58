"""Bitget 合约交易服务

支持开仓、平仓、设置杠杆等功能。
"""
from typing import Dict, List, Optional
from app.services.bitget_client import BitgetClient, BitgetAPIError
from app.services.logger import sys_logger


class BitgetTradeService:
    """Bitget合约交易"""
    
    def __init__(self, client: BitgetClient = None):
        self.client = client
    
    def _require_client(self):
        if not self.client:
            raise ValueError("Bitget客户端未初始化")
    
    def set_leverage(self, symbol: str, leverage: int, margin_coin: str = "USDT",
                     hold_side: str = "") -> Dict:
        """设置杠杆倍数
        
        Args:
            symbol: 合约符号，如 BTCUSDT
            leverage: 杠杆倍数
            margin_coin: 保证金币种
            hold_side: 持仓方向 long/short（逐仓必填）
        """
        self._require_client()
        body = {
            "symbol": symbol,
            "marginCoin": margin_coin,
            "leverage": str(leverage),
        }
        if hold_side:
            body["holdSide"] = hold_side
        return self.client._request("POST", "/api/v2/mix/account/set-leverage", body=body)
    
    def place_order(
        self,
        symbol: str,
        side: str,              # buy/sell (net模式) 或 open_long/open_short (hedge模式)
        size: str,
        order_type: str = "market",
        price: str = "",
        hold_side: str = "",
        margin_mode: str = "crossed",
        margin_coin: str = "USDT",
        reduce_only: bool = False,
        tp_trigger_px: str = "",
        tp_ord_px: str = "",
        sl_trigger_px: str = "",
        sl_ord_px: str = "",
    ) -> Dict:
        """下合约订单
        
        Args:
            symbol: 合约符号
            side: buy/sell 或 open_long/open_short
            size: 数量（张数）
            order_type: market/limit
            price: 限价价格
            hold_side: long/short
            margin_mode: crossed/fixed
            margin_coin: USDT
            reduce_only: 是否只减仓
        """
        self._require_client()
        body = {
            "symbol": symbol,
            "marginCoin": margin_coin,
            "productType": "USDT-FUTURES",
            "side": side,
            "orderType": order_type,
            "size": size,
            "marginMode": margin_mode,
            "force": "GTC",
        }
        if hold_side:
            body["holdSide"] = hold_side
        if price and order_type == "limit":
            body["price"] = price
        if reduce_only:
            body["reduceOnly"] = True
        
        # 止盈止损
        if tp_trigger_px:
            body["presetStopSurplusPrice"] = tp_trigger_px
        if sl_trigger_px:
            body["presetStopLossPrice"] = sl_trigger_px
        
        return self.client._request("POST", "/api/v2/mix/order/place-order", body=body)
    
    def open_long(self, symbol: str, size: str, **kwargs) -> Dict:
        """开多 - net模式使用buy"""
        return self.place_order(symbol, "buy", size, **kwargs)
    
    def open_short(self, symbol: str, size: str, **kwargs) -> Dict:
        """开空 - net模式使用sell"""
        return self.place_order(symbol, "sell", size, **kwargs)
    
    def close_position(self, symbol: str, hold_side: str = "", size: str = "",
                       margin_coin: str = "USDT") -> Dict:
        """平仓
        
        Args:
            symbol: 合约符号
            hold_side: long/short（不传则全平）
            size: 数量（不传则全平）
            margin_coin: 保证金币种
        """
        self._require_client()
        body = {
            "symbol": symbol,
            "marginCoin": margin_coin,
            "productType": "USDT-FUTURES",
        }
        if hold_side:
            body["holdSide"] = hold_side
        if size:
            body["size"] = size
        return self.client._request("POST", "/api/v2/mix/order/close-positions", body=body)
    
    def get_positions(self, product_type: str = "USDT-FUTURES") -> List[Dict]:
        """获取持仓列表"""
        self._require_client()
        return self.client._request("GET", "/api/v2/mix/position/all-position",
                                    params={"productType": product_type})


# 单例
_service_instance: Optional[BitgetTradeService] = None


def get_trade_service(client: BitgetClient = None) -> BitgetTradeService:
    global _service_instance
    if _service_instance is None or client:
        _service_instance = BitgetTradeService(client)
    return _service_instance
