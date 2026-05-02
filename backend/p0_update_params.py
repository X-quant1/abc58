import requests
import json

# 登录
r = requests.post('http://localhost:8000/api/auth/login', json={
    'email': 'admin',
    'password': 'btc2026'
})
token = r.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

# 策略参数优化方案（基于回测数据）
strategy_params = {
    # 趋势策略：TP=2%, SL=0.8%, 移动止损=0.5%
    'trend_break': {'tp': 2.0, 'sl': 0.8, 'trail': 0.5},
    'multi_tf_trend': {'tp': 2.0, 'sl': 0.8, 'trail': 0.5},
    'supertrend': {'tp': 2.0, 'sl': 0.8, 'trail': 0.5},
    'ema_volume': {'tp': 2.0, 'sl': 0.8, 'trail': 0.5},
    'dual_ema': {'tp': 2.0, 'sl': 0.8, 'trail': 0.5},
    'ma_ribbon': {'tp': 2.0, 'sl': 0.8, 'trail': 0.5},

    # 震荡策略：TP=1.5%, SL=1%, 移动止损=0.3%
    'rsi': {'tp': 1.5, 'sl': 1.0, 'trail': 0.3},
    'rsi_macd': {'tp': 1.5, 'sl': 1.0, 'trail': 0.3},
    'kdj': {'tp': 1.5, 'sl': 1.0, 'trail': 0.3},
    'cci': {'tp': 1.5, 'sl': 1.0, 'trail': 0.3},
    'vol_break': {'tp': 1.5, 'sl': 1.0, 'trail': 0.3},

    # 套利策略：TP=0.5%, SL=0.3%, 无移动止损
    'funding_arb': {'tp': 0.5, 'sl': 0.3, 'trail': 0.0},
}

# 获取所有策略
r = requests.get('http://localhost:8000/api/strategy/list', headers=headers)
strategies = r.json()['strategies']

print('=' * 70)
print('批量更新策略止盈止损参数')
print('=' * 70)

updated_count = 0
for s in strategies:
    strategy_type = s['type']
    if strategy_type in strategy_params:
        params = strategy_params[strategy_type]
        update_data = {
            'take_profit_pct': params['tp'],
            'stop_loss_pct': params['sl'],
            'trailing_stop_pct': params['trail']
        }

        try:
            r = requests.put(
                f"http://localhost:8000/api/strategy/{s['id']}",
                json=update_data,
                headers=headers
            )

            if r.status_code == 200:
                print(f"[OK] ID={s['id']}, {s['name']}")
                print(f"     TP={params['tp']}%, SL={params['sl']}%, 移动止损={params['trail']}%")
                updated_count += 1
            else:
                print(f"[FAIL] ID={s['id']}, {s['name']}: {r.text}")
        except Exception as e:
            print(f"[ERROR] ID={s['id']}, {s['name']}: {e}")

print("\n" + "=" * 70)
print(f"更新完成: {updated_count}/{len(strategies)} 个策略")
print("=" * 70)
