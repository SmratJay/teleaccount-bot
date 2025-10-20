"""Check actual schema of users table"""
import sqlite3

conn = sqlite3.connect('teleaccount_bot.db')
cursor = conn.cursor()

# Get table schema
cursor.execute("PRAGMA table_info(users)")
columns = cursor.fetchall()

print("=" * 60)
print("USERS TABLE SCHEMA:")
print("=" * 60)
for col in columns:
    col_id, name, col_type, not_null, default_val, pk = col
    print(f"  {name:<20} {col_type:<15} {'NOT NULL' if not_null else 'NULL':<10} {'PK' if pk else ''}")

conn.close()

