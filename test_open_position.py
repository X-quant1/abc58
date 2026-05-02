"""通过后端API测试开多单"""
import requests
import json
import sys

# 设置UTF-8编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://localhost:8000"

# 1. 登录获取token
print("=" * 60)
print("登录中...")
login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
    'email': 'admin',
    'password': 'btc2026'
})
token_data = login_resp.json()
token = token_data['access_token']
print(f"[OK] 登录成功，用户: {token_data['user']['username']}")

headers = {'Authorization': f'Bearer {token}'}

# 2. 获取当前BTC价格
print("\n" + "=" * 60)
print("获取当前BTC价格...")
ticker_resp = requests.get(f"{BASE_URL}/api/market/ticker/BTC-USDT", headers=headers)
ticker = ticker_resp.json()
print(f"Ticker响应: {json.dumps(ticker, indent=2, ensure_ascii=False)}")

current_price = float(ticker.get('last', ticker.get('price', 0)))
print(f"[OK] 当前价格: ${current_price:.2f}")

# 3. 计算止盈止损价位
print("\n" + "=" * 60)
print("计算止盈止损价位...")

# 参数设置
sz = "0.01"
leverage = 100
tp_pct = 60  # 止盈60%（杠杆收益）
sl_pct = 35  # 止损35%（杠杆亏损）
trail_activate_pct = 50  # 移动止盈激活50%
trail_callback_points = 25  # 回调25点

# 计算价位
tp_price_change = tp_pct / leverage / 100
tp_trigger_px = f"{current_price * (1 + tp_price_change):.2f}"

sl_price_change = sl_pct / leverage / 100
sl_trigger_px = f"{current_price * (1 - sl_price_change):.2f}"

activate_price = f"{current_price * (1 + trail_activate_pct / leverage / 100):.2f}"

print(f"  止盈触发价: ${tp_trigger_px} (收益{tp_pct}%)")
print(f"  止损触发价: ${sl_trigger_px} (亏损{sl_pct}%)")
print(f"  移动止盈激活价: ${activate_price} (收益{trail_activate_pct}%)")
print(f"  移动止盈回调: {trail_callback_points}点")

# 4. 调用开仓API
print("\n" + "=" * 60)
print("开多单中...")
print(f"  合约: BTC-USDT-SWAP")
print(f"  张数: {sz}")
print(f"  杠杆: {leverage}x")
print(f"  止盈: ${tp_trigger_px}")
print(f"  止损: ${sl_trigger_px}")

# 直接调用trade_service
sys.path.insert(0, 'c:/LH/OKX/backend')

from app.services.trade import TradeService
from app.services.market import market_service
from app import config

print(f"\n检查API配置...")
print(f"  OKX_API_KEY: {'已配置' if config.OKX_API_KEY else '未配置'}")
print(f"  OKX_SANDBOX: {config.OKX_SANDBOX}")

if not config.OKX_API_KEY:
    print("\n错误: API密钥未配置！")
    print("请在Settings页面配置API密钥，或检查环境变量")
    sys.exit(1)

# 初始化交易服务
trade_service = TradeService()

try:
    # 设置杠杆
    print("\n设置杠杆...")
    trade_service.set_leverage("BTC-USDT-SWAP", leverage, "cross", pos_side="long")
    print(f"[OK] 杠杆已设置为 {leverage}x")

    # 开多单（带止盈止损）
    print("\n开多单...")
    order_result = trade_service.open_long(
        inst_id="BTC-USDT-SWAP",
        sz=sz,
        lever=leverage,
        td_mode="cross",
        tp_trigger_px=tp_trigger_px,
        sl_trigger_px=sl_trigger_px,
    )
    print(f"[OK] 开仓成功!")
    print(f"  订单ID: {order_result.get('ordId', 'N/A')}")
    print(f"  委托价格: ${order_result.get('px', 'N/A')}")
    print(f"  委托数量: {order_result.get('sz', 'N/A')}")

    # 设置移动止盈
    print("\n设置移动止盈...")
    trade_service.place_algo_trailing(
        inst_id="BTC-USDT-SWAP",
        side="sell",
        sz=sz,
        callback_value=trail_callback_points,
        activate_price=activate_price,
        pos_side="long",
        td_mode="cross",
    )
    print(f"[OK] 移动止盈已设置!")
    print(f"  激活价: ${activate_price}")
    print(f"  回调: {trail_callback_points}点")

    print("\n" + "=" * 60)
    print("[OK] 测试完成！请在OKX后台检查订单和止盈止损设置")
    print("=" * 60)

except Exception as e:
    print(f"\n[ERROR] 错误: {e}")
    import traceback
    traceback.print_exc()
