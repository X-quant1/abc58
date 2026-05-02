"""查询OKX账户持仓模式"""
import subprocess
import os
import json
import sys

sys.path.insert(0, r"c:\LH\OKX\backend")
from app import config
from app.routers.settings import _load_config, _apply_config, is_encrypted, decrypt

# 加载保存的配置
saved = _load_config()
if saved:
    # 解密字段
    for field in ("key", "secret", "passphrase"):
        val = saved.get(field, "")
        if val and is_encrypted(val):
            saved[field] = decrypt(val)
    _apply_config(saved)

# 现在config里有API Key了
print(f"API Key: {config.OKX_API_KEY[:6]}..." if config.OKX_API_KEY else "No API Key!")
print(f"Sandbox: {config.OKX_SANDBOX}")

OKX_CLI = r"C:\LH\OKX\tools\node-v20.18.0-win-x64\okx.cmd"

env = os.environ.copy()
env["OKX_API_KEY"] = config.OKX_API_KEY or ""
env["OKX_SECRET_KEY"] = config.OKX_SECRET_KEY or ""
env["OKX_PASSPHRASE"] = config.OKX_PASSPHRASE or ""
env["OKX_DEMO"] = "1" if config.OKX_SANDBOX.lower() == "true" else "0"
env["OKX_SITE"] = "global"

# 查账户配置
result = subprocess.run(
    [OKX_CLI, "account", "config", "--json"],
    capture_output=True, text=True, timeout=15,
    encoding="utf-8", env=env
)
print(f"\nReturn code: {result.returncode}")
print(f"STDOUT: {result.stdout[:1000]}")
if result.stderr:
    print(f"STDERR: {result.stderr[:300]}")

# 解析
if result.stdout.strip():
    try:
        data = json.loads(result.stdout.strip())
        if isinstance(data, dict) and "data" in data:
            data = data["data"]
        if isinstance(data, list) and len(data) > 0:
            data = data[0]
        print(f"\n=== Account Config ===")
        print(json.dumps(data, indent=2, ensure_ascii=False)[:500])
        if isinstance(data, dict):
            pos_mode = data.get("posMode", "unknown")
            print(f"\n>>> Position Mode: {pos_mode}")
        else:
            print(f"\n>>> Unexpected data type: {type(data)}")
    except json.JSONDecodeError:
        print("Could not parse JSON")
