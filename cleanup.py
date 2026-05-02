"""清理现有持仓和算法单"""
import sys
sys.path.insert(0, 'c:/LH/OKX/backend')

from app.routers.settings import _load_config, _apply_config
saved = _load_config()
if saved:
    _apply_config(saved)

from app.services.trade import TradeService
import subprocess
import os
from app import config

# 设置环境变量
env = os.environ.copy()
env["OKX_API_KEY"] = config.OKX_API_KEY
env["OKX_SECRET_KEY"] = config.OKX_SECRET_KEY
env["OKX_PASSPHRASE"] = config.OKX_PASSPHRASE
env["OKX_DEMO"] = "0"
env["OKX_SITE"] = "global"

OKX_CLI = r"C:\LH\OKX\tools\node-v20.18.0-win-x64\okx.cmd"

print("=" * 60)
print("清理现有持仓和算法单")
print("=" * 60)

# 1. 取消所有算法单
print("\n[1] 取消所有算法单...")
result = subprocess.run(
    [OKX_CLI, "swap", "algo", "orders", "--instId", "BTC-USDT-SWAP"],
    capture_output=True,
    text=True,
    encoding='utf-8',
    errors='ignore',
    env=env
)
print(result.stdout)

# 解析算法单ID
import re
algo_ids = re.findall(r'([0-9]{16,})\s+BTC-USDT-SWAP', result.stdout)

trade_service = TradeService()
for algo_id in algo_ids:
    print(f"\n取消算法单: {algo_id}")
    try:
        result = trade_service.cancel_algo_order("BTC-USDT-SWAP", algo_id)
        print(f"  结果: {result}")
    except Exception as e:
        print(f"  错误: {e}")

# 2. 平仓
print("\n[2] 平仓...")
try:
    result = trade_service.close_position("BTC-USDT-SWAP", mgn_mode="cross", pos_side="long")
    print(f"平仓结果: {result}")
except Exception as e:
    print(f"平仓错误: {e}")

# 3. 查询持仓
print("\n[3] 查询持仓...")
result = subprocess.run(
    [OKX_CLI, "swap", "positions", "--instId", "BTC-USDT-SWAP"],
    capture_output=True,
    text=True,
    encoding='utf-8',
    errors='ignore',
    env=env
)
print(result.stdout)

print("\n" + "=" * 60)
print("清理完成！")
print("=" * 60)
