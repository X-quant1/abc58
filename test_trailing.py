"""完整测试 - 设置移动止盈"""
import sys
sys.path.insert(0, 'c:/LH/OKX/backend')

from app.routers.settings import _load_config, _apply_config
saved = _load_config()
if saved:
    _apply_config(saved)

from app.services.trade import TradeService
from app.services.market import market_service
from app import config

print(f"当前配置:")
print(f"  OKX_API_KEY: {config.OKX_API_KEY[:20]}...")
print(f"  OKX_SANDBOX: {config.OKX_SANDBOX}")

# 获取价格
ticker = market_service.get_ticker("BTC-USDT")
current_price = ticker.get('price', 0)
print(f"\n当前价格: ${current_price}")

# 参数
sz = "0.01"
leverage = 100
trail_activate_pct = 50
trail_callback_points = 25

# 计算激活价
activate_price = current_price * (1 + trail_activate_pct / leverage / 100)

print(f"\n移动止盈参数:")
print(f"  激活价: ${activate_price:.2f}")
print(f"  回调: {trail_callback_points}点")

# 设置移动止盈
print(f"\n设置移动止盈...")
trade_service = TradeService()

try:
    result = trade_service.place_algo_trailing(
        inst_id="BTC-USDT-SWAP",
        side="sell",
        sz=sz,
        callback_value=trail_callback_points,
        activate_price=f"{activate_price:.2f}",
        pos_side="long",
        td_mode="cross",
    )
    print(f"\n移动止盈设置成功!")
    print(f"结果: {result}")

except Exception as e:
    print(f"\n错误: {e}")
    import traceback
    traceback.print_exc()
