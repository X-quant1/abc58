import requests
import json

# 登录
r = requests.post('http://localhost:8000/api/auth/login', json={
    'email': 'admin',
    'password': 'btc2026'
})
token = r.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

# 获取所有策略
r = requests.get('http://localhost:8000/api/strategy/list', headers=headers)
strategies = r.json()['strategies']

print('=' * 70)
print('所有策略状态:')
print('=' * 70)

for s in strategies:
    params = s['params']
    print(f"\nID={s['id']}, name={s['name']}")
    print(f"  类型: {s['type']}")
    print(f"  运行: {s['running']}")
    print(f"  持仓: {s['position']}")
    print(f"  杠杆: {params.get('leverage', 10)}x")
    print(f"  止盈: {params.get('take_profit_pct', 0)}%")
    print(f"  止损: {params.get('stop_loss_pct', 0)}%")
    print(f"  移动止损: {params.get('trailing_stop_pct', 0)}%")
    print(f"  周期: {params.get('timeframes', ['1h'])}")

print("\n" + "=" * 70)
print(f"总计: {len(strategies)} 个策略")
print("=" * 70)
