"""设置路由 - Bitget API 配置管理（加密持久化）"""
import os
import json
import base64
import uuid
import shutil
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from typing import Optional

from app.services.crypto import encrypt, decrypt, is_encrypted
from app.auth import get_current_user

router = APIRouter(prefix="/api/settings", tags=["设置"])

# Bitget配置文件路径
BITGET_CONFIG_FILE = Path(__file__).resolve().parent.parent / "data" / "bitget_config.json"
# 头像上传目录（backend/static/uploads/ai-avatars）
AVATAR_DIR = Path(__file__).resolve().parent.parent.parent / "static" / "uploads" / "ai-avatars"


def _load_bitget_config():
    """加载Bitget配置（自动解密）"""
    if BITGET_CONFIG_FILE.exists():
        try:
            with open(BITGET_CONFIG_FILE, "r", encoding="utf-8") as f:
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


def _has_bitget_config() -> bool:
    """检查是否已配置Bitget API"""
    try:
        from pathlib import Path
        bitget_file = Path(__file__).resolve().parent.parent / "data" / "bitget_config.json"
        if bitget_file.exists():
            import json
            with open(bitget_file, "r") as f:
                data = json.load(f)
            return bool(data.get("key")) and bool(data.get("secret"))
    except Exception:
        pass
    return False


