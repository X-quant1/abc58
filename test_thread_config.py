import sys
sys.path.insert(0, 'c:/LH/OKX/backend')
import asyncio
from app import config
print(f"Main thread: config.OKX_API_KEY = '{config.OKX_API_KEY[:8]}...'")

async def test():
    def check_in_thread():
        from app import config as cfg
        print(f"Thread: config.OKX_API_KEY = '{cfg.OKX_API_KEY[:8]}...'")
        
        from app.services.cache import get_cached_market_service
        ms = get_cached_market_service()
        print(f"Thread: client.api_key = '{ms._service.client.api_key[:8]}...'")
        print(f"Thread: client.has_credentials = {ms._service.client.has_credentials}")
        
        try:
            result = ms.get_account_balance()
            print(f"Thread: balance = {result.get('total_equity')}")
        except Exception as e:
            print(f"Thread: FAILED - {type(e).__name__}: {e}")
    
    await asyncio.to_thread(check_in_thread)

asyncio.run(test())
