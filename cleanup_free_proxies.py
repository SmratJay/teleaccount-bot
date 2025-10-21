#!/usr/bin/env python3
"""
One-time script to clean up free proxies from the database.
This removes all proxies that are NOT from WebShare.io.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from database import get_db_session, close_db_session
from database.operations import ProxyService

def main():
    print("=" * 60)
    print("🧹 CLEANING FREE PROXIES FROM DATABASE")
    print("=" * 60)
    print()
    
    db = get_db_session()
    try:
        # Get stats before cleanup
        print("📊 Getting stats before cleanup...")
        before_stats = ProxyService.get_proxy_stats(db)
        before_total = before_stats.get('total_proxies', 0)
        before_active = before_stats.get('active_proxies', 0)
        
        print(f"   Total proxies: {before_total}")
        print(f"   Active proxies: {before_active}")
        print()
        
        # Remove free proxies
        print("🗑️  Removing all non-WebShare proxies...")
        removed_count = ProxyService.remove_free_proxies(db)
        print(f"   ✅ Removed: {removed_count} free proxies")
        print()
        
        # Get stats after cleanup
        print("📊 Getting stats after cleanup...")
        after_stats = ProxyService.get_proxy_stats(db)
        after_total = after_stats.get('total_proxies', 0)
        after_active = after_stats.get('active_proxies', 0)
        
        print(f"   Total proxies: {after_total}")
        print(f"   Active proxies: {after_active}")
        print()
        
        print("=" * 60)
        print("✅ CLEANUP COMPLETE")
        print("=" * 60)
        print()
        print(f"Summary:")
        print(f"  • Removed: {removed_count} free proxies")
        print(f"  • Remaining: {after_total} WebShare.io proxies")
        print()
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        return 1
    finally:
        close_db_session(db)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
