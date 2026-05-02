"""启动策略ID=15"""
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

# 启动策略
start_resp = requests.post(f"{BASE_URL}/api/strategy/15/start", headers=headers)
print(f"启动结果: {start_resp.json()}")
print(f"\n请查看后端PowerShell窗口，应该看到3个线程启动日志！")
