"""用户 API 配置管理路由

每个用户可以管理自己的交易所 API 配置（CRUD）。
API 凭证使用 Fernet 加密存储在数据库中。
"""
import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.models import User, UserAPIConfig
from app.crud.user_api import CRUDUserAPIConfig
from app.services.crypto import encrypt, decrypt
from app.services.logger import sys_logger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/user-api", tags=["user-api"])

crud_user_api = CRUDUserAPIConfig()


# ─────────────────────────────────────────────────────────
# Pydantic 模型（请求/响应）
# ─────────────────────────────────────────────────────────

class APIConfigCreate(BaseModel):
    """创建 API 配置"""
    exchange: str = Field(default="okx", description="交易所: okx/binance/bybit")
    api_key: str = Field(..., min_length=1, description="API Key")
    api_secret: str = Field(..., min_length=1, description="API Secret")
    api_passphrase: Optional[str] = Field(default="", description="API Passphrase (OKX需要)")
    label: str = Field(default="默认配置", max_length=50, description="配置名称")
    is_sandbox: bool = Field(default=False, description="是否测试网")
    is_default: bool = Field(default=False, description="是否设为默认")


class APIConfigUpdate(BaseModel):
    """更新 API 配置"""
    label: Optional[str] = Field(default=None, max_length=50)
    api_key: Optional[str] = Field(default=None)
    api_secret: Optional[str] = Field(default=None)
    api_passphrase: Optional[str] = Field(default=None)
    is_sandbox: Optional[bool] = None
    is_active: Optional[bool] = None


class APIConfigResponse(BaseModel):
    """API 配置响应（不返回明文凭证）"""
    id: int
    exchange: str
    label: str
    is_sandbox: bool
    is_default: bool
    is_active: bool
    okx_uid: Optional[str] = None
    last_used: Optional[datetime] = None
    created_at: Optional[datetime] = None
    # 返回掩码后的 key（前4后4可见）
    api_key_masked: str = ""

    class Config:
        from_attributes = True

    @classmethod
    def from_model(cls, config: UserAPIConfig) -> dict:
        """从数据库模型生成响应（掩码敏感信息）"""
        key = ""
        try:
            key = decrypt(config.api_key_encrypted)
        except Exception:
            key = "***"

        masked = key[:4] + "****" + key[-4:] if len(key) > 8 else "****"

        return {
            "id": config.id,
            "exchange": config.exchange,
            "label": config.label,
            "is_sandbox": config.is_sandbox,
            "is_default": config.is_default,
            "is_active": config.is_active,
            "okx_uid": config.okx_uid,
            "last_used": config.last_used,
            "created_at": config.created_at,
            "api_key_masked": masked,
        }


# ─────────────────────────────────────────────────────────
# 接口实现
# ─────────────────────────────────────────────────────────

