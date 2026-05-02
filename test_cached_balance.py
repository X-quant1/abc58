import sys
sys.path.insert(0, 'c:/LH/OKX/backend')
import asyncio
from app import config
from app.services.cache import get_cached_market_service

async def test():
    ms = get_cached_market_service()
    print(f"has_credentials: {ms._service.client.has_credentials}")
    
    try:
        import asyncio
        result = await asyncio.wait_for(
            asyncio.to_thread(ms.get_account_balance),
            timeout=10
        )
        print(f"Balance: {result}")
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")

asyncio.run(test())
