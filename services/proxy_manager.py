"""
Proxy management system for Telethon connections.
"""
import os
import json
import random
import logging
import requests
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
# from sqlalchemy.orm import Session
# from database.operations import ProxyService  # Not implemented yet
# from database import get_db_session, close_db_session

logger = logging.getLogger(__name__)

@dataclass
class ProxyConfig:
    """Proxy configuration data class."""
    proxy_type: str  # 'HTTP', 'SOCKS4', 'SOCKS5'
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    country_code: Optional[str] = None

class ProxyManager:
    """Manages proxy connections for Telethon clients."""
    
    def __init__(self):
        self.proxy_list_url = os.getenv('PROXY_LIST_URL')
        self.proxy_username = os.getenv('PROXY_USERNAME')
        self.proxy_password = os.getenv('PROXY_PASSWORD')
        self.country_proxies = self._load_country_specific_proxies()
        
    def get_unique_proxy(self) -> Optional[ProxyConfig]:
        """Get a unique proxy for a new Telethon connection."""
        try:
            # For now, return a random proxy from configured list
            # TODO: Implement database-based proxy management when ProxyService is available
            
            all_proxies = []
            for country_proxies in self.country_proxies.values():
                all_proxies.extend(country_proxies)
            
            if all_proxies:
                return random.choice(all_proxies)
            
            # Fallback to default proxy configuration if available
            if self.proxy_username and self.proxy_password:
                return ProxyConfig(
                    proxy_type='HTTP',
                    host='127.0.0.1',  # Localhost fallback
                    port=8080,
                    username=self.proxy_username,
                    password=self.proxy_password,
                    country_code='US'
                )
            
            logger.warning("No proxies configured")
            return None
                
        except Exception as e:
            logger.error(f"Error getting unique proxy: {e}")
            return None
    
    def _load_country_specific_proxies(self) -> Dict[str, List[ProxyConfig]]:
        """Load proxies organized by country"""
        return {
            'US': [
                ProxyConfig('HTTP', '192.168.1.1', 8080, 'user', 'pass', 'US'),
                # Add more US proxies
            ],
            'GB': [
                ProxyConfig('HTTP', '192.168.1.2', 8080, 'user', 'pass', 'GB'),
                # Add more UK proxies
            ],
            'IN': [
                ProxyConfig('HTTP', '192.168.1.3', 8080, 'user', 'pass', 'IN'),
                # Add more India proxies
            ]
        }
    
    def get_country_specific_proxy(self, country_code: str) -> Optional[ProxyConfig]:
        """Get a proxy from specific country"""
        try:
            if country_code in self.country_proxies:
                available_proxies = self.country_proxies[country_code]
                if available_proxies:
                    return random.choice(available_proxies)
            
            # Fallback to any available proxy
            return self.get_unique_proxy()
            
        except Exception as e:
            logger.error(f"Error getting country-specific proxy: {e}")
            return None
    
    def _refresh_proxy_pool(self) -> bool:
        """Refresh the proxy pool by fetching new proxies."""
        try:
            if not self.proxy_list_url:
                logger.warning("No proxy list URL configured")
                return False
            
            # Fetch proxy list from URL
            response = requests.get(self.proxy_list_url, timeout=30)
            response.raise_for_status()
            
            proxy_data = response.text.strip().split('\n')
            added_count = 0
            
            for proxy_line in proxy_data:
                if self._parse_and_add_proxy(db, proxy_line):
                    added_count += 1
            
            logger.info(f"Added {added_count} new proxies to the pool")
            return added_count > 0
            
        except Exception as e:
            logger.error(f"Failed to refresh proxy pool: {e}")
            return False
    
    def _parse_and_add_proxy(self, proxy_line: str) -> bool:
        """Parse and add a proxy to the database."""
        try:
            # Expected format: TYPE:HOST:PORT:USERNAME:PASSWORD or TYPE:HOST:PORT
            parts = proxy_line.strip().split(':')
            
            if len(parts) < 3:
                return False
            
            proxy_type = parts[0].upper()
            host = parts[1]
            port = int(parts[2])
            
            # Check if proxy type is valid
            if proxy_type not in ['HTTP', 'SOCKS4', 'SOCKS5']:
                return False
            
            username = parts[3] if len(parts) > 3 else self.proxy_username
            password = parts[4] if len(parts) > 4 else self.proxy_password
            
            # TODO: Add to database when ProxyService is implemented
            logger.info(f"Parsed proxy: {proxy_type}://{host}:{port}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to parse proxy line '{proxy_line}': {e}")
            return False
    
    def report_proxy_failure(self, proxy_config: ProxyConfig) -> None:
        """Report a proxy failure."""
        try:
            # TODO: Implement proxy failure reporting when ProxyService is available
            logger.warning(f"Proxy failure reported: {proxy_config.host}:{proxy_config.port}")
                
        except Exception as e:
            logger.error(f"Failed to report proxy failure: {e}")
    
    def get_proxy_dict(self, proxy_config: ProxyConfig) -> Optional[Dict]:
        """Convert ProxyConfig to dict format for Telethon."""
        if not proxy_config:
            return None
        
        proxy_dict = {
            'proxy_type': proxy_config.proxy_type,
            'addr': proxy_config.host,
            'port': proxy_config.port
        }
        
        if proxy_config.username and proxy_config.password:
            proxy_dict['username'] = proxy_config.username
            proxy_dict['password'] = proxy_config.password
        
        return proxy_dict
    
    def get_proxy_json(self, proxy_config: ProxyConfig) -> str:
        """Convert ProxyConfig to JSON string for database storage."""
        if not proxy_config:
            return ""
        
        return json.dumps({
            'proxy_type': proxy_config.proxy_type,
            'host': proxy_config.host,
            'port': proxy_config.port,
            'username': proxy_config.username,
            'password': proxy_config.password,
            'country_code': proxy_config.country_code
        })
    
    def load_proxy_from_json(self, proxy_json: str) -> Optional[ProxyConfig]:
        """Load ProxyConfig from JSON string."""
        try:
            if not proxy_json:
                return None
            
            data = json.loads(proxy_json)
            return ProxyConfig(
                proxy_type=data.get('proxy_type'),
                host=data.get('host'),
                port=data.get('port'),
                username=data.get('username'),
                password=data.get('password'),
                country_code=data.get('country_code')
            )
        except Exception as e:
            logger.error(f"Failed to load proxy from JSON: {e}")
            return None

# Global proxy manager instance
proxy_manager = ProxyManager()