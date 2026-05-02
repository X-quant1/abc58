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

# 1. 平掉所有仓位
print('Step 1: Close all positions...')
close_data = json.dumps({"inst_id": "BTC-USDT-SWAP"}).encode('utf-8')
req_close = urllib.request.Request(
    'http://localhost:8000/api/trade/close-all',
    data=close_data,
    headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
)

try:
    with urllib.request.urlopen(req_close) as response:
        result = json.loads(response.read().decode('utf-8'))
        print(f'  Closed: {result.get("closed", 0)} positions')
except urllib.error.HTTPError as e:
    print(f'  Close failed: {e.code} {e.reason}')

time.sleep(2)

# 2. 设置杠杆为100X
print('\nStep 2: Set leverage to 100X...')
lever_data = json.dumps({
    "inst_id": "BTC-USDT-SWAP",
    "lever": 100,
    "mgn_mode": "cross"
}).encode('utf-8')

req_lever = urllib.request.Request(
    'http://localhost:8000/api/trade/leverage',
    data=lever_data,
    headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    },
    method='POST'
)

try:
    with urllib.request.urlopen(req_lever) as response:
        result = json.loads(response.read().decode('utf-8'))
        print(f'  [OK] Leverage set to 100X')
except urllib.error.HTTPError as e:
    print(f'  [FAIL] Set leverage failed: {e.code} {e.reason}')
    error_body = e.read().decode('utf-8')
    print(f'  Error: {error_body}')

# 3. 获取当前价格
req_price = urllib.request.Request(
    'http://localhost:8000/api/market/ticker?instId=BTC-USDT',
    headers={'Authorization': f'Bearer {token}'}
)

with urllib.request.urlopen(req_price) as response:
    ticker = json.loads(response.read().decode('utf-8'))
    current_price = ticker.get('price', 0)
    print(f'\nStep 3: Current BTC price: ${current_price}')

# 4. 计算止盈止损（100X杠杆）
# 盈利0.3% * 100X = 30%收益率
# 亏损0.25% * 100X = 25%亏损率
tp_pct = 0.3
sl_pct = 0.25
tp_price = current_price * (1 + tp_pct / 100)
sl_price = current_price * (1 - sl_pct / 100)

print(f'\nStep 4: Calculate TP/SL (100X leverage)')
print(f'  TP: ${tp_price:.2f} (+{tp_pct}% = +{tp_pct * 100}% PnL)')
print(f'  SL: ${sl_price:.2f} (-{sl_pct}% = -{sl_pct * 100}% PnL)')

# 5. 开多（带止盈止损）
print(f'\nStep 5: Open long position with TP/SL...')
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

time.sleep(2)

# 6. 查看持仓
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
        leverage = pos.get('leverage', 'N/A')
        print(f'\nStep 6: Position confirmed')
        print(f'  Size: {pos.get("size")} @ ${entry_price}')
        print(f'  Leverage: {leverage}X')
    else:
        print(f'\n  [FAIL] No position found')
        exit(1)

# 7. 计算移动止盈参数
trail_activate_pct = 0.2  # 盈利0.2%激活
trail_callback_points = 15  # 回调15点

activate_price = entry_price * (1 + trail_activate_pct / 100)
callback_ratio = trail_callback_points / current_price

# 应用修复后的逻辑
callback_ratio_fixed = min(callback_ratio, 0.9999)
callback_ratio_fixed = round(callback_ratio_fixed, 4)

print(f'\nStep 7: Trailing stop parameters')
print(f'  Entry price: ${entry_price:.2f}')
print(f'  Activate price: ${activate_price:.2f} (profit {trail_activate_pct}%)')
print(f'  Callback points: {trail_callback_points}')
print(f'  Callback ratio: {callback_ratio_fixed:.6f} ({callback_ratio_fixed*100:.4f}%)')

print(f'\n[INFO] Position opened successfully!')
print(f'  Entry: ${entry_price:.2f}')
print(f'  Leverage: 100X')
print(f'  TP: ${tp_price:.2f} (+{tp_pct * 100}% PnL)')
print(f'  SL: ${sl_price:.2f} (-{sl_pct * 100}% PnL)')
print(f'  Trailing activate: ${activate_price:.2f}')
print(f'  Trailing callback: {trail_callback_points} points ({callback_ratio_fixed*100:.4f}%)')
print(f'\n[INFO] Please check OKX dashboard to verify:')
print(f'  1. Fixed TP/SL orders are set')
print(f'  2. Leverage is 100X')
print(f'  3. Then manually set trailing stop to verify callback ratio')
