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

# 1. 先平掉所有仓位
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

# 2. 等待几秒
import time
print('\nStep 2: Waiting 3 seconds...')
time.sleep(3)

# 3. 启动MACD策略
print('\nStep 3: Starting MACD strategy (ID=1)...')
req_start = urllib.request.Request(
    'http://localhost:8000/api/strategy/1/start',
    data=b'',
    headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    },
    method='POST'
)

try:
    with urllib.request.urlopen(req_start) as response:
        result = json.loads(response.read().decode('utf-8'))
        print(f'  [OK] {result.get("msg")}')
except urllib.error.HTTPError as e:
    print(f'  [FAIL] Start failed: {e.code} {e.reason}')
    error_body = e.read().decode('utf-8')
    print(f'  Error: {error_body}')

# 4. 等待策略开仓
print('\nStep 4: Waiting for strategy to open position (10 seconds)...')
time.sleep(10)

# 5. 查看持仓和日志
req_pos = urllib.request.Request(
    'http://localhost:8000/api/trade/positions',
    headers={'Authorization': f'Bearer {token}'}
)

with urllib.request.urlopen(req_pos) as response:
    result = json.loads(response.read().decode('utf-8'))
    positions = result.get('positions', [])
    if positions:
        print(f'\n  [OK] Position opened:')
        for pos in positions:
            print(f'    Size: {pos.get("size")} @ ${pos.get("avg_price")}')
    else:
        print(f'\n  [INFO] No position yet, strategy may be waiting for signal')

print('\n[INFO] Check the database logs for trailing stop details:')
print('  python c:\\LH\\OKX\\query_recent_logs.py')
