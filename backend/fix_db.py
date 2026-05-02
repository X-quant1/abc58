import sqlite3
conn = sqlite3.connect('c:/LH/OKX/backend/data/btc_quant.db')
c = conn.cursor()

# 列出所有表
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in c.fetchall()]
print(f'Tables: {tables}')

# 查看 quant_robots 表结构
c.execute('PRAGMA table_info(quant_robots)')
cols = [col[1] for col in c.fetchall()]
print(f'quant_robots columns: {cols}')

# 添加 strategies 列（如果不存在）
if 'strategies' not in cols:
    try:
        c.execute("ALTER TABLE quant_robots ADD COLUMN strategies TEXT DEFAULT '[]'")
        conn.commit()
        print('Added strategies column')
    except Exception as e:
        print(f'Error adding column: {e}')
else:
    print('strategies column already exists')

# 创建 robot_trades 表
c.execute('''CREATE TABLE IF NOT EXISTS robot_trades (
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
)''')
c.execute('CREATE INDEX IF NOT EXISTS ix_robot_trades_robot_id ON robot_trades(robot_id)')
conn.commit()
print('Created robot_trades table')

# 验证
c.execute('PRAGMA table_info(quant_robots)')
print(f'Updated columns: {[col[1] for col in c.fetchall()]}')

conn.close()
