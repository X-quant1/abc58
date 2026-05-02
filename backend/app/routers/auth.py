"""认证路由 — 注册 / 登录 / 验证码 / 重置密码 / 用户信息"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User
from app.auth import hash_password, verify_password, create_token, decode_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── 请求模型 ───

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_]+$",
                          description="用户名(字母/数字/下划线)")
    password: str = Field(..., min_length=6, max_length=50, description="密码(至少6位)")
    nickname: str | None = Field(None, max_length=30, description="昵称")
    email: str = Field(..., max_length=120, description="邮箱")
    code: str = Field(..., min_length=6, max_length=6, description="邮箱验证码")


class LoginRequest(BaseModel):
    email: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")


class LoginByCodeRequest(BaseModel):
    email: str = Field(..., description="邮箱")
    code: str = Field(..., min_length=6, max_length=6, description="6位验证码")


class SendCodeRequest(BaseModel):
    email: str = Field(..., description="邮箱地址")
    purpose: str = Field(..., description="用途: login/register/reset")


class ResetPasswordRequest(BaseModel):
    email: str = Field(..., description="邮箱")
    code: str = Field(..., min_length=6, max_length=6, description="验证码")
    new_password: str = Field(..., min_length=6, max_length=50, description="新密码")


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=50, description="新密码(至少6位)")


# ─── 内存验证码存储 ───
_code_store: dict[str, dict] = {}  # { "email:purpose": { code, expire_at, sent_at } }
_code_rate_limit: dict[str, float] = {}  # { "email": last_send_timestamp }


def _generate_code() -> str:
    """生成6位数字验证码"""
    import random
    return f"{random.randint(100000, 999999)}"


def _check_code(email: str, purpose: str, code: str) -> bool:
    """校验验证码"""
    import time
    key = f"{email}:{purpose}"
    entry = _code_store.get(key)
    if not entry:
        return False
    if time.time() > entry["expire_at"]:
        _code_store.pop(key, None)
        return False
    return entry["code"] == code


def _check_rate_limit(email: str) -> bool:
    """检查发送频率限制（同一邮箱60秒内只能发一次）"""
    import time
    last = _code_rate_limit.get(email, 0)
    if time.time() - last < 60:
        return False
    return True


# ─── 路由 ───

@router.post("/send-code")
def send_code(req: SendCodeRequest, db: Session = Depends(get_db)):
    """
    发送邮箱验证码

    purpose: login(登录) / register(注册) / reset(重置密码)
    """
    import time

    email = req.email.strip().lower()
    purpose = req.purpose

    # 校验 purpose
    if purpose not in ("login", "register", "reset"):
        raise HTTPException(status_code=400, detail="无效的验证码用途")

    # 频率限制：同一邮箱60秒内只能发一次
    if not _check_rate_limit(email):
        raise HTTPException(status_code=429, detail="发送太频繁，请60秒后再试")

    # 业务校验
    if purpose == "register":
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            raise HTTPException(status_code=409, detail="该邮箱已被注册")
    elif purpose in ("login", "reset"):
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="该邮箱未注册")

    # 生成验证码并存入内存（5分钟有效）
    code = _generate_code()
    _code_store[f"{email}:{purpose}"] = {
        "code": code,
        "expire_at": time.time() + 300,
        "sent_at": time.time(),
    }
    _code_rate_limit[email] = time.time()

    # 通过 SMTP 发送验证码邮件
    from app.services.notification import send_verification_email
    result = send_verification_email(email, code, purpose)

    if not result["success"]:
        # 邮件发送失败时回滚内存存储
        _code_store.pop(f"{email}:{purpose}", None)
        _code_rate_limit.pop(email, None)
        raise HTTPException(status_code=500, detail=result["message"])

    return {"message": "验证码已发送"}


@router.post("/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """用户注册"""
    email = req.email.strip().lower()

    # 校验验证码
    if not _check_code(email, "register", req.code):
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    # 检查用户名是否已存在
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(status_code=409, detail="用户名已存在")

    # 检查邮箱是否已注册
    existing_email = db.query(User).filter(User.email == email).first()
    if existing_email:
        raise HTTPException(status_code=409, detail="该邮箱已被注册")

    # 创建用户（随机分配头像）
    import random
    random_avatar = f"/avatars/{random.randint(1, 9)}.jpg"
    user = User(
        username=req.username,
        email=email,
        password_hash=hash_password(req.password),
        nickname=req.nickname or req.username,
        avatar=random_avatar,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 清掉已用验证码
    _code_store.pop(f"{email}:register", None)

    # 自动签发 token
    token = create_token(user.id, user.username)
    return {
        "message": "注册成功",
        "access_token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "nickname": user.nickname or user.username,
            "email": user.email,
            "avatar": user.avatar,
            "role": user.role,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
    }


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """用户登录(支持用户名或邮箱)"""
    # 先按用户名查，再按邮箱查
    user = db.query(User).filter(User.username == req.email).first()
    if not user and "@" in req.email:
        user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="账号或密码错误")
    if not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="账号或密码错误")
    if not user.active:
        raise HTTPException(status_code=403, detail="账户已被禁用")

    # 更新最后登录时间
    user.last_login = datetime.now(timezone.utc)
    db.commit()

    token = create_token(user.id, user.username)
    return {
        "message": "登录成功",
        "access_token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "nickname": user.nickname or user.username,
            "email": user.email,
            "avatar": user.avatar or "",
            "role": user.role,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
    }


@router.post("/login-by-code")
def login_by_code(req: LoginByCodeRequest, db: Session = Depends(get_db)):
    """邮箱验证码登录"""
    email = req.email.strip().lower()
    if not _check_code(email, "login", req.code):
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="该邮箱未注册")
    if not user.active:
        raise HTTPException(status_code=403, detail="账户已被禁用")

    user.last_login = datetime.now(timezone.utc)
    db.commit()

    # 验证码登录成功后清掉该验证码
    _code_store.pop(f"{email}:login", None)

    token = create_token(user.id, user.username)
    return {
        "message": "登录成功",
        "access_token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "nickname": user.nickname or user.username,
            "email": user.email,
            "avatar": user.avatar or "",
            "role": user.role,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
    }


@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    """通过邮箱验证码重置密码"""
    email = req.email.strip().lower()
    if not _check_code(email, "reset", req.code):
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="该邮箱未注册")

    user.password_hash = hash_password(req.new_password)
    db.commit()

    # 清掉验证码
    _code_store.pop(f"{email}:reset", None)

    return {"message": "密码重置成功，请重新登录"}


@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == current_user["user_id"]).first()
        if not user:
            raise HTTPException(status_code=401, detail="用户不存在")
        return {
            "id": user.id,
            "username": user.username,
            "nickname": user.nickname,
            "email": user.email,
            "role": user.role,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }
    finally:
        db.close()


@router.post("/change-password")
def change_password(
    req: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改密码"""
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    if not verify_password(req.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="旧密码错误")

    user.password_hash = hash_password(req.new_password)
    db.commit()
    return {"message": "密码修改成功"}


class UpdateProfileRequest(BaseModel):
    nickname: str | None = Field(None, max_length=30, description="昵称")
    avatar: str | None = Field(None, max_length=200, description="头像路径")


@router.put("/profile")
def update_profile(
    req: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新个人资料（昵称、头像）"""
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")

    if req.nickname is not None:
        user.nickname = req.nickname
    if req.avatar is not None:
        user.avatar = req.avatar

    db.commit()
    return {"message": "资料已更新", "nickname": user.nickname, "avatar": user.avatar}
