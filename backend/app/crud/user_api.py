"""用户 API 配置 CRUD 操作"""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models import UserAPIConfig


class CRUDUserAPIConfig(CRUDBase[UserAPIConfig]):
    """用户 API 配置 CRUD 操作"""
    
    def __init__(self):
        super().__init__(UserAPIConfig)
    
    def get_by_user(
        self, 
        db: Session, 
        *, 
        user_id: int
    ) -> List[UserAPIConfig]:
        """获取用户的所有 API 配置"""
        return db.query(UserAPIConfig).filter(
            UserAPIConfig.user_id == user_id
        ).order_by(UserAPIConfig.is_default.desc()).all()
    
    def get_default(
        self, 
        db: Session, 
        *, 
        user_id: int,
        exchange: str = "okx"
    ) -> Optional[UserAPIConfig]:
        """获取用户的默认 API 配置"""
        return db.query(UserAPIConfig).filter(
            UserAPIConfig.user_id == user_id,
            UserAPIConfig.exchange == exchange,
            UserAPIConfig.is_default == True,
            UserAPIConfig.is_active == True
        ).first()
    
    def get_active(
        self,
        db: Session,
        *,
        user_id: int
    ) -> List[UserAPIConfig]:
        """获取用户的所有活跃配置"""
        return db.query(UserAPIConfig).filter(
            UserAPIConfig.user_id == user_id,
            UserAPIConfig.is_active == True
        ).all()
    
    def set_default(
        self, 
        db: Session, 
        *, 
        user_id: int, 
        config_id: int
    ) -> Optional[UserAPIConfig]:
        """设置默认配置（会清除其他默认标记）"""
        # 先清除该用户该交易所的所有默认标记
        config = self.get(db, config_id)
        if not config or config.user_id != user_id:
            return None
        
        db.query(UserAPIConfig).filter(
            UserAPIConfig.user_id == user_id,
            UserAPIConfig.exchange == config.exchange
        ).update({"is_default": False})
        
        # 设置新的默认
        config.is_default = True
        db.commit()
        db.refresh(config)
        return config
    
    def create_config(
        self,
        db: Session,
        *,
        user_id: int,
        exchange: str,
        api_key_encrypted: str,
        api_secret_encrypted: str,
        api_passphrase_encrypted: str = None,
        label: str = "默认配置",
        is_sandbox: bool = False,
        is_default: bool = False,
        okx_uid: str = None
    ) -> UserAPIConfig:
        """创建 API 配置"""
        # 如果设为默认，先清除其他默认
        if is_default:
            db.query(UserAPIConfig).filter(
                UserAPIConfig.user_id == user_id,
                UserAPIConfig.exchange == exchange
            ).update({"is_default": False})
        
        return self.create(db, obj_in={
            "user_id": user_id,
            "exchange": exchange,
            "api_key_encrypted": api_key_encrypted,
            "api_secret_encrypted": api_secret_encrypted,
            "api_passphrase_encrypted": api_passphrase_encrypted,
            "label": label,
            "is_sandbox": is_sandbox,
            "is_default": is_default,
            "okx_uid": okx_uid,
        })
    
    def update_last_used(
        self, 
        db: Session, 
        *, 
        config_id: int
    ) -> Optional[UserAPIConfig]:
        """更新最后使用时间"""
        from datetime import datetime
        config = self.get(db, config_id)
        if config:
            config.last_used = datetime.utcnow()
            db.commit()
            db.refresh(config)
        return config
    
    def delete_by_user(
        self,
        db: Session,
        *,
        user_id: int,
        config_id: int
    ) -> bool:
        """删除用户的 API 配置"""
        config = self.get(db, config_id)
        if config and config.user_id == user_id:
            db.delete(config)
            db.commit()
            return True
        return False
