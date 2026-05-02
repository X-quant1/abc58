"""为策略#12的空单设置止盈止损"""
import sys
sys.path.insert(0, '.')

# 先加载配置（必须先导入settings路由）
from app.routers import settings  # noqa: F401

from app.services.trade import trade_service
from app.services.logger import sys_logger

# 持仓信息
inst_id = "BTC-USDT-SWAP"
pos_side = "short"  # 空单
size = "0.01"
avg_price = 77453.2

# 计算止盈止损价格
# 空单：止盈是价格下跌，止损是价格上涨
tp_price = avg_price * 0.97  # 下跌3%止盈
sl_price = avg_price * 1.05  # 上涨5%止损

print(f"开仓均价: {avg_price}")
print(f"止盈价格: {tp_price:.2f} (下跌3%)")
print(f"止损价格: {sl_price:.2f} (上涨5%)")
print()

# 设置止盈止损
# 空单平仓需要 buy 操作
try:
    result = trade_service.place_algo_tp_sl(
        inst_id=inst_id,
        side="buy",  # 平空需要买入
        sz=size,
        tp_trigger_px=f"{tp_price:.2f}",
        tp_ord_px="-1",  # 市价委托
        sl_trigger_px=f"{sl_price:.2f}",
        sl_ord_px="-1",  # 市价委托
        pos_side=pos_side,
        td_mode="cross",
        reduce_only=True
    )
    print("止盈止损设置成功:")
    print(result)
except Exception as e:
    print(f"设置失败: {e}")
    import traceback
    traceback.print_exc()
