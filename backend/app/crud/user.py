"""用户相关 CRUD 操作"""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models import User


class CRUDUser(CRUDBase[User]):
    """用户 CRUD 操作"""
    
    def __init__(self):
        super().__init__(User)
    
    def get_by_username(self, db: Session, *, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        return db.query(User).filter(User.username == username).first()
    
    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        return db.query(User).filter(User.email == email).first()
    
    def get_by_okx_uid(self, db: Session, *, okx_uid: str) -> Optional[User]:
        """根据 OKX UID 获取用户"""
        return db.query(User).filter(User.okx_uid == okx_uid).first()
    
    def get_admins(self, db: Session) -> List[User]:
        """获取所有管理员"""
        return db.query(User).filter(User.role == "admin").all()
    
    def get_active_users(self, db: Session) -> List[User]:
        """获取所有活跃用户"""
        return db.query(User).filter(User.active == True).all()
    
    def set_role(self, db: Session, *, user_id: int, role: str) -> Optional[User]:
        """设置用户角色"""
        user = self.get(db, user_id)
        if user:
            user.role = role
            db.commit()
            db.refresh(user)
        return user
    
    def update_last_login(self, db: Session, *, user_id: int) -> Optional[User]:
        """更新最后登录时间"""
        from datetime import datetime
        user = self.get(db, user_id)
        if user:
            user.last_login = datetime.utcnow()
            db.commit()
            db.refresh(user)
        return user
    
    def authenticate(self, db: Session, *, username: str, password: str) -> Optional[User]:
        """验证用户登录"""
        from app.auth import verify_password
        user = self.get_by_username(db, username=username)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user
