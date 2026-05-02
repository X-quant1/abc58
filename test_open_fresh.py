"""重新开仓测试 - 完整流程"""
import sys
sys.path.insert(0, "c:/LH/OKX/backend")

from app.routers import settings
from app.services.trade import TradeService
from app.services.market import market_service, _run_okx

def main():
    trade = TradeService()
    
    inst_id = "BTC-USDT-SWAP"
    sz = "0.01"
    leverage = 100
    td_mode = "cross"
    
    # Step 1: 检查当前持仓
    print("Step 1: Check current positions...")
    positions = market_service.get_positions()
    pos_list = [p for p in positions if p.get("instId") == inst_id and p.get("posSide") == "long"]
    if pos_list and float(pos_list[0].get("pos", 0)) > 0:
        print(f"  [WARN] Position already exists: {pos_list[0].get('pos')} @ ${pos_list[0].get('avgPx')}")
        print("  Please close position first.")
        return
    print("  [OK] No existing position")
    
    # Step 2: 获取当前价格
    print("\nStep 2: Get current price...")
    ticker = market_service.get_ticker("BTC-USDT")
    current_price = ticker.get("price", 0)
    print(f"  Current price: ${current_price}")
    
    # Step 3: 设置杠杆
    print(f"\nStep 3: Setting leverage to {leverage}X...")
    try:
        # 先取消所有算法订单（避免杠杆设置失败）
        algo_orders = _run_okx(["swap", "algo", "orders", "--instId", inst_id])
        if isinstance(algo_orders, list) and len(algo_orders) > 0:
            print(f"  Found {len(algo_orders)} algo orders, cancelling...")
            for order in algo_orders:
                algo_id = order.get("algoId", "")
                if algo_id:
                    try:
                        _run_okx(["swap", "algo", "cancel", "--instId", inst_id, "--algoId", algo_id])
                        print(f"    Cancelled {algo_id}")
                    except Exception as e:
                        print(f"    Failed to cancel {algo_id}: {e}")
        
        # 设置杠杆
        result_long = trade.set_leverage(inst_id, leverage, td_mode, pos_side="long")
        print(f"  long: {result_long}")
        result_short = trade.set_leverage(inst_id, leverage, td_mode, pos_side="short")
        print(f"  short: {result_short}")
    except Exception as e:
        print(f"  [WARN] Set leverage failed: {e}")
    
    # Step 4: 验证杠杆设置
    print("\nStep 4: Verify leverage...")
    lev_info = trade.get_leverage(inst_id, td_mode)
    if isinstance(lev_info, list):
        for lev in lev_info:
            print(f"  {lev.get('posSide')}: {lev.get('lever')}X")
    
    # Step 5: 计算止盈止损价格
    tp_pct = 60  # 60%止盈
    sl_pct = 35  # 35%止损
    
    tp_price_change = tp_pct / leverage / 100
    sl_price_change = sl_pct / leverage / 100
    
    tp_trigger_px = f"{current_price * (1 + tp_price_change):.2f}"
    sl_trigger_px = f"{current_price * (1 - sl_price_change):.2f}"
    
    print(f"\nStep 5: TP/SL prices (TP={tp_pct}%, SL={sl_pct}%)")
    print(f"  TP trigger: ${tp_trigger_px} (+{tp_price_change*100:.2f}%)")
    print(f"  SL trigger: ${sl_trigger_px} (-{sl_price_change*100:.2f}%)")
    
    # Step 6: 开多单（附带固定止盈止损）
    print(f"\nStep 6: Open long position (size={sz})...")
    try:
        result = trade.open_long(
            inst_id=inst_id,
            sz=sz,
            lever=None,  # 不设置杠杆，使用当前杠杆
            td_mode=td_mode,
            tp_trigger_px=tp_trigger_px,
            sl_trigger_px=sl_trigger_px,
        )
        print(f"  [OK] Order placed")
        if isinstance(result, list) and len(result) > 0:
            ord_id = result[0].get("ordId", "")
            print(f"  Order ID: {ord_id}")
        else:
            print(f"  Result: {result}")
    except Exception as e:
        print(f"  [ERROR] Open long failed: {e}")
        return
    
    # Step 7: 等待订单成交
    print("\nStep 7: Wait for order to fill...")
    import time
    for i in range(15):
        time.sleep(1)
        positions = market_service.get_positions()
        pos_list = [p for p in positions if p.get("instId") == inst_id and p.get("posSide") == "long"]
        if pos_list and float(pos_list[0].get("pos", 0)) > 0:
            pos = pos_list[0]
            print(f"  [OK] Position found: {pos.get('pos')} @ ${pos.get('avgPx')}")
            print(f"  Leverage: {pos.get('lever')}X")
            break
        print(f"  Waiting... ({i+1}/15)")
    else:
        print("  [WARN] Position not found after 15s, but order was placed")
    
    # Step 8: 设置移动止盈止损
    print("\nStep 8: Setting trailing stop...")
    trail_callback_points = 25
    trail_activate_pct = 50
    activate_price = f"{current_price * (1 + trail_activate_pct / leverage / 100):.2f}"
    
    callback_ratio = trail_callback_points / current_price
    callback_ratio = min(callback_ratio, 0.9999)
    callback_ratio = round(callback_ratio, 4)
    
    print(f"  Activate price: ${activate_price}")
    print(f"  Callback: {trail_callback_points} points ({callback_ratio*100:.4f}%)")
    
    try:
        trail_result = trade.place_algo_trailing(
            inst_id=inst_id,
            side="sell",
            sz=sz,
            callback_pct=callback_ratio * 100,
            activate_price=activate_price,
            pos_side="long",
            td_mode=td_mode,
        )
        print(f"  [OK] Trailing stop set")
        if isinstance(trail_result, list) and len(trail_result) > 0:
            algo_id = trail_result[0].get("algoId", "")
            print(f"  Algo ID: {algo_id}")
    except Exception as e:
        print(f"  [ERROR] Trailing stop failed: {e}")
    
    # Step 9: 检查算法订单
    print("\nStep 9: Check algo orders...")
    algo_orders = _run_okx(["swap", "algo", "orders", "--instId", inst_id])
    if isinstance(algo_orders, list):
        print(f"  Total algo orders: {len(algo_orders)}")
        for i, order in enumerate(algo_orders[:3], 1):
            ord_type = order.get("ordType", "")
            state = order.get("state", "")
            print(f"\n  {i}. {ord_type} ({state})")
            if ord_type == "oco":
                print(f"     TP: ${order.get('tpTriggerPx')} @ {order.get('tpOrdPx')}")
                print(f"     SL: ${order.get('slTriggerPx')} @ {order.get('slOrdPx')}")
            elif ord_type == "move_order_stop":
                print(f"     Activate: ${order.get('activePx')}")
                print(f"     Callback: {order.get('callbackRatio')} ({float(order.get('callbackRatio', 0))*100:.4f}%)")
    
    print("\n" + "="*60)
    print("Test completed. Please check OKX dashboard:")
    print("  1. Position: 0.01 BTC @ 100X leverage")
    print("  2. Fixed TP/SL: OCO order")
    print("  3. Trailing stop: move_order_stop order")
    print("="*60)

if __name__ == "__main__":
    main()
