#!/usr/bin/env python3
"""
Pre-deployment Verification Script for Replit
Run this to check if your bot is ready for deployment
"""
import os
import sys
import importlib.util

def check_file_exists(filepath, description):
    """Check if a file exists"""
    if os.path.exists(filepath):
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ MISSING {description}: {filepath}")
        return False

def check_environment_vars():
    """Check required environment variables"""
    print("\n🔍 Checking Environment Variables...")
    
    required_vars = {
        'BOT_TOKEN': 'Telegram bot token from @BotFather',
        'API_ID': 'Telegram API ID from my.telegram.org',
        'API_HASH': 'Telegram API hash from my.telegram.org',
        'ADMIN_TELEGRAM_ID': 'Your Telegram user ID',
        'LEADER_TELEGRAM_ID': 'Leader Telegram user ID'
    }
    
    missing = []
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if 'TOKEN' in var or 'HASH' in var:
                masked = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
                print(f"✅ {var}: {masked}")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ MISSING {var}: {description}")
            missing.append(var)
    
    return len(missing) == 0

def check_python_modules():
    """Check if required Python modules can be imported"""
    print("\n📦 Checking Python Dependencies...")
    
    required_modules = [
        'telegram',
        'telethon', 
        'sqlalchemy',
        'aiohttp',
        'cryptography',
        'flask'
    ]
    
    missing = []
    for module in required_modules:
        try:
            spec = importlib.util.find_spec(module)
            if spec is not None:
                print(f"✅ {module}: Available")
            else:
                print(f"❌ {module}: Not found")
                missing.append(module)
        except ImportError:
            print(f"❌ {module}: Import error")
            missing.append(module)
    
    if missing:
        print(f"\n💡 To install missing modules, run:")
        print(f"pip install {' '.join(missing)}")
    
    return len(missing) == 0

def check_project_structure():
    """Check if all required files exist"""
    print("\n📁 Checking Project Structure...")
    
    required_files = [
        ('main.py', 'Replit entry point'),
        ('real_main.py', 'Main bot application'),
        ('requirements.txt', 'Python dependencies'),
        ('pyproject.toml', 'Python project config'),
        ('.replit', 'Replit configuration'),
        ('replit.nix', 'Nix environment'),
        ('keep_alive.py', 'Keep-alive service'),
        ('setup_admin.py', 'Admin setup script'),
        ('database/__init__.py', 'Database package'),
        ('database/models.py', 'Database models'),
        ('database/connection.py', 'Database connection'),
        ('handlers/__init__.py', 'Handlers package'),
        ('handlers/real_handlers.py', 'Main handlers'),
        ('services/__init__.py', 'Services package'),
        ('services/real_telegram.py', 'Telegram service'),
    ]
    
    all_exist = True
    for filepath, description in required_files:
        if not check_file_exists(filepath, description):
            all_exist = False
    
    return all_exist

def check_database_connection():
    """Test database connection"""
    print("\n🗄️ Checking Database...")
    
    try:
        # Try to import database modules
        from database import get_db_session, close_db_session
        from database.models import User
        
        print("✅ Database modules imported successfully")
        
        # Try to connect to database
        db = get_db_session()
        if db:
            print("✅ Database connection successful")
            close_db_session(db)
            return True
        else:
            print("❌ Database connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def main():
    """Main verification function"""
    print("🚀 REPLIT DEPLOYMENT VERIFICATION")
    print("=" * 50)
    
    checks = [
        ("Environment Variables", check_environment_vars),
        ("Project Structure", check_project_structure),
        ("Python Dependencies", check_python_modules),
        ("Database Connection", check_database_connection),
    ]
    
    passed = 0
    total = len(checks)
    
    for check_name, check_func in checks:
        try:
            if check_func():
                passed += 1
            else:
                print(f"\n⚠️ {check_name} check failed!")
        except Exception as e:
            print(f"\n💥 {check_name} check crashed: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 VERIFICATION SUMMARY: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 ALL CHECKS PASSED!")
        print("Your bot is ready for Replit deployment!")
        print("\nNext steps:")
        print("1. Upload all files to Replit")
        print("2. Set environment variables in Secrets tab")
        print("3. Run: python setup_admin.py")
        print("4. Run: python main.py")
    else:
        print("❌ SOME CHECKS FAILED!")
        print("Please fix the issues above before deploying.")
        print("\nCommon fixes:")
        print("- Set missing environment variables in Replit Secrets")
        print("- Upload missing files to your Replit project")
        print("- Run: pip install -r requirements.txt")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)