"""测试REST API交易功能"""
import sys
sys.path.insert(0, "c:/LH/OKX/backend")

from app.routers import settings
from app.services.trade_rest import get_trade_service
from app.services.okx_client import get_client

def main():
    print("="*60)
    print("测试 OKX REST API 交易功能")
    print("="*60)
    
    # 获取交易服务
    trade = get_trade_service()
    client = get_client()
    
    inst_id = "BTC-USDT-SWAP"
    sz = "0.01"
    leverage = 100
    
    # Step 1: 测试获取杠杆
    print("\nStep 1: 获取当前杠杆...")
    try:
        lev_info = trade.get_leverage(inst_id, "cross")
        print(f"  [OK] Leverage info: {lev_info}")
    except Exception as e:
        print(f"  [ERROR] {e}")
    
    # Step 2: 测试设置杠杆
    print(f"\nStep 2: 设置杠杆到 {leverage}X...")
    try:
        result_long = trade.set_leverage(inst_id, leverage, "cross", "long")
        print(f"  [OK] Long: {result_long}")
        result_short = trade.set_leverage(inst_id, leverage, "cross", "short")
        print(f"  [OK] Short: {result_short}")
    except Exception as e:
        print(f"  [ERROR] {e}")
    
    # Step 3: 获取当前价格（用于计算止盈止损）
    print("\nStep 3: 获取当前价格...")
    try:
        ticker = client.get("/api/v5/market/ticker?instId=BTC-USDT-SWAP")
        current_price = float(ticker[0].get("last", 0))
        print(f"  [OK] Current price: ${current_price}")
    except Exception as e:
        print(f"  [ERROR] {e}")
        return
    
    # Step 4: 计算止盈止损价格
    tp_pct = 60  # 60%止盈
    sl_pct = 35  # 35%止损
    
    tp_price_change = tp_pct / leverage / 100
    sl_price_change = sl_pct / leverage / 100
    
    tp_trigger_px = f"{current_price * (1 + tp_price_change):.2f}"
    sl_trigger_px = f"{current_price * (1 - sl_price_change):.2f}"
    
    print(f"\nStep 4: 计算止盈止损价格")
    print(f"  TP: ${tp_trigger_px} (+{tp_price_change*100:.2f}%)")
    print(f"  SL: ${sl_trigger_px} (-{sl_price_change*100:.2f}%)")
    
    # Step 5: 测试开仓（附带止盈止损）
    print(f"\nStep 5: 开多仓 (size={sz})...")
    try:
        result = trade.open_long(
            inst_id=inst_id,
            sz=sz,
            lever=None,  # 不设置杠杆，使用当前杠杆
            tp_trigger_px=tp_trigger_px,
            sl_trigger_px=sl_trigger_px,
        )
        print(f"  [OK] Order placed: {result}")
    except Exception as e:
        print(f"  [ERROR] {e}")
        return
    
    # Step 6: 等待订单成交
    print("\nStep 6: 等待订单成交...")
    import time
    for i in range(10):
        time.sleep(1)
        try:
            positions = client.get("/api/v5/account/positions?instId=" + inst_id)
            pos_list = [p for p in positions if p.get("posSide") == "long" and float(p.get("pos", 0)) > 0]
            if pos_list:
                pos = pos_list[0]
                print(f"  [OK] Position: {pos.get('pos')} @ ${pos.get('avgPx')}, leverage={pos.get('lever')}X")
                break
        except Exception as e:
            print(f"  Error checking position: {e}")
        print(f"  Waiting... ({i+1}/10)")
    else:
        print("  [WARN] Position not found after 10s")
    
    # Step 7: 测试设置移动止盈（使用callbackSpread）
    print("\nStep 7: 设置移动止盈 (callbackSpread=25)...")
    try:
        activate_price = f"{current_price * 1.005:.2f}"
        result = trade.place_algo_trailing(
            inst_id=inst_id,
            side="sell",
            sz=sz,
            callback_points=25,  # 使用点数
            activate_price=activate_price,
            pos_side="long",
            td_mode="cross",
        )
        print(f"  [OK] Trailing stop set: {result}")
    except Exception as e:
        print(f"  [ERROR] {e}")
    
    # Step 8: 检查算法订单
    print("\nStep 8: 检查算法订单...")
    try:
        algo_orders = client.get(f"/api/v5/trade/orders-algo-pending?instId={inst_id}")
        if isinstance(algo_orders, list):
            print(f"  Total algo orders: {len(algo_orders)}")
            for i, order in enumerate(algo_orders[:3], 1):
                print(f"\n  {i}. {order.get('ordType')} ({order.get('state')})")
                if order.get('ordType') == 'oco':
                    print(f"     TP: ${order.get('tpTriggerPx')}")
                    print(f"     SL: ${order.get('slTriggerPx')}")
                elif order.get('ordType') == 'move_order_stop':
                    print(f"     Activate: ${order.get('activePx')}")
                    print(f"     Callback: {order.get('callbackSpread')} points")
    except Exception as e:
        print(f"  [ERROR] {e}")
    
    print("\n" + "="*60)
    print("测试完成！请检查OKX Dashboard验证订单")
    print("="*60)

if __name__ == "__main__":
    main()
