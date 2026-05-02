"""优化 KDJ 和量价突破策略参数"""
import sys
sys.path.insert(0, '.')
from app.database import SessionLocal
from app.models import Strategy
import json

db = SessionLocal()

# 定义要更新的策略
updates = {
    4: {  # KDJ金叉死叉
        "name": "KDJ金叉死叉-1H",
        "params": {
            "k_period": 7,           # 9 → 7
            "d_period": 3,           # 保持
            "j_smooth": 3,           # 保持
            "overbought": 70,        # 80 → 70
            "oversold": 30,          # 20 → 30
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
        }
    },
    11: {  # 量价突破
        "name": "量价突破-1H",
        "params": {
            "lookback": 10,          # 20 → 10
            "vol_mult": 1.0,         # 1.5 → 1.0
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
        }
    }
}

print("=== P0: 优化策略参数 ===\n")

for strategy_id, update in updates.items():
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if strategy:
        old_params = strategy.params
        strategy.params = json.dumps(update["params"])
        db.commit()
        
        print(f"[OK] #{strategy_id} {strategy.name}")
        print(f"  旧参数: {old_params}")
        print(f"  新参数: {json.dumps(update['params'], ensure_ascii=False)}")
        print()
    else:
        print(f"[X] #{strategy_id} 策略不存在")

db.close()
print("P0 参数优化完成！")
