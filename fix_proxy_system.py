"""
Fix Proxy System - Update existing proxies and fetch new ones
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent))

from database.models import ProxyPool
from services.webshare_provider import WebShareProvider

load_dotenv()

def fix_existing_proxies():
    """Update existing proxies to have provider='webshare'"""
    print("\n🔧 Updating existing proxies...")
    
    try:
        engine = create_engine('sqlite:///teleaccount_bot.db')
        Session = sessionmaker(bind=engine)
        db = Session()
        
        # Get all proxies without provider
        proxies = db.query(ProxyPool).filter(
            (ProxyPool.provider == None) | (ProxyPool.provider == '')
        ).all()
        
        print(f"   Found {len(proxies)} proxies without provider field")
        
        # Update them
        for proxy in proxies:
            proxy.provider = 'webshare'
        
        db.commit()
        print(f"   ✅ Updated {len(proxies)} proxies to provider='webshare'\n")
        
        # Verify
        webshare_count = db.query(ProxyPool).filter(
            ProxyPool.provider == 'webshare'
        ).count()
        
        print(f"✅ Verification: {webshare_count} WebShare proxies in database\n")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return False


def fetch_new_proxies():
    """Fetch new proxies from WebShare API"""
    print("\n🌐 Fetching proxies from WebShare.io...")
    
    # Check for API key (try both names)
    api_key = os.getenv('WEBSHARE_API_KEY') or os.getenv('WEBSHARE_API_TOKEN')
    
    if not api_key:
        print("❌ No API key found")
        print("   Checked: WEBSHARE_API_KEY and WEBSHARE_API_TOKEN\n")
        return False
    
    print(f"   API Key: {api_key[:20]}...{api_key[-10:]}")
    
    try:
        provider = WebShareProvider(api_key)
        
        # Fetch proxies
        print(f"   Fetching up to 100 proxies...")
        success, count = provider.import_to_database(limit=100)
        
        if success:
            print(f"   ✅ Successfully imported {count} new proxies!\n")
            return True
        else:
            print(f"   ❌ Failed to import proxies\n")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def verify_fix():
    """Verify the fix worked"""
    print("\n✅ Verifying fix...")
    
    try:
        engine = create_engine('sqlite:///teleaccount_bot.db')
        Session = sessionmaker(bind=engine)
        db = Session()
        
        total = db.query(ProxyPool).count()
        webshare = db.query(ProxyPool).filter(ProxyPool.provider == 'webshare').count()
        active = db.query(ProxyPool).filter(ProxyPool.is_active == True).count()
        
        print(f"\n📊 Database Status:")
        print(f"   Total proxies: {total}")
        print(f"   WebShare proxies: {webshare}")
        print(f"   Active proxies: {active}\n")
        
        if webshare > 0:
            print("✅ Fix successful! ProxyManager should now work.\n")
            
            # Test proxy selection
            from services.proxy_manager import ProxyManager
            manager = ProxyManager()
            
            print("🔄 Testing proxy selection...")
            proxy = manager.get_proxy_for_operation('login')
            
            if proxy:
                print(f"✅ Proxy selected successfully!")
                print(f"   IP: {proxy.addr}")
                print(f"   Port: {proxy.port}")
                print(f"   Type: {proxy.proxy_type}\n")
                return True
            else:
                print("⚠️ ProxyManager still returns None")
                print("   Check ProxyManager.get_proxy_for_operation() logic\n")
                return False
        else:
            print("❌ Still no WebShare proxies in database\n")
            return False
        
    except Exception as e:
        print(f"❌ Verification error: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "="*70)
    print("🔧 PROXY SYSTEM FIX")
    print("="*70)
    
    # Step 1: Fix existing proxies
    step1 = fix_existing_proxies()
    
    # Step 2: Fetch new proxies (optional)
    print("Would you like to fetch NEW proxies from WebShare.io?")
    print("(This will ADD to existing proxies)")
    user_input = input("Fetch new proxies? (yes/no): ").strip().lower()
    
    step2 = True
    if user_input == 'yes':
        step2 = fetch_new_proxies()
    
    # Step 3: Verify
    verify_fix()
    
    print("="*70)
    print("🎉 FIX COMPLETE")
    print("="*70 + "\n")
    
    if step1:
        print("✅ Existing proxies updated with provider='webshare'")
    if step2 and user_input == 'yes':
        print("✅ New proxies fetched from WebShare.io")
    
    print("\n🎯 Next Steps:")
    print("   1. Run: python diagnose_proxy_system.py")
    print("   2. Test bot: python real_main.py")
    print("   3. Try connecting a phone number")
    print("   4. Check logs for proxy usage\n")


if __name__ == "__main__":
    main()
