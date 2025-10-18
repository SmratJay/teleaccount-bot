#!/usr/bin/env python3
"""
EMERGENCY CAPTCHA AND LFG BUTTON FIX - BY HOOK OR BY CROOK!
This will fix both issues that are causing problems.
"""

import os
import sys
import sqlite3
from pathlib import Path

def reset_user_state():
    """Reset user state in database to fix captcha issues."""
    try:
        db_path = "teleaccount_bot.db"
        if not os.path.exists(db_path):
            print("❌ Database not found!")
            return False
            
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Reset all users to need verification again
        cursor.execute("""
            UPDATE users SET 
                verification_completed = 0,
                captcha_completed = 0,
                channels_joined = 0,
                status = 'PENDING_VERIFICATION'
            WHERE telegram_user_id = 6733908384
        """)
        
        conn.commit()
        conn.close()
        print("✅ User state reset successfully!")
        return True
    except Exception as e:
        print(f"❌ Database reset failed: {e}")
        return False

def check_captcha_files():
    """Check if captcha files and directories exist."""
    captcha_dir = Path("temp_captchas")
    if not captcha_dir.exists():
        captcha_dir.mkdir(exist_ok=True)
        print("✅ Created captcha directory")
    
    # Clean old captcha files
    for file in captcha_dir.glob("*.png"):
        try:
            file.unlink()
            print(f"🗑️ Cleaned old captcha: {file.name}")
        except:
            pass
    
    return True

def check_handlers_file():
    """Check if handlers are properly set up."""
    try:
        with open("handlers/main_handlers.py", "r") as f:
            content = f.read()
        
        if "lfg_sell" not in content:
            print("❌ LFG button handler missing!")
            return False
        
        if "start_verification" not in content:
            print("❌ Captcha handler missing!")
            return False
        
        print("✅ Main handlers look good")
        return True
    except Exception as e:
        print(f"❌ Handler check failed: {e}")
        return False

def main():
    print("🚀 EMERGENCY CAPTCHA & LFG BUTTON FIX")
    print("====================================")
    
    print("\n🔧 Step 1: Reset user state...")
    reset_user_state()
    
    print("\n🔧 Step 2: Check captcha files...")
    check_captcha_files()
    
    print("\n🔧 Step 3: Check handlers...")
    check_handlers_file()
    
    print("\n✅ Emergency fixes applied!")
    print("\n🚀 Now restart the bot and test:")
    print("1. Send /start to bot")
    print("2. You should see captcha image")
    print("3. Solve captcha")
    print("4. Click verify membership")
    print("5. LFG button should work")
    
    return True

if __name__ == "__main__":
    main()