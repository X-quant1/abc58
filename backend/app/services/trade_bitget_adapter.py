"""Bitget 交易适配器 - 兼容 OKX TradeService 接口

将 OKX 风格的参数转换为 Bitget 参数，供策略系统使用。
"""
import asyncio
from typing import Dict, Optional
from app.services.bitget_client import BitgetClient
from app.services.trade_bitget import BitgetTradeService
from app.services.logger import sys_logger
from app.routers.settings import _load_bitget_config, _has_bitget_config


# OKX 合约面值映射 (1张合约代表多少币)
OKX_FACE_VALUE = {
    "BTC-USDT-SWAP": 0.01,
    "ETH-USDT-SWAP": 0.1,
    "SOL-USDT-SWAP": 1.0,
}


def _inst_id_to_symbol(inst_id: str) -> str:
    """OKX instId 转 Bitget symbol
    BTC-USDT-SWAP -> BTCUSDT
    """
    return inst_id.replace("-USDT-SWAP", "USDT").replace("-USDT-", "USDT")


def _sz_to_size(inst_id: str, sz: str) -> str:
    """前端数量转 Bitget 数量
    
    前端现在直接传 BTC 数量（如 0.0001），不需要转换
    """
    return sz


def _size_to_sz(inst_id: str, size: str) -> str:
    """Bitget 数量转前端数量"""
    return size


