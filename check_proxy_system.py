"""
Comprehensive check of proxy system implementation
"""
from database import engine
from sqlalchemy import inspect, text

print("=" * 80)
print("PROXY SYSTEM IMPLEMENTATION AUDIT")
print("=" * 80)

# 1. Check database schema
print("\n1. DATABASE SCHEMA CHECK")
print("-" * 80)
inspector = inspect(engine)
tables = inspector.get_table_names()

if 'proxy_pool' in tables:
    print("✅ proxy_pool table EXISTS")
    columns = inspector.get_columns('proxy_pool')
    print("\n   Columns:")
    for col in columns:
        print(f"   - {col['name']}: {col['type']}")
else:
    print("❌ proxy_pool table DOES NOT EXIST")

# 2. Check model imports
print("\n2. MODEL IMPORTS CHECK")
print("-" * 80)
try:
    from database.models import ProxyPool
    print("✅ ProxyPool model imports successfully")
    print(f"   Table name: {ProxyPool.__tablename__}")
    print(f"   Columns: {[c.name for c in ProxyPool.__table__.columns]}")
except Exception as e:
    print(f"❌ ProxyPool import failed: {e}")

# 3. Check operations
print("\n3. OPERATIONS MODULE CHECK")
print("-" * 80)
import os
if os.path.exists('database/operations.py'):
    print("✅ operations.py file exists")
    try:
        from database.operations import ProxyService
        print("✅ ProxyService imports successfully")
        methods = [m for m in dir(ProxyService) if not m.startswith('_')]
        print(f"   Methods: {', '.join(methods)}")
    except Exception as e:
        print(f"❌ ProxyService import failed: {e}")
else:
    print("❌ operations.py file DOES NOT EXIST")

# 4. Check proxy manager
print("\n4. PROXY MANAGER CHECK")
print("-" * 80)
try:
    from services.proxy_manager import proxy_manager
    print("✅ proxy_manager imports successfully")
    print(f"   Type: {type(proxy_manager)}")
except Exception as e:
    print(f"❌ proxy_manager import failed: {e}")

# 5. Check daily rotator
print("\n5. DAILY ROTATOR CHECK")
print("-" * 80)
try:
    from services.daily_proxy_rotator import daily_proxy_rotator
    print("✅ daily_proxy_rotator imports successfully")
except Exception as e:
    print(f"❌ daily_proxy_rotator import failed: {e}")

# 6. Check health monitor
print("\n6. HEALTH MONITOR CHECK")
print("-" * 80)
try:
    from services.proxy_health_monitor import proxy_health_monitor
    print("✅ proxy_health_monitor imports successfully")
except Exception as e:
    print(f"❌ proxy_health_monitor import failed: {e}")

# 7. Check admin commands
print("\n7. ADMIN COMMANDS CHECK")
print("-" * 80)
try:
    from handlers.proxy_admin_commands import PROXY_COMMANDS
    print("✅ proxy_admin_commands imports successfully")
    print(f"   Commands: {', '.join(PROXY_COMMANDS.keys())}")
except Exception as e:
    print(f"❌ proxy_admin_commands import failed: {e}")

# 8. Check integration with security bypass
print("\n8. SECURITY BYPASS INTEGRATION CHECK")
print("-" * 80)
try:
    from services.security_bypass import security_bypass
    print("✅ security_bypass imports successfully")
    has_proxy_manager = hasattr(security_bypass, 'proxy_manager')
    print(f"   Has proxy_manager attribute: {has_proxy_manager}")
except Exception as e:
    print(f"❌ security_bypass import failed: {e}")

# 9. Count existing proxies
print("\n9. EXISTING PROXY COUNT")
print("-" * 80)
try:
    from database import get_db_session
    db = get_db_session()
    result = db.execute(text('SELECT COUNT(*) FROM proxy_pool')).fetchone()
    print(f"✅ Proxies in database: {result[0]}")
    db.close()
except Exception as e:
    print(f"❌ Failed to count proxies: {e}")

print("\n" + "=" * 80)
print("AUDIT COMPLETE")
print("=" * 80)
