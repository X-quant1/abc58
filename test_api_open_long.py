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

# 获取当前价格
req_price = urllib.request.Request(
    'http://localhost:8000/api/market/ticker?instId=BTC-USDT',
    headers={'Authorization': f'Bearer {token}'}
)

with urllib.request.urlopen(req_price) as response:
    ticker = json.loads(response.read().decode('utf-8'))
    current_price = ticker.get('price', 0)
    print(f'Current BTC price: {current_price}')

# 计算止盈止损
tp_price = current_price * 1.003  # 0.3%
sl_price = current_price * 0.9975  # 0.25%
print(f'TP price: {tp_price:.2f}')
print(f'SL price: {sl_price:.2f}\n')

# 开多
open_data = json.dumps({
    "inst_id": "BTC-USDT-SWAP",
    "sz": "0.01",
    "lever": 100,
    "td_mode": "cross",
    "tp_trigger_px": f"{tp_price:.2f}",
    "sl_trigger_px": f"{sl_price:.2f}",
}).encode('utf-8')

req2 = urllib.request.Request(
    'http://localhost:8000/api/trade/open-long',
    data=open_data,
    headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
)

try:
    with urllib.request.urlopen(req2) as response:
        result = json.loads(response.read().decode('utf-8'))
        print('Open long result:')
        print(json.dumps(result, indent=2))
except urllib.error.HTTPError as e:
    print(f'Open failed: {e.code} {e.reason}')
    error_body = e.read().decode('utf-8')
    print(error_body)
