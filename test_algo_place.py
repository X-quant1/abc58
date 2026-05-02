"""直接用OKX CLI设置止盈止损"""
import sys
sys.path.insert(0, 'c:/LH/OKX/backend')

from app.routers.settings import _load_config, _apply_config
saved = _load_config()
if saved:
    _apply_config(saved)

from app.services.market import market_service
import subprocess
import os

# 获取价格
ticker = market_service.get_ticker("BTC-USDT")
current_price = ticker.get('price', 0)
print(f"当前价格: ${current_price}")

# 计算价位
tp_price = current_price * (1 + 60 / 100 / 100)
sl_price = current_price * (1 - 35 / 100 / 100)

print(f"止盈: ${tp_price:.2f}")
print(f"止损: ${sl_price:.2f}")

# 设置环境变量
env = os.environ.copy()
from app import config
env["OKX_API_KEY"] = config.OKX_API_KEY
env["OKX_SECRET_KEY"] = config.OKX_SECRET_KEY
env["OKX_PASSPHRASE"] = config.OKX_PASSPHRASE
env["OKX_DEMO"] = "0"
env["OKX_SITE"] = "global"

# 直接调用OKX CLI
OKX_CLI = r"C:\LH\OKX\tools\node-v20.18.0-win-x64\okx.cmd"

cmd = [
    OKX_CLI, "swap", "algo", "place",
    "--instId", "BTC-USDT-SWAP",
    "--side", "sell",
    "--sz", "0.01",
    "--posSide", "long",
    "--tdMode", "cross",
    f"--tpTriggerPx={tp_price:.2f}",
    "--tpOrdPx=-1",
    f"--slTriggerPx={sl_price:.2f}",
    "--slOrdPx=-1",
    "--reduceOnly"
]

print(f"\n命令: {' '.join(cmd)}")
print(f"\n执行...")

result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore', env=env)

print(f"\n返回码: {result.returncode}")
print(f"\nSTDOUT:\n{result.stdout}")
print(f"\nSTDERR:\n{result.stderr}")
