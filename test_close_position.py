import os
import sys
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend'))
sys.path.insert(0, backend_path)
from app.services.market import MarketService
from app.services.trade import TradeService
from app.services.settings import SettingsService

# 加载API配置
settings = SettingsService()
api_config = settings.get_api_config()
if not api_config:
    print('ERROR: API not configured')
    sys.exit(1)

os.environ['OKX_API_KEY'] = api_config['api_key']
os.environ['OKX_SECRET_KEY'] = api_config['secret_key']
os.environ['OKX_PASSPHRASE'] = api_config['passphrase']
os.environ['OKX_DEMO'] = 'true'

# 查看持仓
trade = TradeService()
positions = trade.get_positions('BTC-USDT-SWAP')
print('Current positions:')
for pos in positions:
    pos_side = pos.get('posSide', 'N/A')
    pos_size = pos.get('pos', '0')
    avg_px = pos.get('avgPx', '0')
    print(f'  Side: {pos_side}, Size: {pos_size}, AvgPx: {avg_px}')

# 一键平仓
if positions and any(float(p.get('pos', 0)) > 0 for p in positions):
    print('\nClosing all positions...')
    result = trade.close_all_positions('BTC-USDT-SWAP')
    print(f'Close result: {result}')
else:
    print('\nNo positions to close')
