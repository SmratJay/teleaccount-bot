"""Script to list all users and check admin status."""
from database import get_db_session
from sqlalchemy import select
from database.models import User

db = get_db_session()

try:
    # Get all users
    stmt = select(User)
    users = db.execute(stmt).scalars().all()
    
    if users:
        print(f"\n✅ Found {len(users)} user(s) in database:\n")
        for user in users:
            print(f"{'='*60}")
            print(f"Telegram ID: {user.telegram_user_id}")
            print(f"Username: @{user.username if user.username else 'N/A'}")
            print(f"Name: {user.first_name} {user.last_name if user.last_name else ''}")
            print(f"Is Admin: {'✅ YES' if user.is_admin else '❌ NO'}")
            print(f"Is Leader: {'✅ YES' if user.is_leader else '❌ NO'}")
            print(f"Verification: {'✅ Completed' if user.verification_completed else '⏳ Pending'}")
            print(f"Balance: ${user.balance}")
            print()
    else:
        print("❌ No users found in database!")
        
finally:
    db.close()
