"""完整测试 - 开仓+止盈止损+移动止盈"""
import sys
sys.path.insert(0, 'c:/LH/OKX/backend')

# 先加载API配置
from app.routers.settings import _load_config, _apply_config
saved = _load_config()
if saved:
    _apply_config(saved)
    print("API配置已加载")

from app.services.trade import TradeService
from app.services.market import market_service
from app import config

print(f"\n当前配置:")
print(f"  OKX_API_KEY: {config.OKX_API_KEY[:20]}...")
print(f"  OKX_SANDBOX: {config.OKX_SANDBOX}")

# 获取价格
print(f"\n获取BTC价格...")
ticker = market_service.get_ticker("BTC-USDT")
current_price = ticker.get('price', ticker.get('last', 0))
print(f"当前价格: ${current_price}")

# 参数设置
sz = "0.01"
leverage = 100
tp_pct = 60
sl_pct = 35
trail_activate_pct = 50
trail_callback_points = 25

# 计算价位
tp_price = current_price * (1 + tp_pct / leverage / 100)
sl_price = current_price * (1 - sl_pct / leverage / 100)
activate_price = current_price * (1 + trail_activate_pct / leverage / 100)

print(f"\n止盈触发价: ${tp_price:.2f} (收益{tp_pct}%)")
print(f"止损触发价: ${sl_price:.2f} (亏损{sl_pct}%)")
print(f"移动止盈激活价: ${activate_price:.2f} (收益{trail_activate_pct}%)")
print(f"移动止盈回调: {trail_callback_points}点")

# 开仓
print(f"\n开多单 {sz}张...")
trade_service = TradeService()

try:
    # 设置杠杆
    trade_service.set_leverage("BTC-USDT-SWAP", leverage, "cross", pos_side="long")
    print(f"杠杆已设置为 {leverage}x")

    # 开多单（带止盈止损）
    result = trade_service.open_long(
        inst_id="BTC-USDT-SWAP",
        sz=sz,
        lever=leverage,
        td_mode="cross",
        tp_trigger_px=f"{tp_price:.2f}",
        sl_trigger_px=f"{sl_price:.2f}",
    )

    # 处理返回结果（可能是list或dict）
    if isinstance(result, list):
        result = result[0] if result else {}

    print(f"\n开仓成功!")
    print(f"订单ID: {result.get('ordId', 'N/A')}")
    print(f"委托价格: ${result.get('px', 'N/A')}")
    print(f"委托数量: {result.get('sz', 'N/A')}")

    # 设置移动止盈
    print(f"\n设置移动止盈...")
    trade_service.place_algo_trailing(
        inst_id="BTC-USDT-SWAP",
        side="sell",
        sz=sz,
        callback_value=trail_callback_points,
        activate_price=f"{activate_price:.2f}",
        pos_side="long",
        td_mode="cross",
    )
    print(f"移动止盈已设置!")
    print(f"  激活价: ${activate_price:.2f}")
    print(f"  回调: {trail_callback_points}点")

    print(f"\n{'='*60}")
    print(f"测试完成！请在OKX后台检查订单和止盈止损设置")
    print(f"{'='*60}")

except Exception as e:
    print(f"\n错误: {e}")
    import traceback
    traceback.print_exc()
