"""
Test script for the Telegram Account Bot.
Run this to test basic functionality and database connectivity.
"""
import os
import sys
import asyncio
import logging
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import db_manager, get_db_session, close_db_session
from database.operations import UserService, SystemSettingsService
from services.proxy_manager import ProxyManager
from services.telethon_manager import TelethonManager
from utils.helpers import CaptchaUtils, PhoneUtils, SecurityUtils
from utils.logging_config import setup_logging

async def test_database():
    """Test database connectivity and operations."""
    print("🔍 Testing Database Connectivity...")
    
    try:
        # Test connection
        db = get_db_session()
        print("✅ Database connection successful")
        
        # Test user creation
        test_user = UserService.get_or_create_user(
            db=db,
            telegram_user_id=12345678,
            username="testuser",
            first_name="Test",
            last_name="User"
        )
        print("✅ User creation/retrieval successful")
        
        # Test system settings
        SystemSettingsService.set_setting(db, "test_setting", "test_value", "Test setting")
        value = SystemSettingsService.get_setting(db, "test_setting")
        assert value == "test_value", "Setting value mismatch"
        print("✅ System settings working")
        
        close_db_session(db)
        print("✅ Database tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_utilities():
    """Test utility functions."""
    print("🔍 Testing Utility Functions...")
    
    try:
        # Test phone validation
        is_valid, formatted = PhoneUtils.validate_phone_number("+1234567890")
        assert is_valid, "Phone validation failed"
        assert formatted == "+1234567890", "Phone formatting failed"
        print("✅ Phone utilities working")
        
        # Test captcha generation
        question, answer = CaptchaUtils.generate_math_captcha()
        assert isinstance(question, str) and isinstance(answer, int), "Captcha generation failed"
        print("✅ Captcha utilities working")
        
        # Test security utilities
        password = SecurityUtils.generate_password(16)
        assert len(password) == 16, "Password generation failed"
        
        hash1 = SecurityUtils.hash_password("test123")
        hash2 = SecurityUtils.hash_password("test123")
        assert hash1 == hash2, "Password hashing inconsistent"
        print("✅ Security utilities working")
        
        print("✅ Utility tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Utility test failed: {e}")
        return False

def test_proxy_manager():
    """Test proxy manager functionality."""
    print("🔍 Testing Proxy Manager...")
    
    try:
        proxy_manager = ProxyManager()
        
        # Test proxy configuration
        from services.proxy_manager import ProxyConfig
        test_proxy = ProxyConfig(
            proxy_type="HTTP",
            host="127.0.0.1",
            port=8080,
            username="test",
            password="test123"
        )
        
        # Test JSON conversion
        proxy_json = proxy_manager.get_proxy_json(test_proxy)
        loaded_proxy = proxy_manager.load_proxy_from_json(proxy_json)
        
        assert loaded_proxy.host == test_proxy.host, "Proxy JSON conversion failed"
        print("✅ Proxy configuration working")
        
        print("✅ Proxy manager tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Proxy manager test failed: {e}")
        return False

async def test_telethon_manager():
    """Test Telethon manager initialization."""
    print("🔍 Testing Telethon Manager...")
    
    try:
        # Check environment variables
        api_id = os.getenv('API_ID')
        api_hash = os.getenv('API_HASH')
        
        if not api_id or not api_hash:
            print("⚠️ API_ID and API_HASH not set - skipping Telethon tests")
            return True
        
        # Test manager initialization
        telethon_manager = TelethonManager()
        assert telethon_manager.api_id > 0, "API ID not set"
        assert telethon_manager.api_hash, "API hash not set"
        print("✅ Telethon manager initialized")
        
        print("✅ Telethon manager tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Telethon manager test failed: {e}")
        return False

def test_environment():
    """Test environment configuration."""
    print("🔍 Testing Environment Configuration...")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        # Required variables
        required_vars = [
            'DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD',
            'BOT_TOKEN', 'ADMIN_USER_ID'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"⚠️ Missing environment variables: {', '.join(missing_vars)}")
            print("Please set these in your .env file")
            return False
        
        print("✅ Environment configuration complete")
        return True
        
    except Exception as e:
        print(f"❌ Environment test failed: {e}")
        return False

async def run_all_tests():
    """Run all tests."""
    print("🚀 Starting Telegram Account Bot Tests")
    print("=" * 50)
    
    # Setup logging
    setup_logging()
    
    test_results = {
        "Environment": test_environment(),
        "Database": await test_database(),
        "Utilities": test_utilities(),
        "Proxy Manager": test_proxy_manager(),
        "Telethon Manager": await test_telethon_manager()
    }
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    
    all_passed = True
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
        if not result:
            all_passed = False
    
    print("=" * 50)
    
    if all_passed:
        print("🎉 All tests passed! Your bot is ready to run.")
        print("\nNext steps:")
        print("1. Run 'python main.py' to start the bot")
        print("2. Test with /start command in Telegram")
        print("3. Try the /lfg flow with a test account")
    else:
        print("❌ Some tests failed. Please fix the issues before running the bot.")
        print("\nCommon fixes:")
        print("- Check your .env file configuration")
        print("- Ensure PostgreSQL is running and accessible")
        print("- Verify your Telegram bot token")
        print("- Check database credentials")

if __name__ == "__main__":
    try:
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
    except Exception as e:
        print(f"\n💥 Fatal error during testing: {e}")
        import traceback
        traceback.print_exc()