def _save_bitget_config(data: dict):
    """保存Bitget配置到文件（自动加密敏感字段）"""
    BITGET_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    # 加密后再写入文件
    encrypted = {}
    for k, v in data.items():
        if k in ("key", "secret", "passphrase") and v:
            encrypted[k] = encrypt(str(v))
        else:
            encrypted[k] = v
    with open(BITGET_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(encrypted, f, ensure_ascii=False, indent=2)


class BitgetConfigRequest(BaseModel):
    key: Optional[str] = None
    secret: Optional[str] = None
    passphrase: Optional[str] = None


@router.get("/api")
async def get_api_config():
    """获取Bitget API配置（不返回密钥原文）"""
    saved = _load_bitget_config()
    api_key = saved.get("key", "")

    return {
        "key": api_key[:4] + "****" if api_key and len(api_key) > 4 else (api_key or ""),
        "secret": bool(saved.get("secret")),
        "passphrase": bool(saved.get("passphrase")),
        "bitget_uid": saved.get("bitget_uid", ""),
        "bitget_register_url": "",
    }


@router.post("/bitget_api")
async def save_bitget_api_config(req: BitgetConfigRequest, current_user: dict = Depends(get_current_user)):
    """保存 Bitget API 配置（加密持久化 + 运行时生效）"""
    # 读取已有配置（已解密）
    saved = _load_bitget_config()

    # 更新（用户没修改的字段保持原值）
    if req.key is not None and not req.key.startswith("•"):
        saved["key"] = req.key
    if req.secret is not None and not req.secret.startswith("•"):
        saved["secret"] = req.secret
    if req.passphrase is not None and not req.passphrase.startswith("•"):
        saved["passphrase"] = req.passphrase

    # 加密后持久化到文件
    _save_bitget_config(saved)

    # 验证API配置：获取账户信息
    try:
        from app.services.bitget_client import init_client, get_client
        init_client(saved.get("key", ""), saved.get("secret", ""), saved.get("passphrase", ""))
        client = get_client()
        account_info = client.get_account_info()
        
        # 保存bitget_uid
        bitget_uid = account_info.get("userId", "")
        if bitget_uid:
            saved["bitget_uid"] = bitget_uid
            _save_bitget_config(saved)
            
            # 同步bitget_uid到用户表
            from app.database import SessionLocal
            from app.models import User
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.id == current_user["user_id"]).first()
                if user:
                    user.bitget_uid = bitget_uid
                    db.commit()
            finally:
                db.close()
        
        return {
            "success": True,
            "message": "Bitget API 配置成功",
            "bitget_uid": bitget_uid
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Bitget API 验证失败: {str(e)}")


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


# ═══════════════════════════════════════════════════════
# 站点配置（名称、Logo）
# ═══════════════════════════════════════════════════════

class SiteSettingsRequest(BaseModel):
    site_name: Optional[str] = None
    site_logo: Optional[str] = None  # Base64 或 URL
    site_slogan: Optional[str] = None  # 副标题
    avg_profit: Optional[str] = None  # 平均收益（百分比）
    avg_profit_mode: Optional[str] = "custom"  # custom=自定义 / auto=自动浮动
    active_users: Optional[str] = None  # 活跃用户数
    active_users_mode: Optional[str] = "real"  # custom=自定义 / real=真实数据
    total_strategies: Optional[str] = None  # 策略总数
    total_strategies_mode: Optional[str] = "real"  # custom=自定义 / real=真实数据


@router.get("/site")
async def get_site_settings():
    """获取站点配置"""
    from app.database import SessionLocal
    from app.models import SiteConfig

    db = SessionLocal()
    try:
        defaults = {
            "site_name": "BTC Quant",
            "site_logo": "",
            "site_slogan": "量化交易系统",
            "avg_profit": "5.0",
            "avg_profit_mode": "custom",
            "active_users": "1",
            "active_users_mode": "real",
            "total_strategies": "15",
            "total_strategies_mode": "real",
        }
        result = dict(defaults)
        for key in defaults:
            row = db.query(SiteConfig).filter(SiteConfig.key == key).first()
            if row and row.value:
                result[key] = row.value
        return result
    finally:
        db.close()


@router.post("/site")
async def save_site_settings(req: SiteSettingsRequest, current_user: dict = Depends(get_current_user)):
    """保存站点配置（仅管理员）"""
    from app.database import SessionLocal
    from app.models import User, SiteConfig

    db = SessionLocal()
    try:
        # 检查管理员权限
        user = db.query(User).filter(User.id == current_user["user_id"]).first()
        if not user or user.role != "admin":
            raise HTTPException(status_code=403, detail="仅管理员可操作")

        # 处理 Logo: 如果是 Base64 数据，保存为文件
        logo_value = req.site_logo
        if logo_value and logo_value.startswith("data:image/"):
            # 解析 Base64 数据
            try:
                header, b64data = logo_value.split(",", 1)
                ext = header.split("/")[1].split(";")[0]  # e.g. "png", "jpeg"
                if ext == "jpeg": ext = "jpg"
                logo_dir = Path(__file__).resolve().parent.parent / "static" / "uploads"
                logo_dir.mkdir(parents=True, exist_ok=True)
                # 删除旧 logo 文件
                for f in logo_dir.glob("site-logo.*"):
                    f.unlink()
                # 保存新文件
                filename = f"site-logo.{ext}"
                filepath = logo_dir / filename
                filepath.write_bytes(base64.b64decode(b64data))
                logo_value = f"/static/uploads/{filename}"
            except Exception as e:
                print(f"Logo save error: {e}")

        # 更新或创建配置
        config_items = [
            ("site_name", req.site_name),
            ("site_logo", logo_value),
            ("site_slogan", req.site_slogan),
            ("avg_profit", req.avg_profit),
            ("avg_profit_mode", req.avg_profit_mode),
            ("active_users", req.active_users),
            ("active_users_mode", req.active_users_mode),
            ("total_strategies", req.total_strategies),
            ("total_strategies_mode", req.total_strategies_mode),
        ]
        for key, value in config_items:
            if value is not None:
                row = db.query(SiteConfig).filter(SiteConfig.key == key).first()
                if row:
                    row.value = value
                else:
                    row = SiteConfig(key=key, value=value)
                    db.add(row)
        db.commit()
        return {"message": "站点配置已保存", "site_logo": logo_value}
    finally:
        db.close()


# ═══════════════════════════════════════════════════════
# AI 模型配置（多模型协作）
# ═══════════════════════════════════════════════════════

@router.get("/ai")
async def get_ai_config(current_user: dict = Depends(get_current_user)):
    """获取AI配置（脱敏）"""
    from app.services.ai_analysis import get_ai_config as _get_cfg
    cfg = _get_cfg()

    def _mask_key(k):
        return k[:6] + "****" if len(k) > 6 else (k or "")

    result = {
        "analysts": {},
        "judge": {},
        "quick_analysis": {},
        "configured_count": 0,
    }

    for key, a in cfg.get("analysts", {}).items():
        result["analysts"][key] = {
            "name": a.get("name", key),
            "emoji": a.get("emoji", "🤖"),
            "avatar_url": a.get("avatar_url", ""),
            "role_desc": a.get("role_desc", ""),
            "api_key": _mask_key(a.get("api_key", "")),
            "base_url": a.get("base_url", ""),
            "model": a.get("model", ""),
            "configured": bool(a.get("api_key") and a.get("base_url") and a.get("model")),
        }
        if result["analysts"][key]["configured"]:
            result["configured_count"] += 1

    j = cfg.get("judge", {})
    result["judge"] = {
        "name": j.get("name", "裁决者"),
        "emoji": j.get("emoji", "⚖️"),
        "avatar_url": j.get("avatar_url", ""),
        "role_desc": j.get("role_desc", ""),
        "api_key": _mask_key(j.get("api_key", "")),
        "base_url": j.get("base_url", ""),
        "model": j.get("model", ""),
        "configured": bool(j.get("api_key") and j.get("base_url") and j.get("model")),
    }

    # 快速分析配置
    qa = cfg.get("quick_analysis", {})
    result["quick_analysis"] = {
        "name": qa.get("name", "快速分析"),
        "role_desc": qa.get("role_desc", ""),
        "api_key": _mask_key(qa.get("api_key", "")),
        "base_url": qa.get("base_url", ""),
        "model": qa.get("model", ""),
        "configured": bool(qa.get("api_key") and qa.get("base_url") and qa.get("model")),
    }

    return result


@router.post("/ai")
async def save_ai_config(req: dict, current_user: dict = Depends(get_current_user)):
    """保存AI配置（仅管理员）"""
    from app.database import SessionLocal
    from app.models import User
    from app.services.ai_analysis import get_ai_config as _get_cfg, update_ai_config as _update_cfg

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == current_user["user_id"]).first()
        if not user or user.role != "admin":
            raise HTTPException(status_code=403, detail="仅管理员可操作")

        cfg = _get_cfg()

        # 更新分析师配置
        if "analysts" in req:
            for key, a_cfg in req["analysts"].items():
                if key in cfg["analysts"]:
                    # 只更新有效的 api_key（不是脱敏值）
                    ak = a_cfg.get("api_key", "")
                    if ak and "****" not in ak and not ak.startswith("•"):
                        cfg["analysts"][key]["api_key"] = ak
                    if a_cfg.get("base_url"):
                        cfg["analysts"][key]["base_url"] = a_cfg["base_url"]
                    if a_cfg.get("model"):
                        cfg["analysts"][key]["model"] = a_cfg["model"]
                    # 更新 name 和 emoji
                    if a_cfg.get("name"):
                        cfg["analysts"][key]["name"] = a_cfg["name"]
                    if a_cfg.get("emoji"):
                        cfg["analysts"][key]["emoji"] = a_cfg["emoji"]
                    if a_cfg.get("avatar_url"):
                        cfg["analysts"][key]["avatar_url"] = a_cfg["avatar_url"]

        # 更新裁决者配置
        if "judge" in req:
            j_cfg = req["judge"]
            ak = j_cfg.get("api_key", "")
            if ak and "****" not in ak and not ak.startswith("•"):
                cfg["judge"]["api_key"] = ak
            if j_cfg.get("base_url"):
                cfg["judge"]["base_url"] = j_cfg["base_url"]
            if j_cfg.get("model"):
                cfg["judge"]["model"] = j_cfg["model"]
            # 更新 name 和 emoji
            if j_cfg.get("name"):
                cfg["judge"]["name"] = j_cfg["name"]
            if j_cfg.get("emoji"):
                cfg["judge"]["emoji"] = j_cfg["emoji"]
            if j_cfg.get("avatar_url"):
                cfg["judge"]["avatar_url"] = j_cfg["avatar_url"]

        # 更新快速分析配置
        if "quick_analysis" in req:
            qa_cfg = req["quick_analysis"]
            ak = qa_cfg.get("api_key", "")
            if ak and "****" not in ak and not ak.startswith("•"):
                cfg["quick_analysis"]["api_key"] = ak
            if qa_cfg.get("base_url"):
                cfg["quick_analysis"]["base_url"] = qa_cfg["base_url"]
            if qa_cfg.get("model"):
                cfg["quick_analysis"]["model"] = qa_cfg["model"]
            if qa_cfg.get("name"):
                cfg["quick_analysis"]["name"] = qa_cfg["name"]
            if qa_cfg.get("role_desc"):
                cfg["quick_analysis"]["role_desc"] = qa_cfg["role_desc"]

        _update_cfg(cfg)
        return {"message": "AI 配置已保存"}
    finally:
        db.close()


@router.post("/ai/avatar")
async def upload_ai_avatar(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """上传AI分析师头像"""
    from app.database import SessionLocal
    from app.models import User
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == current_user["user_id"]).first()
        if not user or user.role != "admin":
            raise HTTPException(status_code=403, detail="仅管理员可操作")
        
        # 检查文件类型
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="只能上传图片文件")
        
        # 生成文件名
        ext = file.filename.split(".")[-1] if "." in file.filename else "png"
        filename = f"{uuid.uuid4().hex[:12]}.{ext}"
        filepath = AVATAR_DIR / filename
        
        # 保存文件
        AVATAR_DIR.mkdir(parents=True, exist_ok=True)
        with open(filepath, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        return {"url": f"/static/uploads/ai-avatars/{filename}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")
    finally:
        db.close()
