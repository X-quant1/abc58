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

# 计算移动止盈参数
# 激活价格：盈利0.2% → 开仓价 * 1.002
# 假设开仓价是76868.1
entry_price = 76868.1
activate_price = entry_price * 1.002  # 盈利0.2%激活
callback_points = 15  # 回调15点

# 计算回调比例
callback_ratio = callback_points / current_price
callback_pct = callback_ratio * 100

print(f'Activate price: {activate_price:.2f} (profit 0.2%)')
print(f'Callback points: {callback_points}')
print(f'Callback ratio: {callback_ratio} ({callback_pct:.4f}%)\n')

# 由于API没有直接的移动止盈接口，我需要通过后端服务内部调用
# 让我直接查看后端日志来验证策略是否正确设置了移动止盈

print("Checking strategy logs for trailing stop...")
