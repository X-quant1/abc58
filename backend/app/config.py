"""全局配置"""
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 数据库
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'data' / 'btc_quant.db'}")

# OKX API
OKX_API_KEY = os.getenv("OKX_API_KEY", "")
OKX_SECRET_KEY = os.getenv("OKX_SECRET_KEY", "")
OKX_PASSPHRASE = os.getenv("OKX_PASSPHRASE", "")
OKX_SANDBOX = os.getenv("OKX_SANDBOX", "true")  # 默认用模拟盘

# 服务器
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))

# CORS
CORS_ORIGINS = [
    "http://localhost:5173",   # Vite dev
    "http://localhost:8000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8000",
]

# JWT 认证
JWT_SECRET = os.getenv("JWT_SECRET", "btc-quant-jwt-secret-key-2026")
JWT_ALGORITHM = "HS256"
