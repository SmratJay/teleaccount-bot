"""
Free proxy source integrations.

This module provides integrations with free proxy list providers to automatically
populate the proxy pool.
"""
import asyncio
import aiohttp
import logging
import re
from typing import List, Dict, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ProxySourceIntegration:
    """Base class for proxy source integrations."""
    
    def __init__(self):
        self.name = "Generic Proxy Source"
    
    async def fetch_proxies(self) -> List[Dict[str, any]]:
        """
        Fetch proxies from the source.
        
        Returns:
            List of proxy dicts with keys: ip_address, port, country_code, proxy_type
        """
        raise NotImplementedError


class FreeProxyListNet(ProxySourceIntegration):
    """Integration with free-proxy-list.net"""
    
    def __init__(self):
        super().__init__()
        self.name = "Free-Proxy-List.net"
        self.url = "https://free-proxy-list.net/"
    
    async def fetch_proxies(self) -> List[Dict[str, any]]:
        """Fetch proxies from free-proxy-list.net"""
        proxies = []
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.url, timeout=10) as response:
                    if response.status != 200:
                        logger.warning(f"❌ {self.name}: HTTP {response.status}")
                        return proxies
                    
                    html = await response.text()
                    
                    # Parse HTML table (simple regex approach)
                    # Format: <td>IP</td><td>PORT</td><td>COUNTRY</td><td>...</td><td>HTTPS</td>
                    pattern = r'<tr><td>(\d+\.\d+\.\d+\.\d+)</td><td>(\d+)</td><td>(\w+)</td>.*?<td>(yes|no)</td>'
                    matches = re.findall(pattern, html, re.IGNORECASE)
                    
                    for ip, port, country, https in matches:
                        proxies.append({
                            'ip_address': ip,
                            'port': int(port),
                            'country_code': country,
                            'proxy_type': 'datacenter',
                            'username': None,
                            'password': None
                        })
                    
                    logger.info(f"✅ {self.name}: Found {len(proxies)} proxies")
                    
        except asyncio.TimeoutError:
            logger.error(f"❌ {self.name}: Timeout")
        except Exception as e:
            logger.error(f"❌ {self.name}: {e}")
        
        return proxies


class ProxyListDownloadCom(ProxySourceIntegration):
    """Integration with proxy-list.download"""
    
    def __init__(self):
        super().__init__()
        self.name = "Proxy-List.Download"
        self.url = "https://www.proxy-list.download/api/v1/get?type=http"
    
    async def fetch_proxies(self) -> List[Dict[str, any]]:
        """Fetch proxies from proxy-list.download"""
        proxies = []
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.url, timeout=10) as response:
                    if response.status != 200:
                        logger.warning(f"❌ {self.name}: HTTP {response.status}")
                        return proxies
                    
                    text = await response.text()
                    
                    # Format: IP:PORT (one per line)
                    lines = text.strip().split('\n')
                    
                    for line in lines:
                        line = line.strip()
                        if ':' in line:
                            parts = line.split(':')
                            if len(parts) == 2 and parts[1].isdigit():
                                proxies.append({
                                    'ip_address': parts[0],
                                    'port': int(parts[1]),
                                    'country_code': None,  # Source doesn't provide country
                                    'proxy_type': 'datacenter',
                                    'username': None,
                                    'password': None
                                })
                    
                    logger.info(f"✅ {self.name}: Found {len(proxies)} proxies")
                    
        except asyncio.TimeoutError:
            logger.error(f"❌ {self.name}: Timeout")
        except Exception as e:
            logger.error(f"❌ {self.name}: {e}")
        
        return proxies


class ProxyScrapeAPI(ProxySourceIntegration):
    """Integration with ProxyScrape API (free tier)"""
    
    def __init__(self):
        super().__init__()
        self.name = "ProxyScrape"
        self.url = "https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all"
    
    async def fetch_proxies(self) -> List[Dict[str, any]]:
        """Fetch proxies from ProxyScrape"""
        proxies = []
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.url, timeout=15) as response:
                    if response.status != 200:
                        logger.warning(f"❌ {self.name}: HTTP {response.status}")
                        return proxies
                    
                    text = await response.text()
                    
                    # Format: IP:PORT (one per line)
                    lines = text.strip().split('\n')
                    
                    for line in lines:
                        line = line.strip()
                        if ':' in line:
                            parts = line.split(':')
                            if len(parts) == 2 and parts[1].isdigit():
                                proxies.append({
                                    'ip_address': parts[0],
                                    'port': int(parts[1]),
                                    'country_code': None,
                                    'proxy_type': 'datacenter',
                                    'username': None,
                                    'password': None
                                })
                    
                    logger.info(f"✅ {self.name}: Found {len(proxies)} proxies")
                    
        except asyncio.TimeoutError:
            logger.error(f"❌ {self.name}: Timeout")
        except Exception as e:
            logger.error(f"❌ {self.name}: {e}")
        
        return proxies


