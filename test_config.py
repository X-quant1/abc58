import sys
sys.path.insert(0, 'c:/LH/OKX/backend')

from app import config

print(f"OKX_API_KEY: {config.OKX_API_KEY[:20] if config.OKX_API_KEY else 'NOT SET'}...")
print(f"OKX_SECRET_KEY: {config.OKX_SECRET_KEY[:20] if config.OKX_SECRET_KEY else 'NOT SET'}...")
print(f"OKX_PASSPHRASE: {config.OKX_PASSPHRASE[:10] if config.OKX_PASSPHRASE else 'NOT SET'}...")
print(f"OKX_SANDBOX: {config.OKX_SANDBOX}")
