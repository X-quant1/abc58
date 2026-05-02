"""清理重复的算法订单"""
import sys
sys.path.insert(0, '.')

# 先加载配置
from app.routers import settings  # noqa: F401

from app.services.market import _run_okx
import json

# 获取所有算法订单
result = _run_okx([
    "swap", "algo", "orders",
    "--instId", "BTC-USDT-SWAP"
])

if isinstance(result, list):
    print(f"当前有 {len(result)} 个算法订单")
    print()

    # 取消所有算法订单
    for order in result:
        algo_id = order.get('algoId')
        print(f"取消算法订单: {algo_id}")
        try:
            cancel_result = _run_okx([
                "swap", "algo", "cancel",
                "--instId", "BTC-USDT-SWAP",
                "--algoId", algo_id
            ])
            print(f"  [OK] 已取消")
        except Exception as e:
            print(f"  [ERROR] 取消失败: {e}")

    print()
    print("所有算法订单已取消")
