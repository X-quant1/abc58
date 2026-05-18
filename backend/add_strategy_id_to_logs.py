"""迁移脚本：给 system_logs 表添加 strategy_id 列"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "quant.db")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 检查列是否已存在
cursor.execute("PRAGMA table_info(system_logs)")
columns = [col[1] for col in cursor.fetchall()]

if "strategy_id" not in columns:
    cursor.execute("ALTER TABLE system_logs ADD COLUMN strategy_id INTEGER")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_system_logs_strategy_id ON system_logs(strategy_id)")
    print("✅ strategy_id 列已添加")
else:
    print("ℹ️ strategy_id 列已存在，跳过")

conn.commit()
conn.close()
