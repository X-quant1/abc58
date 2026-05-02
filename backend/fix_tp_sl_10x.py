"""修正止盈止损算法订单（10倍杠杆）"""
import sys
sys.path.insert(0, '.')

# 先加载配置
from app.routers import settings  # noqa: F401

from app.services.market import _run_okx
import json

# 持仓信息（10倍杠杆）
positions = [
    {
        "side": "long",
        "avg_price": 77655.0,
        "size": "0.01",
        "leverage": 10,
        "tp_pct": 3.0,  # 杠杆收益3%
        "sl_pct": 5.0,  # 杠杆亏损5%
    },
    {
        "side": "short",
        "avg_price": 77654.9,
        "size": "0.01",
        "leverage": 10,
        "tp_pct": 3.0,
        "sl_pct": 5.0,
    }
]

print("重新设置止盈止损（10倍杠杆）")
print("=" * 80)

for pos in positions:
    side = pos["side"]
    avg_price = pos["avg_price"]
    size = pos["size"]
    leverage = pos["leverage"]
    tp_pct = pos["tp_pct"]
    sl_pct = pos["sl_pct"]

    # 计算止盈止损价格（10倍杠杆）
    if side == "long":
        # 多单：止盈是上涨，止损是下跌
        tp_price = avg_price * (1 + tp_pct / leverage / 100)  # 0.3%
        sl_price = avg_price * (1 - sl_pct / leverage / 100)  # 0.5%
        algo_side = "sell"  # 平多需要卖出
    else:
        # 空单：止盈是下跌，止损是上涨
        tp_price = avg_price * (1 - tp_pct / leverage / 100)  # 0.3%
        sl_price = avg_price * (1 + sl_pct / leverage / 100)  # 0.5%
        algo_side = "buy"  # 平空需要买入

    print(f"\n{side.upper()} 单:")
    print(f"  开仓价: {avg_price}")
    print(f"  杠杆: {leverage}x")
    print(f"  止盈价: {tp_price:.2f} (杠杆收益{tp_pct}%, 价格变动{tp_pct/leverage}%)")
    print(f"  止损价: {sl_price:.2f} (杠杆亏损{sl_pct}%, 价格变动{sl_pct/leverage}%)")

    # 设置止盈算法订单
    print(f"  设置止盈...")
    try:
        tp_result = _run_okx([
            "swap", "algo", "place",
            "--instId", "BTC-USDT-SWAP",
            "--side", algo_side,
            "--sz", size,
            "--posSide", side,
            "--tdMode", "cross",
            "--reduceOnly",
            f"--tpTriggerPx={tp_price:.2f}",
            "--tpOrdPx=-1"
        ])
        algo_id = tp_result[0].get("algoId") if isinstance(tp_result, list) else "N/A"
        print(f"    [OK] 止盈算法订单: {algo_id}")
    except Exception as e:
        print(f"    [ERROR] 止盈设置失败: {e}")

    # 设置止损算法订单
    print(f"  设置止损...")
    try:
        sl_result = _run_okx([
            "swap", "algo", "place",
            "--instId", "BTC-USDT-SWAP",
            "--side", algo_side,
            "--sz", size,
            "--posSide", side,
            "--tdMode", "cross",
            "--reduceOnly",
            f"--slTriggerPx={sl_price:.2f}",
            "--slOrdPx=-1"
        ])
        algo_id = sl_result[0].get("algoId") if isinstance(sl_result, list) else "N/A"
        print(f"    [OK] 止损算法订单: {algo_id}")
    except Exception as e:
        print(f"    [ERROR] 止损设置失败: {e}")

print("\n完成！")
