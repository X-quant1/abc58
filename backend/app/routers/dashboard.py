"""Dashboard 路由 - 总览数据"""
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from datetime import datetime, date
import json
import random
import os
import asyncio

from app.services.cache import get_cached_market_service
from app import config
from app.models import Strategy, Trade, User, AiChatHistory, AiJudgeRecord
from app.database import SessionLocal

# 预导入Bitget客户端
from app.services.bitget_client import BitgetClient

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

# 获取带缓存的行情服务
_ms = get_cached_market_service

# 平均收益持久化文件（模拟数据，每日0点随机浮动）
_AVG_PROFIT_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "platform_stats.json")


def _get_avg_profit() -> float:
    """自动模式：每天在原数值上随机浮动 -1.5 到 2.5"""
    today = str(date.today())
    try:
        if os.path.exists(_AVG_PROFIT_FILE):
            with open(_AVG_PROFIT_FILE, "r") as f:
                data = json.load(f)
        else:
            data = {"avg_profit": 5.0, "last_update": "2000-01-01"}
    except Exception:
        data = {"avg_profit": 5.0, "last_update": "2000-01-01"}

    if data.get("last_update") != today:
        current = data.get("avg_profit", 5.0)
        drift = round(random.uniform(-1.5, 2.5), 2)
        current = round(current + drift, 2)
        data = {"avg_profit": current, "last_update": today}
        try:
            with open(_AVG_PROFIT_FILE, "w") as f:
                json.dump(data, f)
        except Exception:
            pass

    return data["avg_profit"]


# 从settings导入
from app.routers.settings import _has_bitget_config


@router.get("/overview")
async def get_overview():
    """获取总览数据：多币种行情 + 账户信息 + 持仓"""
    import asyncio
    from app.services.bitget_client import BitgetClient

    symbols_bg = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "DOTUSDT"]

    prices = {}
    account_info = {"account_balance": None, "unrealized_pnl": None, "currencies": []}
    positions_info = []
    funding_info = {"funding_balance": None, "funding_details": []}

    # 行情（Bitget）
    try:
        from app.routers.settings import _load_bitget_config
        bg_cfg = _load_bitget_config()
        if bg_cfg.get("key"):
            bg_client = BitgetClient(bg_cfg["key"], bg_cfg["secret"], bg_cfg["passphrase"])
            all_tickers = bg_client.get_tickers()
            ticker_map = {t["symbol"]: t for t in all_tickers}
            for s in symbols_bg:
                t = ticker_map.get(s, {})
                prices[s] = {"price": float(t.get("lastPr", 0)), "change_24h": float(t.get("change24h", 0))}
        else:
            prices = {s: {"price": 0, "change_24h": 0} for s in symbols_bg}
    except Exception:
        prices = {s: {"price": 0, "change_24h": 0} for s in symbols_bg}

    # Bitget合约账户余额
    if _has_bitget_config():
        try:
            from app.routers.settings import _load_bitget_config
            bg = _load_bitget_config()
            if bg.get("key"):
                bg_client = BitgetClient(bg["key"], bg["secret"], bg["passphrase"])
                mix_acc = bg_client.get_mix_account()
                if mix_acc:
                    account_info = {
                        "account_balance": float(mix_acc.get("accountEquity", 0)),
                        "unrealized_pnl": float(mix_acc.get("unrealizedPL", 0)),
                        "currencies": [],
                    }
        except Exception as e:
            pass

    # 恐惧贪婪指数
    fear_greed = 50
    btc_change = prices.get("BTCUSDT", {}).get("change_24h", 0)
    if btc_change > 5: fear_greed = 75
    elif btc_change > 2: fear_greed = 65
    elif btc_change > 0: fear_greed = 55
    elif btc_change > -2: fear_greed = 45
    elif btc_change > -5: fear_greed = 35
    else: fear_greed = 25

    # 策略统计
    strategy_stats = {"running_count": 0, "total_profit": 0.0}
    try:
        db = SessionLocal()
        running = db.query(Strategy).filter(Strategy.enabled == True).all()
        strategy_stats["running_count"] = len(running)
        from sqlalchemy import func
        total_pnl = db.query(func.sum(Trade.pnl)).scalar()
        strategy_stats["total_profit"] = float(total_pnl) if total_pnl else 0.0
        db.close()
    except Exception:
        try:
            db.close()
        except Exception:
            pass

    return {
        **account_info,
        **funding_info,
        "positions": positions_info,
        "position_count": len(positions_info),
        "has_api_key": _has_bitget_config(),
        "running_strategies": strategy_stats["running_count"],
        "total_strategy_profit": strategy_stats["total_profit"],
        "btc_price": prices.get("BTCUSDT", {}).get("price", 0),
        "btc_change_24h": prices.get("BTCUSDT", {}).get("change_24h", 0),
        "eth_price": prices.get("ETHUSDT", {}).get("price", 0),
        "eth_change_24h": prices.get("ETHUSDT", {}).get("change_24h", 0),
        "prices": prices,
        "fear_greed_index": fear_greed,
    }


