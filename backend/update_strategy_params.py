"""更新策略参数"""
import sys
sys.path.insert(0, '.')
from app.database import SessionLocal
from app.models import Strategy
import json

db = SessionLocal()

# 定义要更新的策略
updates = {
    3: {  # RSI超卖超买
        "name": "RSI超卖超买-1H",
        "params": {
            "period": 6,           # 14 → 6
            "oversold": 40,        # 30 → 40
            "overbought": 60,      # 70 → 60
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
    5: {  # CCI趋势反转
        "name": "CCI趋势反转-1H",
        "params": {
            "period": 10,          # 20 → 10
            "overbought": 80,      # 100 → 80
            "oversold": -80,       # -100 → -80
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
    10: {  # 均线多空排列
        "name": "均线多空排列-1H",
        "params": {
            "period1": 3,          # 5 → 3
            "period2": 7,          # 10 → 7
            "period3": 13,         # 20 → 13
            "period4": 21,         # 60 → 21
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

print("=== 更新策略参数 ===\n")

for strategy_id, update in updates.items():
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if strategy:
        old_params = strategy.params
        strategy.params = json.dumps(update["params"])  # 序列化为 JSON 字符串
        db.commit()
        
        print(f"[OK] #{strategy_id} {strategy.name}")
        print(f"  旧参数: {json.dumps(old_params, ensure_ascii=False)}")
        print(f"  新参数: {json.dumps(update['params'], ensure_ascii=False)}")
        print()
    else:
        print(f"[X] #{strategy_id} 策略不存在")

db.close()
print("更新完成！")
