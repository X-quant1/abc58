import sqlite3
conn = sqlite3.connect('c:/LH/OKX/backend/data.db')
c = conn.cursor()

# 列出所有表
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in c.fetchall()]
print(f'Tables in database: {tables}')

conn.close()
