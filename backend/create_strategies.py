"""Create profitable strategies from backtest results (with regime filter).

All strategies use:
- 1H timeframe
- 0.01 contracts (minimal risk for testing)
- regime filter ON
- cross margin, 10x leverage
- TP=0 (unlimited), SL=5%, trailing=0

Usage:
  cd c:\LH\\OKX\\backend
  python create_strategies.py
"""
import urllib.request, json

BASE = "http://localhost:8000"

def api_post(path, data):
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(data).encode(),
        method="POST",
        headers={"Content-Type": "application/json"}
    )
    try:
        r = urllib.request.urlopen(req, timeout=15)
        return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return {"_error": f"HTTP {e.code}", "_body": body[:500]}

# Profitable strategies with regime filter (from 59-day backtest)
STRATEGIES = [
    {
        "name": "RSI超卖超买-1H",
        "type": "rsi",
        "inst_id": "BTC-USDT-SWAP",
        "size_mode": "fixed",
        "size": 0.01,
        "leverage": 10,
        "td_mode": "cross",
        "take_profit_pct": 0,
        "stop_loss_pct": 5,
        "trailing_stop_pct": 0,
        "use_regime_filter": True,
        "params": {"period": 14, "oversold": 30, "overbought": 70, "timeframe": "1h"},
    },
    {
        "name": "KDJ金叉死叉-1H",
        "type": "kdj",
        "inst_id": "BTC-USDT-SWAP",
        "size_mode": "fixed",
        "size": 0.01,
        "leverage": 10,
        "td_mode": "cross",
        "take_profit_pct": 0,
        "stop_loss_pct": 5,
        "trailing_stop_pct": 0,
        "use_regime_filter": True,
        "params": {"k_period": 9, "d_period": 3, "j_smooth": 3, "overbought": 80, "oversold": 20, "timeframe": "1h"},
    },
    {
        "name": "CCI趋势反转-1H",
        "type": "cci",
        "inst_id": "BTC-USDT-SWAP",
        "size_mode": "fixed",
        "size": 0.01,
        "leverage": 10,
        "td_mode": "cross",
        "take_profit_pct": 0,
        "stop_loss_pct": 5,
        "trailing_stop_pct": 0,
        "use_regime_filter": True,
        "params": {"period": 20, "overbought": 100, "oversold": -100, "timeframe": "1h"},
    },
    {
        "name": "RSI+MACD共振-1H",
        "type": "rsi_macd",
        "inst_id": "BTC-USDT-SWAP",
        "size_mode": "fixed",
        "size": 0.01,
        "leverage": 10,
        "td_mode": "cross",
        "take_profit_pct": 0,
        "stop_loss_pct": 5,
        "trailing_stop_pct": 0,
        "use_regime_filter": True,
        "params": {"rsi_period": 6, "macd_fast": 12, "macd_slow": 26, "macd_signal": 9, "rsi_oversold": 30, "rsi_overbought": 70, "timeframe": "1h"},
    },
    {
        "name": "SuperTrend趋势-1H",
        "type": "supertrend",
        "inst_id": "BTC-USDT-SWAP",
        "size_mode": "fixed",
        "size": 0.01,
        "leverage": 10,
        "td_mode": "cross",
        "take_profit_pct": 0,
        "stop_loss_pct": 5,
        "trailing_stop_pct": 0,
        "use_regime_filter": True,
        "params": {"atr_period": 10, "multiplier": 3, "timeframe": "1h"},
    },
    {
        "name": "EMA量能确认-1H",
        "type": "ema_volume",
        "inst_id": "BTC-USDT-SWAP",
        "size_mode": "fixed",
        "size": 0.01,
        "leverage": 10,
        "td_mode": "cross",
        "take_profit_pct": 0,
        "stop_loss_pct": 5,
        "trailing_stop_pct": 0,
        "use_regime_filter": True,
        "params": {"fast_period": 12, "slow_period": 26, "vol_period": 20, "vol_mult": 1.5, "timeframe": "1h"},
    },
    {
        "name": "双时间框架EMA-1H",
        "type": "dual_ema",
        "inst_id": "BTC-USDT-SWAP",
        "size_mode": "fixed",
        "size": 0.01,
        "leverage": 10,
        "td_mode": "cross",
        "take_profit_pct": 0,
        "stop_loss_pct": 5,
        "trailing_stop_pct": 0,
        "use_regime_filter": True,
        "params": {"trend_period": 50, "signal_period": 10, "timeframe": "1h"},
    },
    {
        "name": "均线多空排列-1H",
        "type": "ma_ribbon",
        "inst_id": "BTC-USDT-SWAP",
        "size_mode": "fixed",
        "size": 0.01,
        "leverage": 10,
        "td_mode": "cross",
        "take_profit_pct": 0,
        "stop_loss_pct": 5,
        "trailing_stop_pct": 0,
        "use_regime_filter": True,
        "params": {"period1": 5, "period2": 10, "period3": 20, "period4": 60, "timeframe": "1h"},
    },
    {
        "name": "量价突破-1H",
        "type": "vol_break",
        "inst_id": "BTC-USDT-SWAP",
        "size_mode": "fixed",
        "size": 0.01,
        "leverage": 10,
        "td_mode": "cross",
        "take_profit_pct": 0,
        "stop_loss_pct": 5,
        "trailing_stop_pct": 0,
        "use_regime_filter": True,
        "params": {"lookback": 20, "vol_mult": 1.5, "timeframe": "1h"},
    },
]

print("=" * 60)
print("  Creating Profitable Strategies (Regime Filter ON)")
print("=" * 60)

created = []
for s in STRATEGIES:
    result = api_post("/api/strategy/create", s)
    if "_error" in result:
        print(f"  FAILED: {s['name']} - {result}")
    elif result.get("ok"):
        sid = result.get("strategy", {}).get("id", "?")
        print(f"  Created #{sid}: {s['name']} [{s['type']}]")
        created.append(sid)
    else:
        print(f"  FAILED: {s['name']} - {result}")

print(f"\n  Total created: {len(created)} strategies")
print("\n  NOTE: Only ONE strategy can run at a time per contract.")
print("  These strategies are created but NOT started.")
print("  Start them one by one from the Strategy page in the UI.")