@router.get("/pnl_curve")
async def get_pnl_curve(days: int = 30):
    """获取资产曲线（基于账户账单）"""
    import asyncio
    def _fetch():
        return _ms().get_bills(limit=min(days * 4, 100))
    try:
        data = await asyncio.wait_for(asyncio.to_thread(_fetch), timeout=6.0)
    except Exception:
        data = []
    try:
        daily_map = {}
        for bill in data:
            ts = bill.get("timestamp", 0)
            if not ts:
                continue
            date_str = datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d")
            equity = bill.get("account_equity", 0)
            if equity and (date_str not in daily_map or ts > daily_map[date_str]["ts"]):
                daily_map[date_str] = {"ts": ts, "equity": equity}
        curve = [{"date": d, "equity": daily_map[d]["equity"]} for d in sorted(daily_map)]
        return {"data": curve}
    except Exception:
        return {"data": []}


@router.get("/recent_trades")
async def get_recent_trades(limit: int = 10):
    """获取最近交易记录"""
    import asyncio
    def _fetch():
        return _ms().get_bills(limit=limit)
    try:
        trades = await asyncio.wait_for(asyncio.to_thread(_fetch), timeout=6.0)
    except Exception:
        trades = []
    try:
        results = []
        for t in trades:
            if not isinstance(t, dict):
                continue
            results.append({
                "id": t.get("bill_id", ""),
                "symbol": t.get("instId", ""),
                "side": "买入" if t.get("side") == "buy" else ("卖出" if t.get("side") == "sell" else t.get("type", "")),
                "price": t.get("px", 0) or t.get("fillPx", 0),
                "size": t.get("sz", 0) or t.get("fillSz", 0),
                "pnl": t.get("pnl", 0),
                "fee": t.get("fee", 0),
                "timestamp": t.get("timestamp", 0),
                "type": t.get("type", ""),
            })
        return {"trades": results}
    except Exception:
        return {"trades": []}


@router.get("/platform_stats")
async def get_platform_stats():
    """获取平台统计数据：策略总数、活跃用户、平均收益、胜率、运行中策略"""
    from app.database import SessionLocal as DB
    from app.models import User, SiteConfig, Strategy, Trade

    db = DB()
    try:
        # 读取配置
        def get_config(key, default=""):
            row = db.query(SiteConfig).filter(SiteConfig.key == key).first()
            return row.value if row and row.value else default

        # 活跃用户
        active_users_mode = get_config("active_users_mode", "real")
        if active_users_mode == "custom":
            active_users = int(get_config("active_users", "1"))
        else:
            active_users = db.query(User).count()

        # 策略总数
        total_strategies_mode = get_config("total_strategies_mode", "real")
        if total_strategies_mode == "custom":
            total_strategies = int(get_config("total_strategies", "15"))
        else:
            total_strategies = db.query(Strategy).count()

        # 运行中的策略
        running_strategies = db.query(Strategy).filter(Strategy.enabled == True).count()

        # 平均收益
        avg_profit_mode = get_config("avg_profit_mode", "custom")
        if avg_profit_mode == "custom":
            avg_profit = float(get_config("avg_profit", "5.0"))
        else:
            avg_profit = _get_avg_profit()

        # 胜率
        try:
            trades = db.query(Trade).filter(Trade.pnl.isnot(None), Trade.pnl != 0).all()
            if trades:
                winning_trades = sum(1 for t in trades if t.pnl and t.pnl > 0)
                win_rate = (winning_trades / len(trades) * 100)
            else:
                win_rate = 68.5
        except:
            win_rate = 68.5

        return {
            "total_strategies": total_strategies,
            "active_users": active_users,
            "avg_profit": avg_profit,
            "win_rate": round(win_rate, 1),
            "running_strategies": running_strategies,
        }
    except Exception as e:
        print(f"[Dashboard] platform_stats error: {e}")
        raise
    finally:
        db.close()


