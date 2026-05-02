"""测试开多单 - 带止盈止损和移动止盈"""
import sys
import os
sys.path.insert(0, 'c:/LH/OKX/backend')

# 设置环境变量（从后端配置加载）
os.environ['OKX_DEMO'] = '1'  # 使用模拟盘

from app.services.trade import TradeService
from app.services.market import market_service
from app import config

# 检查API密钥是否已配置
print("=" * 60)
print("检查API密钥配置...")
print("=" * 60)
print(f"OKX_API_KEY: {'已配置' if config.OKX_API_KEY else '未配置'}")
print(f"OKX_SECRET_KEY: {'已配置' if config.OKX_SECRET_KEY else '未配置'}")
print(f"OKX_PASSPHRASE: {'已配置' if config.OKX_PASSPHRASE else '未配置'}")
print(f"OKX_SANDBOX: {config.OKX_SANDBOX}")

if not all([config.OKX_API_KEY, config.OKX_SECRET_KEY, config.OKX_PASSPHRASE]):
    print("\n错误: API密钥未配置，请先在Settings页面配置API密钥")
    sys.exit(1)

# 初始化交易服务
trade_service = TradeService()

# 参数设置
inst_id = "BTC-USDT-SWAP"
sz = "0.01"  # 0.01张
leverage = 100  # 100倍杠杆
td_mode = "cross"  # 全仓模式

# 止盈止损参数（百分比）
tp_pct = 60  # 止盈60%（杠杆收益）
sl_pct = 35  # 止损35%（杠杆亏损）

# 移动止盈参数
trail_activate_pct = 50  # 激活阈值50%（杠杆收益）
trail_callback_points = 25  # 回调25点

print("\n" + "=" * 60)
print("测试开多单 - 带止盈止损和移动止盈")
print("=" * 60)

# 1. 获取当前价格
print("\n[1] 获取当前BTC价格...")
ticker = market_service.get_ticker("BTC-USDT")
current_price = ticker.get("price", 0)
print(f"    当前价格: ${current_price:.2f}")

# 2. 计算止盈止损价位
print("\n[2] 计算止盈止损价位...")
# 止盈：价格上涨 tp_pct/leverage/100
tp_price_change = tp_pct / leverage / 100
tp_trigger_px = f"{current_price * (1 + tp_price_change):.2f}"
print(f"    止盈触发价: ${tp_trigger_px} (收益{tp_pct}%)")

# 止损：价格下跌 sl_pct/leverage/100
sl_price_change = sl_pct / leverage / 100
sl_trigger_px = f"{current_price * (1 - sl_price_change):.2f}"
print(f"    止损触发价: ${sl_trigger_px} (亏损{sl_pct}%)")

# 移动止盈激活价
activate_price = f"{current_price * (1 + trail_activate_pct / leverage / 100):.2f}"
print(f"    移动止盈激活价: ${activate_price} (收益{trail_activate_pct}%)")
print(f"    移动止盈回调: {trail_callback_points}点")

# 3. 设置杠杆
print("\n[3] 设置杠杆...")
try:
    trade_service.set_leverage(inst_id, leverage, td_mode, pos_side="long")
    print(f"    杠杆已设置为 {leverage}x")
except Exception as e:
    print(f"    设置杠杆失败（可能已设置）: {e}")

# 4. 开多单（带止盈止损）
print("\n[4] 开多单...")
print(f"    合约: {inst_id}")
print(f"    张数: {sz}")
print(f"    止盈: ${tp_trigger_px}")
print(f"    止损: ${sl_trigger_px}")

try:
    order_result = trade_service.open_long(
        inst_id=inst_id,
        sz=sz,
        lever=leverage,
        td_mode=td_mode,
        tp_trigger_px=tp_trigger_px,
        sl_trigger_px=sl_trigger_px,
    )
    print(f"    开仓成功!")
    print(f"    订单ID: {order_result.get('ordId', 'N/A')}")
    print(f"    委托价格: ${order_result.get('px', 'N/A')}")
    print(f"    委托数量: {order_result.get('sz', 'N/A')}")
except Exception as e:
    print(f"    开仓失败: {e}")
    sys.exit(1)

# 5. 设置移动止盈
print("\n[5] 设置移动止盈...")
try:
    trade_service.place_algo_trailing(
        inst_id=inst_id,
        side="sell",  # 多单平仓方向是sell
        sz=sz,
        callback_value=trail_callback_points,  # 点数模式
        activate_price=activate_price,
        pos_side="long",
        td_mode=td_mode,
    )
    print(f"    移动止盈已设置!")
    print(f"    激活价: ${activate_price}")
    print(f"    回调: {trail_callback_points}点")
except Exception as e:
    print(f"    设置移动止盈失败: {e}")

print("\n" + "=" * 60)
print("测试完成！请在OKX后台检查订单和止盈止损设置")
print("=" * 60)
