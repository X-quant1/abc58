import sqlite3
conn = sqlite3.connect('c:/LH/OKX/backend/data/btc_quant.db')
cursor = conn.cursor()

# 检查是否有 avatar 列
cols = cursor.execute("PRAGMA table_info(users)").fetchall()
print("Current columns:", [c[1] for c in cols])

# 添加 avatar 列
if 'avatar' not in [c[1] for c in cols]:
    cursor.execute('ALTER TABLE users ADD COLUMN avatar VARCHAR(200) DEFAULT ""')
    conn.commit()
    print("Added avatar column")
else:
    print("avatar already exists")

# 重置 admin 密码
import sys
sys.path.insert(0, 'c:/LH/OKX/backend')
from app.auth import hash_password
cursor.execute("UPDATE users SET password_hash = ? WHERE username = 'admin'", (hash_password('btc2026'),))
conn.commit()
print("Admin password reset to: btc2026")

conn.close()
