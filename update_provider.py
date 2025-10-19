import sqlite3

conn = sqlite3.connect('teleaccount_bot.db')
cursor = conn.cursor()
cursor.execute("UPDATE proxy_pool SET provider = 'webshare'")
updated = cursor.rowcount
conn.commit()
conn.close()
print(f'Updated {updated} proxies to webshare provider')
