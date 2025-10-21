"""
Daily proxy rotation and maintenance system.
Handles automatic proxy rotation, health checks, and cleanup.
"""
import logging
import asyncio
from datetime import datetime, time, timezone
from typing import Dict, Any, Optional
from services.proxy_manager import proxy_manager

logger = logging.getLogger(__name__)

class DailyProxyRotator:
    """Manages daily proxy rotation and maintenance tasks."""
    
    def __init__(self):
        self.is_running = False
        self.last_rotation = None
        self.rotation_interval_hours = 24  # Rotate every 24 hours
        
    async def start_daily_rotation(self):
        """Start the daily proxy rotation scheduler."""
        if self.is_running:
            logger.warning("Daily proxy rotation is already running")
            return
        
        self.is_running = True
        logger.info("Starting daily proxy rotation scheduler")
        
        try:
            while self.is_running:
                await self._wait_until_next_rotation()
                await self._perform_daily_rotation()
        except Exception as e:
            logger.error(f"Daily proxy rotation scheduler failed: {e}")
        finally:
            self.is_running = False
    
    def stop_daily_rotation(self):
        """Stop the daily proxy rotation scheduler."""
        logger.info("Stopping daily proxy rotation scheduler")
        self.is_running = False
    
    async def _wait_until_next_rotation(self):
        """Wait until the next rotation time."""
        current_time = datetime.now(timezone.utc)
        
        # Calculate next rotation time (next midnight UTC)
        next_rotation = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        if next_rotation <= current_time:
            next_rotation = next_rotation.replace(day=next_rotation.day + 1)
        
        wait_seconds = (next_rotation - current_time).total_seconds()
        
        logger.info(f"Next proxy rotation scheduled in {wait_seconds:.0f} seconds (at {next_rotation})")
        await asyncio.sleep(wait_seconds)
    
    async def _perform_daily_rotation(self):
        """Perform the daily proxy rotation tasks."""
        try:
            logger.info("Starting daily proxy rotation...")
            
            # Perform health check
            health_result = proxy_manager.perform_health_check()
            logger.info(f"Health check result: {health_result}")
            
            # Perform rotation
            rotation_result = proxy_manager.rotate_daily_proxies()
            logger.info(f"Daily rotation result: {rotation_result}")
            
            # Update last rotation timestamp
            self.last_rotation = datetime.now(timezone.utc)
            
            # Log summary
            self._log_rotation_summary(health_result, rotation_result)
            
        except Exception as e:
            logger.error(f"Daily proxy rotation failed: {e}")
    
    def _log_rotation_summary(self, health_result: Dict[str, Any], rotation_result: Dict[str, Any]):
        """Log a summary of the rotation results."""
        try:
            summary = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "health_check": {
                    "status": health_result.get("status"),
                    "total_proxies": health_result.get("total_proxies", 0),
                    "active_proxies": health_result.get("active_proxies", 0),
                    "tested_count": health_result.get("tested_count", 0),
                    "working_count": health_result.get("working_count", 0),
                    "success_rate": health_result.get("success_rate", 0)
                },
                "rotation": {
                    "status": rotation_result.get("status"),
                    "cleaned_proxies": rotation_result.get("cleaned_proxies", 0),
                    "refresh_success": rotation_result.get("refresh_success", False),
                    "current_stats": rotation_result.get("current_stats", {})
                }
            }
            
            logger.info(f"Daily proxy rotation summary: {summary}")
            
        except Exception as e:
            logger.error(f"Failed to log rotation summary: {e}")
    
    async def force_rotation_now(self) -> Dict[str, Any]:
        """Force an immediate proxy rotation (for manual triggering)."""
        try:
            logger.info("Forcing immediate proxy rotation...")
            
            # Perform health check
            health_result = proxy_manager.perform_health_check()
            
            # Perform rotation
            rotation_result = proxy_manager.rotate_daily_proxies()
            
            # Update last rotation timestamp
            self.last_rotation = datetime.now(timezone.utc)
            
            result = {
                "status": "completed",
                "forced": True,
                "timestamp": self.last_rotation.isoformat(),
                "health_check": health_result,
                "rotation": rotation_result
            }
            
            logger.info(f"Force rotation completed: {result}")
            return result
            
        except Exception as e:
            error_result = {
                "status": "error",
                "forced": True,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            logger.error(f"Force rotation failed: {error_result}")
            return error_result
    
    def get_rotation_status(self) -> Dict[str, Any]:
        """Get the current status of the proxy rotation system."""
        return {
            "is_running": self.is_running,
            "last_rotation": self.last_rotation.isoformat() if self.last_rotation else None,
            "rotation_interval_hours": self.rotation_interval_hours,
            "next_rotation": self._calculate_next_rotation_time()
        }
    
    def _calculate_next_rotation_time(self) -> Optional[str]:
        """Calculate when the next rotation will occur."""
        if not self.last_rotation:
            return None
        
        next_rotation = self.last_rotation.replace(hour=0, minute=0, second=0, microsecond=0)
        if next_rotation <= self.last_rotation:
            next_rotation = next_rotation.replace(day=next_rotation.day + 1)
        
        return next_rotation.isoformat()

# Global instance
daily_proxy_rotator = DailyProxyRotator()

async def start_proxy_rotation_scheduler():
    """Start the proxy rotation scheduler (call this from main application)."""
    await daily_proxy_rotator.start_daily_rotation()

def stop_proxy_rotation_scheduler():
    """Stop the proxy rotation scheduler."""
    daily_proxy_rotator.stop_daily_rotation()

async def force_proxy_rotation() -> Dict[str, Any]:
    """Force an immediate proxy rotation."""
    return await daily_proxy_rotator.force_rotation_now()

def get_proxy_rotation_status() -> Dict[str, Any]:
    """Get the current proxy rotation status."""
    return daily_proxy_rotator.get_rotation_status()
