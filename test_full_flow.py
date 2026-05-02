"""完整测试 - 开仓+止盈止损+移动止盈"""
import sys
sys.path.insert(0, 'c:/LH/OKX/backend')

from app.routers.settings import _load_config, _apply_config
saved = _load_config()
if saved:
    _apply_config(saved)

from app.services.trade import TradeService
from app.services.market import market_service
from app import config
import subprocess
import os

# 设置环境变量
env = os.environ.copy()
env["OKX_API_KEY"] = config.OKX_API_KEY
env["OKX_SECRET_KEY"] = config.OKX_SECRET_KEY
env["OKX_PASSPHRASE"] = config.OKX_PASSPHRASE
env["OKX_DEMO"] = "0"
env["OKX_SITE"] = "global"

OKX_CLI = r"C:\LH\OKX\tools\node-v20.18.0-win-x64\okx.cmd"

print("=" * 60)
print("完整测试 - 开仓+止盈止损+移动止盈")
print("=" * 60)

# 参数设置
sz = "0.01"
leverage = 100
tp_pct = 60  # 止盈60%
sl_pct = 35  # 止损35%
trail_activate_pct = 50  # 移动止盈激活50%
trail_callback_points = 25  # 回调25点

# 1. 获取当前价格
print("\n[1] 获取当前BTC价格...")
ticker = market_service.get_ticker("BTC-USDT")
current_price = ticker.get('price', 0)
print(f"    当前价格: ${current_price:.2f}")

# 2. 计算价位
print("\n[2] 计算止盈止损价位...")
tp_price = current_price * (1 + tp_pct / leverage / 100)
sl_price = current_price * (1 - sl_pct / leverage / 100)
activate_price = current_price * (1 + trail_activate_pct / leverage / 100)

print(f"    止盈触发价: ${tp_price:.2f} (收益{tp_pct}%)")
print(f"    止损触发价: ${sl_price:.2f} (亏损{sl_pct}%)")
print(f"    移动止盈激活价: ${activate_price:.2f} (收益{trail_activate_pct}%)")
print(f"    移动止盈回调: {trail_callback_points}点")

# 3. 设置杠杆
print("\n[3] 设置杠杆...")
trade_service = TradeService()
try:
    trade_service.set_leverage("BTC-USDT-SWAP", leverage, "cross", pos_side="long")
    print(f"    杠杆已设置为 {leverage}x")
except Exception as e:
    print(f"    设置杠杆失败（可能已设置）: {e}")

# 4. 开多单（不带止盈止损）
print("\n[4] 开多单...")
try:
    result = trade_service.open_long(
        inst_id="BTC-USDT-SWAP",
        sz=sz,
        lever=leverage,
        td_mode="cross",
    )
    if isinstance(result, list):
        result = result[0] if result else {}
    print(f"    开仓成功!")
    print(f"    订单ID: {result.get('ordId', 'N/A')}")
except Exception as e:
    print(f"    开仓失败: {e}")
    sys.exit(1)

# 5. 设置OCO止盈止损
print("\n[5] 设置OCO止盈止损...")
try:
    result = trade_service.place_algo_tp_sl(
        inst_id="BTC-USDT-SWAP",
        side="sell",
        sz=sz,
        tp_trigger_px=f"{tp_price:.2f}",
        tp_ord_px="-1",
        sl_trigger_px=f"{sl_price:.2f}",
        sl_ord_px="-1",
        pos_side="long",
        td_mode="cross",
    )
    if isinstance(result, list):
        result = result[0] if result else {}
    print(f"    OCO订单设置成功!")
    print(f"    算法单ID: {result.get('algoId', 'N/A')}")
except Exception as e:
    print(f"    设置OCO订单失败: {e}")

# 6. 设置移动止盈
print("\n[6] 设置移动止盈...")
try:
    # 计算回调比例
    callback_ratio = trail_callback_points / current_price
    callback_ratio = max(0.001, min(callback_ratio, 1.0))

    result = trade_service.place_algo_trailing(
        inst_id="BTC-USDT-SWAP",
        side="sell",
        sz=sz,
        callback_pct=callback_ratio * 100,
        activate_price=f"{activate_price:.2f}",
        pos_side="long",
        td_mode="cross",
    )
    if isinstance(result, list):
        result = result[0] if result else {}
    print(f"    移动止盈设置成功!")
    print(f"    算法单ID: {result.get('algoId', 'N/A')}")
except Exception as e:
    print(f"    设置移动止盈失败: {e}")

# 7. 查询算法单
print("\n[7] 查询算法单...")
result = subprocess.run(
    [OKX_CLI, "swap", "algo", "orders", "--instId", "BTC-USDT-SWAP"],
    capture_output=True,
    text=True,
    encoding='utf-8',
    errors='ignore',
    env=env
)
print(result.stdout)

print("\n" + "=" * 60)
print("测试完成！请检查OKX后台")
print("=" * 60)
