import sqlite3
import json

conn = sqlite3.connect(r'c:\LH\OKX\backend\data\btc_quant.db')
cursor = conn.cursor()

# 查询最近的策略日志
cursor.execute("""
    SELECT created_at, level, module, message, detail
    FROM system_logs
    WHERE module = 'strategy' AND message LIKE '%callback%'
    ORDER BY created_at DESC
    LIMIT 20
""")

rows = cursor.fetchall()
print(f"Found {len(rows)} log entries:\n")
for row in rows:
    created_at, level, module, message, detail = row
    print(f"[{created_at}] [{level}] {message}")
    if detail:
        try:
            detail_obj = json.loads(detail)
            print(f"  Detail: {json.dumps(detail_obj, indent=2)}")
        except:
            print(f"  Detail: {detail}")
    print()

conn.close()
