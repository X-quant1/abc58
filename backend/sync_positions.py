"""同步持仓状态 - 从OKX API检查真实持仓并更新数据库"""
from app.database import SessionLocal
from app.models import Strategy
from app.services.trade import trade_service
from app.services.crypto import decrypt, is_encrypted
from pathlib import Path
import json
import os

# 加载API配置
CONFIG_FILE = Path(__file__).resolve().parent / "data" / "api_config.json"

def load_api_config():
    """从文件加载API配置"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 解密
        for field in ("key", "secret", "passphrase"):
            val = data.get(field, "")
            if is_encrypted(val):
                data[field] = decrypt(val)
        return data
    return {}

# 加载配置
config = load_api_config()
if not config.get("key"):
    print("错误: 未配置API Key")
    exit(1)

# 设置环境变量
os.environ["OKX_API_KEY"] = config["key"]
os.environ["OKX_SECRET_KEY"] = config["secret"]
os.environ["OKX_PASSPHRASE"] = config["passphrase"]
os.environ["OKX_SANDBOX"] = "true" if config.get("sandbox", True) else "false"
os.environ["OKX_DEMO"] = "1" if config.get("sandbox", True) else "0"
os.environ["OKX_SITE"] = "global"

print(f'=== API配置已加载 ===')
print(f'API Key: {config["key"][:4]}****')

db = SessionLocal()

try:
    # 获取OKX真实持仓
    inst_id = "BTC-USDT-SWAP"
    positions = trade_service.get_swap_positions(inst_id)
    
    print(f'\n=== OKX真实持仓 ===')
    print(f'持仓数据: {positions}')
    
    # 判断真实持仓方向
    okx_position = "none"
    for pos in positions:
        if pos.get("symbol", "") == inst_id:
            raw_size = pos.get("size", "0")
            try:
                sz = float(raw_size) if raw_size else 0.0
            except (ValueError, TypeError):
                sz = 0.0
            
            if sz > 0:
                side = pos.get("side", "")
                if side == "long":
                    okx_position = "long"
                elif side == "short":
                    okx_position = "short"
                print(f'  持仓方向: {okx_position}, 数量: {sz}')
                break
    
    if okx_position == "none":
        print('  无持仓')
    
    # 更新数据库中所有策略的持仓状态
    print(f'\n=== 更新数据库持仓状态 ===')
    strategies = db.query(Strategy).filter(Strategy.position != 'none').all()
    
    for s in strategies:
        print(f'  #{s.id} {s.name}: {s.position} -> {okx_position}')
        s.position = okx_position
    
    db.commit()
    print(f'\n已更新 {len(strategies)} 个策略的持仓状态')

finally:
    db.close()
