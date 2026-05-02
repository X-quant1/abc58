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
req2 = urllib.request.Request(
    'http://localhost:8000/api/strategy/1/stop',
    data=b'',
    headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    },
    method='POST'
)

try:
    with urllib.request.urlopen(req2) as response:
        result = json.loads(response.read().decode('utf-8'))
        print('Stop strategy result:')
        print(json.dumps(result, indent=2))
except urllib.error.HTTPError as e:
    print(f'Stop failed: {e.code} {e.reason}')
    error_body = e.read().decode('utf-8')
    print(error_body)

# 一键平仓
close_data = json.dumps({"inst_id": "BTC-USDT-SWAP"}).encode('utf-8')
req3 = urllib.request.Request(
    'http://localhost:8000/api/trade/close-all',
    data=close_data,
    headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
)

try:
    with urllib.request.urlopen(req3) as response:
        result = json.loads(response.read().decode('utf-8'))
        print('\nClose all positions result:')
        print(json.dumps(result, indent=2))
except urllib.error.HTTPError as e:
    print(f'Close failed: {e.code} {e.reason}')
    error_body = e.read().decode('utf-8')
    print(error_body)
