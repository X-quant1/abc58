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
    pass

time.sleep(2)

# 2. 设置杠杆为100X（long方向）
print('\nStep 2: Set leverage to 100X (long side)...')
lever_data = json.dumps({
    "inst_id": "BTC-USDT-SWAP",
    "lever": 100,
    "mgn_mode": "cross",
    "pos_side": "long"
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
        print(f'  [OK] Leverage set: {json.dumps(result, indent=2)}')
except urllib.error.HTTPError as e:
    error_body = e.read().decode('utf-8')
    print(f'  [FAIL] {error_body}')

# 3. 获取当前价格
req_price = urllib.request.Request(
    'http://localhost:8000/api/market/ticker?instId=BTC-USDT',
    headers={'Authorization': f'Bearer {token}'}
)

with urllib.request.urlopen(req_price) as response:
    ticker = json.loads(response.read().decode('utf-8'))
    current_price = ticker.get('price', 0)
    print(f'\nStep 3: Current BTC price: ${current_price}')

# 4. 计算止盈止损
tp_pct = 0.3
sl_pct = 0.25
tp_price = current_price * (1 + tp_pct / 100)
sl_price = current_price * (1 - sl_pct / 100)

print(f'\nStep 4: Calculate TP/SL')
print(f'  TP: ${tp_price:.2f} (+{tp_pct * 100}% PnL @ 100X)')
print(f'  SL: ${sl_price:.2f} (-{sl_pct * 100}% PnL @ 100X)')

# 5. 开多（不带止盈止损，先测试基本下单）
print(f'\nStep 5: Open long position (NO TP/SL first)...')
open_data = json.dumps({
    "inst_id": "BTC-USDT-SWAP",
    "sz": "0.01",
    "lever": 100,
    "td_mode": "cross",
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
        print(f'  Result: {json.dumps(result, indent=2)}')
except urllib.error.HTTPError as e:
    error_body = e.read().decode('utf-8')
    print(f'  [FAIL] {error_body}')
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

print(f'\n[INFO] Basic order test complete. Leverage: {leverage}X')
print(f'[INFO] Next step: Test with TP/SL')
