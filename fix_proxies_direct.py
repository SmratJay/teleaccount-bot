"""
Direct SQL fix for proxy provider field
"""

import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

def fix_proxies_sql():
    """Fix proxies using direct SQL"""
    print("\n🔧 Fixing proxies with direct SQL...")
    
    try:
        conn = sqlite3.connect('teleaccount_bot.db')
        cursor = conn.cursor()
        
        # Check current state
        cursor.execute("SELECT COUNT(*) FROM proxy_pool")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM proxy_pool WHERE provider = 'webshare'")
        webshare = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM proxy_pool WHERE provider IS NULL OR provider = ''")
        no_provider = cursor.fetchone()[0]
        
        print(f"\n📊 Current Status:")
        print(f"   Total proxies: {total}")
        print(f"   WebShare proxies: {webshare}")
        print(f"   No provider: {no_provider}\n")
        
        # Update proxies without provider
        cursor.execute("""
            UPDATE proxy_pool 
            SET provider = 'webshare'
            WHERE provider IS NULL OR provider = '' OR provider = 'free'
        """)
        
        updated = cursor.rowcount
        conn.commit()
        
        print(f"✅ Updated {updated} proxies to provider='webshare'\n")
        
        # Verify
        cursor.execute("SELECT COUNT(*) FROM proxy_pool WHERE provider = 'webshare'")
        webshare_after = cursor.fetchone()[0]
        
        print(f"📊 After Update:")
        print(f"   WebShare proxies: {webshare_after}")
        print(f"   Active proxies: ", end="")
        
        cursor.execute("SELECT COUNT(*) FROM proxy_pool WHERE is_active = 1")
        active = cursor.fetchone()[0]
        print(f"{active}\n")
        
        # Show sample
        cursor.execute("""
            SELECT ip_address, port, provider, is_active, country_code 
            FROM proxy_pool 
            LIMIT 5
        """)
        
        print("📋 Sample Proxies:")
        for row in cursor.fetchall():
            print(f"   {row[0]}:{row[1]} - provider={row[2]}, active={row[3]}, country={row[4]}")
        
        conn.close()
        
        if webshare_after > 0:
            print("\n✅ Fix successful!\n")
            return True
        else:
            print("\n❌ Fix failed\n")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_proxy_manager():
    """Test if ProxyManager works now"""
    print("\n🔄 Testing ProxyManager...")
    
    try:
        from services.proxy_manager import ProxyManager
        
        manager = ProxyManager()
        
        # Test selection
        proxy = manager.get_proxy_for_operation('login')
        
        if proxy:
            print(f"✅ Proxy selected successfully!")
            print(f"   IP: {proxy.addr}")
            print(f"   Port: {proxy.port}")
            print(f"   Type: {proxy.proxy_type}\n")
            return True
        else:
            print("❌ ProxyManager still returns None\n")
            return False
            
    except Exception as e:
        print(f"❌ ProxyManager error: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "="*70)
    print("🔧 DIRECT SQL PROXY FIX")
    print("="*70)
    
    # Fix proxies
    if fix_proxies_sql():
        # Test ProxyManager
        test_proxy_manager()
    
    print("="*70)
    print("✅ FIX COMPLETE")
    print("="*70 + "\n")
    
    print("🎯 Next Steps:")
    print("   1. Run: python diagnose_proxy_system.py")
    print("   2. Test bot with: python real_main.py")
    print("   3. Try connecting a phone number")
    print("   4. Check logs for: 'Using proxy: ...'")
    print()


if __name__ == "__main__":
    main()
