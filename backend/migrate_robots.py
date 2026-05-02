"""迁移脚本：更新 quant_robots 表结构，添加 robot_trades 表"""
import sqlite3
import json
import os

DB_PATH = "c:/LH/OKX/backend/data.db"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. 检查并添加 strategies 列
    cursor.execute("PRAGMA table_info(quant_robots)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'strategies' not in columns:
        print("添加 strategies 列...")
        cursor.execute("ALTER TABLE quant_robots ADD COLUMN strategies TEXT DEFAULT '[]'")
        # 迁移旧数据
        if 'strategy_type' in columns:
            cursor.execute("SELECT id, strategy_type FROM quant_robots WHERE strategy_type IS NOT NULL AND strategy_type != ''")
            for row in cursor.fetchall():
                robot_id, strategy_type = row
                strategies_json = json.dumps([strategy_type]) if strategy_type else '[]'
                cursor.execute("UPDATE quant_robots SET strategies = ? WHERE id = ?", (strategies_json, robot_id))
        print("strategies 列添加完成")

    # 2. 删除旧的 strategy_type 和 strategy_params 列（SQLite 不支持 DROP COLUMN，保留但不使用）

    # 3. 创建 robot_trades 表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS robot_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            robot_id INTEGER NOT NULL,
            strategy_type VARCHAR(30) NOT NULL,
            side VARCHAR(10) NOT NULL,
            entry_price REAL NOT NULL,
            exit_price REAL,
            size REAL DEFAULT 1.0,
            pnl REAL DEFAULT 0,
            status VARCHAR(20) DEFAULT 'open',
            opened_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            closed_at DATETIME,
            FOREIGN KEY (robot_id) REFERENCES quant_robots(id)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_robot_trades_robot_id ON robot_trades(robot_id)")
    print("robot_trades 表创建完成")

    conn.commit()
    conn.close()
    print("迁移完成！")

if __name__ == "__main__":
    migrate()
