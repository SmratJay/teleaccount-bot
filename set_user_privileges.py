#!/usr/bin/env python3
"""
Set user privileges for @popexenon (user ID: 6733908384)
"""
import os
import sys
sys.path.append('.')

from database import get_db_session, close_db_session
from database.models import User, UserStatus

def set_user_privileges():
    """Set admin and leader privileges for the specified user."""
    user_id = 6733908384  # @popexenon
    
    db = get_db_session()
    try:
        # Find or create user
        user = db.query(User).filter(User.telegram_user_id == user_id).first()
        
        if not user:
            print(f"Creating new user record for {user_id}")
            user = User(
                telegram_user_id=user_id,
                username="popexenon",
                first_name="Admin",
                is_admin=True,
                is_leader=True,
                status=UserStatus.ACTIVE,
                verification_completed=True,
                captcha_completed=True,
                channels_joined=True
            )
            db.add(user)
        else:
            print(f"Updating existing user {user_id}")
            user.is_admin = True
            user.is_leader = True
            user.status = UserStatus.ACTIVE
            user.verification_completed = True
            user.captcha_completed = True
            user.channels_joined = True
            
        db.commit()
        
        print(f"✅ User {user_id} (@popexenon) privileges set:")
        print(f"   - Admin: {user.is_admin}")
        print(f"   - Leader: {user.is_leader}")
        print(f"   - Status: {user.status.value}")
        print(f"   - Verified: {user.verification_completed}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting privileges: {e}")
        db.rollback()
        return False
    finally:
        close_db_session(db)

if __name__ == "__main__":
    print("Setting user privileges for @popexenon...")
    success = set_user_privileges()
    if success:
        print("✅ Privileges set successfully!")
    else:
        print("❌ Failed to set privileges!")