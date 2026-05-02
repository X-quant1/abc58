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

# 开多单，同时设置止盈止损
# 模拟MACD策略参数：
# - 止盈：0.3%
# - 止损：0.25%
# - 移动激活：0.2%
# - 回调点数：15点

open_data = json.dumps({
    "inst_id": "BTC-USDT-SWAP",
    "side": "buy",
    "size": 0.01,
    "pos_side": "long",
    "td_mode": "cross",
    "tp_trigger_px": "",  # 将由后端计算
    "sl_trigger_px": "",  # 将由后端计算
    "tp_pct": 0.3,        # 止盈0.3%
    "sl_pct": 0.25,       # 止损0.25%
    "trail_activate_pct": 0.2,  # 移动激活0.2%
    "trail_callback_points": 15  # 回调15点
}).encode('utf-8')

req2 = urllib.request.Request(
    'http://localhost:8000/api/trade/open-position',
    data=open_data,
    headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
)

try:
    with urllib.request.urlopen(req2) as response:
        result = json.loads(response.read().decode('utf-8'))
        print('Open position result:')
        print(json.dumps(result, indent=2))
except urllib.error.HTTPError as e:
    print(f'Open failed: {e.code} {e.reason}')
    error_body = e.read().decode('utf-8')
    print(error_body)