class GeonodeAPI(ProxySourceIntegration):
    """Integration with Geonode free proxy API"""
    
    def __init__(self):
        super().__init__()
        self.name = "Geonode"
        self.url = "https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc"
    
    async def fetch_proxies(self) -> List[Dict[str, any]]:
        """Fetch proxies from Geonode API"""
        proxies = []
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.url, timeout=15) as response:
                    if response.status != 200:
                        logger.warning(f"❌ {self.name}: HTTP {response.status}")
                        return proxies
                    
                    data = await response.json()
                    
                    # Parse JSON response
                    if 'data' in data:
                        for proxy in data['data']:
                            proxies.append({
                                'ip_address': proxy.get('ip'),
                                'port': int(proxy.get('port')),
                                'country_code': proxy.get('country', 'Unknown'),
                                'proxy_type': 'datacenter',
                                'username': None,
                                'password': None
                            })
                    
                    logger.info(f"✅ {self.name}: Found {len(proxies)} proxies")
                    
        except asyncio.TimeoutError:
            logger.error(f"❌ {self.name}: Timeout")
        except Exception as e:
            logger.error(f"❌ {self.name}: {e}")
        
        return proxies


class ProxySourceAggregator:
    """Aggregates proxies from multiple sources."""
    
    def __init__(self):
        self.sources = [
            ProxyScrapeAPI(),
            GeonodeAPI(),
            ProxyListDownloadCom(),
            # FreeProxyListNet(),  # Disabled: requires more complex HTML parsing
        ]
    
    async def fetch_all_proxies(self) -> List[Dict[str, any]]:
        """
        Fetch proxies from all sources concurrently.
        
        Returns:
            List of unique proxies
        """
        logger.info(f"🔍 Fetching proxies from {len(self.sources)} sources...")
        
        # Fetch from all sources concurrently
        tasks = [source.fetch_proxies() for source in self.sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results
        all_proxies = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"❌ Source {self.sources[i].name} failed: {result}")
            elif isinstance(result, list):
                all_proxies.extend(result)
        
        # Deduplicate by IP:PORT
        seen = set()
        unique_proxies = []
        
        for proxy in all_proxies:
            key = f"{proxy['ip_address']}:{proxy['port']}"
            if key not in seen:
                seen.add(key)
                unique_proxies.append(proxy)
        
        logger.info(f"✅ Fetched {len(unique_proxies)} unique proxies from {len(self.sources)} sources")
        
        return unique_proxies
    
    async def import_to_database(self, db):
        """
        Fetch and import proxies to database.
        
        Args:
            db: Database session
            
        Returns:
            Dict with stats: {'new': int, 'updated': int, 'failed': int}
        """
        from database.operations import ProxyService
        from database.models import ProxyPool
        
        proxies = await self.fetch_all_proxies()
        
        if not proxies:
            logger.warning("⚠️ No proxies fetched from any source")
            return {'new': 0, 'updated': 0, 'failed': 0}
        
        new_count = 0
        updated_count = 0
        failed_count = 0
        
        for proxy_data in proxies:
            try:
                # Check if proxy already exists
                existing = db.query(ProxyPool).filter_by(
                    ip_address=proxy_data['ip_address'],
                    port=proxy_data['port']
                ).first()
                
                if existing:
                    updated_count += 1
                    continue
                
                # Add new proxy
                ProxyService.add_proxy(
                    db=db,
                    ip_address=proxy_data['ip_address'],
                    port=proxy_data['port'],
                    username=proxy_data.get('username'),
                    password=proxy_data.get('password'),
                    country_code=proxy_data.get('country_code')
                )
                
                new_count += 1
                
            except Exception as e:
                logger.error(f"❌ Failed to import {proxy_data['ip_address']}:{proxy_data['port']}: {e}")
                failed_count += 1
        
        logger.info(f"📊 Import complete: {new_count} new, {updated_count} updated, {failed_count} failed")
        
        return {'new': new_count, 'updated': updated_count, 'failed': failed_count}


# Global instance
proxy_aggregator = ProxySourceAggregator()


async def refresh_proxy_pool_from_sources(db):
    """
    Convenience function to refresh proxy pool from all sources.
    
    Args:
        db: Database session
        
    Returns:
        Number of proxies imported
    """
    return await proxy_aggregator.import_to_database(db)


async def refresh_free_proxies():
    """Fetch free proxies and import to database."""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    
    from database import get_db_session, close_db_session
    
    print("🔄 Fetching free proxies from multiple sources...")
    
    aggregator = ProxySourceAggregator()
    proxies = await aggregator.fetch_all_proxies()
    
    print(f"✅ Fetched {len(proxies)} unique proxies")
    
    # Import to database
    db = get_db_session()
    try:
        stats = await aggregator.import_to_database(db)
        print(f"\n📊 Import Results:")
        print(f"   ✅ New proxies: {stats['new']}")
        print(f"   🔄 Updated: {stats['updated']}")
        print(f"   ❌ Failed: {stats['failed']}")
        return stats
    finally:
        close_db_session(db)


if __name__ == "__main__":
    # Test proxy fetching
    import sys
    
    async def test():
        print("🧪 Testing Proxy Source Integration")
        print("=" * 60)
        
        aggregator = ProxySourceAggregator()
        proxies = await aggregator.fetch_all_proxies()
        
        print(f"\n📊 Summary:")
        print(f"Total unique proxies: {len(proxies)}")
        
        # Show first 5
        print(f"\n📋 Sample proxies:")
        for i, proxy in enumerate(proxies[:5]):
            print(f"  {i+1}. {proxy['ip_address']}:{proxy['port']} ({proxy.get('country_code', 'Unknown')})")
        
        # Count by country
        countries = {}
        for proxy in proxies:
            country = proxy.get('country_code', 'Unknown')
            countries[country] = countries.get(country, 0) + 1
        
        print(f"\n🌍 Top countries:")
        for country, count in sorted(countries.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {country}: {count}")
        
        # Import to database
        print(f"\n📥 Importing to database...")
        stats = await refresh_free_proxies()
    
    asyncio.run(test())