@router.get("/market_regime")
async def get_market_regime():
    """获取市场状态仪表盘数据"""
    import asyncio

    def _fetch():
        result = {
            "regime": "ranging",
            "score": 0,
            "details": {},
            "btc_price": 0,
            "btc_change_24h": 0,
            "funding_rate": 0,
        }
        try:
            # 1. 获取BTC 1h K线（Bitget）
            from app.routers.settings import _load_bitget_config
            bg_cfg2 = _load_bitget_config()
            if bg_cfg2.get("key"):
                bg2 = BitgetClient(bg_cfg2["key"], bg_cfg2["secret"], bg_cfg2["passphrase"])
                raw_klines = bg2.get_klines("BTCUSDT", "1H", 100)
            else:
                raw_klines = []
            if raw_klines and len(raw_klines) > 60:
                # 转换Bitget K线格式到dict格式
                klines = []
                for item in raw_klines:
                    klines.append({
                        "timestamp": int(item[0]),
                        "open": float(item[1]),
                        "high": float(item[2]),
                        "low": float(item[3]),
                        "close": float(item[4]),
                        "volume": float(item[5]),
                    })
                from app.services.market_regime import market_regime_detector
                regime_data = market_regime_detector.detect_with_score(klines)
                result["regime"] = regime_data["regime"]
                result["score"] = regime_data["score"]
                result["details"] = regime_data.get("details", {})

                # 判断趋势方向
                if len(klines) >= 2:
                    last_close = klines[-1]["close"]
                    prev_close = klines[-25]["close"] if len(klines) > 25 else klines[0]["close"]
                    result["trend_direction"] = "up" if last_close > prev_close else "down"
        except Exception as e:
            print(f"[Dashboard] Market regime error: {e}")

        try:
            # 2. BTC合约价格和涨跌幅（Bitget）
            from app.routers.settings import _load_bitget_config
            bg_cfg3 = _load_bitget_config()
            if bg_cfg3.get("key"):
                bg3 = BitgetClient(bg_cfg3["key"], bg_cfg3["secret"], bg_cfg3["passphrase"])
                btc_ticker = bg3.get_ticker("BTCUSDT")
                if btc_ticker:
                    result["btc_price"] = float(btc_ticker.get("lastPr", 0))
                    change_str = btc_ticker.get("change24h", "0")
                    result["btc_change_24h"] = float(change_str) if change_str else 0
                    result["funding_rate"] = float(btc_ticker.get("fundingRate", 0))
        except Exception:
            pass

        try:
            # 3. 资金费率（直接用 MarketService，缓存层无此方法）
            from app.services.market import MarketService
            ms = MarketService()
            rates = ms.get_funding_rate("BTC-USDT-SWAP")
            if rates and isinstance(rates, list) and len(rates) > 0:
                result["funding_rate"] = float(rates[0].get("fundingRate", 0))
        except Exception as e:
            print(f"[Dashboard] Funding rate error: {e}")

        try:
            # 4. 恐惧贪婪指数
            btc_change = result.get("btc_change_24h", 0)
            if btc_change > 5: result["fear_greed"] = 75
            elif btc_change > 2: result["fear_greed"] = 65
            elif btc_change > 0: result["fear_greed"] = 55
            elif btc_change > -2: result["fear_greed"] = 45
            elif btc_change > -5: result["fear_greed"] = 35
            else: result["fear_greed"] = 25
        except Exception:
            result["fear_greed"] = 50

        return result

    try:
        data = await asyncio.wait_for(asyncio.to_thread(_fetch), timeout=10.0)
    except asyncio.TimeoutError:
        data = {"regime": "ranging", "score": 0, "details": {}, "btc_price": 0, "btc_change_24h": 0, "funding_rate": 0, "fear_greed": 50}

    # 市场状态中文映射
    regime_labels = {
        "strong_trend": "强趋势",
        "trending": "趋势",
        "weak_trend": "弱趋势",
        "ranging": "震荡",
        "volatile": "高波动",
    }
    data["regime_label"] = regime_labels.get(data["regime"], "震荡")
    return data


