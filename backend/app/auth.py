"""JWT 认证与密码哈希工具"""
import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.config import JWT_SECRET, JWT_ALGORITHM

security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """ bcrypt 哈希密码 """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """ 验证密码 """
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_token(user_id: int, username: str, expires_hours: int = 72) -> str:
    """ 签发 JWT (默认 72 小时过期) """
    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=expires_hours),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """ 解码 JWT，过期则抛异常 """
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    """ FastAPI 依赖注入：从 Authorization header 解析当前用户

    Returns:
        {"user_id": int, "username": str, "role": str}

    Raises:
        HTTPException 401: 无 token / token 无效 / token 过期
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="未登录，请先登录")

    try:
        payload = decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效的登录凭证")

    user_id = int(payload["sub"])
    username = payload["username"]

    # 从数据库查询用户角色
    from app.models import User
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        role = user.role if user else "user"
    finally:
        db.close()

    return {
        "user_id": user_id,
        "username": username,
        "role": role,
    }


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict | None:
    """可选的用户获取（不强制登录），用于区分 admin 和普通用户"""
    if not credentials or not credentials.credentials:
        return None
    try:
        payload = decode_token(credentials.credentials)
        return {
            "user_id": int(payload["sub"]),
            "username": payload["username"],
        }
    except:
        return None
