"""为当前持仓设置止盈止损（完整版）"""
import sys
sys.path.insert(0, '.')

# 先加载配置
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

# 先取消现有的止损算法订单
print("取消现有算法订单...")
try:
    trade_service._run_okx([
        "swap", "algo", "cancel",
        "--instId", inst_id,
        "--algoId", "3509705213416701952"
    ])
    print("[OK] 已取消")
except Exception as e:
    print(f"取消失败（可能已不存在）: {e}")

print()

# 重新设置止盈止损
print("设置新的止盈止损算法订单...")
try:
    result = trade_service.place_algo_tp_sl(
        inst_id=inst_id,
        side="buy",  # 平空需要买入
        sz=size,
        tp_trigger_px=f"{tp_price:.2f}",  # 止盈触发价
        tp_ord_px="-1",  # 市价委托
        sl_trigger_px=f"{sl_price:.2f}",  # 止损触发价
        sl_ord_px="-1",  # 市价委托
        pos_side=pos_side,
        td_mode="cross",
        reduce_only=True
    )
    print("[OK] 止盈止损设置成功:")
    print(result)
except Exception as e:
    print(f"[ERROR] 设置失败: {e}")
    import traceback
    traceback.print_exc()
