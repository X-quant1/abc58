import os
import sys
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend'))
sys.path.insert(0, backend_path)

# 必须在导入app模块前设置环境变量
from dotenv import load_dotenv
env_file = os.path.join(backend_path, '.env')
if os.path.exists(env_file):
    load_dotenv(env_file)

os.environ['OKX_DEMO'] = 'true'

from app.services.trade import trade_service
from app.services.market import market_service

# 获取当前价格
ticker = market_service.get_ticker("BTC-USDT")
current_price = ticker.get('price', 0)
print(f'Current BTC price: ${current_price}')

# 计算移动止盈参数
entry_price = 76874.95
trail_activate_pct = 0.2
trail_callback_points = 15

activate_price = entry_price * (1 + trail_activate_pct / 100)
callback_ratio = trail_callback_points / current_price

print(f'\nTrailing stop parameters:')
print(f'  Entry price: ${entry_price:.2f}')
print(f'  Activate price: ${activate_price:.2f} (profit {trail_activate_pct}%)')
print(f'  Callback points: {trail_callback_points}')
print(f'  Current price: ${current_price}')
print(f'  Callback ratio (before fix): {callback_ratio:.6f} ({callback_ratio*100:.4f}%)')

# 应用修复后的逻辑
callback_ratio_fixed = min(callback_ratio, 0.9999)
callback_ratio_fixed = round(callback_ratio_fixed, 4)

print(f'  Callback ratio (after fix): {callback_ratio_fixed:.6f} ({callback_ratio_fixed*100:.4f}%)')
print(f'  Callback percentage: {callback_ratio_fixed * 100:.4f}%')

# 设置移动止盈
print(f'\nSetting trailing stop...')
try:
    result = trade_service.place_algo_trailing(
        inst_id="BTC-USDT-SWAP",
        side="sell",
        sz="0.01",
        callback_pct=callback_ratio_fixed * 100,  # 转换为百分比
        activate_price=f"{activate_price:.2f}",
        pos_side="long",
        td_mode="cross",
    )
    print(f'[OK] Trailing stop set successfully!')
    print(f'Result: {result}')
except Exception as e:
    print(f'[FAIL] Trailing stop failed: {e}')
    import traceback
    traceback.print_exc()
