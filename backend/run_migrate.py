import sqlite3
conn = sqlite3.connect('c:/LH/OKX/backend/data.db')
c = conn.cursor()

# 添加 strategies 列
try:
    c.execute("ALTER TABLE quant_robots ADD COLUMN strategies TEXT DEFAULT '[]'")
    conn.commit()
    print('Added strategies column')
except Exception as e:
    print(f'Error or column exists: {e}')

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
cols = [col[1] for col in c.fetchall()]
print(f'quant_robots columns: {cols}')

conn.close()
