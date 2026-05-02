"""数据库初始化"""
from sqlalchemy import create_engine, text, inspect, event
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# ─── SQLite WAL 模式 ───
# WAL (Write-Ahead Logging) 允许读写并发，多策略线程同时写入时不阻塞读查询
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=5000")  # 等待锁最多5秒
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def migrate_tables():
    """自动为已有表添加缺失的列（SQLite 不支持 ALTER ADD IF NOT EXISTS）"""
    inspector = inspect(engine)
    migrations = {
        "strategies": {
            "position": "ALTER TABLE strategies ADD COLUMN position VARCHAR(10) DEFAULT 'none'",
        },
        "users": {
            "is_subordinate": "ALTER TABLE users ADD COLUMN is_subordinate BOOLEAN DEFAULT 0",
        },
    }
    for table_name, columns in migrations.items():
        if not inspector.has_table(table_name):
            continue
        existing = {col["name"] for col in inspector.get_columns(table_name)}
        for col_name, sql in columns.items():
            if col_name not in existing:
                try:
                    with engine.connect() as conn:
                        conn.execute(text(sql))
                        conn.commit()
                    print(f"[DB] Migrated: {table_name}.{col_name}")
                except Exception as e:
                    print(f"[DB] Migration skipped {table_name}.{col_name}: {e}")


def get_db():
    """依赖注入：获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
