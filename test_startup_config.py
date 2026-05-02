import sys
sys.path.insert(0, 'c:/LH/OKX/backend')
from app.routers.settings import _load_config, _apply_config
from app import config

saved = _load_config()
print(f"Before apply: OKX_API_KEY='{config.OKX_API_KEY[:8] if config.OKX_API_KEY else ''}'")
_apply_config(saved)
print(f"After apply: OKX_API_KEY='{config.OKX_API_KEY[:8] if config.OKX_API_KEY else ''}'")

# Now check if the dashboard module sees the same config
from app.routers import dashboard
# dashboard.py imports: from app import config
print(f"Dashboard's config ref is same object: {dashboard.config is config}")
print(f"Dashboard's config.OKX_API_KEY='{dashboard.config.OKX_API_KEY[:8] if dashboard.config.OKX_API_KEY else ''}'")

# Check the _ms reference
from app.services.cache import get_cached_market_service
from app.services.okx_client import reset_client
from app.services import cache as cache_module, market_rest as market_module

reset_client()
cache_module._cached_market_service = None
market_module._market_service = None

ms = get_cached_market_service()
print(f"ms client has_credentials: {ms._service.client.has_credentials}")
print(f"ms client api_key: {ms._service.client.api_key[:8] if ms._service.client.api_key else ''}")

# Try balance
try:
    bal = ms.get_account_balance()
    print(f"Balance: {bal.get('total_equity')}")
except Exception as e:
    print(f"Balance error: {e}")
