"""添加策略实例表"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "btc_quant.db")

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 检查表是否已存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='strategy_instances'")
    if cursor.fetchone():
        print("strategy_instances 表已存在，跳过迁移")
        conn.close()
        return

    # 创建策略实例表
    cursor.execute("""
        CREATE TABLE strategy_instances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_id INTEGER NOT NULL,
            user_id INTEGER,
            name VARCHAR(50) NOT NULL,
            params TEXT NOT NULL,
            enabled BOOLEAN DEFAULT 0,
            position VARCHAR(10) DEFAULT 'none',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (strategy_id) REFERENCES strategies(id)
        )
    """)

    # 给strategies表添加is_official字段（如果不存在）
    cursor.execute("PRAGMA table_info(strategies)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'is_official' not in columns:
        cursor.execute("ALTER TABLE strategies ADD COLUMN is_official BOOLEAN DEFAULT 1")
        print("已添加 is_official 字段到 strategies 表")

    conn.commit()
    print("✅ 迁移完成：strategy_instances 表已创建")

    # 显示表结构
    cursor.execute("PRAGMA table_info(strategy_instances)")
    print("\nstrategy_instances 表结构:")
    for col in cursor.fetchall():
        print(f"  {col[1]}: {col[2]}")

    conn.close()

if __name__ == "__main__":
    migrate()
