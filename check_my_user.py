import sqlite3

conn = sqlite3.connect('teleaccount_bot.db')
cursor = conn.cursor()

# Check user by telegram_user_id
print("=" * 60)
print("CHECKING USER: @popexenon (ID: 6733908384)")
print("=" * 60)

cursor.execute("""
    SELECT telegram_user_id, username, is_admin, is_leader, balance, status 
    FROM users 
    WHERE telegram_user_id = 6733908384
""")
result = cursor.fetchone()

if result:
    print("\n✅ USER FOUND IN DATABASE:")
    print(f"  Telegram ID: {result[0]}")
    print(f"  Username: {result[1]}")
    print(f"  Is Admin: {result[2]} {'✅ YES' if result[2] else '❌ NO'}")
    print(f"  Is Leader: {result[3]} {'✅ YES' if result[3] else '❌ NO'}")
    print(f"  Balance: ${result[4]}")
    print(f"  Status: {result[5]}")
else:
    print("\n❌ USER NOT FOUND!")
    print("  This could be why you can't see the admin menu.")

# Check all users in the database
print("\n" + "=" * 60)
print("ALL USERS IN DATABASE:")
print("=" * 60)
cursor.execute("SELECT telegram_user_id, username, is_admin, is_leader FROM users")
all_users = cursor.fetchall()
if all_users:
    for user in all_users:
        admin_badge = "👑 ADMIN" if user[2] else ""
        leader_badge = "⭐ LEADER" if user[3] else ""
        print(f"  ID: {user[0]}, Username: {user[1]}, {admin_badge} {leader_badge}")
else:
    print("  No users found in database!")

conn.close()