@router.post("/ai_analysis")
async def ai_market_analysis():
    """AI市场分析 - SSE流式返回（单模型）"""
    from app.services.ai_analysis import (
        get_configured_analysts, call_analyst, build_market_prompt,
    )

    configured = get_configured_analysts()
    if not configured:
        return {"error": "AI 未配置，请联系管理员在后台设置 API Key"}

    # 复用市场状态数据
    regime_data = await get_market_regime()
    market_prompt = build_market_prompt(regime_data)

    # 使用第一个已配置的分析师
    analyst_key = configured[0]

    async def _stream():
        import queue as q
        buf = q.Queue()

        def _worker():
            try:
                for chunk in call_analyst(analyst_key, market_prompt, timeout=25.0):
                    buf.put(("chunk", chunk))
                buf.put(("done", None))
            except Exception as e:
                buf.put(("error", str(e)))

        import threading
        t = threading.Thread(target=_worker, daemon=True)
        t.start()

        while True:
            try:
                msg_type, msg_data = buf.get(timeout=30)
                if msg_type == "chunk":
                    yield f"data: {json.dumps({'content': msg_data}, ensure_ascii=False)}\n\n"
                elif msg_type == "done":
                    yield f"data: {json.dumps({'done': True})}\n\n"
                    break
                elif msg_type == "error":
                    yield f"data: {json.dumps({'error': msg_data}, ensure_ascii=False)}\n\n"
                    break
            except Exception:
                yield f"data: {json.dumps({'error': '响应超时'})}\n\n"
                break

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/ai_team_analysis")
async def ai_team_analysis():
    """AI团队协作分析 - 多模型并行分析 + 裁决"""
    from app.services.ai_analysis import (
        get_configured_analysts, call_analyst, call_judge, build_market_prompt,
    )

    configured = get_configured_analysts()
    if not configured:
        return {"error": "未配置任何分析师，请先在管理后台配置"}

    # 复用市场状态数据
    regime_data = await get_market_regime()
    market_prompt = build_market_prompt(regime_data)

    # 用于存储结果以便保存
    result_holder = {"opinions": {}, "judge": "", "market_data": regime_data, "period": ""}

    # 确定周期（基于当前时间的半小时）
    now = datetime.now()
    if now.minute < 30:
        period = f"{now.hour:02d}00-{now.hour:02d}30"
    else:
        period = f"{now.hour:02d}30-{(now.hour + 1) % 24:02d}00"
    result_holder["period"] = period

    async def _stream():
        import queue as q
        import threading

        # 存储各分析师完整观点
        opinions = {}

        # 顺序调用每个分析师（避免并发闭包问题）
        for analyst_key in configured:
            opinions[analyst_key] = ""
            print(f"[AI分析] 开始调用: {analyst_key}")

            # 调用分析师
            try:
                chunk_count = 0
                for chunk in call_analyst(analyst_key, market_prompt, timeout=35.0):
                    opinions[analyst_key] += chunk
                    chunk_count += 1
                    yield f"data: {json.dumps({'type': 'analyst', 'analyst': analyst_key, 'content': chunk}, ensure_ascii=False)}\n\n"
                print(f"[AI分析] {analyst_key} 完成，共{chunk_count}个chunk")
            except Exception as e:
                print(f"[AI分析] {analyst_key} 失败: {e}")
                yield f"data: {json.dumps({'type': 'analyst', 'analyst': analyst_key, 'error': str(e)}, ensure_ascii=False)}\n\n"

        # 所有分析师完成后，调用裁决者
        yield f"data: {json.dumps({'type': 'judge_start'}, ensure_ascii=False)}\n\n"

        judge_buf = q.Queue()
        def _judge_worker():
            try:
                for chunk in call_judge(opinions, market_prompt, timeout=30.0):
                    judge_buf.put(("chunk", chunk))
                judge_buf.put(("done", None))
            except Exception as e:
                judge_buf.put(("error", str(e)))

        threading.Thread(target=_judge_worker, daemon=True).start()

        judge_content = ""
        while True:
            try:
                msg = judge_buf.get(timeout=35)
                if msg[0] == "chunk":
                    judge_content += msg[1]
                    yield f"data: {json.dumps({'type': 'judge', 'content': msg[1]}, ensure_ascii=False)}\n\n"
                elif msg[0] == "done":
                    # 保存结果到 holder
                    result_holder["opinions"] = opinions.copy()
                    result_holder["judge"] = judge_content
                    
                    # 解析判断并保存到 AiJudgeRecord
                    try:
                        _parse_and_save_judge(result_holder)
                    except Exception as e:
                        print(f"[Dashboard] Save judge record error: {e}")
                    
                    break
                elif msg[0] == "error":
                    yield f"data: {json.dumps({'type': 'judge', 'error': msg[1]}, ensure_ascii=False)}\n\n"
                    break
            except Exception:
                yield f"data: {json.dumps({'type': 'judge', 'error': '响应超时'}, ensure_ascii=False)}\n\n"
                break

        yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/ai_quick_analysis")
