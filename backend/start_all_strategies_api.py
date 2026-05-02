"""启用并启动所有策略"""
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
    print('[OK] 登录成功')

# 2. 获取策略列表
req = urllib.request.Request(
    'http://127.0.0.1:8000/api/admin/strategies/list',
    headers={'Authorization': f'Bearer {token}'}
)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())
    strategies = [s for s in data.get('strategies', []) if s['id'] >= 3 and s['id'] <= 12]

print(f'[OK] 找到 {len(strategies)} 个策略需要启动')
print()

# 3. 启动所有策略（start方法会自动设置enabled=True）
print('=== 启动策略 ===')
for s in strategies:
    req = urllib.request.Request(
        f'http://127.0.0.1:8000/api/strategy/{s["id"]}/start',
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
            print(f'[OK] #{s["id"]} {s["name"]} 已启动')
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f'[X] #{s["id"]} {s["name"]} 启动失败: {error_body}')

print()
print('启动完成！')