class BitgetTradeAdapter:
    """Bitget 交易适配器 - 兼容 OKX TradeService 接口
    
    将 OKX 风格的调用转换为 Bitget API 调用。
    所有方法都是同步接口，内部使用 asyncio.run() 执行异步操作。
    """
    
    def __init__(self):
        self._service = None
        self._client = None
    
    def _get_service(self) -> BitgetTradeService:
        """获取 Bitget 交易服务"""
        if self._service is None:
            if not _has_bitget_config():
                raise RuntimeError("请先绑定 Bitget API")
            cfg = _load_bitget_config()
            self._client = BitgetClient(cfg["key"], cfg["secret"], cfg["passphrase"])
            self._service = BitgetTradeService(self._client)
        return self._service
    
    def _run_async(self, coro):
        """运行异步协程"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    
    # ─── 杠杆设置 ───
    
    def set_leverage(self, inst_id: str, lever: int, mgn_mode: str = "cross", pos_side: str = "") -> Dict:
        """设置杠杆"""
        service = self._get_service()
        symbol = _inst_id_to_symbol(inst_id)
        margin_mode = "crossed" if mgn_mode == "cross" else "isolated"
        
        async def _do():
            return await service.set_leverage(
                symbol=symbol,
                leverage=lever,
                margin_mode=margin_mode,
            )
        
        result = self._run_async(_do())
        sys_logger.info("trade", f"Bitget leverage set: {symbol} x{lever} {margin_mode}")
        return result
    
    # ─── 下单 ───
    
    def place_order(
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
    ) -> Dict:
        """下合约订单"""
        service = self._get_service()
        symbol = _inst_id_to_symbol(inst_id)
        size = _sz_to_size(inst_id, sz)
        
        # 确定交易方向
        if pos_side == "long":
            trade_side = "Open" if side == "buy" else "Close"
        elif pos_side == "short":
            trade_side = "Open" if side == "sell" else "Close"
        else:
            # net 模式：根据 side 判断
            trade_side = "Open"
        
        # Bitget side
        bitget_side = side

        # 确定持仓方向（双向持仓模式需要）
        hold_side = ""
        if pos_side == "long":
            hold_side = "long"
        elif pos_side == "short":
            hold_side = "short"

        async def _do():
            return await service.place_order(
                symbol=symbol,
                side=bitget_side,
                size=size,
                trade_side=trade_side,
                order_type=ord_type,
                price=px,
                margin_mode="crossed" if td_mode == "cross" else "isolated",
                reduce_only=reduce_only,
                preset_tp_price=tp_trigger_px,
                preset_sl_price=sl_trigger_px,
                hold_side=hold_side,
            )
        
        result = self._run_async(_do())
        sys_logger.info("trade", f"Bitget order: {symbol} {side} {size} TP={tp_trigger_px} SL={sl_trigger_px}")
        return result
    
    # ─── 开仓 ───
    
    def open_long(
        self,
        inst_id: str,
        sz: str,
        lever: int = 10,
        td_mode: str = "cross",
        tp_trigger_px: str = "",
        sl_trigger_px: str = "",
    ) -> Dict:
        """开多仓"""
        service = self._get_service()
        symbol = _inst_id_to_symbol(inst_id)
        size = _sz_to_size(inst_id, sz)
        margin_mode = "crossed" if td_mode == "cross" else "isolated"

        async def _do():
            return await service.open_long(
                symbol=symbol,
                size=size,
                tp_price=tp_trigger_px,
                sl_price=sl_trigger_px,
                margin_mode=margin_mode,
            )

        result = self._run_async(_do())
        sys_logger.info("trade", f"Bitget open long: {symbol} {size} margin={margin_mode} TP={tp_trigger_px} SL={sl_trigger_px}")
        return result

    def open_short(
        self,
        inst_id: str,
        sz: str,
        lever: int = 10,
        td_mode: str = "cross",
        tp_trigger_px: str = "",
        sl_trigger_px: str = "",
    ) -> Dict:
        """开空仓"""
        service = self._get_service()
        symbol = _inst_id_to_symbol(inst_id)
        size = _sz_to_size(inst_id, sz)
        margin_mode = "crossed" if td_mode == "cross" else "isolated"

        async def _do():
            return await service.open_short(
                symbol=symbol,
                size=size,
                tp_price=tp_trigger_px,
                sl_price=sl_trigger_px,
                margin_mode=margin_mode,
            )

        result = self._run_async(_do())
        sys_logger.info("trade", f"Bitget open short: {symbol} {size} margin={margin_mode} TP={tp_trigger_px} SL={sl_trigger_px}")
        return result
    
    # ─── 平仓 ───
    
    def close_position(self, inst_id: str, pos_side: str = "", mgn_mode: str = "cross") -> Dict:
        """平仓"""
        service = self._get_service()
        symbol = _inst_id_to_symbol(inst_id)
        
        hold_side = ""
        if pos_side == "long":
            hold_side = "long"
        elif pos_side == "short":
            hold_side = "short"
        
        async def _do():
            return await service.close_position(symbol=symbol, hold_side=hold_side)
        
        result = self._run_async(_do())
        sys_logger.info("trade", f"Bitget close position: {symbol} {pos_side}")
        return result
    
    # ─── 追踪止损 ───
    
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
        """设置追踪止损/移动止盈
        
        Args:
            inst_id: 合约ID
            side: buy / sell
            sz: 数量（OKX张数）
            callback_pct: 回调比例（百分比，如 1.5 表示 1.5%）
            callback_points: 回调点数（优先级高于callback_pct）
            activate_price: 激活价格
            pos_side: 持仓方向
        """
        service = self._get_service()
        symbol = _inst_id_to_symbol(inst_id)
        size = _sz_to_size(inst_id, sz)
        
        # 持仓方向
        hold_side = "long" if pos_side == "long" else "short" if pos_side == "short" else "long"

        # 回调比例：点数模式优先，百分比模式次之
        range_rate = "0.01"  # 默认 1%
        if callback_points and callback_points > 0:
            # 点数模式：将点数转换为比例（回调点数 / 当前价格）
            # 例如：回调 150 点，当前价格 95000 → range_rate = 150/95000 = 0.001579
            try:
                from app.services.cache import get_cached_market_service
                ms = get_cached_market_service()
                ticker = ms.get_ticker(inst_id.replace("-USDT-SWAP", ""))
                current_price = ticker.get("price", 0)
                if current_price > 0:
                    range_rate = f"{callback_points / current_price:.6f}"
                else:
                    range_rate = f"{callback_pct / 100:.4f}" if callback_pct and callback_pct > 0 else "0.01"
            except Exception:
                range_rate = f"{callback_pct / 100:.4f}" if callback_pct and callback_pct > 0 else "0.01"
        elif callback_pct and callback_pct > 0:
            range_rate = f"{callback_pct / 100:.4f}"
        
        async def _do():
            return await service.place_trailing_stop(
                symbol=symbol,
                hold_side=hold_side,
                trigger_price=activate_price or "1",  # 触发价，传空会报错
                range_rate=range_rate,
                size=size,
            )
        
        result = self._run_async(_do())
        sys_logger.info("trade", f"Bitget trailing stop: {symbol} {hold_side} range={range_rate}")
        return result
    
    # ─── 持仓查询 ───
    
    def get_swap_positions(self, inst_id: str = "") -> list:
        """获取合约持仓"""
        service = self._get_service()
        
        async def _do():
            positions = await service.get_positions()
            # 转换为 OKX 格式
            result = []
            for pos in positions:
                if inst_id and _inst_id_to_symbol(inst_id) != pos.get("symbol"):
                    continue
                if float(pos.get("total", 0)) > 0:
                    result.append({
                        "instId": pos["symbol"].replace("USDT", "-USDT-SWAP"),
                        "posSide": pos.get("holdSide", ""),
                        "pos": _size_to_sz(pos["symbol"] + "-USDT-SWAP", pos.get("total", "0")),
                        "avgPx": pos.get("openPriceAvg", ""),
                        "upl": pos.get("unrealizedPL", "0"),
                    })
            return result
        
        return self._run_async(_do())


# 全局单例
_trade_adapter = None


def get_trade_service() -> BitgetTradeAdapter:
    """获取交易服务单例（Bitget 适配器）"""
    global _trade_adapter
    if _trade_adapter is None:
        _trade_adapter = BitgetTradeAdapter()
    return _trade_adapter
