import os
import sys
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend'))
sys.path.insert(0, backend_path)

from app.services.trade import trade_service
from app.services.market import market_service

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(os.path.join(backend_path, '.env'))

# 设置demo环境
os.environ['OKX_DEMO'] = 'true'

print("Testing open_long with TP/SL...")

# 先获取当前价格
ticker = market_service.get_ticker("BTC-USDT")
current_price = ticker.get('price', 0)
print(f"Current BTC price: {current_price}")

if current_price > 0:
    # 计算止盈止损价格
    tp_price = current_price * 1.003  # 0.3%
    sl_price = current_price * 0.9975  # 0.25%

    print(f"TP price: {tp_price:.2f}")
    print(f"SL price: {sl_price:.2f}")

    # 开多
    try:
        result = trade_service.open_long(
            inst_id="BTC-USDT-SWAP",
            sz="0.01",
            lever=100,
            td_mode="cross",
            tp_trigger_px=f"{tp_price:.2f}",
            sl_trigger_px=f"{sl_price:.2f}",
        )
        print(f"\nOpen long result:")
        print(result)
    except Exception as e:
        print(f"\nOpen long failed: {e}")
        import traceback
        traceback.print_exc()
