"""WebSocket 路由 + 实时数据推送后台任务

提供 /ws 端点，以及后台定时推送行情/账户/持仓数据。
"""
import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.ws_manager import ws_manager
from app.services.cache import get_cached_market_service as _get_ms

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """WebSocket 主端点

    客户端连接后自动接收以下消息:
    - ticker: BTC 实时价格（每 5s 推送）
    - account: 账户余额（每 30s 推送，需 API Key）
    - position: 持仓变化（每 30s 推送，需 API Key）
    - signal: 策略信号（策略引擎触发时推送）
    - trade: 成交通知（下单成交时推送）
    - strategy_status: 策略运行状态变化
    """
    await ws_manager.connect(ws)
    try:
        while True:
            # 保持连接，接收客户端消息（心跳等）
            try:
                data = await asyncio.wait_for(ws.receive_text(), timeout=60)
                # 处理客户端请求
                msg = json.loads(data) if data else {}
                msg_type = msg.get("type", "")

                if msg_type == "ping":
                    await ws.send_text(json.dumps({"type": "pong"}))
                elif msg_type == "subscribe":
                    # 客户端订阅特定频道（预留）
                    await ws.send_text(json.dumps({
                        "type": "subscribed",
                        "data": {"channels": msg.get("channels", [])},
                    }))
            except asyncio.TimeoutError:
                # 发送心跳
                try:
                    await ws.send_text(json.dumps({"type": "heartbeat"}))
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(ws)


# ─── 后台推送任务 ───

_push_task = None


async def start_push_tasks():
    """启动后台推送任务"""
    global _push_task
    _push_task = asyncio.create_task(_push_loop())
    print("[WS] Push tasks started")


async def stop_push_tasks():
    """停止后台推送任务"""
    global _push_task
    if _push_task:
        _push_task.cancel()
        try:
            await _push_task
        except asyncio.CancelledError:
            pass
        _push_task = None
    print("[WS] Push tasks stopped")


async def _push_loop():
    """后台推送循环

    - 每 5 秒推送 BTC 行情
    - 每 30 秒推送账户/持仓数据
    """
    ticker_interval = 5
    account_interval = 30
    ticker_counter = 0
    account_counter = 0

    while True:
        try:
            await asyncio.sleep(1)  # 1秒基础间隔

            # 行情推送（每 5s）
            ticker_counter += 1
            if ticker_counter >= ticker_interval:
                ticker_counter = 0
                try:
                    ticker = await asyncio.to_thread(_get_ms().get_ticker, "BTC-USDT-SWAP")
                    ticker["symbol"] = "BTC-USDT"  # 去掉SWAP后缀，前端兼容
                    await ws_manager.broadcast("ticker", ticker)
                except Exception:
                    pass
                try:
                    eth_ticker = await asyncio.to_thread(_get_ms().get_ticker, "ETH-USDT-SWAP")
                    eth_ticker["symbol"] = "ETH-USDT"
                    await ws_manager.broadcast("ticker", eth_ticker)
                except Exception:
                    pass

            # 账户/持仓推送（每 30s）
            account_counter += 1
            if account_counter >= account_interval:
                account_counter = 0
                try:
                    from app import config
                    if _has_bitget_config():
                        from app.services.bitget_client import get_client
                        client = get_client()
                        if client:
                            balance = client.get_balance("USDT")
                            await ws_manager.broadcast("account", {
                                "account_balance": balance,
                                "unrealized_pnl": 0,
                            })
                except Exception:
                    pass

        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"[WS] Push loop error: {e}")

        await asyncio.sleep(1)
