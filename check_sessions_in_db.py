import sqlite3

conn = sqlite3.connect('teleaccount_bot.db')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("Tables in database:")
for table in tables:
    print(f"  - {table[0]}")

# Check telegram_accounts table for session data
print("\nChecking telegram_accounts table...")
cursor.execute("PRAGMA table_info(telegram_accounts)")
columns = cursor.fetchall()
print("\nColumns in telegram_accounts:")
for col in columns:
    print(f"  - {col[1]} ({col[2]})")

# Check if there are any accounts in the database
cursor.execute("SELECT COUNT(*) FROM telegram_accounts")
count = cursor.fetchone()[0]
print(f"\nTotal accounts in database: {count}")

if count > 0:
    cursor.execute("SELECT id, phone_number, status, session_string FROM telegram_accounts LIMIT 5")
    accounts = cursor.fetchall()
    print("\nSample accounts:")
    for acc in accounts:
        has_session = "YES" if acc[3] else "NO"
        print(f"  ID: {acc[0]}, Phone: {acc[1]}, Status: {acc[2]}, Session: {has_session}")

conn.close()

