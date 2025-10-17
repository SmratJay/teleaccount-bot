#!/usr/bin/env python3
"""
Reset user verification state for captcha testing
"""
import logging
from database import get_db_session, close_db_session
from database.models import User, UserStatus
from database.operations import UserService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_user_verification(user_id: int = 6733908384):
    """Reset user verification status for fresh testing."""
    db = get_db_session()
    
    try:
        # Get user
        user = UserService.get_user_by_telegram_id(db, user_id)
        
        if user:
            # Reset verification fields
            user.captcha_completed = False
            user.channels_joined = False
            user.verification_completed = False
            user.status = UserStatus.PENDING_VERIFICATION
            
            db.commit()
            
            logger.info(f"✅ Reset verification for user {user_id}")
            logger.info(f"   - captcha_completed: {user.captcha_completed}")
            logger.info(f"   - channels_joined: {user.channels_joined}")  
            logger.info(f"   - verification_completed: {user.verification_completed}")
            logger.info(f"   - status: {user.status.value}")
        else:
            logger.warning(f"❌ User {user_id} not found")
            
    except Exception as e:
        logger.error(f"Error resetting user verification: {e}")
        db.rollback()
    finally:
        close_db_session(db)

if __name__ == "__main__":
    print("🔄 Resetting user verification state for captcha testing...")
    reset_user_verification()
    print("✅ User verification reset complete!")
    print("\n📋 How to test captcha system:")
    print("1. Start the bot: python real_main.py")
    print("2. Send /start command to the bot")
    print("3. Should trigger verification process with captcha")
    print("4. Test both visual and text captcha modes")
    print("5. Check that captcha images are generated and cleaned up")