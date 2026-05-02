"""测试开仓并设置止盈止损和移动止盈止损"""
import sys
sys.path.insert(0, "c:/LH/OKX/backend")

# 先加载API配置
from app.routers import settings  # 这会触发配置加载

from app.services.trade import TradeService
from app.services.market import market_service

def main():
    trade = TradeService()
    
    inst_id = "BTC-USDT-SWAP"
    sz = "0.01"
    leverage = 100
    td_mode = "cross"
    
    # 获取当前价格
    print("Step 1: Get current price...")
    ticker = market_service.get_ticker("BTC-USDT")
    current_price = ticker.get("price", 0)
    print(f"  Current price: ${current_price}")
    
    # 设置杠杆
    print(f"\nStep 2: Setting leverage to {leverage}X...")
    try:
        result_long = trade.set_leverage(inst_id, leverage, td_mode, pos_side="long")
        print(f"  long: {result_long}")
        result_short = trade.set_leverage(inst_id, leverage, td_mode, pos_side="short")
        print(f"  short: {result_short}")
    except Exception as e:
        print(f"  [WARN] Set leverage failed: {e}")
    
    # 验证杠杆设置
    print("\nStep 3: Verify leverage...")
    lev_info = trade.get_leverage(inst_id, td_mode)
    print(f"  Leverage info: {lev_info}")
    
    # 计算止盈止损价格
    tp_pct = 60  # 60%止盈
    sl_pct = 35  # 35%止损
    
    # 根据策略参数计算实际价格变动百分比
    # 公式: price_change_pct = tp_pct / leverage / 100
    # 例如: 60% / 100 / 100 = 0.006 = 0.6%
    tp_price_change = tp_pct / leverage / 100
    sl_price_change = sl_pct / leverage / 100
    
    tp_trigger_px = f"{current_price * (1 + tp_price_change):.2f}"
    sl_trigger_px = f"{current_price * (1 - sl_price_change):.2f}"
    
    print(f"\nStep 4: TP/SL prices (TP={tp_pct}%, SL={sl_pct}%)")
    print(f"  TP trigger: ${tp_trigger_px} (+{tp_price_change*100:.2f}%)")
    print(f"  SL trigger: ${sl_trigger_px} (-{sl_price_change*100:.2f}%)")
    
    # 开多单（附带固定止盈止损）
    print(f"\nStep 5: Open long position (size={sz})...")
    try:
        result = trade.open_long(
            inst_id=inst_id,
            sz=sz,
            lever=None,  # 不设置杠杆，使用当前杠杆
            td_mode=td_mode,
            tp_trigger_px=tp_trigger_px,
            sl_trigger_px=sl_trigger_px,
        )
        print(f"  [OK] Order result: {result}")
        # OKX CLI返回的是list
        if isinstance(result, list) and len(result) > 0:
            ord_id = result[0].get("ordId", "")
        else:
            ord_id = result.get("ordId", "") if isinstance(result, dict) else ""
        print(f"  Order ID: {ord_id}")
    except Exception as e:
        print(f"  [ERROR] Open long failed: {e}")
        return
    
    # 等待订单成交
    print("\nStep 6: Wait for order to fill...")
    import time
    for i in range(10):
        time.sleep(1)
        # 检查持仓
        positions = market_service.get_positions()
        # 过滤出当前合约的持仓
        pos_list = [p for p in positions if p.get("instId") == inst_id]
        if pos_list:
            pos = pos_list[0]
            print(f"  Position found: {pos.get('size')} @ ${pos.get('avgPx')}")
            break
        print(f"  Waiting... ({i+1}/10)")
    else:
        print("  [WARN] Position not found after 10s")
    
    # 设置移动止盈止损
    print("\nStep 7: Setting trailing stop...")
    # 回调点数 = 25点（根据策略参数）
    trail_callback_points = 25
    # 激活价格 = 当前价格 * (1 + 50% / 100 / 100) = 0.5%涨幅
    trail_activate_pct = 50
    activate_price = f"{current_price * (1 + trail_activate_pct / leverage / 100):.2f}"
    
    # 计算回调比例
    callback_ratio = trail_callback_points / current_price
    callback_ratio = min(callback_ratio, 0.9999)
    callback_ratio = round(callback_ratio, 4)
    
    print(f"  Activate price: ${activate_price}")
    print(f"  Callback: {trail_callback_points} points ({callback_ratio*100:.4f}%)")
    
    try:
        trail_result = trade.place_algo_trailing(
            inst_id=inst_id,
            side="sell",  # 平多
            sz=sz,
            callback_pct=callback_ratio * 100,
            activate_price=activate_price,
            pos_side="long",
            td_mode=td_mode,
        )
        print(f"  [OK] Trailing stop result: {trail_result}")
    except Exception as e:
        print(f"  [ERROR] Trailing stop failed: {e}")
    
    # 检查算法订单
    print("\nStep 8: Check algo orders...")
    from app.services.market import _run_okx
    algo_orders = _run_okx(["swap", "algo", "orders", "--instId", inst_id])
    print(f"  Algo orders count: {len(algo_orders) if isinstance(algo_orders, list) else 0}")
    if isinstance(algo_orders, list):
        for i, order in enumerate(algo_orders[:5], 1):  # 只显示前5个
            print(f"  {i}. {order.get('ordType')}: TP={order.get('tpTriggerPx')}, SL={order.get('slTriggerPx')}, callback={order.get('callbackRatio')}")
    
    print("\n[DONE] Test completed. Please check OKX dashboard to verify:")
    print("  1. Position opened with correct leverage (100X)")
    print("  2. Fixed TP/SL orders created")
    print("  3. Trailing stop order created")

if __name__ == "__main__":
    main()
