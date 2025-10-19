"""
Proxy health monitoring and failure tracking system.
Monitors proxy performance, tracks failures, and manages proxy lifecycle.
"""
import logging
import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from services.proxy_manager import proxy_manager, ProxyConfig
from database.operations import ProxyService
from database import get_db_session, close_db_session

logger = logging.getLogger(__name__)

@dataclass
class ProxyHealthMetrics:
    """Health metrics for a proxy."""
    proxy_id: int
    response_time: float
    success_rate: float
    total_tests: int
    consecutive_failures: int
    last_tested: datetime
    is_healthy: bool

class ProxyHealthMonitor:
    """Monitors proxy health and manages proxy lifecycle."""
    
    def __init__(self):
        self.is_monitoring = False
        self.monitor_interval = 300  # 5 minutes between checks
        self.max_consecutive_failures = 3
        self.health_history: Dict[int, List[ProxyHealthMetrics]] = {}
        
    async def start_monitoring(self):
        """Start the proxy health monitoring system."""
        if self.is_monitoring:
            logger.warning("Proxy health monitoring is already running")
            return
        
        self.is_monitoring = True
        logger.info("Starting proxy health monitoring")
        
        try:
            while self.is_monitoring:
                await self._perform_health_checks()
                await asyncio.sleep(self.monitor_interval)
        except Exception as e:
            logger.error(f"Proxy health monitoring failed: {e}")
        finally:
            self.is_monitoring = False
    
    def stop_monitoring(self):
        """Stop the proxy health monitoring system."""
        logger.info("Stopping proxy health monitoring")
        self.is_monitoring = False
    
    async def _perform_health_checks(self):
        """Perform health checks on active proxies."""
        try:
            db = get_db_session()
            
            # Get all active proxies
            active_proxies = ProxyService.get_all_proxies(db)
            
            if not active_proxies:
                logger.info("No active proxies to monitor")
                close_db_session(db)
                return
            
            logger.info(f"Monitoring health of {len(active_proxies)} active proxies")
            
            # Test proxies in parallel (with concurrency limit)
            semaphore = asyncio.Semaphore(10)  # Max 10 concurrent tests
            
            async def test_proxy_with_semaphore(proxy_record):
                async with semaphore:
                    return await self._test_proxy_health(proxy_record)
            
            # Run health tests
            tasks = [test_proxy_with_semaphore(proxy) for proxy in active_proxies]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            healthy_count = 0
            failed_count = 0
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Health test failed for proxy {active_proxies[i].id}: {result}")
                    failed_count += 1
                    continue
                
                proxy_record, is_healthy, response_time = result
                
                if is_healthy:
                    healthy_count += 1
                    # Reset consecutive failures
                    self._update_proxy_health(proxy_record.id, True, response_time)
                else:
                    failed_count += 1
                    # Increment consecutive failures
                    consecutive_failures = self._update_proxy_health(proxy_record.id, False, response_time)
                    
                    # Deactivate if too many consecutive failures
                    if consecutive_failures >= self.max_consecutive_failures:
                        ProxyService.deactivate_proxy(db, proxy_record.id, f"Too many consecutive failures ({consecutive_failures})")
                        logger.warning(f"Deactivated proxy {proxy_record.id} due to {consecutive_failures} consecutive failures")
            
            close_db_session(db)
            
            logger.info(f"Health check completed: {healthy_count} healthy, {failed_count} failed")
            
        except Exception as e:
            logger.error(f"Health check cycle failed: {e}")
            if 'db' in locals():
                close_db_session(db)
    
    async def _test_proxy_health(self, proxy_record) -> Tuple[Any, bool, float]:
        """Test the health of a single proxy."""
        proxy_config = ProxyConfig(
            proxy_type='HTTP',
            host=proxy_record.ip_address,
            port=proxy_record.port,
            username=proxy_record.username,
            password=proxy_record.password
        )
        
        start_time = time.time()
        try:
            # Perform connectivity test
            is_working = proxy_manager.test_proxy_connectivity(proxy_config)
            response_time = time.time() - start_time
            
            return proxy_record, is_working, response_time
            
        except Exception as e:
            response_time = time.time() - start_time
            logger.warning(f"Health test error for proxy {proxy_record.id}: {e}")
            return proxy_record, False, response_time
    
    def _update_proxy_health(self, proxy_id: int, success: bool, response_time: float) -> int:
        """Update health metrics for a proxy and return consecutive failures."""
        if proxy_id not in self.health_history:
            self.health_history[proxy_id] = []
        
        # Create new metrics
        metrics = ProxyHealthMetrics(
            proxy_id=proxy_id,
            response_time=response_time,
            success_rate=1.0 if success else 0.0,
            total_tests=1,
            consecutive_failures=0 if success else 1,
            last_tested=datetime.now(timezone.utc),
            is_healthy=success
        )
        
        # Calculate consecutive failures
        history = self.health_history[proxy_id]
        if history:
            last_metrics = history[-1]
            if success:
                metrics.consecutive_failures = 0
            else:
                metrics.consecutive_failures = last_metrics.consecutive_failures + 1
            
            # Calculate success rate over last 10 tests
            recent_tests = history[-9:] + [metrics]  # Last 9 + current
            success_count = sum(1 for m in recent_tests if m.is_healthy)
            metrics.success_rate = success_count / len(recent_tests)
            metrics.total_tests = sum(m.total_tests for m in recent_tests)
        
        # Keep only last 50 metrics
        self.health_history[proxy_id].append(metrics)
        if len(self.health_history[proxy_id]) > 50:
            self.health_history[proxy_id] = self.health_history[proxy_id][-50:]
        
        return metrics.consecutive_failures
    
    def get_proxy_health_report(self, proxy_id: Optional[int] = None) -> Dict[str, Any]:
        """Get health report for a specific proxy or all proxies."""
        try:
            if proxy_id:
                return self._get_single_proxy_report(proxy_id)
            else:
                return self._get_all_proxies_report()
        except Exception as e:
            logger.error(f"Failed to get health report: {e}")
            return {"error": str(e)}
    
    def _get_single_proxy_report(self, proxy_id: int) -> Dict[str, Any]:
        """Get health report for a single proxy."""
        if proxy_id not in self.health_history:
            return {"proxy_id": proxy_id, "status": "no_data"}
        
        history = self.health_history[proxy_id]
        if not history:
            return {"proxy_id": proxy_id, "status": "no_data"}
        
        latest = history[-1]
        
        # Calculate averages
        recent_tests = history[-10:]  # Last 10 tests
        avg_response_time = sum(m.response_time for m in recent_tests) / len(recent_tests)
        avg_success_rate = sum(m.success_rate for m in recent_tests) / len(recent_tests)
        
        return {
            "proxy_id": proxy_id,
            "status": "healthy" if latest.is_healthy else "unhealthy",
            "current_health": latest.is_healthy,
            "consecutive_failures": latest.consecutive_failures,
            "last_tested": latest.last_tested.isoformat(),
            "average_response_time": round(avg_response_time, 3),
            "average_success_rate": round(avg_success_rate, 3),
            "total_tests": latest.total_tests,
            "recent_performance": [
                {
                    "tested_at": m.last_tested.isoformat(),
                    "healthy": m.is_healthy,
                    "response_time": round(m.response_time, 3),
                    "consecutive_failures": m.consecutive_failures
                }
                for m in recent_tests[-5:]  # Last 5 tests
            ]
        }
    
    def _get_all_proxies_report(self) -> Dict[str, Any]:
        """Get health report for all proxies."""
        reports = {}
        summary = {
            "total_proxies": len(self.health_history),
            "healthy_proxies": 0,
            "unhealthy_proxies": 0,
            "average_success_rate": 0.0,
            "total_tests": 0
        }
        
        success_rates = []
        
        for proxy_id in self.health_history:
            report = self._get_single_proxy_report(proxy_id)
            reports[str(proxy_id)] = report
            
            if report.get("current_health"):
                summary["healthy_proxies"] += 1
            else:
                summary["unhealthy_proxies"] += 1
            
            if "average_success_rate" in report:
                success_rates.append(report["average_success_rate"])
            
            summary["total_tests"] += report.get("total_tests", 0)
        
        if success_rates:
            summary["average_success_rate"] = round(sum(success_rates) / len(success_rates), 3)
        
        return {
            "summary": summary,
            "proxies": reports
        }
    
    def get_unhealthy_proxies(self) -> List[int]:
        """Get list of proxy IDs that are currently unhealthy."""
        unhealthy = []
        for proxy_id, history in self.health_history.items():
            if history and not history[-1].is_healthy:
                unhealthy.append(proxy_id)
        return unhealthy
    
    def reset_proxy_health(self, proxy_id: int):
        """Reset health history for a proxy (useful after manual reactivation)."""
        if proxy_id in self.health_history:
            self.health_history[proxy_id] = []
            logger.info(f"Reset health history for proxy {proxy_id}")

# Global instance
proxy_health_monitor = ProxyHealthMonitor()

async def start_proxy_health_monitoring():
    """Start the proxy health monitoring system."""
    await proxy_health_monitor.start_monitoring()

def stop_proxy_health_monitoring():
    """Stop the proxy health monitoring system."""
    proxy_health_monitor.stop_monitoring()

def get_proxy_health_report(proxy_id: Optional[int] = None) -> Dict[str, Any]:
    """Get proxy health report."""
    return proxy_health_monitor.get_proxy_health_report(proxy_id)

def get_unhealthy_proxies() -> List[int]:
    """Get list of unhealthy proxy IDs."""
    return proxy_health_monitor.get_unhealthy_proxies()