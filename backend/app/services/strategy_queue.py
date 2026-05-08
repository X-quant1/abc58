"""策略交易队列集成

将策略信号通过队列异步执行，支持高并发。

使用方式：
1. 在 main.py 启动时调用 init_task_queue()
2. 策略信号 → task_queue.enqueue() → Worker 异步执行
"""
import logging
from typing import Optional
from app.services.task_queue import Task, task_queue, enqueue_trade
from app.services.trade_rest import get_trade_service
from app.services.cache import get_cached_market_service
from app.services.logger import sys_logger

logger = logging.getLogger(__name__)


def handle_open_long(payload: dict) -> dict:
    """处理开多信号"""
    try:
        trade_service = get_trade_service()
        result = trade_service.open_long(
            inst_id=payload.get("inst_id", "BTC-USDT-SWAP"),
            sz=str(payload.get("size", 1)),
            lever=int(payload.get("leverage", 10)),
            td_mode=payload.get("td_mode", "cross"),
            tp_trigger_px=payload.get("tp_trigger_px", ""),
            sl_trigger_px=payload.get("sl_trigger_px", ""),
        )
        sys_logger.info("task_queue", f"Open long executed: {result}")
        return {"success": True, "result": result}
    except Exception as e:
        sys_logger.error("task_queue", f"Open long failed: {e}")
        return {"success": False, "error": str(e)}


def handle_open_short(payload: dict) -> dict:
    """处理开空信号"""
    try:
        trade_service = get_trade_service()
        result = trade_service.open_short(
            inst_id=payload.get("inst_id", "BTC-USDT-SWAP"),
            sz=str(payload.get("size", 1)),
            lever=int(payload.get("leverage", 10)),
            td_mode=payload.get("td_mode", "cross"),
            tp_trigger_px=payload.get("tp_trigger_px", ""),
            sl_trigger_px=payload.get("sl_trigger_px", ""),
        )
        sys_logger.info("task_queue", f"Open short executed: {result}")
        return {"success": True, "result": result}
    except Exception as e:
        sys_logger.error("task_queue", f"Open short failed: {e}")
        return {"success": False, "error": str(e)}


def handle_close_position(payload: dict) -> dict:
    """处理平仓信号"""
    try:
        trade_service = get_trade_service()
        result = trade_service.close_position(
            inst_id=payload.get("inst_id", "BTC-USDT-SWAP"),
            pos_side=payload.get("pos_side", "long"),
        )
        sys_logger.info("task_queue", f"Close position executed: {result}")
        return {"success": True, "result": result}
    except Exception as e:
        sys_logger.error("task_queue", f"Close position failed: {e}")
        return {"success": False, "error": str(e)}


def handle_set_leverage(payload: dict) -> dict:
    """处理设置杠杆"""
    try:
        trade_service = get_trade_service()
        result = trade_service.set_leverage(
            inst_id=payload.get("inst_id", "BTC-USDT-SWAP"),
            lever=int(payload.get("leverage", 10)),
            td_mode=payload.get("td_mode", "cross"),
        )
        sys_logger.info("task_queue", f"Set leverage executed: {result}")
        return {"success": True, "result": result}
    except Exception as e:
        sys_logger.error("task_queue", f"Set leverage failed: {e}")
        return {"success": False, "error": str(e)}


def handle_algo_trailing(payload: dict) -> dict:
    """处理移动止盈信号"""
    try:
        trade_service = get_trade_service()
        result = trade_service.place_algo_trailing(
            inst_id=payload.get("inst_id", "BTC-USDT-SWAP"),
            side=payload.get("side", "buy"),
            sz=payload.get("sz", "1"),
            callback_points=payload.get("callback_points"),
            callback_pct=payload.get("callback_pct"),
            activate_price=payload.get("activate_price", ""),
            pos_side=payload.get("pos_side", "long"),
            td_mode=payload.get("td_mode", "cross"),
        )
        sys_logger.info("task_queue", f"Algo trailing executed: {result}")
        return {"success": True, "result": result}
    except Exception as e:
        sys_logger.error("task_queue", f"Algo trailing failed: {e}")
        return {"success": False, "error": str(e)}


def init_task_queue(worker_count: int = 4):
    """初始化任务队列（在应用启动时调用）"""
    # 注册处理器
    task_queue.register_handler("open_long", handle_open_long)
    task_queue.register_handler("open_short", handle_open_short)
    task_queue.register_handler("close_position", handle_close_position)
    task_queue.register_handler("set_leverage", handle_set_leverage)
    task_queue.register_handler("algo_trailing", handle_algo_trailing)
    
    # 启动工作线程
    task_queue.start(worker_count=worker_count)
    logger.info(f"[TaskQueue] Initialized with {worker_count} workers")


# ─────────────────────────────────────────────────────────
# 便捷函数：供策略引擎调用
# ─────────────────────────────────────────────────────────

def queue_open_long(inst_id: str, size: float, leverage: int = 10,
                    tp_trigger_px: str = "", sl_trigger_px: str = "",
                    callback=None) -> bool:
    """入队开多任务"""
    payload = {
        "inst_id": inst_id,
        "size": size,
        "leverage": leverage,
        "tp_trigger_px": tp_trigger_px,
        "sl_trigger_px": sl_trigger_px,
    }
    return enqueue_trade("open_long", payload, callback)


def queue_open_short(inst_id: str, size: float, leverage: int = 10,
                     tp_trigger_px: str = "", sl_trigger_px: str = "",
                     callback=None) -> bool:
    """入队开空任务"""
    payload = {
        "inst_id": inst_id,
        "size": size,
        "leverage": leverage,
        "tp_trigger_px": tp_trigger_px,
        "sl_trigger_px": sl_trigger_px,
    }
    return enqueue_trade("open_short", payload, callback)


def queue_close_position(inst_id: str, pos_side: str, callback=None) -> bool:
    """入队平仓任务"""
    payload = {
        "inst_id": inst_id,
        "pos_side": pos_side,
    }
    return enqueue_trade("close_position", payload, callback)


def queue_algo_trailing(
    inst_id: str, side: str, sz: str,
    callback_points: float = None, callback_pct: float = None,
    activate_price: str = "", pos_side: str = "long",
    td_mode: str = "cross", callback=None
) -> bool:
    """入队移动止盈任务"""
    payload = {
        "inst_id": inst_id,
        "side": side,
        "sz": sz,
        "callback_points": callback_points,
        "callback_pct": callback_pct,
        "activate_price": activate_price,
        "pos_side": pos_side,
        "td_mode": td_mode,
    }
    return enqueue_trade("algo_trailing", payload, callback)
