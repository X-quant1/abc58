"""创建新策略实例"""
import sys
sys.path.insert(0, '.')
from app.database import SessionLocal
from app.models import Strategy
import json

db = SessionLocal()

# 定义新策略
new_strategies = [
    {
        "name": "多时间框架趋势-1H",
        "type": "multi_tf_trend",
        "params": {
            "trend_period": 50,
            "signal_period": 10,
            "timeframe": "1h",
            "inst_id": "BTC-USDT-SWAP",
            "size_mode": "fixed",
            "size": 0.01,
            "size_pct": 10,
            "leverage": 10,
            "take_profit_pct": 0.0,
            "stop_loss_pct": 5.0,
            "trailing_stop_pct": 0.0,
            "td_mode": "cross"
        },
        "enabled": False  # 默认不启用，需要用户手动启用
    },
    {
        "name": "资金费率套利-1H",
        "type": "funding_arb",
        "params": {
            "funding_threshold": 0.0001,
            "min_interval": 8,
            "timeframe": "1h",
            "inst_id": "BTC-USDT-SWAP",
            "size_mode": "fixed",
            "size": 0.01,
            "size_pct": 10,
            "leverage": 10,
            "take_profit_pct": 0.0,
            "stop_loss_pct": 5.0,
            "trailing_stop_pct": 0.0,
            "td_mode": "cross"
        },
        "enabled": False
    }
]

print("=== 创建新策略实例 ===\n")

for strategy_data in new_strategies:
    # 检查是否已存在
    existing = db.query(Strategy).filter(
        Strategy.name == strategy_data["name"]
    ).first()

    if existing:
        print(f"[跳过] {strategy_data['name']} 已存在 (ID: {existing.id})")
        continue

    # 创建新策略
    strategy = Strategy(
        name=strategy_data["name"],
        type=strategy_data["type"],
        params=json.dumps(strategy_data["params"]),
        position="none",
        enabled=strategy_data["enabled"]
    )
    db.add(strategy)
    db.commit()
    db.refresh(strategy)

    print(f"[创建] {strategy.name} (ID: {strategy.id})")
    print(f"  类型: {strategy.type}")
    print(f"  启用: {strategy.enabled}")
    print()

db.close()
print("完成！请在前端策略管理页面启用这些策略。")
