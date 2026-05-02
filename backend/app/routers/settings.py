"""设置路由 - OKX API 配置管理（加密持久化）"""
import os
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from app import config
from app.services.crypto import encrypt, decrypt, is_encrypted
from app.auth import get_current_user

router = APIRouter(prefix="/api/settings", tags=["设置"])

# 持久化配置文件路径
CONFIG_FILE = Path(__file__).resolve().parent.parent / "data" / "api_config.json"


def _load_config():
    """从文件加载配置（自动解密）"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 自动解密密文字段
            for field in ("key", "secret", "passphrase"):
                val = data.get(field, "")
                if is_encrypted(val):
                    data[field] = decrypt(val)
            return data
        except Exception:
            pass
    return {}


def _save_config(data: dict):
    """保存配置到文件（自动加密敏感字段）"""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    # 加密后再写入文件
    encrypted = {}
    for k, v in data.items():
        if k in ("key", "secret", "passphrase") and v:
            encrypted[k] = encrypt(str(v))
        else:
            encrypted[k] = v
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(encrypted, f, ensure_ascii=False)


def _apply_config(data: dict):
    """将配置应用到运行时（config 模块 + 环境变量）"""
    key = data.get("key", "")
    secret = data.get("secret", "")
    passphrase = data.get("passphrase", "")
    sandbox = data.get("sandbox", True)

    config.OKX_API_KEY = key
    config.OKX_SECRET_KEY = secret
    config.OKX_PASSPHRASE = passphrase
    config.OKX_SANDBOX = "true" if sandbox else "false"

    os.environ["OKX_API_KEY"] = key
    os.environ["OKX_SECRET_KEY"] = secret
    os.environ["OKX_PASSPHRASE"] = passphrase
    os.environ["OKX_SANDBOX"] = "true" if sandbox else "false"
    os.environ["OKX_DEMO"] = "1" if sandbox else "0"
    os.environ["OKX_SITE"] = "global"


# ─── 启动时自动加载已保存的配置 ───
_saved = _load_config()
if _saved:
    _apply_config(_saved)
    # 首次迁移：如果文件中的值是明文，自动加密后回写
    needs_re_encrypt = False
    for field in ("key", "secret", "passphrase"):
        val = _saved.get(field, "")
        if val and not is_encrypted(val):
            needs_re_encrypt = True
            break
    if needs_re_encrypt:
        _save_config(_saved)


class ApiConfigRequest(BaseModel):
    key: Optional[str] = None
    secret: Optional[str] = None
    passphrase: Optional[str] = None
    sandbox: bool = True


@router.get("/api")
async def get_api_config():
    """获取当前 API 配置（不返回密钥原文）"""
    from app.database import SessionLocal
    from app.models import SiteConfig

    saved = _load_config()
    # 从已保存配置读取（即使 config 模块未加载）
    api_key = saved.get("key", "")

    # 读取注册链接
    register_urls = {}
    db = SessionLocal()
    try:
        for key in ("okx_register_url", "bitget_register_url", "htx_register_url"):
            row = db.query(SiteConfig).filter(SiteConfig.key == key).first()
            register_urls[key] = row.value if row else ""
    finally:
        db.close()

    return {
        "key": api_key[:4] + "****" if api_key and len(api_key) > 4 else (api_key or ""),
        "secret": bool(saved.get("secret")),
        "passphrase": bool(saved.get("passphrase")),
        "sandbox": saved.get("sandbox", True),
        "okx_uid": saved.get("okx_uid", ""),
        **register_urls,
    }


@router.post("/api")
async def save_api_config(req: ApiConfigRequest, current_user: dict = Depends(get_current_user)):
    """保存 API 配置（加密持久化 + 运行时生效 + 同步 UID 到用户表）"""
    # 读取已有配置（已解密）
    saved = _load_config()

    # 更新（用户没修改的字段保持原值）
    if req.key is not None and not req.key.startswith("•"):
        saved["key"] = req.key
    if req.secret is not None and not req.secret.startswith("•"):
        saved["secret"] = req.secret
    if req.passphrase is not None and not req.passphrase.startswith("•"):
        saved["passphrase"] = req.passphrase
    saved["sandbox"] = req.sandbox

    # 加密后持久化到文件
    _save_config(saved)

    # 应用到运行时（用解密后的明文）
    _apply_config(saved)

    # 重置 OKX 客户端和缓存单例
    from app.services.okx_client import reset_client
    reset_client()
    from app.services import cache as cache_module
    cache_module._cached_market_service = None

    okx_uid = saved.get("okx_uid", "")

    # 同步 okx_uid 到当前用户的数据库记录
    if okx_uid:
        from app.database import SessionLocal
        from app.models import User, SubordinateUID
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == current_user["user_id"]).first()
            if user and not user.okx_uid:
                user.okx_uid = okx_uid

                # 检查是否是下级用户
                is_sub = db.query(SubordinateUID).filter(SubordinateUID.uid == okx_uid).first() is not None

                # 如果数据库中没有，且最近 5 分钟内没有抓取过，才触发抓取
                if not is_sub:
                    import os
                    import time
                    lock_file = "c:/LH/OKX/backend/data/fetch_subordinates.lock"

                    should_fetch = False
                    if not os.path.exists(lock_file):
                        should_fetch = True
                    else:
                        # 检查锁文件是否超过 5 分钟
                        lock_time = os.path.getmtime(lock_file)
                        if time.time() - lock_time > 300:
                            should_fetch = True

                    if should_fetch:
                        try:
                            # 创建锁文件，防止并发
                            with open(lock_file, "w") as f:
                                f.write(str(time.time()))

                            import subprocess
                            subprocess.run([
                                "C:\\LH\\OKX\\tools\\node-v20.18.0-win-x64\\node.exe",
                                "c:\\LH\\OKX\\fetch_uids_v2.js"
                            ], cwd="c:\\LH\\OKX", timeout=60, capture_output=True)

                            # 重新检查
                            is_sub = db.query(SubordinateUID).filter(SubordinateUID.uid == okx_uid).first() is not None
                        except Exception:
                            pass

                user.is_subordinate = is_sub
                db.commit()
        finally:
            db.close()

    return {
        "message": "API 配置已保存（加密存储）",
        "okx_uid": okx_uid
    }


@router.post("/test-connection")
async def test_connection():
    """测试 OKX API 连接"""
    if not config.OKX_API_KEY:
        raise HTTPException(status_code=403, detail="请先配置 OKX API Key")

    try:
        from app.services.cache import get_cached_market_service
        balance = get_cached_market_service().get_account_balance()
        return {
            "success": True,
            "equity": balance["total_equity"],
            "currencies": len(balance["details"]),
            "message": "OKX API 连接成功",
        }
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"连接失败: {str(e)}")


@router.post("/refresh-uid")
async def refresh_okx_uid():
    """刷新OKX UID"""
    if not config.OKX_API_KEY:
        raise HTTPException(status_code=403, detail="请先配置 OKX API Key")

    try:
        from app.services.cache import get_cached_market_service
        ms = get_cached_market_service()
        okx_uid = ms.get_account_uid() if hasattr(ms, 'get_account_uid') else None
        if okx_uid:
            # 保存到配置文件
            saved = _load_config()
            saved["okx_uid"] = okx_uid
            _save_config(saved)
            return {"success": True, "okx_uid": okx_uid, "message": "OKX UID 已更新"}
        else:
            raise HTTPException(status_code=502, detail="无法获取UID")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"获取UID失败: {str(e)}")


# ═══════════════════════════════════════════════════════
# 通知配置（SMTP 邮件）
# ═══════════════════════════════════════════════════════

# 通知配置文件（与 API 配置分开存储）
NOTIFY_CONFIG_FILE = Path(__file__).resolve().parent.parent / "data" / "notify_config.json"


def _load_notify_config():
    """加载通知配置"""
    if NOTIFY_CONFIG_FILE.exists():
        try:
            with open(NOTIFY_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 解密密码
            pwd = data.get("smtp_password", "")
            if pwd and is_encrypted(pwd):
                data["smtp_password"] = decrypt(pwd)
            return data
        except Exception:
            pass
    return {}


def _save_notify_config(data: dict):
    """保存通知配置（加密密码）"""
    NOTIFY_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    encrypted = dict(data)
    pwd = data.get("smtp_password", "")
    if pwd:
        encrypted["smtp_password"] = encrypt(str(pwd))
    with open(NOTIFY_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(encrypted, f, ensure_ascii=False)


def _apply_notify_config(data: dict):
    """应用到运行时"""
    from app.services.notification import notify_config
    notify_config.smtp_host = data.get("smtp_host", "")
    notify_config.smtp_port = int(data.get("smtp_port", 465))
    notify_config.smtp_user = data.get("smtp_user", "")
    notify_config.smtp_password = data.get("smtp_password", "")
    notify_config.smtp_to = data.get("smtp_to", "")
    notify_config.smtp_ssl = data.get("smtp_ssl", True)
    notify_config.email_enabled = data.get("email_enabled", False)
    notify_config.notify_trade = data.get("notify_trade", True)
    notify_config.notify_error = data.get("notify_error", True)
    notify_config.notify_system = data.get("notify_system", True)


# 启动时加载通知配置
_notify_saved = _load_notify_config()
if _notify_saved:
    _apply_notify_config(_notify_saved)


class NotifyConfigRequest(BaseModel):
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_to: Optional[str] = None
    smtp_ssl: Optional[bool] = None
    email_enabled: Optional[bool] = None
    notify_trade: Optional[bool] = None
    notify_error: Optional[bool] = None
    notify_system: Optional[bool] = None


@router.get("/notify")
async def get_notify_config():
    """获取当前通知配置"""
    from app.services.notification import notify_config
    return {
        "smtp_host": notify_config.smtp_host,
        "smtp_port": notify_config.smtp_port,
        "smtp_user": notify_config.smtp_user,
        "smtp_password": "****" if notify_config.smtp_password else "",
        "smtp_to": notify_config.smtp_to,
        "smtp_ssl": notify_config.smtp_ssl,
        "email_enabled": notify_config.email_enabled,
        "notify_trade": notify_config.notify_trade,
        "notify_error": notify_config.notify_error,
        "notify_system": notify_config.notify_system,
    }


@router.post("/notify")
async def save_notify_config(req: NotifyConfigRequest):
    """保存通知配置"""
    saved = _load_notify_config()
    req_dict = req.model_dump(exclude_none=True)
    # 密码：如果用户没有修改（还是 ****），保持原值
    if req_dict.get("smtp_password", "").startswith("•"):
        del req_dict["smtp_password"]
    saved.update(req_dict)
    _save_notify_config(saved)
    _apply_notify_config(saved)
    return {"message": "通知配置已保存"}


@router.post("/notify/test")
async def test_notify_email():
    """测试邮件发送"""
    from app.services.notification import notification_service
    result = notification_service.test_email()
    if not result["success"]:
        raise HTTPException(status_code=502, detail=result["message"])
    return result
