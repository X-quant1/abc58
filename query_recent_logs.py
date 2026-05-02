import sqlite3
import json

conn = sqlite3.connect(r'c:\LH\OKX\backend\data\btc_quant.db')
cursor = conn.cursor()

# 查询最近的策略日志（包含detail）
cursor.execute("""
    SELECT created_at, level, module, message, detail
    FROM system_logs
    WHERE module = 'strategy'
    ORDER BY created_at DESC
    LIMIT 10
""")

rows = cursor.fetchall()
print(f"Found {len(rows)} log entries:\n")
for row in rows:
    created_at, level, module, message, detail = row
    print(f"[{created_at}] [{level}] {message}")
    if detail:
        print(f"  Detail: {detail}")
    print()

conn.close()
