"""停止策略"""
import requests
import sys

sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://localhost:8000"

# 登录
login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
    "email": "admin",
    "password": "btc2026"
})
token = login_resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 停止策略
stop_resp = requests.post(f"{BASE_URL}/api/strategy/15/stop", headers=headers)
print(f"停止结果: {stop_resp.json()}")
