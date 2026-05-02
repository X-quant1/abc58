import sqlite3
import json

conn = sqlite3.connect('c:/LH/OKX/backend/data/btc_quant.db')
c = conn.cursor()

# 查看现有数据
c.execute("SELECT id, name, strategy_type, strategies FROM quant_robots")
rows = c.fetchall()
print(f"Found {len(rows)} robots:")
for row in rows:
    print(f"  ID={row[0]}, name={row[1]}, strategy_type={row[2]}, strategies={row[3]}")

# 迁移 strategy_type -> strategies
c.execute("SELECT id, strategy_type FROM quant_robots WHERE strategy_type IS NOT NULL AND strategy_type != ''")
for row in c.fetchall():
    robot_id, strategy_type = row
    if strategy_type:
        strategies_json = json.dumps([strategy_type])
        c.execute("UPDATE quant_robots SET strategies = ? WHERE id = ?", (strategies_json, robot_id))
        print(f"Updated robot {robot_id}: strategies = {strategies_json}")

conn.commit()

# 验证
c.execute("SELECT id, name, strategies FROM quant_robots")
print("\nUpdated data:")
for row in c.fetchall():
    print(f"  ID={row[0]}, name={row[1]}, strategies={row[2]}")

conn.close()
