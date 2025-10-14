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
from sqlalchemy.orm import Session
from database.operations import ProxyService
from database import get_db_session, close_db_session

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
        
    def get_unique_proxy(self) -> Optional[ProxyConfig]:
        """Get a unique proxy for a new Telethon connection."""
        db = get_db_session()
        try:
            # Get an available proxy from the database
            proxy_record = ProxyService.get_available_proxy(db)
            
            if proxy_record:
                # Mark as used
                ProxyService.mark_proxy_used(db, proxy_record.id)
                
                # Return proxy configuration
                return ProxyConfig(
                    proxy_type=proxy_record.proxy_type,
                    host=proxy_record.host,
                    port=proxy_record.port,
                    username=proxy_record.username,
                    password=proxy_record.password,
                    country_code=proxy_record.country_code
                )
            else:
                # No proxy available, try to fetch new ones
                if self._refresh_proxy_pool(db):
                    # Try again after refresh
                    proxy_record = ProxyService.get_available_proxy(db)
                    if proxy_record:
                        ProxyService.mark_proxy_used(db, proxy_record.id)
                        return ProxyConfig(
                            proxy_type=proxy_record.proxy_type,
                            host=proxy_record.host,
                            port=proxy_record.port,
                            username=proxy_record.username,
                            password=proxy_record.password,
                            country_code=proxy_record.country_code
                        )
                
                logger.warning("No available proxies found")
                return None
                
        except Exception as e:
            logger.error(f"Error getting unique proxy: {e}")
            return None
        finally:
            close_db_session(db)
    
    def _refresh_proxy_pool(self, db: Session) -> bool:
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
    
    def _parse_and_add_proxy(self, db: Session, proxy_line: str) -> bool:
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
            
            # Add to database
            ProxyService.add_proxy(
                db=db,
                proxy_type=proxy_type,
                host=host,
                port=port,
                username=username,
                password=password
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to parse proxy line '{proxy_line}': {e}")
            return False
    
    def report_proxy_failure(self, proxy_config: ProxyConfig) -> None:
        """Report a proxy failure."""
        db = get_db_session()
        try:
            # Find the proxy in the database
            from database.models import ProxyPool
            proxy_record = db.query(ProxyPool).filter(
                ProxyPool.host == proxy_config.host,
                ProxyPool.port == proxy_config.port
            ).first()
            
            if proxy_record:
                ProxyService.mark_proxy_failed(db, proxy_record.id)
                
        except Exception as e:
            logger.error(f"Failed to report proxy failure: {e}")
        finally:
            close_db_session(db)
    
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