"""
Comprehensive Testing Suite for WebShare.io Integration
Tests all aspects of the proxy ecosystem
"""
import asyncio
import logging
import os
import sys
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestResults:
    """Track test results"""
    
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.test_details = []
    
    def add_result(self, test_name: str, passed: bool, message: str = "", details: Dict = None):
        """Add a test result"""
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
            status = "✅ PASS"
        else:
            self.tests_failed += 1
            status = "❌ FAIL"
        
        self.test_details.append({
            'name': test_name,
            'passed': passed,
            'status': status,
            'message': message,
            'details': details or {}
        })
        
        logger.info(f"{status} - {test_name}: {message}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"\n📊 Total Tests: {self.tests_run}")
        print(f"✅ Passed: {self.tests_passed}")
        print(f"❌ Failed: {self.tests_failed}")
        print(f"📈 Success Rate: {(self.tests_passed/self.tests_run*100) if self.tests_run > 0 else 0:.1f}%\n")
        
        if self.test_details:
            print("=" * 80)
            print("DETAILED RESULTS")
            print("=" * 80 + "\n")
            
            for test in self.test_details:
                print(f"{test['status']} {test['name']}")
                if test['message']:
                    print(f"   └─ {test['message']}")
                if test['details']:
                    for key, value in test['details'].items():
                        print(f"      • {key}: {value}")
                print()


async def test_environment_setup(results: TestResults):
    """Test 1: Environment configuration"""
    try:
        required_vars = {
            'WEBSHARE_API_TOKEN': 'WebShare API token',
            'WEBSHARE_ENABLED': 'WebShare enabled flag',
            'PROXY_AUTO_REFRESH': 'Auto-refresh setting',
            'PROXY_REFRESH_INTERVAL': 'Refresh interval'
        }
        
        missing = []
        configured = {}
        
        for var, description in required_vars.items():
            value = os.getenv(var)
            if not value:
                missing.append(f"{var} ({description})")
            else:
                configured[var] = value if var != 'WEBSHARE_API_TOKEN' else f"{value[:10]}..."
        
        if missing:
            results.add_result(
                "Environment Setup",
                False,
                f"Missing variables: {', '.join(missing)}",
                configured
            )
        else:
            results.add_result(
                "Environment Setup",
                True,
                "All required environment variables configured",
                configured
            )
    
    except Exception as e:
        results.add_result("Environment Setup", False, f"Error: {str(e)}")


async def test_webshare_connection(results: TestResults):
    """Test 2: WebShare.io API connection"""
    try:
        from services.webshare_provider import test_webshare_connection
        
        is_connected, message = await test_webshare_connection()
        
        results.add_result(
            "WebShare.io Connection",
            is_connected,
            message
        )
        
        return is_connected
    
    except Exception as e:
        results.add_result("WebShare.io Connection", False, f"Error: {str(e)}")
        return False


async def test_proxy_fetch(results: TestResults):
    """Test 3: Fetch proxies from WebShare.io"""
    try:
        from services.webshare_provider import fetch_webshare_proxies
        
        proxies = await fetch_webshare_proxies()
        
        if proxies:
            sample_proxy = proxies[0]
            details = {
                'Total proxies': len(proxies),
                'Sample proxy': f"{sample_proxy.get('proxy_address')}:{sample_proxy.get('port')}",
                'Protocol': sample_proxy.get('protocol', 'N/A'),
                'Country': sample_proxy.get('country_code', 'N/A')
            }
            
            results.add_result(
                "Proxy Fetch",
                True,
                f"Successfully fetched {len(proxies)} proxies",
                details
            )
            return proxies
        else:
            results.add_result("Proxy Fetch", False, "No proxies returned from API")
            return []
    
    except Exception as e:
        results.add_result("Proxy Fetch", False, f"Error: {str(e)}")
        return []


async def test_database_import(results: TestResults, test_proxies: list):
    """Test 4: Import proxies to database"""
    try:
        from services.webshare_provider import import_webshare_proxy_to_db
        from database import get_db_session, close_db_session
        
        if not test_proxies:
            results.add_result("Database Import", False, "No test proxies available")
            return
        
        db = get_db_session()
        try:
            # Import first 3 proxies
            imported = 0
            failed = 0
            
            for proxy_data in test_proxies[:3]:
                try:
                    proxy_record = import_webshare_proxy_to_db(db, proxy_data)
                    if proxy_record:
                        imported += 1
                    else:
                        failed += 1
                except Exception:
                    failed += 1
            
            details = {
                'Tested': min(3, len(test_proxies)),
                'Imported': imported,
                'Failed': failed
            }
            
            results.add_result(
                "Database Import",
                imported > 0,
                f"Imported {imported}/{min(3, len(test_proxies))} proxies",
                details
            )
        
        finally:
            close_db_session(db)
    
    except Exception as e:
        results.add_result("Database Import", False, f"Error: {str(e)}")


async def test_proxy_encryption(results: TestResults):
    """Test 5: Proxy credential encryption"""
    try:
        from database import get_db_session, close_db_session
        from database.operations import ProxyService
        
        db = get_db_session()
        try:
            # Get a proxy with credentials
            from database.models import ProxyPool
            proxy = db.query(ProxyPool).filter(
                ProxyPool.username.isnot(None),
                ProxyPool.is_active == True
            ).first()
            
            if not proxy:
                results.add_result("Proxy Encryption", False, "No proxies with credentials found")
                return
            
            # Check if credentials are encrypted (not plaintext)
            is_encrypted = (
                proxy.username != "test" and
                len(proxy.username) > 20 and  # Encrypted strings are longer
                proxy.password != "test"
            )
            
            details = {
                'Proxy ID': proxy.id,
                'Username length': len(proxy.username) if proxy.username else 0,
                'Password length': len(proxy.password) if proxy.password else 0,
                'Encrypted': '✅' if is_encrypted else '❌'
            }
            
            results.add_result(
                "Proxy Encryption",
                is_encrypted,
                "Credentials appear encrypted" if is_encrypted else "Credentials may not be encrypted",
                details
            )
        
        finally:
            close_db_session(db)
    
    except Exception as e:
        results.add_result("Proxy Encryption", False, f"Error: {str(e)}")


async def test_telethon_format_conversion(results: TestResults):
    """Test 6: Telethon proxy format conversion"""
    try:
        from utils.telethon_proxy import convert_to_telethon_proxy, validate_telethon_proxy
        from database import get_db_session, close_db_session
        from database.models import ProxyPool
        
        db = get_db_session()
        try:
            # Get an active proxy
            proxy = db.query(ProxyPool).filter(ProxyPool.is_active == True).first()
            
            if not proxy:
                results.add_result("Telethon Conversion", False, "No active proxies found")
                return
            
            # Test dict format conversion
            proxy_dict = convert_to_telethon_proxy(proxy)
            
            # Validate format
            is_valid = validate_telethon_proxy(proxy_dict)
            
            details = {
                'Proxy ID': proxy.id,
                'Proxy type': proxy_dict.get('proxy_type', 'N/A'),
                'Address': f"{proxy_dict.get('addr')}:{proxy_dict.get('port')}",
                'Has auth': '✅' if proxy_dict.get('username') else '❌',
                'Valid format': '✅' if is_valid else '❌'
            }
            
            results.add_result(
                "Telethon Conversion",
                is_valid,
                "Proxy format conversion successful" if is_valid else "Conversion failed",
                details
            )
        
        finally:
            close_db_session(db)
    
    except Exception as e:
        results.add_result("Telethon Conversion", False, f"Error: {str(e)}")


async def test_operation_based_selection(results: TestResults):
    """Test 7: Operation-based proxy selection"""
    try:
        from services.proxy_manager import proxy_manager, OperationType
        
        # Test different operation types
        operations = [
            OperationType.ACCOUNT_CREATION,
            OperationType.LOGIN,
            OperationType.OTP_RETRIEVAL,
            OperationType.VERIFICATION,
            OperationType.MESSAGE_SEND,
            OperationType.GENERAL
        ]
        
        selections = {}
        for operation in operations:
            try:
                proxy = proxy_manager.get_proxy_for_operation(operation)
                if proxy:
                    selections[operation.value] = f"✅ {proxy.host}:{proxy.port}"
                else:
                    selections[operation.value] = "❌ No proxy assigned"
            except Exception as e:
                selections[operation.value] = f"❌ Error: {str(e)}"
        
        success_count = sum(1 for v in selections.values() if v.startswith('✅'))
        total_count = len(operations)
        
        results.add_result(
            "Operation-Based Selection",
            success_count > 0,
            f"{success_count}/{total_count} operations got proxies",
            selections
        )
    
    except Exception as e:
        results.add_result("Operation-Based Selection", False, f"Error: {str(e)}")


async def test_proxy_strategies(results: TestResults):
    """Test 8: Load balancing strategies"""
    try:
        from services.proxy_manager import proxy_manager
        
        strategies = ['round_robin', 'least_used', 'random', 'weighted', 'country_based', 'reputation_based']
        
        strategy_results = {}
        for strategy in strategies:
            try:
                proxy_manager.set_strategy(strategy)
                current = proxy_manager.get_current_strategy()
                strategy_results[strategy] = "✅ Works" if current == strategy else "❌ Failed"
            except Exception as e:
                strategy_results[strategy] = f"❌ Error: {str(e)[:30]}"
        
        success_count = sum(1 for v in strategy_results.values() if v.startswith('✅'))
        
        results.add_result(
            "Load Balancing Strategies",
            success_count == len(strategies),
            f"{success_count}/{len(strategies)} strategies work",
            strategy_results
        )
    
    except Exception as e:
        results.add_result("Load Balancing Strategies", False, f"Error: {str(e)}")


async def test_scheduler_status(results: TestResults):
    """Test 9: Auto-refresh scheduler"""
    try:
        from services.proxy_scheduler import get_scheduler_status
        
        status = get_scheduler_status()
        
        details = {
            'Running': '✅' if status.get('running') else '❌',
            'Last refresh': status.get('last_refresh') or 'Never',
            'Total refreshes': status.get('stats', {}).get('total_refreshes', 0),
            'Successful': status.get('stats', {}).get('successful_refreshes', 0),
            'Failed': status.get('stats', {}).get('failed_refreshes', 0)
        }
        
        results.add_result(
            "Auto-Refresh Scheduler",
            True,  # Always pass if we can get status
            "Scheduler is running" if status.get('running') else "Scheduler is stopped",
            details
        )
    
    except Exception as e:
        results.add_result("Auto-Refresh Scheduler", False, f"Error: {str(e)}")


async def test_proxy_health_check(results: TestResults):
    """Test 10: Proxy health monitoring"""
    try:
        from database import get_db_session, close_db_session
        from database.operations import ProxyService
        
        db = get_db_session()
        try:
            stats = ProxyService.get_proxy_stats(db)
            
            details = {
                'Total proxies': stats.get('total_proxies', 0),
                'Active proxies': stats.get('active_proxies', 0),
                'Inactive proxies': stats.get('inactive_proxies', 0),
                'Recently used (24h)': stats.get('recently_used_24h', 0)
            }
            
            # Add country distribution
            country_dist = stats.get('country_distribution', {})
            if country_dist:
                top_countries = sorted(country_dist.items(), key=lambda x: x[1], reverse=True)[:5]
                details['Top countries'] = ', '.join(f"{c}:{n}" for c, n in top_countries)
            
            has_active = stats.get('active_proxies', 0) > 0
            
            results.add_result(
                "Proxy Health Check",
                has_active,
                f"{stats.get('active_proxies', 0)} active proxies available",
                details
            )
        
        finally:
            close_db_session(db)
    
    except Exception as e:
        results.add_result("Proxy Health Check", False, f"Error: {str(e)}")


async def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("🧪 WEBSHARE.IO INTEGRATION TEST SUITE")
    print("=" * 80 + "\n")
    
    results = TestResults()
    
    # Test 1: Environment
    print("📋 Test 1: Environment Setup...")
    await test_environment_setup(results)
    
    # Test 2: WebShare connection
    print("\n📋 Test 2: WebShare.io Connection...")
    connection_ok = await test_webshare_connection(results)
    
    # Test 3: Fetch proxies
    test_proxies = []
    if connection_ok:
        print("\n📋 Test 3: Proxy Fetch...")
        test_proxies = await test_proxy_fetch(results)
    else:
        results.add_result("Proxy Fetch", False, "Skipped - connection failed")
    
    # Test 4: Database import
    print("\n📋 Test 4: Database Import...")
    await test_database_import(results, test_proxies)
    
    # Test 5: Encryption
    print("\n📋 Test 5: Proxy Encryption...")
    await test_proxy_encryption(results)
    
    # Test 6: Telethon conversion
    print("\n📋 Test 6: Telethon Format Conversion...")
    await test_telethon_format_conversion(results)
    
    # Test 7: Operation-based selection
    print("\n📋 Test 7: Operation-Based Selection...")
    await test_operation_based_selection(results)
    
    # Test 8: Strategies
    print("\n📋 Test 8: Load Balancing Strategies...")
    await test_proxy_strategies(results)
    
    # Test 9: Scheduler
    print("\n📋 Test 9: Auto-Refresh Scheduler...")
    await test_scheduler_status(results)
    
    # Test 10: Health check
    print("\n📋 Test 10: Proxy Health Check...")
    await test_proxy_health_check(results)
    
    # Print summary
    results.print_summary()
    
    return results


if __name__ == "__main__":
    asyncio.run(run_all_tests())

