import json
import app.routers.settings  # 加载API密钥
from app.database import SessionLocal
from app.models import Strategy

db = SessionLocal()
strategies = db.query(Strategy).all()

print("=" * 80)
print("策略止盈止损点位计算（70000点做多，100X杠杆）")
print("=" * 80)
print()

base_price = 70000  # 基准价格
leverage = 100      # 杠杆倍数

for s in strategies:
    params = json.loads(s.params) if s.params else {}

    # 获取参数
    tp_pct = float(params.get("take_profit_pct", 0))      # 止盈%（杠杆收益）
    sl_pct = float(params.get("stop_loss_pct", 0))        # 止损%（杠杆亏损）
    ts_pct = float(params.get("trailing_stop_pct", 0))    # 移动止损%（回调比例）
    leverage_param = int(params.get("leverage", 10))      # 杠杆倍数参数

    # 计算价格变动百分比
    tp_price_change_pct = tp_pct / leverage / 100 if tp_pct > 0 else 0
    sl_price_change_pct = sl_pct / leverage / 100 if sl_pct > 0 else 0
    ts_price_change_pct = ts_pct / leverage / 100 if ts_pct > 0 else 0

    # 计算具体点位
    tp_price = base_price * (1 + tp_price_change_pct) if tp_pct > 0 else 0
    sl_price = base_price * (1 - sl_price_change_pct) if sl_pct > 0 else 0

    print(f"#{s.id} {s.name}")
    print(f"  杠杆倍数: {leverage_param}X")
    print(f"  止盈: {tp_pct}% (杠杆收益) → 价格变动{tp_price_change_pct*100:.4f}% → 止盈价 {tp_price:.2f}" if tp_pct > 0 else "  止盈: 未设置")
    print(f"  止损: {sl_pct}% (杠杆亏损) → 价格变动{sl_price_change_pct*100:.4f}% → 止损价 {sl_price:.2f}" if sl_pct > 0 else "  止损: 未设置")
    print(f"  移动止损: {ts_pct}% (回调比例) → 价格变动{ts_price_change_pct*100:.4f}%" if ts_pct > 0 else "  移动止损: 未设置")
    print()

db.close()
