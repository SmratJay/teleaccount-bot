import sqlite3

conn = sqlite3.connect('teleaccount_bot.db')
cursor = conn.cursor()

cursor.execute('SELECT id, username, password FROM proxy_pool LIMIT 5')
for row in cursor.fetchall():
    has_pwd = 'YES' if row[2] else 'NO'
    pwd_len = len(row[2]) if row[2] else 0
    print(f"ID {row[0]}: Username={row[1]}, HasPassword={has_pwd}, Length={pwd_len}")

conn.close()
