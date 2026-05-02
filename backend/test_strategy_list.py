"""测试策略列表API"""
import requests

# 登录
r = requests.post('http://localhost:8000/api/auth/login', json={'email': 'admin', 'password': 'btc2026'})
print('登录响应:', r.json())
token = r.json()['access_token']

# 获取策略列表（正确路径）
r2 = requests.get('http://localhost:8000/api/strategy/list', headers={'Authorization': f'Bearer {token}'})
data = r2.json()

print(f'\n返回策略数: {len(data.get("strategies", []))}')
print(f'is_admin: {data.get("is_admin")}')
if data.get('strategies'):
    print('\n前5个策略:')
    for s in data['strategies'][:5]:
        print(f'  #{s["id"]} {s["name"]} | published={s["published"]} | enabled={s["enabled"]} | warning={s.get("unpublished_warning")}')
