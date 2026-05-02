"""Dashboard 路由 - 总览数据"""
from fastapi import APIRouter
from datetime import datetime, date
import json
import random
import os

from app.services.cache import get_cached_market_service
from app import config
from app.models import Strategy, Trade, User
from app.database import SessionLocal

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

# 获取带缓存的行情服务
_ms = get_cached_market_service

# 平均收益持久化文件（模拟数据，每日0点随机浮动）
_AVG_PROFIT_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "platform_stats.json")


def _get_avg_profit() -> float:
    """获取平均收益，每天0点自动浮动 -1~2%"""
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
        # 新的一天，随机浮动 -1 到 +2
        current = data.get("avg_profit", 5.0)
        drift = round(random.uniform(-1, 2), 2)
        current = round(current + drift, 2)
        data = {"avg_profit": current, "last_update": today}
        try:
            with open(_AVG_PROFIT_FILE, "w") as f:
                json.dump(data, f)
        except Exception:
            pass

    return data["avg_profit"]


@router.get("/overview")
async def get_overview():
    """获取总览数据：多币种行情 + 账户信息 + 持仓"""
    import asyncio

    symbols = ["BTC-USDT", "ETH-USDT", "BNB-USDT", "SOL-USDT", "XRP-USDT", "ADA-USDT", "DOGE-USDT", "DOT-USDT"]

    def _fetch_all():
        """所有数据在单个线程中按顺序获取"""
        # 行情
        prices = {}
        try:
            all_tickers = _ms().get_tickers("SPOT")
            ticker_map = {t["symbol"]: t for t in all_tickers}
            for s in symbols:
                prices[s] = ticker_map.get(s, {"price": 0, "change_24h": 0})
        except Exception:
            prices = {s: {"price": 0, "change_24h": 0} for s in symbols}

        # 账户
        account_info = {"account_balance": None, "unrealized_pnl": None, "currencies": []}
        if config.OKX_API_KEY:
            try:
                acc = _ms().get_account_balance()
                account_info = {
                    "account_balance": acc.get("total_equity"),
                    "unrealized_pnl": acc.get("total_unrealized_pnl"),
                    "currencies": acc.get("details", []),
                }
            except Exception:
                pass

        # 持仓
        positions_info = []
        if config.OKX_API_KEY:
            try:
                positions_info = _ms().get_positions()
            except Exception:
                pass

        # 资金
        funding_info = {"funding_balance": None, "funding_details": []}
        if config.OKX_API_KEY:
            try:
                funding = _ms().get_funding_balance()
                funding_info = {"funding_balance": funding.get("total_equity", 0), "funding_details": funding.get("details", [])}
            except Exception:
                pass

        return prices, account_info, positions_info, funding_info

    try:
        prices, account_info, positions_info, funding_info = await asyncio.wait_for(
            asyncio.to_thread(_fetch_all), timeout=15.0
        )
    except asyncio.TimeoutError:
        prices = {s: {"price": 0, "change_24h": 0} for s in symbols}
        account_info = {"account_balance": None, "unrealized_pnl": None, "currencies": []}
        positions_info = []
        funding_info = {"funding_balance": None, "funding_details": []}

    # 恐惧贪婪指数
    fear_greed = 50
    btc_change = prices.get("BTC-USDT", {}).get("change_24h", 0) if isinstance(prices, dict) else 0
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
        # 计算所有交易的盈亏总和
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
        "has_api_key": bool(config.OKX_API_KEY),
        "running_strategies": strategy_stats["running_count"],
        "total_strategy_profit": strategy_stats["total_profit"],
        # 多币种价格
        "btc_price": prices.get("BTC-USDT", {}).get("price", 0),
        "btc_change_24h": prices.get("BTC-USDT", {}).get("change_24h", 0),
        "eth_price": prices.get("ETH-USDT", {}).get("price", 0),
        "eth_change_24h": prices.get("ETH-USDT", {}).get("change_24h", 0),
        "prices": prices,
        # 恐惧贪婪指数
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
    db = SessionLocal()
    try:
        from app.models import User

        # 策略总数
        total_strategies = db.query(Strategy).count()

        # 运行中的策略
        running_strategies = db.query(Strategy).filter(Strategy.enabled == True).count()

        # 活跃用户数（总用户数）
        active_users = db.query(User).count()

        # 平均收益：模拟数据，每日0点随机浮动 -1~2%
        avg_profit = _get_avg_profit()

        # 胜率（从交易记录）
        trades = db.query(Trade).filter(Trade.pnl.isnot(None), Trade.pnl != 0).all()
        if trades:
            winning_trades = sum(1 for t in trades if t.pnl and t.pnl > 0)
            win_rate = (winning_trades / len(trades) * 100)
        else:
            win_rate = 68.5

        return {
            "total_strategies": total_strategies,
            "active_users": active_users,
            "avg_profit": avg_profit,
            "win_rate": round(win_rate, 1),
            "running_strategies": running_strategies,
        }
    except Exception as e:
        print(f"[Dashboard] Failed to get platform stats: {e}")
        return {
            "total_strategies": 15,
            "active_users": 1,
            "avg_profit": _get_avg_profit(),
            "win_rate": 68.5,
            "running_strategies": 0,
        }
    finally:
        db.close()
