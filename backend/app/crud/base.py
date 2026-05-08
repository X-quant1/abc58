"""CRUD 基础类

提供通用的数据库操作方法，子类可继承扩展
"""
from typing import TypeVar, Generic, Type, List, Optional, Any
from sqlalchemy.orm import Session
from app.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class CRUDBase(Generic[ModelType]):
    """CRUD 基础类，提供通用数据库操作"""
    
    def __init__(self, model: Type[ModelType]):
        """
        Args:
            model: SQLAlchemy 模型类
        """
        self.model = model
    
    def get(self, db: Session, id: int) -> Optional[ModelType]:
        """根据 ID 获取单条记录"""
        return db.query(self.model).filter(self.model.id == id).first()
    
    def get_multi(
        self, 
        db: Session, 
        *, 
        skip: int = 0, 
        limit: int = 100,
        **filters
    ) -> List[ModelType]:
        """获取多条记录，支持分页和过滤"""
        query = db.query(self.model)
        for key, value in filters.items():
            if hasattr(self.model, key) and value is not None:
                query = query.filter(getattr(self.model, key) == value)
        return query.offset(skip).limit(limit).all()
    
    def create(self, db: Session, *, obj_in: dict) -> ModelType:
        """创建记录"""
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update(
        self, 
        db: Session, 
        *, 
        db_obj: ModelType, 
        obj_in: dict
    ) -> ModelType:
        """更新记录"""
        for key, value in obj_in.items():
            if hasattr(db_obj, key):
                setattr(db_obj, key, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def delete(self, db: Session, *, id: int) -> bool:
        """删除记录"""
        obj = self.get(db, id)
        if obj:
            db.delete(obj)
            db.commit()
            return True
        return False
    
    def count(self, db: Session, **filters) -> int:
        """统计记录数"""
        query = db.query(self.model)
        for key, value in filters.items():
            if hasattr(self.model, key) and value is not None:
                query = query.filter(getattr(self.model, key) == value)
        return query.count()
    
    def exists(self, db: Session, **filters) -> bool:
        """检查记录是否存在"""
        return self.count(db, **filters) > 0
