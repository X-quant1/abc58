"""交易执行服务 - OKX 合约交易

负责合约开仓/平仓/止损止盈/一键平仓等操作。
"""
import json
from typing import Optional

from app.services.market import _run_okx, _to_okx_instId, OKXAPIError, OKX_ERR_INSUFFICIENT_BALANCE
from app.services.logger import sys_logger


def safe_float(val, default=0.0):
    """安全转换为 float，处理 OKX API 返回空字符串的情况"""
    try:
        return float(val) if val not in (None, "", "None") else default
    except (ValueError, TypeError):
        return default


class TradeService:
    """OKX 合约交易服务"""

    # ─── 杠杆设置 ───

    def set_leverage(self, inst_id: str, lever: int, mgn_mode: str = "cross",
                     pos_side: str = "") -> dict:
        """设置杠杆倍数

        Args:
            inst_id: 合约ID，如 BTC-USDT-SWAP
            lever: 杠杆倍数，如 10
            mgn_mode: 保证金模式 cross=全仓 isolated=逐仓
            pos_side: 持仓方向 net/long/short（逐仓必填）
        """
        args = ["swap", "leverage", "--instId", inst_id,
                "--lever", str(lever), "--mgnMode", mgn_mode]
        if pos_side:
            args.extend(["--posSide", pos_side])
        return _run_okx(args)

    def get_leverage(self, inst_id: str, mgn_mode: str = "cross") -> dict:
        """获取当前杠杆设置"""
        return _run_okx(["swap", "get-leverage", "--instId", inst_id,
                         "--mgnMode", mgn_mode])

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
    ) -> dict:
        """下合约订单

        OKX 合约下单通过 okx swap place 命令。
        支持：
        - 开多: side=buy, posSide=long (双向持仓) 或 side=buy, posSide=net (单向)
        - 开空: side=sell, posSide=short (双向持仓) 或 side=sell, posSide=net (单向)
        - 平多: side=sell, posSide=long 或 side=sell, posSide=net + reduceOnly
        - 平空: side=buy, posSide=short 或 side=buy, posSide=net + reduceOnly
        """
        args = [
            "swap", "place",
            "--instId", inst_id,
            "--side", side,
            "--ordType", ord_type,
            "--sz", sz,
            "--posSide", pos_side,
            "--tdMode", td_mode,
        ]
        if px and ord_type == "limit":
            args.extend(["--px", px])
        if reduce_only:
            args.append("--reduceOnly")
        if cl_ord_id:
            args.extend(["--clOrdId", cl_ord_id])
        # 止盈止损（使用attachAlgoOrds方式）
        # 根据OKX API文档，推荐使用attachAlgoOrds参数
        # 但OKX CLI通过--tpTriggerPx等参数实现
        # 注意：负数参数必须用等号形式
        if tp_trigger_px:
            args.extend(["--tpTriggerPx", tp_trigger_px])
            tp_price = tp_ord_px or "-1"
            args.append(f"--tpOrdPx={tp_price}")
        if sl_trigger_px:
            args.extend(["--slTriggerPx", sl_trigger_px])
            sl_price = sl_ord_px or "-1"
            args.append(f"--slOrdPx={sl_price}")

        return _run_okx(args)

    def open_long(
        self,
        inst_id: str = "BTC-USDT-SWAP",
        sz: str = "0.01",
        lever: int = None,  # 不设置默认值，由调用方决定是否设置杠杆
        td_mode: str = "cross",
        ord_type: str = "market",
        px: str = "",
        tp_trigger_px: str = "",
        sl_trigger_px: str = "",
    ) -> dict:
        """开多单

        如果传入lever参数，会自动设置杠杆，然后下单。
        如果不传lever参数，则使用当前杠杆设置。
        posSide=long 适用于双向持仓模式（long_short_mode）。
        posSide=net 适用于单向持仓模式。
        """
        # 只有明确传入lever参数时才设置杠杆
        if lever is not None:
            try:
                result = self.set_leverage(inst_id, lever, td_mode, pos_side="long")
                sys_logger.info("trade", f"Set leverage to {lever}X for long: {result}")
            except Exception as e:
                sys_logger.warn("trade", f"Set leverage failed (will continue): {e}")

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
        lever: int = None,  # 不设置默认值，由调用方决定是否设置杠杆
        td_mode: str = "cross",
        ord_type: str = "market",
        px: str = "",
        tp_trigger_px: str = "",
        sl_trigger_px: str = "",
    ) -> dict:
        """开空单
        
        如果传入lever参数，会自动设置杠杆，然后下单。
        如果不传lever参数，则使用当前杠杆设置。
        """
        # 只有明确传入lever参数时才设置杠杆
        if lever is not None:
            try:
                self.set_leverage(inst_id, lever, td_mode, pos_side="short")
            except Exception as e:
                sys_logger.warn("trade", f"Set leverage failed (will continue): {e}")

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
        auto_cxl: bool = True,
    ) -> dict:
        """平仓（单个合约）

        Args:
            inst_id: 合约ID
            mgn_mode: 保证金模式
            pos_side: 持仓方向 net/long/short
            auto_cxl: 是否自动撤销该合约的未成交订单
        """
        args = [
            "swap", "close",
            "--instId", inst_id,
            "--mgnMode", mgn_mode,
            "--posSide", pos_side,
        ]
        if auto_cxl:
            args.append("--autoCxl")
        return _run_okx(args)

    def close_all_positions(self) -> dict:
        """一键平仓 — 平掉所有合约持仓

        先获取所有持仓，然后逐个平仓。
        返回每个合约的平仓结果。
        """
        from app.services.market import market_service
        positions = market_service.get_positions()
        if not positions:
            return {"closed": 0, "results": [], "msg": "no positions to close"}

        results = []
        for pos in positions:
            inst_id = pos.get("symbol", "")
            side = pos.get("side", "")
            # OKX posSide: long/short/net
            pos_side = side if side in ("long", "short") else "net"
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

    def cancel_order(self, inst_id: str, ord_id: str = "", cl_ord_id: str = "") -> dict:
        """撤销合约订单"""
        args = ["swap", "cancel", inst_id]
        if ord_id:
            args.extend(["--ordId", ord_id])
        if cl_ord_id:
            args.extend(["--clOrdId", cl_ord_id])
        return _run_okx(args)

    # ─── 查询 ───

    def get_swap_positions(self, inst_id: str = "") -> list:
        """获取合约持仓"""
        args = ["swap", "positions"]
        if inst_id:
            args.append(inst_id)
        data = _run_okx(args)
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
        """获取合约委托列表"""
        args = ["swap", "orders"]
        if inst_id:
            args.extend(["--instId", inst_id])
        if history:
            args.append("--history")
        data = _run_okx(args)
        return data if isinstance(data, list) else []

    def get_swap_fills(self, inst_id: str = "") -> list:
        """获取合约成交流水"""
        args = ["swap", "fills"]
        if inst_id:
            args.extend(["--instId", inst_id])
        data = _run_okx(args)
        return data if isinstance(data, list) else []

    def cancel_algo_order(self, inst_id: str, algo_id: str) -> dict:
        """取消算法单"""
        args = [
            "swap", "algo", "cancel",
            "--instId", inst_id,
            "--algoId", algo_id,
        ]
        return _run_okx(args)

    # ─── 移动止损算法单 ───

    def place_algo_trailing(
        self,
        inst_id: str,
        side: str,
        sz: str,
        callback_pct: float = None,
        callback_points: float = None,  # 回调点数
        activate_price: str = "",
        pos_side: str = "net",
        td_mode: str = "cross",
        reduce_only: bool = True,
    ) -> dict:
        """下移动止损（追踪止损）算法单

        Args:
            callback_pct: 回调比例（百分比），如 1.5 表示回调 1.5% 触发
            callback_points: 回调点数，如 25 表示回调 25 点触发（优先级高于callback_pct）
            activate_price: 激活价格，价格达到此价位后开始追踪
        
        Note:
            OKX API支持callbackSpread参数，但CLI不支持。
            当使用callback_points时，系统会直接调用API使用callbackSpread参数。
        """
        # 如果使用点数模式，直接调用API（使用callbackSpread参数）
        if callback_points is not None and callback_points > 0:
            from app.services.market import _call_okx_api
            
            body = {
                "instId": inst_id,
                "tdMode": td_mode,
                "side": side,
                "posSide": pos_side,
                "sz": sz,
                "ordType": "move_order_stop",
                "callbackSpread": str(callback_points),  # 使用callbackSpread参数
            }
            
            if activate_price:
                body["activePx"] = activate_price
            
            if reduce_only:
                body["reduceOnly"] = "true"
            
            sys_logger.info("trade", f"Placing trailing stop via API: callbackSpread={callback_points}")
            return _call_okx_api("POST", "/api/v5/trade/order-algo", body)
        
        # 比例模式：使用CLI（因为CLI支持callbackRatio）
        args = [
            "swap", "algo", "trail",
            "--instId", inst_id,
            "--side", side,
            "--sz", sz,
            "--posSide", pos_side,
            "--tdMode", td_mode,
        ]

        if callback_pct is not None:
            # 将百分比转换为比例（例如 1.5% -> 0.015）
            ratio = callback_pct / 100
            args.extend(["--callbackRatio", str(ratio)])

        # 激活价格
        if activate_price:
            args.extend(["--activePx", activate_price])

        if reduce_only:
            args.append("--reduceOnly")

        return _run_okx(args)

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
    ) -> dict:
        """下止损止盈算法单（OCO类型）"""
        args = [
            "swap", "algo", "place",
            "--instId", inst_id,
            "--side", side,
            "--sz", sz,
            "--posSide", pos_side,
            "--tdMode", td_mode,
            "--ordType", "oco",  # OCO类型支持同时设置止盈止损
        ]
        if tp_trigger_px:
            args.extend(["--tpTriggerPx", tp_trigger_px])
            args.append(f"--tpOrdPx={tp_ord_px}")
        if sl_trigger_px:
            args.extend(["--slTriggerPx", sl_trigger_px])
            args.append(f"--slOrdPx={sl_ord_px}")
        if reduce_only:
            args.append("--reduceOnly")

        return _run_okx(args)


# 单例
trade_service = TradeService()
