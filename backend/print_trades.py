"""Print detailed trades for verification."""
import sys
sys.path.insert(0, ".")
from datetime import datetime
from app.services.strategy import STRATEGY_REGISTRY
from app.services.backtest import backtest_engine
from app.services.market import market_service

SYMBOL = "BTC-USDT-SWAP"

for tf in ["4h", "1d"]:
    limit = 300
    print("=" * 90)
    print(f"  TIMEFRAME: {tf}  |  LIMIT: {limit} candles")
    print("=" * 90)

    klines = market_service.get_klines(symbol="BTC-USDT", timeframe=tf, limit=limit)
    if not klines or len(klines) < 50:
        print("ERROR: no klines")
        continue

    t0 = datetime.fromtimestamp(klines[0]["timestamp"] / 1000)
    t1 = datetime.fromtimestamp(klines[-1]["timestamp"] / 1000)
    print(f"  Date: {t0.strftime('%Y-%m-%d')} ~ {t1.strftime('%Y-%m-%d')} ({(t1-t0).days} days)")
    print()

    for stype, scls in sorted(STRATEGY_REGISTRY.items()):
        params = dict(scls.default_params)
        params["timeframe"] = tf
        params["size_mode"] = "fixed"
        params["size"] = 1
        params["take_profit_pct"] = 0
        params["stop_loss_pct"] = 5
        params["trailing_stop_pct"] = 0
        params["inst_id"] = SYMBOL

        try:
            r = backtest_engine.run(
                strategy_type=stype, params=params, symbol=SYMBOL,
                timeframe=tf, klines=klines, initial_capital=10000,
                leverage=10, fee_rate=0.0005, slippage=0.0005,
            )
        except Exception as e:
            print(f"  {scls.strategy_name} ERROR: {e}")
            continue

        if not r.get("ok"):
            print(f"  {scls.strategy_name} FAILED")
            continue

        trades = r.get("trades", [])
        if not trades:
            print(f"  {scls.strategy_name}: No trades")
            continue

        print(f"  --- {scls.strategy_name} | Return: {r['total_return']:.1f}% | Trades: {r['trade_count']} | WinRate: {r['win_rate']:.0f}% ---")
        for t in trades:
            ts = t.get("time", 0)
            if isinstance(ts, (int, float)) and ts > 1e12:
                dt_str = datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d %H:%M")
            elif isinstance(ts, (int, float)) and ts > 1e9:
                dt_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
            else:
                dt_str = str(ts)

            side = t.get("side", "")
            price = t.get("price", 0)
            sz = t.get("sz", 0)
            reason = t.get("reason", "")
            pnl = t.get("pnl", None)
            fee = t.get("fee", 0)
            margin = t.get("margin", None)

            # Translate side
            if side == "open_long":
                action = "OPEN LONG  "
            elif side == "open_short":
                action = "OPEN SHORT "
            elif side == "close_long":
                action = "CLOSE LONG "
            elif side == "close_short":
                action = "CLOSE SHORT"
            else:
                action = side

            # Translate reason
            reason_map = {
                "take_profit": "TP",
                "stop_loss": "SL",
                "signal": "Signal",
                "trailing_stop": "Trailing",
                "backtest_end": "End",
            }
            reason_str = reason_map.get(reason, reason)

            if pnl is not None:
                print(f"    {dt_str} | {action} | ${price:>10,.2f} | sz={sz} | PnL=${pnl:>8.2f} | fee=${fee:.2f} | {reason_str}")
            else:
                print(f"    {dt_str} | {action} | ${price:>10,.2f} | sz={sz} | margin=${margin:>8.2f} | fee=${fee:.2f}")

        print()

print("\nDone.")