async def ai_quick_analysis():
    """快速分析 - 使用独立的快速分析API配置"""
    from app.services.ai_analysis import (
        call_quick_analysis, get_ai_config,
    )

    # 检查快速分析是否配置
    cfg = get_ai_config()
    qa = cfg.get("quick_analysis", {})
    if not qa.get("api_key") or not qa.get("base_url") or not qa.get("model"):
        return {"error": "快速分析API未配置，请先在管理后台配置"}

    # 获取市场数据
    regime_data = await get_market_regime()

    # 构建精简市场prompt
    market_data = regime_data.copy()
    market_data.pop("details", None)
    details = regime_data.get("details", {}) or {}

    def _num(val, default=0):
        if isinstance(val, dict):
            return val.get("value", default) or default
        return val if val is not None else default

    btc_price = _num(regime_data.get("btc_price"), 0)
    btc_change = _num(regime_data.get("btc_change_24h"), 0)
    funding = _num(regime_data.get("funding_rate"), 0)
    fear_greed = regime_data.get("fear_greed", 50) or 50
    direction = regime_data.get("trend_direction", "")
    regime_label = regime_data.get("regime_label", "震荡")
    score = regime_data.get("score", 0) or 0
    adx = _num(details.get("adx"), 0)
    vol_ratio = _num(details.get("vol_ratio"), 0)

    support = btc_price * 0.98 if direction == "up" else btc_price * 0.97
    resistance = btc_price * 1.02 if direction == "up" else btc_price * 1.03

    quick_prompt = f"""【快速行情分析】
BTC ${btc_price:,.0f}（24h {btc_change:+.2f}%），状态：{regime_label}（评分{round(score*100)}）
ADX {adx:.1f}，波动率比 {vol_ratio:.2f}，资金费率 {funding*100:.4f}%，恐惧贪婪 {fear_greed}
支撑 ${support:,.0f} / 压力 ${resistance:,.0f}

请用简洁的语言给出：
1. 当前行情一句话判断（做多/做空/观望）
2. 核心理由（1-2句话）
3. 建议操作和关键价位

保持简短，不要超过80字。"""

    result_holder = {"content": "", "analyst": "quick_analysis"}

    async def _stream():
        import queue as q
        import threading

        buf = q.Queue()

        def _worker():
            try:
                for chunk in call_quick_analysis(quick_prompt, timeout=20.0):
                    buf.put(("chunk", chunk))
                buf.put(("done", None))
            except Exception as e:
                buf.put(("error", str(e)))

        threading.Thread(target=_worker, daemon=True).start()

        while True:
            try:
                msg = buf.get(timeout=25)
                if msg[0] == "chunk":
                    result_holder["content"] += msg[1]
                    yield f"data: {json.dumps({'content': msg[1]}, ensure_ascii=False)}\n\n"
                elif msg[0] == "done":
                    # 解析判断并保存
                    try:
                        _parse_and_save_quick_judge(result_holder)
                    except Exception as e:
                        print(f"[Dashboard] Quick judge save error: {e}")
                    yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"
                    break
                elif msg[0] == "error":
                    yield f"data: {json.dumps({'error': msg[1]}, ensure_ascii=False)}\n\n"
                    break
            except Exception:
                yield f"data: {json.dumps({'error': '响应超时'}, ensure_ascii=False)}\n\n"
                break

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _parse_and_save_quick_judge(result_holder: dict):
    """解析快速分析结果，提取判断并保存"""
    import re
    from datetime import timedelta

    content = result_holder.get("content", "")
    if not content:
        return

    direction = "hold"
    if re.search(r'做多|买入|开多|long|buy', content, re.I):
        direction = "long"
    elif re.search(r'做空|卖出|开空|short|sell', content, re.I):
        direction = "short"

    if direction == "hold":
        return

    entry_price = None
    stop_loss = None
    price_patterns = [
        r'入场[价位价]*[：:]\s*([\d,]+(?:\.\d+)?)',
        r'建议入场\s*([\d,]+(?:\.\d+)?)',
        r'价格[：:]\s*([\d,]+(?:\.\d+)?)',
        r'\$(\d{2,3},?\d{3}(?:\.\d+)?)',
    ]
    for pattern in price_patterns:
        match = re.search(pattern, content)
        if match:
            try:
                entry_price = float(match.group(1).replace(',', ''))
                break
            except:
                pass

    sl_patterns = [
        r'止损[价位价]*[：:]\s*([\d,]+(?:\.\d+)?)',
        r'SL[：:]\s*([\d,]+(?:\.\d+)?)',
    ]
    for pattern in sl_patterns:
        match = re.search(pattern, content)
        if match:
            try:
                stop_loss = float(match.group(1).replace(',', ''))
                break
            except:
                pass

    reason = content[:200] if len(content) > 200 else content

    db = SessionLocal()
    try:
        record = AiJudgeRecord(
            period="quick",
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            reason=reason,
            verify_after=datetime.now() + timedelta(hours=3),
            verified=False,
            result="pending"
        )
        db.add(record)
        db.commit()
        print(f"[Dashboard] Quick analysis saved: {direction} @ {entry_price}, SL: {stop_loss}")
    except Exception as e:
        db.rollback()
        print(f"[Dashboard] Quick analysis save error: {e}")
    finally:
        db.close()


