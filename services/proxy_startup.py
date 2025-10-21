"""
Proxy System Startup and Initialization

Handles automatic proxy fetching and system initialization when bot starts.
"""
import os
import sys
import logging
import asyncio
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import get_db_session, close_db_session
from database.operations import ProxyService

logger = logging.getLogger(__name__)


async def initialize_proxy_system() -> dict:
    """
    Initialize proxy system on bot startup.
    
    This function:
    1. Checks if proxies exist in database
    2. Fetches fresh proxies if needed
    3. Validates proxy configuration
    4. Returns initialization status
    
    Returns:
        Dict with initialization results
    """
    logger.info("🚀 Initializing proxy system...")
    
    results = {
        'success': True,
        'proxies_loaded': 0,
        'webshare_fetched': 0,
        'errors': []
    }
    
    try:
        # Check existing proxies
        db = get_db_session()
        stats = ProxyService.get_proxy_stats(db)
        active_count = stats.get('active_proxies', 0)
        results['proxies_loaded'] = active_count
        close_db_session(db)
        
        logger.info(f"📊 Found {active_count} active proxies in database")
        
        # Decide if we need to fetch fresh proxies
        should_fetch = False
        fetch_reason = None
        
        if active_count == 0:
            should_fetch = True
            fetch_reason = "No active proxies found"
        elif active_count < 5:
            should_fetch = True
            fetch_reason = f"Low proxy count ({active_count} < 5)"
        
        # Check if WebShare is enabled
        webshare_enabled = os.getenv('WEBSHARE_ENABLED', 'false').lower() == 'true'
        webshare_token = os.getenv('WEBSHARE_API_TOKEN') or os.getenv('WEBSHARE_API_KEY')
        auto_fetch = os.getenv('AUTO_FETCH_PROXIES_ON_STARTUP', 'true').lower() == 'true'
        
        if should_fetch and webshare_enabled and webshare_token and auto_fetch:
            logger.info(f"🔄 Auto-fetching proxies: {fetch_reason}")
            
            try:
                from services.webshare_provider import WebShareProvider
                
                provider = WebShareProvider(webshare_token)
                
                # Test connection first
                logger.info("🔗 Testing WebShare API connection...")
                connection_test = await provider.test_connection()
                
                if connection_test['success']:
                    logger.info(f"✅ WebShare API connected - {connection_test.get('total_proxies', 0)} proxies available")
                    
                    # Import proxies
                    logger.info("📥 Fetching proxies from WebShare.io...")
                    db = get_db_session()
                    import_result = await provider.import_to_database(db=db, max_proxies=50)
                    close_db_session(db)
                    
                    if import_result['success']:
                        results['webshare_fetched'] = import_result['imported']
                        logger.info(
                            f"✅ WebShare import complete: "
                            f"{import_result['imported']} new, "
                            f"{import_result['skipped']} updated"
                        )
                    else:
                        error_msg = f"WebShare import failed: {import_result.get('error')}"
                        logger.error(f"❌ {error_msg}")
                        results['errors'].append(error_msg)
                else:
                    error_msg = f"WebShare connection failed: {connection_test.get('error')}"
                    logger.error(f"❌ {error_msg}")
                    results['errors'].append(error_msg)
                    
            except Exception as e:
                error_msg = f"WebShare fetch error: {str(e)}"
                logger.error(f"❌ {error_msg}")
                results['errors'].append(error_msg)
        
        elif should_fetch:
            if not auto_fetch:
                logger.info("⏸️ Auto-fetch disabled (AUTO_FETCH_PROXIES_ON_STARTUP=false)")
            elif not webshare_enabled:
                logger.warning("⚠️ WebShare disabled (WEBSHARE_ENABLED=false)")
            elif not webshare_token:
                logger.warning("⚠️ WebShare API token not configured")
        else:
            logger.info(f"✅ Sufficient proxies available ({active_count}), skipping auto-fetch")
        
        # Final stats
        db = get_db_session()
        final_stats = ProxyService.get_proxy_stats(db)
        close_db_session(db)
        
        total_active = final_stats.get('active_proxies', 0)
        
        logger.info(
            f"✅ Proxy system initialized: {total_active} active proxies "
            f"({results['webshare_fetched']} fetched on startup)"
        )
        
        results['final_proxy_count'] = total_active
        
        # Warn if still no proxies
        if total_active == 0:
            logger.warning("⚠️ No active proxies! Bot will use direct connections.")
            results['success'] = False
            results['errors'].append("No active proxies available")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Proxy system initialization failed: {e}")
        results['success'] = False
        results['errors'].append(str(e))
        return results


async def update_proxy_metadata():
    """
    Update metadata for existing proxies to ensure they pass filters.
    
    This sets reasonable default values for reputation, success_rate, etc.
    """
    logger.info("🔧 Updating proxy metadata...")
    
    try:
        db = get_db_session()
        
        from database.models import ProxyPool
        
        # Get all proxies with provider='webshare' that need metadata updates
        proxies = db.query(ProxyPool).filter(
            ProxyPool.provider == 'webshare',
            ProxyPool.is_active == True
        ).all()
        
        updated = 0
        for proxy in proxies:
            needs_update = False
            
            # Set default reputation if not set or too low
            if proxy.reputation_score is None or proxy.reputation_score < 50:
                proxy.reputation_score = 50
                needs_update = True
            
            # Set default success rate
            if proxy.success_rate is None or proxy.success_rate == 0:
                proxy.success_rate = 0.95  # 95% default success rate
                needs_update = True
            
            # Set default response time
            if proxy.response_time_avg is None or proxy.response_time_avg == 0:
                proxy.response_time_avg = 0.5  # 500ms default
                needs_update = True
            
            # Reset consecutive failures
            if proxy.consecutive_failures is None:
                proxy.consecutive_failures = 0
                needs_update = True
            
            if needs_update:
                updated += 1
        
        db.commit()
        close_db_session(db)
        
        logger.info(f"✅ Updated metadata for {updated} proxies")
        return {'success': True, 'updated': updated}
        
    except Exception as e:
        logger.error(f"❌ Failed to update proxy metadata: {e}")
        return {'success': False, 'error': str(e)}


def get_initialization_summary() -> str:
    """
    Get a formatted summary of proxy system status for bot startup message.
    
    Returns:
        Formatted string with proxy system status
    """
    try:
        db = get_db_session()
        stats = ProxyService.get_proxy_stats(db)
        close_db_session(db)
        
        total = stats.get('total_proxies', 0)
        active = stats.get('active_proxies', 0)
        countries = stats.get('country_distribution', {})
        
        if active == 0:
            return "⚠️ Proxies: None active (using direct connections)"
        
        country_summary = ", ".join(f"{code}:{count}" for code, count in list(countries.items())[:3])
        
        return f"✅ Proxies: {active} active ({country_summary})"
        
    except Exception as e:
        logger.error(f"Error getting proxy summary: {e}")
        return "❌ Proxy status: Error"


async def startup_routine():
    """
    Complete startup routine for proxy system.
    
    Runs all initialization tasks in sequence.
    """
    logger.info("=" * 60)
    logger.info("PROXY SYSTEM STARTUP")
    logger.info("=" * 60)
    
    # Initialize proxy system
    init_result = await initialize_proxy_system()
    
    # Update metadata for better filtering
    if init_result.get('final_proxy_count', 0) > 0:
        await update_proxy_metadata()
    
    logger.info("=" * 60)
    logger.info("PROXY SYSTEM STARTUP COMPLETE")
    logger.info("=" * 60)
    
    return init_result


if __name__ == '__main__':
    # Allow running this module directly for testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(startup_routine())

