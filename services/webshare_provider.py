"""
WebShare.io Proxy Provider Integration

Official API Documentation: https://proxy2.webshare.io/docs/

This service integrates with WebShare.io to fetch datacenter SOCKS5 proxies
for use in Telegram operations.
"""
import os
import sys
import logging
import aiohttp
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database.operations import ProxyService
from database import get_db_session, close_db_session

logger = logging.getLogger(__name__)


class WebShareProvider:
    """WebShare.io proxy provider integration."""
    
    def __init__(self, api_token: Optional[str] = None):
        """
        Initialize WebShare provider.
        
        Args:
            api_token: WebShare API token. If not provided, will read from env.
        """
        self.api_token = api_token or os.getenv('WEBSHARE_API_TOKEN')
        self.base_url = "https://proxy.webshare.io/api/v2"
        self.provider_name = "WebShare.io"
        
        if not self.api_token:
            logger.warning("⚠️ WEBSHARE_API_TOKEN not found in environment")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests."""
        return {
            'Authorization': f'Token {self.api_token}',
            'Content-Type': 'application/json'
        }
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to WebShare API.
        
        Returns:
            Dict with status, message, and optional error
        """
        if not self.api_token:
            return {
                'success': False,
                'message': 'API token not configured',
                'error': 'WEBSHARE_API_TOKEN not set in environment'
            }
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/proxy/list/?mode=direct&page=1&page_size=1"
                
                async with session.get(url, headers=self._get_headers(), timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            'success': True,
                            'message': 'Connection successful',
                            'total_proxies': data.get('count', 0)
                        }
                    elif response.status == 401:
                        return {
                            'success': False,
                            'message': 'Authentication failed',
                            'error': 'Invalid API token'
                        }
                    else:
                        error_text = await response.text()
                        return {
                            'success': False,
                            'message': f'HTTP {response.status}',
                            'error': error_text[:200]
                        }
        
        except asyncio.TimeoutError:
            return {
                'success': False,
                'message': 'Connection timeout',
                'error': 'Request timed out after 10 seconds'
            }
        except Exception as e:
            return {
                'success': False,
                'message': 'Connection error',
                'error': str(e)
            }
    
    async def fetch_proxies(self, page: int = 1, page_size: int = 100) -> Dict[str, Any]:
        """
        Fetch proxies from WebShare API.
        
        Args:
            page: Page number (1-indexed)
            page_size: Number of proxies per page (max 100)
            
        Returns:
            Dict with proxies list and metadata
        """
        if not self.api_token:
            logger.error("❌ Cannot fetch proxies: API token not configured")
            return {
                'success': False,
                'proxies': [],
                'error': 'API token not configured'
            }
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/proxy/list/?mode=direct&page={page}&page_size={page_size}"
                
                logger.info(f"🔍 Fetching proxies from {self.provider_name} (page {page})...")
                
                async with session.get(url, headers=self._get_headers(), timeout=15) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"❌ HTTP {response.status}: {error_text[:200]}")
                        return {
                            'success': False,
                            'proxies': [],
                            'error': f'HTTP {response.status}'
                        }
                    
                    data = await response.json()
                    
                    proxies = []
                    for item in data.get('results', []):
                        proxy = {
                            'ip_address': item.get('proxy_address'),
                            'port': item.get('port'),
                            'username': item.get('username'),
                            'password': item.get('password'),
                            'country_code': item.get('country_code'),
                            'proxy_type': 'datacenter',
                            'protocol': 'socks5',  # WebShare provides SOCKS5
                            'valid_until': item.get('valid'),
                            'provider': self.provider_name
                        }
                        proxies.append(proxy)
                    
                    logger.info(f"✅ Fetched {len(proxies)} proxies from {self.provider_name}")
                    
                    return {
                        'success': True,
                        'proxies': proxies,
                        'total_count': data.get('count', 0),
                        'page': page,
                        'page_size': page_size,
                        'has_next': data.get('next') is not None
                    }
        
        except asyncio.TimeoutError:
            logger.error(f"❌ Timeout fetching proxies from {self.provider_name}")
            return {
                'success': False,
                'proxies': [],
                'error': 'Request timeout'
            }
        except Exception as e:
            logger.error(f"❌ Error fetching proxies from {self.provider_name}: {e}")
            return {
                'success': False,
                'proxies': [],
                'error': str(e)
            }
    
    async def fetch_all_proxies(self, max_pages: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch all available proxies from WebShare (with pagination).
        
        Args:
            max_pages: Maximum number of pages to fetch
            
        Returns:
            List of all proxy dictionaries
        """
        all_proxies = []
        page = 1
        
        while page <= max_pages:
            result = await self.fetch_proxies(page=page, page_size=100)
            
            if not result['success']:
                logger.error(f"Failed to fetch page {page}: {result.get('error')}")
                break
            
            proxies = result['proxies']
            all_proxies.extend(proxies)
            
            logger.info(f"📊 Fetched page {page}: {len(proxies)} proxies (total: {len(all_proxies)})")
            
            if not result.get('has_next'):
                break
            
            page += 1
        
        logger.info(f"✅ Total proxies fetched: {len(all_proxies)}")
        return all_proxies
    
    async def import_to_database(self, db=None, max_proxies: Optional[int] = None) -> Dict[str, Any]:
        """
        Fetch proxies from WebShare and import to database.
        
        Args:
            db: Database session (will create one if not provided)
            max_proxies: Maximum number of proxies to import (None = all)
            
        Returns:
            Dict with import statistics
        """
        should_close_db = False
        if db is None:
            db = get_db_session()
            should_close_db = True
        
        try:
            # Fetch proxies
            max_pages = (max_proxies // 100 + 1) if max_proxies else 10
            proxies = await self.fetch_all_proxies(max_pages=max_pages)
            
            if not proxies:
                return {
                    'success': False,
                    'imported': 0,
                    'skipped': 0,
                    'failed': 0,
                    'error': 'No proxies fetched'
                }
            
            # Limit if requested
            if max_proxies:
                proxies = proxies[:max_proxies]
            
            # Import to database
            imported = 0
            skipped = 0
            failed = 0
            
            logger.info(f"📦 Importing {len(proxies)} proxies to database...")
            
            for proxy_data in proxies:
                try:
                    # Check if proxy already exists
                    from database.models import ProxyPool
                    existing = db.query(ProxyPool).filter_by(
                        ip_address=proxy_data['ip_address'],
                        port=proxy_data['port']
                    ).first()
                    
                    if existing:
                        # Update existing proxy
                        existing.is_active = True
                        existing.username = proxy_data.get('username')
                        if proxy_data.get('password'):
                            existing.set_encrypted_password(proxy_data['password'])
                        existing.country_code = proxy_data.get('country_code')
                        existing.proxy_type = proxy_data.get('proxy_type', 'datacenter')
                        db.commit()
                        skipped += 1
                    else:
                        # Add new proxy
                        ProxyService.add_proxy(
                            db=db,
                            ip_address=proxy_data['ip_address'],
                            port=proxy_data['port'],
                            username=proxy_data.get('username'),
                            password=proxy_data.get('password'),
                            country_code=proxy_data.get('country_code'),
                            provider='webshare'  # Mark as WebShare provider
                        )
                        imported += 1
                    
                except Exception as e:
                    logger.error(f"❌ Failed to import {proxy_data['ip_address']}:{proxy_data['port']}: {e}")
                    failed += 1
            
            logger.info(f"✅ Import complete: {imported} new, {skipped} updated, {failed} failed")
            
            return {
                'success': True,
                'imported': imported,
                'skipped': skipped,
                'failed': failed,
                'total': len(proxies)
            }
        
        except Exception as e:
            logger.error(f"❌ Import error: {e}")
            return {
                'success': False,
                'imported': 0,
                'skipped': 0,
                'failed': 0,
                'error': str(e)
            }
        finally:
            if should_close_db:
                close_db_session(db)
    
    async def get_account_info(self) -> Dict[str, Any]:
        """
        Get WebShare account information (bandwidth, proxy count, etc.).
        
        Returns:
            Dict with account information
        """
        if not self.api_token:
            return {
                'success': False,
                'error': 'API token not configured'
            }
        
        try:
            async with aiohttp.ClientSession() as session:
                # Get subscription info
                url = f"{self.base_url}/subscription/"
                
                async with session.get(url, headers=self._get_headers(), timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        return {
                            'success': True,
                            'bandwidth_used': data.get('bandwidth_used', 0),
                            'bandwidth_limit': data.get('bandwidth_limit', 0),
                            'proxy_count': data.get('proxy_count', 0),
                            'plan': data.get('subscription_type', 'Unknown'),
                            'status': data.get('status', 'Unknown')
                        }
                    else:
                        error_text = await response.text()
                        return {
                            'success': False,
                            'error': f'HTTP {response.status}: {error_text[:200]}'
                        }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


# Global instance
webshare_provider = WebShareProvider()


async def refresh_webshare_proxies(max_proxies: Optional[int] = None) -> Dict[str, Any]:
    """
    Convenience function to refresh proxies from WebShare.io.
    
    Args:
        max_proxies: Maximum number of proxies to import
        
    Returns:
        Import statistics
    """
    return await webshare_provider.import_to_database(max_proxies=max_proxies)


if __name__ == "__main__":
    # Test WebShare integration
    import sys
    
    async def test():
        print("🧪 Testing WebShare.io Integration")
        print("=" * 60)
        
        provider = WebShareProvider()
        
        # Test 1: Connection
        print("\n1️⃣  Testing API Connection...")
        result = await provider.test_connection()
        if result['success']:
            print(f"✅ Connection successful!")
            print(f"   Total proxies available: {result.get('total_proxies', 'N/A')}")
        else:
            print(f"❌ Connection failed: {result['message']}")
            print(f"   Error: {result.get('error')}")
            if 'API token' in result.get('error', ''):
                print(f"\n💡 To fix: Add WEBSHARE_API_TOKEN to your .env file")
                print(f"   Get your token at: https://proxy.webshare.io/userapi/")
            sys.exit(1)
        
        # Test 2: Fetch proxies
        print("\n2️⃣  Fetching First Page of Proxies...")
        fetch_result = await provider.fetch_proxies(page=1, page_size=5)
        if fetch_result['success']:
            proxies = fetch_result['proxies']
            print(f"✅ Fetched {len(proxies)} proxies")
            print(f"   Total available: {fetch_result.get('total_count', 'N/A')}")
            
            # Show samples
            print(f"\n📋 Sample proxies:")
            for i, p in enumerate(proxies[:3]):
                print(f"   {i+1}. {p['ip_address']}:{p['port']} ({p.get('country_code', 'Unknown')})")
        else:
            print(f"❌ Fetch failed: {fetch_result.get('error')}")
        
        # Test 3: Account info
        print("\n3️⃣  Getting Account Information...")
        account = await provider.get_account_info()
        if account['success']:
            print(f"✅ Account info retrieved:")
            print(f"   Plan: {account.get('plan')}")
            print(f"   Proxies: {account.get('proxy_count')}")
            print(f"   Bandwidth: {account.get('bandwidth_used')} / {account.get('bandwidth_limit')}")
        else:
            print(f"❌ Account info failed: {account.get('error')}")
        
        print("\n" + "=" * 60)
        print("✅ WebShare.io integration test complete!")
    
    asyncio.run(test())
