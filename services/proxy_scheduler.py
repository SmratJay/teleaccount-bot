"""
Proxy Auto-Refresh Scheduler
Automatically fetches fresh proxies and cleans up dead ones
"""
import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class ProxyRefreshScheduler:
    """Manages automatic proxy pool refresh"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self.last_refresh = None
        self.refresh_stats = {
            'total_refreshes': 0,
            'successful_refreshes': 0,
            'failed_refreshes': 0,
            'last_error': None
        }
        
    async def refresh_all_proxies(self):
        """Refresh proxies from all enabled sources"""
        try:
            logger.info("🔄 Starting automatic proxy refresh...")
            start_time = datetime.now()
            
            results = {
                'webshare': {'enabled': False, 'success': False, 'count': 0, 'error': None},
                'free_sources': {'enabled': False, 'success': False, 'count': 0, 'error': None},
                'cleanup': {'removed': 0, 'error': None}
            }
            
            # Check WebShare.io
            webshare_enabled = os.getenv('WEBSHARE_ENABLED', 'false').lower() == 'true'
            webshare_token = os.getenv('WEBSHARE_API_TOKEN')
            
            if webshare_enabled and webshare_token:
                try:
                    from services.webshare_provider import refresh_webshare_proxies
                    results['webshare']['enabled'] = True
                    
                    stats = await refresh_webshare_proxies()
                    results['webshare']['success'] = True
                    results['webshare']['count'] = stats.get('new', 0) + stats.get('updated', 0)
                    
                    logger.info(f"✅ WebShare refresh: {stats['new']} new, {stats['updated']} updated, {stats['failed']} failed")
                    
                except Exception as e:
                    results['webshare']['error'] = str(e)
                    logger.error(f"❌ WebShare refresh failed: {e}")
            
            # Check free sources
            free_sources_enabled = os.getenv('FREE_PROXY_SOURCES_ENABLED', 'true').lower() == 'true'
            
            if free_sources_enabled:
                try:
                    from services.proxy_sources import refresh_free_proxies
                    results['free_sources']['enabled'] = True
                    
                    stats = await refresh_free_proxies()
                    results['free_sources']['success'] = True
                    results['free_sources']['count'] = stats.get('new', 0)
                    
                    logger.info(f"✅ Free sources refresh: {stats['new']} new, {stats['updated']} updated")
                    
                except Exception as e:
                    results['free_sources']['error'] = str(e)
                    logger.error(f"❌ Free sources refresh failed: {e}")
            
            # Clean up dead proxies
            try:
                from database import get_db_session, close_db_session
                from database.operations import ProxyService
                
                db = get_db_session()
                try:
                    # Deactivate proxies with 3+ consecutive failures
                    cleaned = ProxyService.cleanup_old_proxies(db, days_inactive=7)
                    results['cleanup']['removed'] = cleaned
                    
                    logger.info(f"🧹 Cleaned up {cleaned} old/dead proxies")
                    
                except Exception as e:
                    results['cleanup']['error'] = str(e)
                    logger.error(f"❌ Cleanup failed: {e}")
                finally:
                    close_db_session(db)
                    
            except Exception as e:
                results['cleanup']['error'] = str(e)
                logger.error(f"❌ Cleanup failed: {e}")
            
            # Update stats
            elapsed = (datetime.now() - start_time).total_seconds()
            self.last_refresh = datetime.now()
            self.refresh_stats['total_refreshes'] += 1
            
            total_new = results['webshare']['count'] + results['free_sources']['count']
            has_errors = results['webshare']['error'] or results['free_sources']['error'] or results['cleanup']['error']
            
            if not has_errors:
                self.refresh_stats['successful_refreshes'] += 1
                logger.info(f"✅ Proxy refresh completed in {elapsed:.2f}s: {total_new} total proxies, {results['cleanup']['removed']} cleaned")
            else:
                self.refresh_stats['failed_refreshes'] += 1
                self.refresh_stats['last_error'] = str(has_errors)
                logger.warning(f"⚠️ Proxy refresh completed with errors in {elapsed:.2f}s")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Fatal error in proxy refresh: {e}", exc_info=True)
            self.refresh_stats['failed_refreshes'] += 1
            self.refresh_stats['last_error'] = str(e)
            return {'error': str(e)}
    
    def start(self, interval_seconds: int = None):
        """
        Start the scheduler.
        
        Args:
            interval_seconds: Refresh interval in seconds (default from env or 86400 = 24 hours)
        """
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        # Get interval from env or use provided/default
        if interval_seconds is None:
            interval_seconds = int(os.getenv('PROXY_REFRESH_INTERVAL', '86400'))
        
        # Check if auto-refresh is enabled
        auto_refresh_enabled = os.getenv('PROXY_AUTO_REFRESH', 'true').lower() == 'true'
        
        if not auto_refresh_enabled:
            logger.info("⏸️ Proxy auto-refresh is disabled (PROXY_AUTO_REFRESH=false)")
            return
        
        # Add refresh job
        self.scheduler.add_job(
            self.refresh_all_proxies,
            trigger=IntervalTrigger(seconds=interval_seconds),
            id='proxy_refresh',
            name='Proxy Pool Refresh',
            replace_existing=True,
            max_instances=1  # Prevent overlapping refreshes
        )
        
        # Add daily cleanup job at 3 AM
        self.scheduler.add_job(
            self._daily_cleanup,
            trigger=CronTrigger(hour=3, minute=0),
            id='proxy_cleanup',
            name='Daily Proxy Cleanup',
            replace_existing=True
        )
        
        self.scheduler.start()
        self.is_running = True
        
        hours = interval_seconds / 3600
        logger.info(f"✅ Proxy refresh scheduler started (interval: {hours:.1f} hours)")
        logger.info(f"📅 Next refresh: {self.scheduler.get_job('proxy_refresh').next_run_time}")
    
    async def _daily_cleanup(self):
        """Perform daily cleanup of old proxies"""
        try:
            logger.info("🧹 Running daily proxy cleanup...")
            
            from database import get_db_session, close_db_session
            from database.operations import ProxyService
            
            db = get_db_session()
            try:
                # Remove proxies inactive for 30+ days
                removed = ProxyService.cleanup_old_proxies(db, days_inactive=30)
                logger.info(f"✅ Daily cleanup: removed {removed} old proxies")
                
                # Get stats
                stats = ProxyService.get_proxy_stats(db)
                logger.info(f"📊 Current pool: {stats.get('active_proxies', 0)} active, {stats.get('total_proxies', 0)} total")
                
            finally:
                close_db_session(db)
                
        except Exception as e:
            logger.error(f"❌ Daily cleanup failed: {e}", exc_info=True)
    
    def stop(self):
        """Stop the scheduler"""
        if not self.is_running:
            logger.warning("Scheduler is not running")
            return
        
        self.scheduler.shutdown(wait=False)
        self.is_running = False
        logger.info("⏹️ Proxy refresh scheduler stopped")
    
    async def trigger_refresh_now(self) -> Dict[str, Any]:
        """Manually trigger a refresh immediately"""
        logger.info("🔄 Manual proxy refresh triggered")
        return await self.refresh_all_proxies()
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status"""
        status = {
            'running': self.is_running,
            'last_refresh': self.last_refresh.isoformat() if self.last_refresh else None,
            'stats': self.refresh_stats.copy()
        }
        
        if self.is_running and self.scheduler.get_job('proxy_refresh'):
            job = self.scheduler.get_job('proxy_refresh')
            status['next_refresh'] = job.next_run_time.isoformat() if job.next_run_time else None
        
        return status
    
    def get_next_refresh_time(self) -> datetime:
        """Get the next scheduled refresh time"""
        if not self.is_running:
            return None
        
        job = self.scheduler.get_job('proxy_refresh')
        return job.next_run_time if job else None


