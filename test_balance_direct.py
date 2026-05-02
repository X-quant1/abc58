import sys
sys.path.insert(0, 'c:/LH/OKX/backend')
from app.routers.settings import _load_config, _apply_config
from app.services.okx_client import get_client, reset_client

# Load config
saved = _load_config()
print(f"Saved key: {saved.get('key','')[:8]}...")
print(f"Saved secret len: {len(saved.get('secret',''))}")
print(f"Saved passphrase len: {len(saved.get('passphrase',''))}")
print(f"Saved sandbox: {saved.get('sandbox')}")

# Apply
_apply_config(saved)
reset_client()

# Test direct OKX call
client = get_client()
print(f"Client has_credentials: {client.has_credentials}")
print(f"Client sandbox: {client.sandbox}")

try:
    data = client.get("/api/v5/account/balance")
    print(f"Balance: {data}")
except Exception as e:
    print(f"Balance FAILED: {type(e).__name__}: {e}")
