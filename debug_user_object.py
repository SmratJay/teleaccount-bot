"""Debug what the actual db_user object contains"""
import sys
sys.path.insert(0, 'd:/teleaccount_bot')

from database import get_db_session, close_db_session
from database.operations import UserService

db = get_db_session()
try:
    print("=" * 60)
    print("DEBUGGING UserService.get_user_by_telegram_id()")
    print("=" * 60)
    
    user = UserService.get_user_by_telegram_id(db, 6733908384)
    
    print(f"\n✅ User object returned: {type(user)}")
    print(f"   Module: {type(user).__module__}")
    print(f"   Class: {type(user).__name__}")
    
    print(f"\n📋 All attributes:")
    for attr in dir(user):
        if not attr.startswith('_'):
            try:
                value = getattr(user, attr)
                if not callable(value):
                    print(f"   {attr}: {value}")
            except Exception as e:
                print(f"   {attr}: <error: {e}>")
    
    print(f"\n🔍 Critical checks:")
    print(f"   hasattr(user, 'is_admin'): {hasattr(user, 'is_admin')}")
    print(f"   hasattr(user, 'is_leader'): {hasattr(user, 'is_leader')}")
    print(f"   hasattr(user, 'balance'): {hasattr(user, 'balance')}")
    print(f"   hasattr(user, 'telegram_user_id'): {hasattr(user, 'telegram_user_id')}")
    
    if hasattr(user, 'is_admin'):
        print(f"\n✅ user.is_admin = {user.is_admin}")
    if hasattr(user, 'is_leader'):
        print(f"✅ user.is_leader = {user.is_leader}")
    if hasattr(user, 'balance'):
        print(f"✅ user.balance = {user.balance}")
        
finally:
    close_db_session(db)
