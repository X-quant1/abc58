import sqlite3
for db_path in ['c:/LH/OKX/backend/btc_quant.db', 'c:/LH/OKX/backend/data/btc_quant.db', 'c:/LH/OKX/backend/app/data/btc_quant.db']:
    try:
        conn = sqlite3.connect(db_path)
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        print(f"{db_path}: {tables}")
        conn.close()
    except Exception as e:
        print(f"{db_path}: ERROR - {e}")