def _parse_and_save_judge(result_holder: dict):
    """解析裁决内容，提取判断并保存到数据库"""
    import re
    from datetime import timedelta
    
    judge_content = result_holder.get("judge", "")
    if not judge_content:
        return
    
    # 解析判断方向
    direction = "hold"
    if re.search(r'做多|买入|long|buy', judge_content, re.I):
        direction = "long"
    elif re.search(r'做空|卖出|short|sell', judge_content, re.I):
        direction = "short"
    
    # 解析入场价
    entry_price = None
    # 匹配 "入场价: 95000" "入场：95000" "建议入场 95000" 等
    price_patterns = [
        r'入场价[：:]\s*([\d,]+(?:\.\d+)?)',
        r'入场[：:]\s*([\d,]+(?:\.\d+)?)',
        r'建议入场\s*([\d,]+(?:\.\d+)?)',
        r'入场价位[：:]\s*([\d,]+(?:\.\d+)?)',
        r'价格[：:]\s*([\d,]+(?:\.\d+)?)',
    ]
    for pattern in price_patterns:
        match = re.search(pattern, judge_content)
        if match:
            try:
                entry_price = float(match.group(1).replace(',', ''))
                break
            except:
                pass
    
    # 解析止损位
    stop_loss = None
    sl_patterns = [
        r'止损[：:]\s*([\d,]+(?:\.\d+)?)',
        r'止损位[：:]\s*([\d,]+(?:\.\d+)?)',
        r'止损价[：:]\s*([\d,]+(?:\.\d+)?)',
    ]
    for pattern in sl_patterns:
        match = re.search(pattern, judge_content)
        if match:
            try:
                stop_loss = float(match.group(1).replace(',', ''))
                break
            except:
                pass
    
    # 如果是观望，不保存记录
    if direction == "hold":
        return
    
    # 提取判断理由（取裁决内容的前200字）
    reason = judge_content[:200] if len(judge_content) > 200 else judge_content
    
    # 保存到数据库
    db = SessionLocal()
    try:
        record = AiJudgeRecord(
            period=result_holder.get("period", ""),
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            reason=reason,
            verify_after=datetime.now() + timedelta(hours=3),
            verified=False,
            result="pending"
        )
        db.add(record)
        db.commit()
        print(f"[Dashboard] Saved judge record: {direction} @ {entry_price}, SL: {stop_loss}")
    except Exception as e:
        db.rollback()
        print(f"[Dashboard] Save judge record error: {e}")
    finally:
        db.close()


