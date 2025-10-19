"""Script to check admin status in database."""
from database import SessionLocal
from database.models import User

session = SessionLocal()
user = session.query(User).filter(User.telegram_user_id == 6733908384).first()

if user:
    print(f"✅ User Found!")
    print(f"   User ID: {user.telegram_user_id}")
    print(f"   Username: {user.username}")
    print(f"   Is Admin: {user.is_admin}")
    print(f"   Is Leader: {user.is_leader}")
    print(f"   Verification Completed: {user.verification_completed}")
    print(f"   Language: {user.language_code}")
else:
    print("❌ User not found in database!")
    print("   Your user ID (6733908384) doesn't exist in the database yet.")
    print("   You need to start the bot with /start first to create your user record.")

session.close()
