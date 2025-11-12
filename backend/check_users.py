"""Check users in database"""
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'bloodbank.db')

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.execute('SELECT * FROM users')
rows = cur.fetchall()
print(f'Total users in database: {len(rows)}')
for row in rows:
    print(f'User {row["id"]}: {row["name"]} ({row["email"]}) - Contact: {row["contact"]}, Blood Group: {row["blood_group"]}')
conn.close()

