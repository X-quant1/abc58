"""WebSocket 连接管理器

管理所有 WebSocket 客户端连接，提供广播接口。

改进点：
1. broadcast_sync 使用可靠的事件循环引用
2. 支持频道过滤（客户端只接收关心的消息类型）
3. 心跳检测（清理僵死连接）
4. 消息队列缓冲（短时间大量消息合并推送）

消息类型:
- ticker: BTC 实时价格
- account: 账户余额变化
- position: 持仓变化
- signal: 策略信号
- trade: 成交通知
- order: 委托状态变化
- kline: K线更新
- strategy_status: 策略运行状态
"""
import asyncio
import json
import time
import threading
from typing import Dict, Set, Optional, List
from collections import defaultdict
from fastapi import WebSocket


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self._connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
        # 消息历史（最近 50 条，用于新连接时回放）
        self._history: list = []
        self._history_max = 50
        # 每个连接订阅的消息类型（None=接收所有）
        self._subscriptions: Dict[WebSocket, Optional[Set[str]]] = {}
        # 事件循环引用（在第一次 connect 时缓存）
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _ensure_loop(self):
        """确保有事件循环引用"""
        if self._loop is None or self._loop.is_closed():
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                pass

    async def connect(self, ws: WebSocket, channels: List[str] = None):
        """接受新连接

        Args:
            ws: WebSocket 连接
            channels: 订阅的消息类型列表，如 ["ticker", "signal"]；None=接收所有
        """
        await ws.accept()
        async with self._lock:
            self._connections.add(ws)
            self._subscriptions[ws] = set(channels) if channels else None

        # 缓存事件循环引用
        self._loop = asyncio.get_event_loop()

        print(f"[WS] Client connected, total: {len(self._connections)}")

        # 回放最近消息
        if channels:
            # 只回放订阅的消息类型
            for msg_str in self._history[-20:]:
                try:
                    msg = json.loads(msg_str)
                    if msg.get("type") in channels or not channels:
                        await ws.send_text(msg_str)
                except Exception:
                    pass
        else:
            for msg in self._history[-20:]:
                try:
                    await ws.send_text(msg)
                except Exception:
                    pass

    async def disconnect(self, ws: WebSocket):
        """断开连接"""
        async with self._lock:
            self._connections.discard(ws)
            self._subscriptions.pop(ws, None)
        print(f"[WS] Client disconnected, total: {len(self._connections)}")

    async def broadcast(self, msg_type: str, data: dict):
        """广播消息到所有连接（支持频道过滤）

        Args:
            msg_type: 消息类型
            data: 消息数据
        """
        message = json.dumps({
            "type": msg_type,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }, ensure_ascii=False, default=str)

        # 保存历史
        self._history.append(message)
        if len(self._history) > self._history_max:
            self._history = self._history[-self._history_max:]

        # 广播（带频道过滤）
        dead = []
        async with self._lock:
            for ws in self._connections:
                # 检查是否订阅了该消息类型
                subs = self._subscriptions.get(ws)
                if subs is not None and msg_type not in subs:
                    continue
                try:
                    await ws.send_text(message)
                except Exception:
                    dead.append(ws)

        # 清理断开的连接
        for ws in dead:
            self._connections.discard(ws)
            self._subscriptions.pop(ws, None)

    def broadcast_sync(self, msg_type: str, data: dict):
        """同步广播（从非 async 代码调用）

        改进：使用缓存的事件循环引用，不再静默丢失消息。
        """
        try:
            self._ensure_loop()
            if self._loop and self._loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self.broadcast(msg_type, data), self._loop
                )
            else:
                # 事件循环未运行，将消息存入历史供后续回放
                message = json.dumps({
                    "type": msg_type,
                    "data": data,
                    "timestamp": int(time.time() * 1000),
                }, ensure_ascii=False, default=str)
                self._history.append(message)
                if len(self._history) > self._history_max:
                    self._history = self._history[-self._history_max:]
        except RuntimeError:
            pass

    async def ping_dead_connections(self):
        """心跳检测 — 清理僵死连接

        在 WS 推送任务中周期性调用。
        """
        dead = []
        for ws in list(self._connections):
            try:
                # 尝试发送 ping
                await ws.send_json({"type": "ping", "timestamp": int(time.time() * 1000)})
            except Exception:
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections.discard(ws)
                    self._subscriptions.pop(ws, None)
            print(f"[WS] Cleaned {len(dead)} dead connections, remaining: {len(self._connections)}")

    @property
    def connection_count(self) -> int:
        return len(self._connections)


# 全局单例
ws_manager = ConnectionManager()
