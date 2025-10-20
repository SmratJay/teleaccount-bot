"""
Comprehensive Proxy System Diagnostic
Checks database, WebShare API, proxy selection logic, and fixes issues
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from database.models import ProxyPool
from services.proxy_manager import ProxyManager
from services.webshare_provider import WebShareProvider

load_dotenv()

def check_database_proxies():
    """Check proxy database status"""
    print("\n" + "="*70)
    print("📊 DATABASE PROXY ANALYSIS")
    print("="*70 + "\n")
    
    try:
        engine = create_engine('sqlite:///teleaccount_bot.db')
        Session = sessionmaker(bind=engine)
        db = Session()
        
        # Check if provider column exists
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('proxy_pool')]
        
        print(f"📋 ProxyPool table columns: {', '.join(columns)}")
        print(f"   ✅ 'provider' column exists: {'provider' in columns}\n")
        
        # Get all proxies
        proxies = db.query(ProxyPool).all()
        print(f"📦 Total proxies in database: {len(proxies)}")
        
        if len(proxies) == 0:
            print("   ❌ NO PROXIES FOUND IN DATABASE!")
            print("   🔧 Root Cause: Database is empty")
            print("   💡 Solution: Need to fetch proxies from WebShare.io\n")
            return False
        
        # Check provider field
        webshare_proxies = []
        no_provider = []
        other_providers = []
        
        for proxy in proxies:
            if hasattr(proxy, 'provider'):
                if proxy.provider == 'webshare':
                    webshare_proxies.append(proxy)
                elif proxy.provider is None:
                    no_provider.append(proxy)
                else:
                    other_providers.append(proxy)
            else:
                no_provider.append(proxy)
        
        print(f"   🌐 WebShare proxies: {len(webshare_proxies)}")
        print(f"   ❓ No provider set: {len(no_provider)}")
        print(f"   🔄 Other providers: {len(other_providers)}\n")
        
        # Check active status
        active_proxies = [p for p in proxies if p.is_active]
        inactive_proxies = [p for p in proxies if not p.is_active]
        
        print(f"✅ Active proxies: {len(active_proxies)}")
        print(f"❌ Inactive proxies: {len(inactive_proxies)}\n")
        
        # Show sample proxies
        print("📋 Sample Proxies (first 5):")
        for i, proxy in enumerate(proxies[:5], 1):
            provider = getattr(proxy, 'provider', 'MISSING')
            print(f"   {i}. {proxy.ip_address}:{proxy.port}")
            print(f"      Provider: {provider}")
            print(f"      Active: {proxy.is_active}")
            print(f"      Country: {proxy.country_code}")
            print(f"      Type: {proxy.proxy_type}\n")
        
        db.close()
        
        # Diagnosis
        if len(webshare_proxies) == 0:
            print("❌ ROOT CAUSE FOUND: No proxies have provider='webshare'")
            print("   🔧 ProxyManager filters for provider='webshare' but finds none")
            print("   💡 Solution: Fetch proxies from WebShare API with correct provider tag\n")
            return False
        
        if len(active_proxies) == 0:
            print("❌ ROOT CAUSE FOUND: All proxies are inactive")
            print("   💡 Solution: Activate proxies or fetch new ones\n")
            return False
        
        print("✅ Database has proxies with correct provider field\n")
        return True
        
    except Exception as e:
        print(f"❌ Error checking database: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def check_webshare_api():
    """Check WebShare API connectivity and credentials"""
    print("\n" + "="*70)
    print("🌐 WEBSHARE API CHECK")
    print("="*70 + "\n")
    
    api_key = os.getenv('WEBSHARE_API_KEY')
    
    if not api_key:
        print("❌ WEBSHARE_API_KEY not found in .env")
        print("   💡 Add: WEBSHARE_API_KEY=your_key_here\n")
        return False
    
    print(f"✅ API Key found: {api_key[:20]}...{api_key[-10:]}")
    print(f"   Length: {len(api_key)} characters\n")
    
    try:
        provider = WebShareProvider(api_key)
        
        print("🔄 Testing API connectivity...")
        proxies = provider.fetch_proxies(limit=5)
        
        if proxies:
            print(f"✅ Successfully fetched {len(proxies)} proxies from WebShare!")
            print("\n📋 Sample Proxy:")
            sample = proxies[0]
            print(f"   IP: {sample['proxy_address']}")
            print(f"   Port: {sample['port']}")
            print(f"   Username: {sample['username']}")
            print(f"   Country: {sample['country_code']}")
            print(f"   Type: {sample['proxy_type']}\n")
            return True
        else:
            print("❌ API returned no proxies")
            print("   💡 Check your WebShare subscription\n")
            return False
            
    except Exception as e:
        print(f"❌ WebShare API error: {e}")
        print("   💡 Check API key validity\n")
        return False


def check_proxy_manager():
    """Check ProxyManager configuration and logic"""
    print("\n" + "="*70)
    print("⚙️ PROXY MANAGER CHECK")
    print("="*70 + "\n")
    
    try:
        manager = ProxyManager()
        
        print("✅ ProxyManager initialized\n")
        
        # Test proxy selection
        print("🔄 Testing proxy selection for 'login' operation...")
        proxy = manager.get_proxy_for_operation('login', phone='+919821757044')
        
        if proxy:
            print(f"✅ Proxy selected successfully!")
            print(f"   IP: {proxy.addr}")
            print(f"   Port: {proxy.port}")
            print(f"   Type: {proxy.proxy_type}\n")
            return True
        else:
            print("❌ No proxy returned from get_proxy_for_operation()")
            print("   🔧 This is the ROOT CAUSE of direct connections")
            print("   💡 ProxyManager.get_proxy_for_operation() returns None\n")
            return False
            
    except Exception as e:
        print(f"❌ ProxyManager error: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def fix_proxies():
    """Attempt to fix proxy issues"""
    print("\n" + "="*70)
    print("🔧 AUTOMATIC FIX ATTEMPT")
    print("="*70 + "\n")
    
    api_key = os.getenv('WEBSHARE_API_KEY')
    if not api_key:
        print("❌ Cannot fix: WEBSHARE_API_KEY not set\n")
        return False
    
    try:
        print("🔄 Fetching proxies from WebShare.io...")
        provider = WebShareProvider(api_key)
        
        # Import to database
        success, count = provider.import_to_database(limit=100)
        
        if success:
            print(f"✅ Successfully imported {count} proxies to database!")
            print(f"   All proxies saved with provider='webshare'\n")
            
            # Verify
            engine = create_engine('sqlite:///teleaccount_bot.db')
            Session = sessionmaker(bind=engine)
            db = Session()
            
            webshare_proxies = db.query(ProxyPool).filter(
                ProxyPool.provider == 'webshare'
            ).count()
            
            print(f"✅ Verification: {webshare_proxies} WebShare proxies in database\n")
            db.close()
            
            return True
        else:
            print(f"❌ Failed to import proxies\n")
            return False
            
    except Exception as e:
        print(f"❌ Fix failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def analyze_proxy_selection_logic():
    """Analyze the proxy selection logic in detail"""
    print("\n" + "="*70)
    print("🔍 PROXY SELECTION LOGIC ANALYSIS")
    print("="*70 + "\n")
    
    try:
        from services.proxy_manager import ProxyManager
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        engine = create_engine('sqlite:///teleaccount_bot.db')
        Session = sessionmaker(bind=engine)
        db = Session()
        
        # Get all proxies
        all_proxies = db.query(ProxyPool).filter(ProxyPool.is_active == True).all()
        print(f"📊 Active proxies in database: {len(all_proxies)}\n")
        
        if len(all_proxies) == 0:
            print("❌ No active proxies found!")
            print("   This is why ProxyManager returns None\n")
            db.close()
            return False
        
        # Check WebShare filter
        webshare_proxies = [
            p for p in all_proxies 
            if hasattr(p, 'provider') and p.provider == 'webshare'
        ]
        
        print(f"🔍 Filter: provider='webshare'")
        print(f"   Result: {len(webshare_proxies)} proxies\n")
        
        if len(webshare_proxies) == 0:
            print("❌ ROOT CAUSE IDENTIFIED:")
            print("   1. Database HAS active proxies")
            print("   2. BUT none have provider='webshare'")
            print("   3. ProxyManager filters for provider='webshare'")
            print("   4. Filter returns empty list")
            print("   5. get_proxy_for_operation() returns None")
            print("   6. Bot uses direct connection\n")
            
            print("🔧 SOLUTION:")
            print("   Run WebShareProvider.import_to_database()")
            print("   This will set provider='webshare' correctly\n")
        else:
            print("✅ WebShare proxies found! Filter should work.\n")
        
        db.close()
        return len(webshare_proxies) > 0
        
    except Exception as e:
        print(f"❌ Analysis error: {e}\n")
        return False


def main():
    """Run comprehensive diagnostic"""
    print("\n" + "="*70)
    print("🔬 COMPREHENSIVE PROXY SYSTEM DIAGNOSTIC")
    print("="*70)
    
    results = {
        'database': False,
        'api': False,
        'manager': False,
        'logic': False
    }
    
    # Step 1: Check database
    results['database'] = check_database_proxies()
    
    # Step 2: Check WebShare API
    results['api'] = check_webshare_api()
    
    # Step 3: Analyze selection logic
    results['logic'] = analyze_proxy_selection_logic()
    
    # Step 4: Check ProxyManager
    results['manager'] = check_proxy_manager()
    
    # Summary
    print("\n" + "="*70)
    print("📊 DIAGNOSTIC SUMMARY")
    print("="*70 + "\n")
    
    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {check.upper()}")
    
    # Determine root cause
    print("\n" + "="*70)
    print("🎯 ROOT CAUSE ANALYSIS")
    print("="*70 + "\n")
    
    if not results['database']:
        print("🔴 PRIMARY ISSUE: Database has no proxies or wrong provider")
        print("\n🔧 SOLUTION:")
        print("   1. Run: python -c \"from services.webshare_provider import WebShareProvider; import os; provider = WebShareProvider(os.getenv('WEBSHARE_API_KEY')); provider.import_to_database(limit=100)\"")
        print("   OR")
        print("   2. Use /fetch_webshare command in Telegram bot")
        print("   OR")
        print("   3. Run this script with --fix flag\n")
        
        # Offer auto-fix
        user_input = input("🔧 Attempt automatic fix now? (yes/no): ").strip().lower()
        if user_input == 'yes':
            if fix_proxies():
                print("\n✅ Fix successful! Re-running diagnostics...\n")
                # Re-run checks
                results['database'] = check_database_proxies()
                results['logic'] = analyze_proxy_selection_logic()
                results['manager'] = check_proxy_manager()
    
    elif not results['api']:
        print("🔴 PRIMARY ISSUE: WebShare API not working")
        print("\n🔧 SOLUTION:")
        print("   1. Check WEBSHARE_API_KEY in .env")
        print("   2. Verify API key at https://proxy.webshare.io/")
        print("   3. Check WebShare subscription status\n")
    
    elif not results['logic']:
        print("🔴 PRIMARY ISSUE: Proxy selection logic filtering out all proxies")
        print("\n🔧 SOLUTION:")
        print("   Proxies exist but don't have provider='webshare' field")
        print("   Re-import proxies with correct provider field\n")
    
    elif not results['manager']:
        print("🔴 PRIMARY ISSUE: ProxyManager.get_proxy_for_operation() returns None")
        print("\n🔧 SOLUTION:")
        print("   Check ProxyManager filtering logic")
        print("   Verify proxy selection rules\n")
    
    else:
        print("✅ ALL CHECKS PASSED!")
        print("   Proxies should be working correctly now.\n")
    
    print("="*70)
    print("📚 For more info, see: PROXY_ECOSYSTEM_COMPLETE.md")
    print("="*70 + "\n")


if __name__ == "__main__":
    import sys
    
    if '--fix' in sys.argv or '-f' in sys.argv:
        fix_proxies()
    else:
        main()
