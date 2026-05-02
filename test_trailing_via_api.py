import urllib.request
import urllib.error
import json

# 登录
login_data = json.dumps({"email": "admin", "password": "btc2026"}).encode('utf-8')
req = urllib.request.Request(
    'http://localhost:8000/api/auth/login',
    data=login_data,
    headers={'Content-Type': 'application/json'}
)

with urllib.request.urlopen(req) as response:
    result = json.loads(response.read().decode('utf-8'))
    token = result.get('access_token')
    print('Login successful\n')

# 获取当前价格和持仓
req_price = urllib.request.Request(
    'http://localhost:8000/api/market/ticker?instId=BTC-USDT',
    headers={'Authorization': f'Bearer {token}'}
)

with urllib.request.urlopen(req_price) as response:
    ticker = json.loads(response.read().decode('utf-8'))
    current_price = ticker.get('price', 0)
    print(f'Current BTC price: ${current_price}')

req_pos = urllib.request.Request(
    'http://localhost:8000/api/trade/positions',
    headers={'Authorization': f'Bearer {token}'}
)

with urllib.request.urlopen(req_pos) as response:
    result = json.loads(response.read().decode('utf-8'))
    positions = result.get('positions', [])
    if positions:
        pos = positions[0]
        entry_price = pos.get('avg_price', 0)
        pos_size = pos.get('size', 0)
        print(f'Current position: {pos_size} @ ${entry_price}\n')
    else:
        print('No position found!\n')
        exit(1)

# 计算移动止盈参数
trail_activate_pct = 0.2  # 盈利0.2%激活
trail_callback_points = 15  # 回调15点

activate_price = entry_price * (1 + trail_activate_pct / 100)
callback_ratio = trail_callback_points / current_price

print(f'Trailing stop parameters:')
print(f'  Entry price: ${entry_price:.2f}')
print(f'  Activate price: ${activate_price:.2f} (profit {trail_activate_pct}%)')
print(f'  Callback points: {trail_callback_points}')
print(f'  Current price: ${current_price}')
print(f'  Callback ratio: {callback_ratio:.6f} ({callback_ratio*100:.4f}%)')

# 应用修复后的逻辑
callback_ratio_fixed = min(callback_ratio, 0.9999)
callback_ratio_fixed = round(callback_ratio_fixed, 4)

print(f'  Callback ratio (after fix): {callback_ratio_fixed:.6f} ({callback_ratio_fixed*100:.4f}%)')
print(f'\n[INFO] The fix ensures callback ratio is not forced to 0.001 minimum')
print(f'[INFO] Before fix: max(0.001, min(callback_ratio, 1.0))')
print(f'[INFO] After fix: min(callback_ratio, 0.9999) + round(callback_ratio, 4)')

# 由于API没有暴露移动止盈接口，需要通过策略引擎测试
# 或者我可以创建一个临时的API端点来测试
print(f'\n[INFO] To test trailing stop, please:')
print(f'  1. Start MACD strategy (ID=1) via frontend')
print(f'  2. Check the trailing stop order in OKX dashboard')
print(f'  3. Verify callback ratio is {callback_ratio_fixed*100:.4f}% (not 0.1%)')
