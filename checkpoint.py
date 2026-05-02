import sqlite3
conn = sqlite3.connect('c:/LH/OKX/backend/data/btc_quant.db')
cursor = conn.cursor()
cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
print("Checkpoint done:", cursor.fetchone())
conn.close()
