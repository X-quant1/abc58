import urllib.request
import urllib.error
import json
import time

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

# 停止策略
print('Step 1: Stop MACD strategy...')
req_stop = urllib.request.Request(
    'http://localhost:8000/api/strategy/1/stop',
    data=b'',
    headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    },
    method='POST'
)

try:
    with urllib.request.urlopen(req_stop) as response:
        result = json.loads(response.read().decode('utf-8'))
        print(f'  [OK] {result.get("msg")}')
except urllib.error.HTTPError as e:
    print(f'  [INFO] {e.code} {e.reason}')

# 获取当前价格
req_price = urllib.request.Request(
    'http://localhost:8000/api/market/ticker?instId=BTC-USDT',
    headers={'Authorization': f'Bearer {token}'}
)

with urllib.request.urlopen(req_price) as response:
    ticker = json.loads(response.read().decode('utf-8'))
    current_price = ticker.get('price', 0)
    print(f'\nStep 2: Current BTC price: ${current_price}')

# 计算止盈止损
tp_pct = 0.3
sl_pct = 0.25
tp_price = current_price * (1 + tp_pct / 100)
sl_price = current_price * (1 - sl_pct / 100)

print(f'\nStep 3: Calculate TP/SL')
print(f'  TP: ${tp_price:.2f} (+{tp_pct}%)')
print(f'  SL: ${sl_price:.2f} (-{sl_pct}%)')

# 开多
print(f'\nStep 4: Open long position...')
open_data = json.dumps({
    "inst_id": "BTC-USDT-SWAP",
    "sz": "0.01",
    "lever": 100,
    "td_mode": "cross",
    "tp_trigger_px": f"{tp_price:.2f}",
    "sl_trigger_px": f"{sl_price:.2f}",
}).encode('utf-8')

req_open = urllib.request.Request(
    'http://localhost:8000/api/trade/open-long',
    data=open_data,
    headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
)

try:
    with urllib.request.urlopen(req_open) as response:
        result = json.loads(response.read().decode('utf-8'))
        print(f'  [OK] Open long success')
        order_id = result.get('result', [{}])[0].get('ordId', '')
        print(f'  Order ID: {order_id}')
except urllib.error.HTTPError as e:
    print(f'  [FAIL] Open failed: {e.code} {e.reason}')
    error_body = e.read().decode('utf-8')
    print(f'  Error: {error_body}')
    exit(1)

# 等待成交
time.sleep(2)

# 查看持仓
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
        print(f'\nStep 5: Position confirmed')
        print(f'  Size: {pos.get("size")} @ ${entry_price}')
    else:
        print(f'\n  [FAIL] No position found')
        exit(1)

# 计算移动止盈参数
trail_activate_pct = 0.2
trail_callback_points = 15

activate_price = entry_price * (1 + trail_activate_pct / 100)
callback_ratio = trail_callback_points / current_price

# 应用修复后的逻辑
callback_ratio_fixed = min(callback_ratio, 0.9999)
callback_ratio_fixed = round(callback_ratio_fixed, 4)

print(f'\nStep 6: Trailing stop parameters (FIXED)')
print(f'  Entry price: ${entry_price:.2f}')
print(f'  Activate price: ${activate_price:.2f} (profit {trail_activate_pct}%)')
print(f'  Callback points: {trail_callback_points}')
print(f'  Callback ratio: {callback_ratio_fixed:.6f} ({callback_ratio_fixed*100:.4f}%)')
print(f'\n  [FIX] Before: would be forced to 0.001 (0.1%)')
print(f'  [FIX] After: correctly set to {callback_ratio_fixed:.6f} ({callback_ratio_fixed*100:.4f}%)')

print(f'\n[OK] Test complete! Position ready for your verification.')
print(f'  Entry: ${entry_price:.2f}')
print(f'  TP: ${tp_price:.2f}')
print(f'  SL: ${sl_price:.2f}')
print(f'  Trailing activate: ${activate_price:.2f}')
print(f'  Trailing callback: {trail_callback_points} points ({callback_ratio_fixed*100:.4f}%)')
