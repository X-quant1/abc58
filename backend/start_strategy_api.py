"""通过API启动策略"""
import urllib.request
import json

# 1. 登录获取token
login_data = json.dumps({"email": "admin", "password": "btc2026"}).encode()
req = urllib.request.Request(
    'http://127.0.0.1:8000/api/auth/login',
    data=login_data,
    headers={'Content-Type': 'application/json'}
)
with urllib.request.urlopen(req) as resp:
    login_result = json.loads(resp.read().decode())
    token = login_result['access_token']
    print(f'[OK] 登录成功')

# 2. 启动策略#3 (RSI)
req = urllib.request.Request(
    'http://127.0.0.1:8000/api/strategy/3/start',
    data=b'',
    method='POST',
    headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
)
try:
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode())
        print(f'[OK] 启动策略#3: {result}')
except urllib.error.HTTPError as e:
    error_body = e.read().decode()
    print(f'[X] 启动失败: {e.code} {error_body}')