@router.get("/ai_chat_history")
async def get_ai_chat_history(limit: int = 20):
    """获取AI聊天历史记录（最近N条）"""
    db = SessionLocal()
    try:
        records = db.query(AiChatHistory)\
            .order_by(AiChatHistory.created_at.desc())\
            .limit(limit)\
            .all()
        
        results = []
        for r in records:
            # 解析JSON字段
            try:
                opinions_data = json.loads(r.opinions) if r.opinions else {}
            except:
                opinions_data = {}
            
            try:
                market_data = json.loads(r.market_data) if r.market_data else {}
            except:
                market_data = {}
            
            results.append({
                "id": r.id,
                "period": r.period,
                "opinions": opinions_data,
                "judge": r.judge or "",
                "market_data": market_data,
                "created_at": r.created_at.strftime("%Y-%m-%dT%H:%M:%S") + "Z" if r.created_at else None,
            })
        
        return {"history": results}
    except Exception as e:
        return {"history": [], "error": str(e)}
    finally:
        db.close()


@router.get("/ai_judge_records")
async def get_ai_judge_records(limit: int = 10):
    """获取AI判断追踪记录（最近N条）"""
    db = SessionLocal()
    try:
        records = db.query(AiJudgeRecord)\
            .order_by(AiJudgeRecord.created_at.desc())\
            .limit(limit)\
            .all()
        
        results = []
        for r in records:
            results.append({
                "id": r.id,
                "period": r.period,
                "direction": r.direction,
                "entry_price": r.entry_price,
                "stop_loss": r.stop_loss,
                "reason": r.reason,
                "verify_after": r.verify_after.strftime("%Y-%m-%dT%H:%M:%S") + "Z" if r.verify_after else None,
                "verified": r.verified,
                "price_at_verify": r.price_at_verify,
                "result": r.result,
                "created_at": r.created_at.strftime("%Y-%m-%dT%H:%M:%S") + "Z" if r.created_at else None,
            })
        
        return {"records": results}
    except Exception as e:
        return {"records": [], "error": str(e)}
    finally:
        db.close()


@router.post("/verify_judge_records")
async def verify_judge_records():
    """验证超过3小时的判断记录"""
    db = SessionLocal()
    try:
        from app.services.cache import get_cached_market_service
        
        # 查找需要验证的记录
        now = datetime.now()
        records = db.query(AiJudgeRecord)\
            .filter(AiJudgeRecord.verified == False)\
            .filter(AiJudgeRecord.verify_after <= now)\
            .all()
        
        verified_count = 0
        for record in records:
            try:
                # 获取当前BTC价格
                ticker = get_cached_market_service().get_ticker("BTC-USDT-SWAP")
                if not ticker:
                    continue
                
                current_price = ticker.get("price", 0)
                record.price_at_verify = current_price
                
                # 判断结果
                if record.direction == "long":
                    # 做多：价格上涨为正确
                    if current_price > record.entry_price:
                        record.result = "correct"
                    else:
                        record.result = "wrong"
                elif record.direction == "short":
                    # 做空：价格下跌为正确
                    if current_price < record.entry_price:
                        record.result = "correct"
                    else:
                        record.result = "wrong"
                else:
                    record.result = "pending"
                
                record.verified = True
                verified_count += 1
            except Exception as e:
                print(f"[Dashboard] Verify record {record.id} error: {e}")
                continue
        
        db.commit()
        return {"verified_count": verified_count}
    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()