@router.get("/list")
async def list_configs(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户的所有 API 配置"""
    configs = crud_user_api.get_by_user(db, user_id=current_user["id"])
    return {
        "code": 0,
        "data": [APIConfigResponse.from_model(c) for c in configs],
    }


@router.post("/create")
async def create_config(
    body: APIConfigCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建新的 API 配置"""
    user_id = current_user["id"]

    # 检查配置数量限制（每用户最多5个）
    count = crud_user_api.count(db, user_id=user_id)
    if count >= 5:
        raise HTTPException(status_code=400, detail="每个用户最多配置5个API")

    # 如果设为默认，先清除同交易所的其他默认标记
    if body.is_default:
        existing = crud_user_api.get_by_user(db, user_id=user_id)
        for c in existing:
            if c.exchange == body.exchange and c.is_default:
                c.is_default = False
        db.commit()

    # 加密存储
    config = crud_user_api.create(db, obj_in={
        "user_id": user_id,
        "exchange": body.exchange,
        "api_key_encrypted": encrypt(body.api_key),
        "api_secret_encrypted": encrypt(body.api_secret),
        "api_passphrase_encrypted": encrypt(body.api_passphrase) if body.api_passphrase else "",
        "label": body.label,
        "is_sandbox": body.is_sandbox,
        "is_default": body.is_default,
    })

    sys_logger.info("user_api", f"User #{user_id} created API config: {config.exchange}/{config.label}")

    return {
        "code": 0,
        "message": "配置创建成功",
        "data": APIConfigResponse.from_model(config),
    }


@router.put("/update/{config_id}")
async def update_config(
    config_id: int,
    body: APIConfigUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新 API 配置（只更新传入的字段）"""
    user_id = current_user["id"]
    config = crud_user_api.get(db, config_id)

    if not config or config.user_id != user_id:
        raise HTTPException(status_code=404, detail="配置不存在")

    update_data = {}
    if body.label is not None:
        update_data["label"] = body.label
    if body.is_sandbox is not None:
        update_data["is_sandbox"] = body.is_sandbox
    if body.is_active is not None:
        update_data["is_active"] = body.is_active
    if body.api_key is not None:
        update_data["api_key_encrypted"] = encrypt(body.api_key)
    if body.api_secret is not None:
        update_data["api_secret_encrypted"] = encrypt(body.api_secret)
    if body.api_passphrase is not None:
        update_data["api_passphrase_encrypted"] = encrypt(body.api_passphrase)

    if update_data:
        config = crud_user_api.update(db, db_obj=config, obj_in=update_data)

    return {
        "code": 0,
        "message": "配置更新成功",
        "data": APIConfigResponse.from_model(config),
    }


@router.delete("/delete/{config_id}")
async def delete_config(
    config_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除 API 配置"""
    user_id = current_user["id"]
    config = crud_user_api.get(db, config_id)

    if not config or config.user_id != user_id:
        raise HTTPException(status_code=404, detail="配置不存在")

    crud_user_api.delete(db, id=config_id)
    sys_logger.info("user_api", f"User #{user_id} deleted API config #{config_id}")

    return {"code": 0, "message": "配置已删除"}


@router.put("/set-default/{config_id}")
async def set_default_config(
    config_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """设置某个配置为默认"""
    user_id = current_user["id"]
    config = crud_user_api.set_default(db, user_id=user_id, config_id=config_id)

    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")

    return {
        "code": 0,
        "message": f"已将「{config.label}」设为默认配置",
        "data": APIConfigResponse.from_model(config),
    }


@router.get("/default")
async def get_default_config(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户的默认 API 配置"""
    user_id = current_user["id"]
    config = crud_user_api.get_default(db, user_id=user_id)

    if not config:
        return {"code": 0, "data": None, "message": "暂无默认配置"}

    return {
        "code": 0,
        "data": APIConfigResponse.from_model(config),
    }


@router.post("/test/{config_id}")
async def test_config(
    config_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """测试 API 配置是否有效（尝试获取账户信息）"""
    import asyncio

    user_id = current_user["id"]
    config = crud_user_api.get(db, config_id)

    if not config or config.user_id != user_id:
        raise HTTPException(status_code=404, detail="配置不存在")

    # 解密凭证
    try:
        api_key = decrypt(config.api_key_encrypted)
        api_secret = decrypt(config.api_secret_encrypted)
        api_passphrase = decrypt(config.api_passphrase_encrypted) if config.api_passphrase_encrypted else ""
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"凭证解密失败: {e}")

    if config.exchange == "okx":
        return await _test_okx_connection(api_key, api_secret, api_passphrase, config.is_sandbox, config_id, db)
    else:
        raise HTTPException(status_code=400, detail=f"暂不支持测试 {config.exchange} 交易所")


async def _test_okx_connection(
    api_key: str,
    api_secret: str,
    api_passphrase: str,
    is_sandbox: bool,
    config_id: int,
    db: Session,
):
    """测试 OKX API 连接"""
    try:
        from app.services.okx_client import OKXClient

        # 创建临时客户端测试连接
        client = OKXClient(
            api_key=api_key,
            api_secret=api_secret,
            passphrase=api_passphrase,
            sandbox=is_sandbox,
        )

        # 在线程中执行同步请求
        import concurrent.futures
        loop = asyncio.get_event_loop()

        with concurrent.futures.ThreadPoolExecutor() as pool:
            result = await loop.run_in_executor(
                pool, client.request, "GET", "/api/v5/account/balance"
            )

        if result and result.get("code") == "0":
            data = result.get("data", [{}])[0]
            # 更新 UID
            uid = data.get("uid", "")
            if uid:
                config = crud_user_api.get(db, config_id)
                if config:
                    config.okx_uid = uid
                    config.last_used = datetime.utcnow()
                    db.commit()

            sys_logger.info("user_api", f"API config #{config_id} test OK, uid={uid}")
            return {
                "code": 0,
                "message": "连接成功",
                "data": {
                    "uid": uid,
                    "total_eq": data.get("totalEq", "0"),
                },
            }
        else:
            error_msg = result.get("msg", "未知错误") if result else "无响应"
            sys_logger.warn("user_api", f"API config #{config_id} test FAILED: {error_msg}")
            return {
                "code": 1,
                "message": f"连接失败: {error_msg}",
                "data": None,
            }

    except Exception as e:
        sys_logger.error("user_api", f"API config #{config_id} test error: {e}")
        return {
            "code": 1,
            "message": f"测试异常: {str(e)}",
            "data": None,
        }
