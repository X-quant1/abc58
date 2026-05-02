"""测试移动止盈 - 获取详细错误"""
import sys
sys.path.insert(0, 'c:/LH/OKX/backend')

from app.routers.settings import _load_config, _apply_config
saved = _load_config()
if saved:
    _apply_config(saved)

from app.services.trade import TradeService
from app.services.market import market_service

# 获取价格
ticker = market_service.get_ticker("BTC-USDT")
current_price = ticker.get('price', 0)
print(f"当前价格: ${current_price}")

# 参数
sz = "0.01"
activate_price = current_price * (1 + 50 / 100 / 100)  # 50%收益激活

print(f"激活价: ${activate_price:.2f}")
print(f"回调: 25点")

# 直接调用OKX CLI
import subprocess
OKX_CLI = r"C:\LH\OKX\tools\node-v20.18.0-win-x64\okx.cmd"

cmd = [
    OKX_CLI, "swap", "algo", "trail",
    "--instId", "BTC-USDT-SWAP",
    "--side", "sell",
    "--sz", sz,
    "--posSide", "long",
    "--tdMode", "cross",
    "--callbackRatio", "25",
    "--activePx", f"{activate_price:.2f}",
    "--reduceOnly"
]

print(f"\n命令: {' '.join(cmd)}")
print(f"\n执行...")

result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')

print(f"\n返回码: {result.returncode}")
print(f"\nSTDOUT:\n{result.stdout}")
print(f"\nSTDERR:\n{result.stderr}")
