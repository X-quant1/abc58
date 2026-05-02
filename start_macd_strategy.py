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

# 启动MACD策略（ID=1）
req2 = urllib.request.Request(
    'http://localhost:8000/api/strategy/1/start',
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
        print('Start strategy result:')
        print(json.dumps(result, indent=2))
except urllib.error.HTTPError as e:
    print(f'Start failed: {e.code} {e.reason}')
    error_body = e.read().decode('utf-8')
    print(error_body)

# 等待几秒查看状态
print('\nWaiting 5 seconds...')
time.sleep(5)

# 查看策略状态
req3 = urllib.request.Request(
    'http://localhost:8000/api/strategy/list',
    headers={'Authorization': f'Bearer {token}'}
)

with urllib.request.urlopen(req3) as response:
    result = json.loads(response.read().decode('utf-8'))
    strategies = result.get('strategies', [])
    for s in strategies:
        if s.get('id') == 1:
            print(f"\nStrategy status:")
            print(f"  Enabled: {s.get('enabled')}")
            print(f"  Running: {s.get('running')}")
            print(f"  Position: {s.get('position')}")
