"""
Configure System to Use ONLY WebShare Premium Proxies
Removes all free/hardcoded proxies and sets up WebShare-only mode
"""
import os
import sys
import asyncio
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import get_db_session, close_db_session
from database.models import ProxyPool
from services.webshare_provider import WebShareProvider

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def configure_webshare_only():
    """Configure system to use only WebShare proxies."""
    
    logger.info("=" * 80)
    logger.info("CONFIGURING WEBSHARE-ONLY MODE")
    logger.info("=" * 80)
    
    # Step 1: Check current proxy status
    logger.info("\n📊 Step 1: Checking current proxy status...")
    db = get_db_session()
    
    total_proxies = db.query(ProxyPool).count()
    webshare_proxies = db.query(ProxyPool).filter(ProxyPool.provider == 'webshare').count()
    free_proxies = total_proxies - webshare_proxies
    
    logger.info(f"   Total proxies: {total_proxies}")
    logger.info(f"   WebShare proxies: {webshare_proxies}")
    logger.info(f"   Free proxies: {free_proxies}")
    
    # Step 2: Remove all non-WebShare proxies
    if free_proxies > 0:
        logger.info(f"\n🗑️ Step 2: Removing {free_proxies} free/hardcoded proxies...")
        deleted = db.query(ProxyPool).filter(
            (ProxyPool.provider != 'webshare') | (ProxyPool.provider == None)
        ).delete()
        db.commit()
        logger.info(f"   ✅ Removed {deleted} free proxies")
    else:
        logger.info("\n✅ Step 2: No free proxies to remove")
    
    # Step 3: Check WebShare configuration
    logger.info("\n🔑 Step 3: Checking WebShare configuration...")
    
    api_token = os.getenv('WEBSHARE_API_TOKEN')
    enabled = os.getenv('WEBSHARE_ENABLED', 'false').lower() == 'true'
    
    if not api_token or api_token == 'your_webshare_token_here':
        logger.error("   ❌ WEBSHARE_API_TOKEN not configured!")
        logger.error("   Please add your API token to .env file")
        close_db_session(db)
        return False
    
    if not enabled:
        logger.error("   ❌ WEBSHARE_ENABLED is false!")
        logger.error("   Please set WEBSHARE_ENABLED=true in .env file")
        close_db_session(db)
        return False
    
    logger.info(f"   ✅ API Token: {api_token[:10]}...{api_token[-10:]}")
    logger.info(f"   ✅ WebShare enabled: {enabled}")
    
    # Step 4: Test WebShare connection
    logger.info("\n🔌 Step 4: Testing WebShare connection...")
    
    webshare = WebShareProvider(api_token)
    
    try:
        account_info = await webshare.get_account_info()
        if account_info:
            logger.info(f"   ✅ Connected to WebShare!")
            logger.info(f"   Email: {account_info.get('email')}")
            logger.info(f"   Available proxies: {account_info.get('proxy_count', 0)}")
            logger.info(f"   Account type: {account_info.get('account_type', 'Unknown')}")
        else:
            logger.error("   ❌ Failed to connect to WebShare")
            close_db_session(db)
            return False
    except Exception as e:
        logger.error(f"   ❌ Error connecting to WebShare: {e}")
        close_db_session(db)
        return False
    
    # Step 5: Fetch WebShare proxies
    logger.info("\n📥 Step 5: Fetching WebShare proxies...")
    
    current_webshare = db.query(ProxyPool).filter(ProxyPool.provider == 'webshare').count()
    
    if current_webshare == 0:
        logger.info("   No WebShare proxies in database, fetching...")
        proxy_count = int(os.getenv('WEBSHARE_PROXY_COUNT', '100'))
        
        success = await webshare.fetch_and_store_proxies(limit=proxy_count)
        
        if success:
            new_count = db.query(ProxyPool).filter(ProxyPool.provider == 'webshare').count()
            logger.info(f"   ✅ Fetched {new_count} WebShare proxies")
        else:
            logger.error("   ❌ Failed to fetch WebShare proxies")
            close_db_session(db)
            return False
    else:
        logger.info(f"   ✅ Already have {current_webshare} WebShare proxies")
    
    # Step 6: Verify final status
    logger.info("\n✅ Step 6: Verifying final configuration...")
    
    total = db.query(ProxyPool).count()
    webshare = db.query(ProxyPool).filter(ProxyPool.provider == 'webshare').count()
    active = db.query(ProxyPool).filter(
        ProxyPool.provider == 'webshare',
        ProxyPool.is_active == True
    ).count()
    
    logger.info(f"   Total proxies: {total}")
    logger.info(f"   WebShare proxies: {webshare}")
    logger.info(f"   Active WebShare proxies: {active}")
    
    if total == webshare and webshare > 0:
        logger.info("\n" + "=" * 80)
        logger.info("🎉 SUCCESS! SYSTEM NOW USES ONLY WEBSHARE PREMIUM PROXIES")
        logger.info("=" * 80)
        logger.info(f"\n✅ {webshare} premium WebShare proxies ready to use")
        logger.info("✅ All free/hardcoded proxies removed")
        logger.info("✅ System configured for WebShare-only mode")
        close_db_session(db)
        return True
    else:
        logger.error("\n❌ Configuration incomplete!")
        logger.error(f"Total: {total}, WebShare: {webshare}")
        close_db_session(db)
        return False


async def main():
    """Main function."""
    success = await configure_webshare_only()
    
    if success:
        print("\n" + "=" * 80)
        print("NEXT STEPS:")
        print("=" * 80)
        print("1. Restart your bot:")
        print("   D:/teleaccount_bot/.venv/Scripts/python.exe bot_proxy_test.py")
        print("")
        print("2. Test in Telegram:")
        print("   /proxy_stats     - Should show only WebShare proxies")
        print("   /proxy_providers - Should show only 'webshare' provider")
        print("   /proxy_test      - All proxies will be WebShare premium")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("CONFIGURATION FAILED - Please check:")
        print("=" * 80)
        print("1. WEBSHARE_API_TOKEN is set in .env")
        print("2. WEBSHARE_ENABLED=true in .env")
        print("3. Your WebShare account is active")
        print("4. You have available proxies in your plan")
        print("=" * 80)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nConfiguration cancelled by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