# Global scheduler instance
proxy_refresh_scheduler = ProxyRefreshScheduler()


# Convenience functions
def start_proxy_scheduler(interval_seconds: int = None):
    """Start the global proxy refresh scheduler"""
    proxy_refresh_scheduler.start(interval_seconds)


def stop_proxy_scheduler():
    """Stop the global proxy refresh scheduler"""
    proxy_refresh_scheduler.stop()


async def refresh_proxies_now() -> Dict[str, Any]:
    """Manually trigger proxy refresh"""
    return await proxy_refresh_scheduler.trigger_refresh_now()


def get_scheduler_status() -> Dict[str, Any]:
    """Get scheduler status"""
    return proxy_refresh_scheduler.get_status()


# Test/demo
if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    async def test_scheduler():
        print("\n" + "=" * 60)
        print("🧪 TESTING PROXY REFRESH SCHEDULER")
        print("=" * 60 + "\n")
        
        # Test immediate refresh
        print("📋 Testing immediate refresh...")
        results = await proxy_refresh_scheduler.trigger_refresh_now()
        
        print("\n📊 Refresh Results:")
        for source, data in results.items():
            if isinstance(data, dict):
                print(f"\n  {source.upper()}:")
                for key, value in data.items():
                    print(f"    {key}: {value}")
        
        # Show status
        print("\n📊 Scheduler Status:")
        status = proxy_refresh_scheduler.get_status()
        for key, value in status.items():
            print(f"  {key}: {value}")
        
        print("\n" + "=" * 60)
        print("✅ Test Complete")
        print("=" * 60 + "\n")
    
    asyncio.run(test_scheduler())

