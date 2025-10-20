"""Script to set admin and leader privileges for a user."""
from database import get_db_session
from database.models_old import User

def set_admin_privileges(telegram_user_id: int):
    """Set admin and leader privileges for a user."""
    db = get_db_session()
    
    try:
        # Query user from database
        user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
        
        if not user:
            print(f"❌ User {telegram_user_id} not found in database!")
            print("   User needs to start the bot with /start first.")
            return False
        
        # Update privileges
        user.is_admin = True
        user.is_leader = True
        db.commit()
        
        print(f"\n✅ Successfully updated user {telegram_user_id}:")
        print(f"   Username: @{user.username if user.username else 'N/A'}")
        print(f"   Name: {user.first_name} {user.last_name if user.last_name else ''}")
        print(f"   Is Admin: ✅ YES")
        print(f"   Is Leader: ✅ YES\n")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def list_all_users():
    """List all users in the database."""
    db = get_db_session()
    
    try:
        # Query all users from database
        users = db.query(User).all()
        
        if not users:
            print("❌ No users found in database!")
            return
            
        print(f"\n{'='*70}")
        print(f"USERS IN DATABASE ({len(users)} total)")
        print(f"{'='*70}\n")
        
        for user in users:
            print(f"Telegram ID: {user.telegram_user_id}")
            print(f"Username: @{user.username if user.username else 'N/A'}")
            print(f"Name: {user.first_name} {user.last_name if user.last_name else ''}")
            print(f"Is Admin: {'✅ YES' if user.is_admin else '❌ NO'}")
            print(f"Is Leader: {'✅ YES' if user.is_leader else '❌ NO'}")
            print(f"Balance: ${user.balance}")
            print(f"Verified: {'✅ YES' if user.verification_completed else '❌ NO'}")
            print(f"{'-'*70}\n")
            
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    
    print("\n🔧 USER ADMIN MANAGEMENT SCRIPT\n")
    
    if len(sys.argv) > 1:
        # Set admin for specific user
        try:
            user_id = int(sys.argv[1])
            set_admin_privileges(user_id)
        except ValueError:
            print("❌ Invalid user ID. Must be a number.")
    else:
        # List all users
        list_all_users()
        print("\n💡 To set admin privileges, run: python manage_admin.py <telegram_user_id>")
        print("   Example: python manage_admin.py 6733908384\n")
