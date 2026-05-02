"""测试获取BTC价格"""
import requests
import json

BASE_URL = "http://localhost:8000"

print("获取BTC价格...")
ticker_resp = requests.get(f"{BASE_URL}/api/market/ticker/BTC-USDT")
print(f"状态码: {ticker_resp.status_code}")
print(f"响应内容:")
print(json.dumps(ticker_resp.json(), indent=2, ensure_ascii=False))
