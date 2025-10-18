#!/usr/bin/env python3
"""
Admin Setup Script for Replit Deployment
Run this once after deploying to set up admin privileges
"""
import os
import sys
sys.path.append('.')

from database import get_db_session, close_db_session
from database.models import User, UserStatus

def setup_admin():
    """Set up admin privileges for the bot owner"""
    # Your Telegram user ID (from @popexenon)
    user_id = 6733908384
    
    print(f"🔧 Setting up admin privileges for user {user_id}...")
    
    db = get_db_session()
    try:
        # Find or create user
        user = db.query(User).filter(User.telegram_user_id == user_id).first()
        
        if not user:
            print(f"📝 Creating new admin user record...")
            user = User(
                telegram_user_id=user_id,
                username="popexenon",
                first_name="Admin",
                is_admin=True,
                is_leader=True,
                status=UserStatus.ACTIVE,
                verification_completed=True,
                captcha_completed=True,
                channels_joined=True,
                balance=0.0
            )
            db.add(user)
        else:
            print(f"🔄 Updating existing user privileges...")
            user.is_admin = True
            user.is_leader = True
            user.status = UserStatus.ACTIVE
            user.verification_completed = True
            user.captcha_completed = True
            user.channels_joined = True
            
        db.commit()
        
        print("✅ Admin setup completed successfully!")
        print(f"   👤 User ID: {user.telegram_user_id}")
        print(f"   👑 Admin: {user.is_admin}")
        print(f"   🏆 Leader: {user.is_leader}")
        print(f"   📊 Status: {user.status.value}")
        print(f"   ✅ Verified: {user.verification_completed}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting up admin privileges: {e}")
        db.rollback()
        return False
    finally:
        close_db_session(db)

def verify_environment():
    """Verify that all required environment variables are set"""
    print("🔍 Verifying environment variables...")
    
    required_vars = [
        'BOT_TOKEN',
        'API_ID', 
        'API_HASH',
        'ADMIN_TELEGRAM_ID'
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"❌ Missing environment variables: {missing}")
        print("Please set these in the Replit Secrets tab")
        return False
    
    print("✅ All required environment variables are set")
    return True

if __name__ == "__main__":
    print("🚀 REPLIT ADMIN SETUP")
    print("=" * 50)
    
    # Verify environment first
    if not verify_environment():
        print("❌ Environment setup incomplete. Please fix and try again.")
        sys.exit(1)
    
    # Setup admin privileges
    success = setup_admin()
    
    if success:
        print("\n🎉 Setup completed successfully!")
        print("Your bot is ready to use with full admin privileges.")
        print("\nNext steps:")
        print("1. Start your bot with: python main.py")
        print("2. Send /start to your bot on Telegram")
        print("3. You should see admin panel buttons")
    else:
        print("\n❌ Setup failed! Check the error messages above.")
        sys.exit(1)