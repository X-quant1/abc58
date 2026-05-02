"""分别设置止盈和止损算法订单"""
import sys
sys.path.insert(0, '.')

# 先加载配置
from app.routers import settings  # noqa: F401

from app.services.market import _run_okx
import json

# 持仓信息
inst_id = "BTC-USDT-SWAP"
pos_side = "short"
size = "0.01"
avg_price = 77453.2

# 计算止盈止损价格
tp_price = avg_price * 0.97  # 下跌3%止盈
sl_price = avg_price * 1.05  # 上涨5%止损

print(f"开仓均价: {avg_price}")
print(f"止盈价格: {tp_price:.2f} (下跌3%)")
print(f"止损价格: {sl_price:.2f} (上涨5%)")
print()

# 1. 设置止盈算法订单
print("1. 设置止盈算法订单...")
tp_args = [
    "swap", "algo", "place",
    "--instId", inst_id,
    "--side", "buy",
    "--sz", size,
    "--posSide", pos_side,
    "--tdMode", "cross",
    "--reduceOnly",
    f"--tpTriggerPx={tp_price:.2f}",
    "--tpOrdPx=-1"
]

try:
    tp_result = _run_okx(tp_args)
    print(f"[OK] 止盈算法订单已创建: {tp_result[0].get('algoId')}")
except Exception as e:
    print(f"[ERROR] 止盈设置失败: {e}")

print()

# 2. 设置止损算法订单
print("2. 设置止损算法订单...")
sl_args = [
    "swap", "algo", "place",
    "--instId", inst_id,
    "--side", "buy",
    "--sz", size,
    "--posSide", pos_side,
    "--tdMode", "cross",
    "--reduceOnly",
    f"--slTriggerPx={sl_price:.2f}",
    "--slOrdPx=-1"
]

try:
    sl_result = _run_okx(sl_args)
    print(f"[OK] 止损算法订单已创建: {sl_result[0].get('algoId')}")
except Exception as e:
    print(f"[ERROR] 止损设置失败: {e}")

print()
print("完成！")
