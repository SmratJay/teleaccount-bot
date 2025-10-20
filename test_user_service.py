"""Test if UserService now returns real data from database"""
import sys
sys.path.insert(0, 'd:/teleaccount_bot')

from database import get_db_session, close_db_session
from database.operations import UserService

db = get_db_session()
try:
    print("Testing UserService.get_user_by_telegram_id()")
    print("=" * 60)
    
    # Test with your telegram ID
    user = UserService.get_user_by_telegram_id(db, 6733908384)
    
    if user:
        print(f"✅ User found!")
        print(f"  Telegram ID: {user.telegram_user_id}")
        print(f"  Username: {user.username}")
        print(f"  Balance: ${user.balance}")
        
        # Check if attributes exist
        if hasattr(user, 'is_admin'):
            print(f"  Is Admin: {user.is_admin} {'✅ YES' if user.is_admin else '❌ NO'}")
        else:
            print(f"  Is Admin: ❌ ATTRIBUTE MISSING!")
            
        if hasattr(user, 'is_leader'):
            print(f"  Is Leader: {user.is_leader} {'✅ YES' if user.is_leader else '❌ NO'}")
        else:
            print(f"  Is Leader: ❌ ATTRIBUTE MISSING!")
            
        if hasattr(user, 'status'):
            print(f"  Status: {user.status}")
        else:
            print(f"  Status: ❌ ATTRIBUTE MISSING!")
    else:
        print("❌ User not found!")
        
finally:
    close_db_session(db)

