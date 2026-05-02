import requests

# 登录
r = requests.post('http://localhost:8000/api/auth/login', json={
    'email': 'admin',
    'password': 'btc2026'
})
token = r.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

# 获取运行中的策略
r2 = requests.get('http://localhost:8000/api/strategy/list', headers=headers)
strategies = r2.json()['strategies']
running = [s for s in strategies if s['running']]

print(f'找到 {len(running)} 个运行中的策略，正在停止...')

# 停止所有策略
for s in running:
    try:
        r = requests.post(f"http://localhost:8000/api/strategy/{s['id']}/stop", headers=headers)
        if r.status_code == 200:
            print(f"  [OK] 已停止: {s['name']} (ID={s['id']})")
        else:
            print(f"  [FAIL] 停止失败: {s['name']} - {r.text}")
    except Exception as e:
        print(f"  [ERROR] {s['name']}: {e}")

print('\n所有策略已停止！')
