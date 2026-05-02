"""测试移动止盈 - 使用正确比例"""
import sys
sys.path.insert(0, 'c:/LH/OKX/backend')

from app.routers.settings import _load_config, _apply_config
saved = _load_config()
if saved:
    _apply_config(saved)

from app.services.trade import TradeService
from app.services.market import market_service

# 获取价格
ticker = market_service.get_ticker("BTC-USDT")
current_price = ticker.get('price', 0)
print(f"当前价格: ${current_price}")

# 参数
sz = "0.01"
trail_callback_points = 25  # 25点

# 计算比例
callback_ratio = trail_callback_points / current_price
print(f"回调点数: {trail_callback_points}点")
print(f"转换为比例: {callback_ratio:.6f} ({callback_ratio*100:.4f}%)")

# 激活价（50%收益）
activate_price = current_price * (1 + 50 / 100 / 100)
print(f"激活价: ${activate_price:.2f}")

# 设置移动止盈
print(f"\n设置移动止盈...")
trade_service = TradeService()

try:
    result = trade_service.place_algo_trailing(
        inst_id="BTC-USDT-SWAP",
        side="sell",
        sz=sz,
        callback_pct=callback_ratio * 100,  # 转换为百分比
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
