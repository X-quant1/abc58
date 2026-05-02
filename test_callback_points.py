"""测试使用点数模式设置移动止盈"""
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
    positions = _run_okx(["swap", "positions", "BTC-USDT-SWAP"])
    
    if not isinstance(positions, list):
        print("  [ERROR] Failed to get positions")
        return
    
    # 找到long方向且pos > 0的持仓
    pos_list = [p for p in positions if p.get("posSide") == "long" and float(p.get("pos", 0)) > 0]
    
    if not pos_list:
        print("  [ERROR] No long position found. Please open position first.")
        return
    
    pos = pos_list[0]
    print(f"  Position: {pos.get('pos')} @ ${pos.get('avgPx')}")
    
    # Step 2: 取消现有的移动止盈订单
    print("\nStep 2: Cancel existing trailing stop orders...")
    algo_orders = _run_okx(["swap", "algo", "orders", "--instId", inst_id])
    if isinstance(algo_orders, list):
        for order in algo_orders:
            if order.get("ordType") == "move_order_stop":
                algo_id = order.get("algoId", "")
                if algo_id:
                    try:
                        _run_okx(["swap", "algo", "cancel", "--instId", inst_id, "--algoId", algo_id])
                        print(f"  Cancelled: {algo_id}")
                    except Exception as e:
                        print(f"  Failed to cancel {algo_id}: {e}")
    
    # Step 3: 获取当前价格
    print("\nStep 3: Get current price...")
    ticker = market_service.get_ticker("BTC-USDT")
    current_price = ticker.get("price", 0)
    print(f"  Current price: ${current_price}")
    
    # Step 4: 使用点数模式设置移动止盈
    print("\nStep 4: Set trailing stop with points mode...")
    callback_points = 25  # 25点
    activate_price = f"{current_price * 1.005:.2f}"  # 激活价：当前价+0.5%
    
    print(f"  Callback points: {callback_points}")
    print(f"  Activate price: ${activate_price}")
    
    try:
        result = trade.place_algo_trailing(
            inst_id=inst_id,
            side="sell",
            sz=sz,
            callback_points=callback_points,  # 直接传递点数
            activate_price=activate_price,
            pos_side="long",
            td_mode=td_mode,
        )
        print(f"  [OK] Trailing stop set")
        if isinstance(result, list) and len(result) > 0:
            algo_id = result[0].get("algoId", "")
            print(f"  Algo ID: {algo_id}")
    except Exception as e:
        print(f"  [ERROR] Failed: {e}")
        return
    
    # Step 5: 验证结果
    print("\nStep 5: Verify trailing stop order...")
    algo_orders = _run_okx(["swap", "algo", "orders", "--instId", inst_id])
    if isinstance(algo_orders, list):
        for order in algo_orders:
            if order.get("ordType") == "move_order_stop" and order.get("state") == "live":
                print(f"  ordType: {order.get('ordType')}")
                print(f"  state: {order.get('state')}")
                print(f"  callbackRatio: {order.get('callbackRatio')} ({float(order.get('callbackRatio', 0))*100:.4f}%)")
                print(f"  activePx: ${order.get('activePx')}")
                
                # 计算实际点数
                actual_points = float(order.get('callbackRatio', 0)) * current_price
                print(f"  Actual points: {actual_points:.2f}")
    
    print("\n[DONE] Test completed!")

if __name__ == "__main__":
    main()
