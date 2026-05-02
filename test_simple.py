"""简单测试 - 获取价格和开仓"""
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
print(f"Ticker: {ticker}")

current_price = ticker.get('price', ticker.get('last', 0))
print(f"当前价格: ${current_price}")

# 计算止盈止损价位
sz = "0.01"
leverage = 100
tp_pct = 60
sl_pct = 35

tp_price = current_price * (1 + tp_pct / leverage / 100)
sl_price = current_price * (1 - sl_pct / leverage / 100)

print(f"\n止盈触发价: ${tp_price:.2f} (收益{tp_pct}%)")
print(f"止损触发价: ${sl_price:.2f} (亏损{sl_pct}%)")

# 开仓
print(f"\n开多单 {sz}张...")
trade_service = TradeService()

try:
    # 设置杠杆
    trade_service.set_leverage("BTC-USDT-SWAP", leverage, "cross", pos_side="long")
    print(f"杠杆已设置为 {leverage}x")

    # 开多单
    result = trade_service.open_long(
        inst_id="BTC-USDT-SWAP",
        sz=sz,
        lever=leverage,
        td_mode="cross",
        tp_trigger_px=f"{tp_price:.2f}",
        sl_trigger_px=f"{sl_price:.2f}",
    )
    print(f"\n开仓成功!")
    print(f"订单ID: {result.get('ordId')}")
    print(f"委托价格: ${result.get('px')}")
    print(f"委托数量: {result.get('sz')}")

except Exception as e:
    print(f"\n错误: {e}")
    import traceback
    traceback.print_exc()
