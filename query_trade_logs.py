import sqlite3
import json

conn = sqlite3.connect(r'c:\LH\OKX\backend\data\btc_quant.db')
cursor = conn.cursor()

# 查询最近的trade日志
cursor.execute("""
    SELECT created_at, level, module, message
    FROM system_logs
    WHERE module = 'trade' OR (module = 'strategy' AND message LIKE '%leverage%')
    ORDER BY created_at DESC
    LIMIT 20
""")

rows = cursor.fetchall()
print(f"Found {len(rows)} log entries:\n")
for row in rows:
    created_at, level, module, message = row
    print(f"[{created_at}] [{level}] [{module}] {message}")

conn.close()
