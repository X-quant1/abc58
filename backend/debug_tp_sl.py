"""调试止盈止损参数"""
import sys
sys.path.insert(0, '.')

# 先加载配置
from app.routers import settings  # noqa: F401

from app.services.trade import trade_service

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

# 检查参数
tp_trigger_px = f"{tp_price:.2f}"
sl_trigger_px = f"{sl_price:.2f}"

print(f"tp_trigger_px: '{tp_trigger_px}'")
print(f"sl_trigger_px: '{sl_trigger_px}'")
print(f"tp_trigger_px 是否为空: {not tp_trigger_px}")
print(f"sl_trigger_px 是否为空: {not sl_trigger_px}")
print()

# 调用方法
print("调用 place_algo_tp_sl...")
result = trade_service.place_algo_tp_sl(
    inst_id=inst_id,
    side="buy",
    sz=size,
    tp_trigger_px=tp_trigger_px,
    tp_ord_px="-1",
    sl_trigger_px=sl_trigger_px,
    sl_ord_px="-1",
    pos_side=pos_side,
    td_mode="cross",
    reduce_only=True
)
print("结果:")
print(result)
