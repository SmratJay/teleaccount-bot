"""
Proxy management system for Telethon connections.
"""
import os
import sys
import json
import random
import logging
import requests
import socket
from typing import Dict, Optional, List, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database.operations import ProxyService
from database import get_db_session, close_db_session
from services.proxy_load_balancer import ProxyLoadBalancer, LoadBalancingStrategy

logger = logging.getLogger(__name__)


class OperationType(Enum):
    """Types of operations that require proxies."""
    ACCOUNT_CREATION = "account_creation"
    LOGIN = "login"
    OTP_RETRIEVAL = "otp_retrieval"
    MESSAGE_SEND = "message_send"
    VERIFICATION = "verification"
    BULK_OPERATION = "bulk_operation"
    TESTING = "testing"
    GENERAL = "general"

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
        self.health_check_interval = int(os.getenv('PROXY_HEALTH_CHECK_INTERVAL', '300'))  # 5 minutes default
        self.last_health_check = None
        self.load_balancer = ProxyLoadBalancer()
        
        # Load operation rules from config
        self._load_operation_rules()
    
    def _load_operation_rules(self):
        """Load proxy selection rules for different operations."""
        # Default rules (can be overridden by config file)
        self.operation_rules = {
            OperationType.ACCOUNT_CREATION: {
                'proxy_types': ['residential', 'datacenter'],
                'min_reputation': 45,  # Lowered to work with fresh proxies
                'strategy': LoadBalancingStrategy.BEST_REPUTATION,
                'country_match': True
            },
            OperationType.LOGIN: {
                'proxy_types': ['residential', 'datacenter'],
                'min_reputation': 40,  # Lowered to work with fresh proxies
                'strategy': LoadBalancingStrategy.WEIGHTED_RANDOM,
                'country_match': True
            },
            OperationType.OTP_RETRIEVAL: {
                'proxy_types': ['residential', 'datacenter'],
                'min_reputation': 40,  # Lowered to work with fresh proxies
                'strategy': LoadBalancingStrategy.WEIGHTED_RANDOM,
                'country_match': False
            },
            OperationType.MESSAGE_SEND: {
                'proxy_types': ['datacenter', 'free'],
                'min_reputation': 50,
                'strategy': LoadBalancingStrategy.LEAST_RECENTLY_USED,
                'country_match': False
            },
            OperationType.VERIFICATION: {
                'proxy_types': ['datacenter', 'residential'],
                'min_reputation': 60,
                'strategy': LoadBalancingStrategy.WEIGHTED_RANDOM,
                'country_match': True
            },
            OperationType.BULK_OPERATION: {
                'proxy_types': ['datacenter', 'free'],
                'min_reputation': 40,
                'strategy': LoadBalancingStrategy.LEAST_RECENTLY_USED,
                'country_match': False
            },
            OperationType.TESTING: {
                'proxy_types': ['free', 'datacenter'],
                'min_reputation': 20,
                'strategy': LoadBalancingStrategy.RANDOM,
                'country_match': False
            },
            OperationType.GENERAL: {
                'proxy_types': ['datacenter', 'free'],
                'min_reputation': 50,
                'strategy': LoadBalancingStrategy.WEIGHTED_RANDOM,
                'country_match': False
            }
        }
        
        # Try to load from config file if exists
        try:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'proxy_config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                    if 'operation_rules' in config_data:
                        # Merge with defaults
                        for op_name, rules in config_data['operation_rules'].items():
                            try:
                                op_type = OperationType(op_name)
                                if 'strategy' in rules and isinstance(rules['strategy'], str):
                                    rules['strategy'] = LoadBalancingStrategy[rules['strategy'].upper()]
                                self.operation_rules[op_type].update(rules)
                                logger.info(f"Loaded custom rules for operation: {op_name}")
                            except (ValueError, KeyError) as e:
                                logger.warning(f"Invalid operation type or strategy in config: {op_name}")
        except Exception as e:
            logger.warning(f"Could not load proxy config file: {e}, using defaults")
    
    def get_proxy_for_operation(
        self, 
        operation: OperationType, 
        country_code: Optional[str] = None
    ) -> Optional[ProxyConfig]:
        """
        Get the best proxy for a specific operation type.
        
        Args:
            operation: Type of operation (account creation, login, etc.)
            country_code: Optional country code to match
            
        Returns:
            ProxyConfig if found, None otherwise
        """
        db = None
        try:
            db = get_db_session()
            
            # Handle both string and Enum operation types
            if isinstance(operation, str):
                operation_key = operation.upper()
                # Try to find matching OperationType
                try:
                    operation_enum = OperationType[operation_key]
                    operation_name = operation_enum.value
                except KeyError:
                    operation_enum = OperationType.GENERAL
                    operation_name = operation
            else:
                operation_enum = operation
                operation_name = operation.value
            
            # Get rules for this operation
            rules = self.operation_rules.get(operation_enum, self.operation_rules[OperationType.GENERAL])
            
            logger.info(f"Selecting proxy for operation: {operation_name}, rules: {rules}")
            
            # Get proxies that match criteria
            min_reputation = rules['min_reputation']
            proxy_types = rules['proxy_types']
            strategy = rules['strategy']
            country_match = rules.get('country_match', False)
            
            # If country matching required and country code provided, prioritize it
            target_country = country_code if (country_match and country_code) else None
            
            # Get available proxies from database - ONLY WebShare proxies
            all_proxies = ProxyService.get_all_proxies(db)
            
            # CRITICAL: Filter to ONLY WebShare premium proxies
            # Filter out any hardcoded or free proxies
            webshare_proxies = [p for p in all_proxies if getattr(p, 'provider', None) == 'webshare']
            
            if not webshare_proxies:
                logger.error("No WebShare proxies found! Please run /fetch_webshare command in Telegram bot")
                return None
            
            logger.info(f"Filtering from {len(webshare_proxies)} WebShare premium proxies")
            
            # Filter proxies based on criteria
            suitable_proxies = []
            for proxy in webshare_proxies:
                # Check if proxy is active and healthy
                if not proxy.is_active or not proxy.is_healthy:
                    continue
                
                # Check reputation
                if proxy.reputation_score < min_reputation:
                    continue
                
                # Check proxy type
                proxy_type = getattr(proxy, 'proxy_type', 'datacenter') or 'datacenter'
                if proxy_type not in proxy_types:
                    continue
                
                # Check country match if required
                if target_country and proxy.country_code != target_country:
                    # Don't skip yet, but prioritize country matches
                    pass
                
                suitable_proxies.append(proxy)
            
            if not suitable_proxies:
                logger.warning(f"No suitable WebShare proxies found for operation {operation_name}, trying fallback")
                # Try with relaxed criteria (still WebShare only)
                suitable_proxies = [p for p in webshare_proxies if p.is_active and p.reputation_score >= 30]
            
            if not suitable_proxies:
                logger.error(f"No proxies available for operation {operation_name}")
                return None
            
            # If country matching is important, separate country matches
            if target_country:
                country_matches = [p for p in suitable_proxies if p.country_code == target_country]
                if country_matches:
                    suitable_proxies = country_matches
                    logger.info(f"Using {len(country_matches)} proxies matching country {target_country}")
            
            # Use load balancer to select proxy
            selected_proxy = self.load_balancer.select_proxy(suitable_proxies, strategy)
            
            if selected_proxy:
                logger.info(
                    f"Selected proxy for {operation_name}: "
                    f"{selected_proxy.ip_address}:{selected_proxy.port} "
                    f"(reputation: {selected_proxy.reputation_score}, "
                    f"type: {getattr(selected_proxy, 'proxy_type', 'datacenter')}, "
                    f"country: {selected_proxy.country_code})"
                )
                
                # Convert to ProxyConfig
                return ProxyConfig(
                    proxy_type=self._get_proxy_type_string(selected_proxy),
                    host=selected_proxy.ip_address,
                    port=selected_proxy.port,
                    username=selected_proxy.username,
                    password=selected_proxy.get_decrypted_password() if hasattr(selected_proxy, 'get_decrypted_password') else selected_proxy.password,
                    country_code=selected_proxy.country_code
                )
            
            return None
                
        except Exception as e:
            logger.error(f"Error getting proxy for operation {operation_name}: {e}", exc_info=True)
            return None
        finally:
            if db:
                close_db_session(db)
    
    def _get_proxy_type_string(self, proxy_record) -> str:
        """Get proxy type string from database record."""
        proxy_type = getattr(proxy_record, 'proxy_type', None)
        if proxy_type:
            # Map database proxy types to Telethon types
            type_map = {
                'http': 'HTTP',
                'https': 'HTTP',
                'socks4': 'SOCKS4',
                'socks5': 'SOCKS5',
                'datacenter': 'SOCKS5',  # WebShare datacenter proxies are SOCKS5
                'residential': 'SOCKS5',
                'free': 'HTTP'
            }
            return type_map.get(proxy_type.lower(), 'SOCKS5')
        return 'SOCKS5'  # Default to SOCKS5
        
    def get_unique_proxy(self, country_code: str = None) -> Optional[ProxyConfig]:
        """
        Get a unique proxy for a new Telethon connection.
        DEPRECATED: Use get_proxy_for_operation() instead for better proxy selection.
        """
        logger.warning("get_unique_proxy() is deprecated, use get_proxy_for_operation() instead")
        # Default to GENERAL operation
        return self.get_proxy_for_operation(OperationType.GENERAL, country_code)
    
    def _guess_country_from_ip(self, ip_address: str) -> Optional[str]:
        """Make a basic guess about country from IP address."""
        try:
            # This is a very basic implementation
            # In production, you'd use a proper IP geolocation service
            if ip_address.startswith(('192.168.', '10.', '172.')):
                return None  # Local/private IPs
            
            # Some basic mappings (very simplified)
            octets = ip_address.split('.')
            if len(octets) == 4:
                first_octet = int(octets[0])
                if 1 <= first_octet <= 126:
                    return 'US'  # Class A - often US
                elif 128 <= first_octet <= 191:
                    return 'EU'  # Class B - often Europe
                elif 192 <= first_octet <= 223:
                    return 'AS'  # Class C - often Asia
            
            return 'US'  # Default fallback
        except:
            return None
    
    def get_country_specific_proxy(self, country_code: str) -> Optional[ProxyConfig]:
        """Get a proxy from specific country"""
        return self.get_unique_proxy(country_code)
    
    def refresh_proxy_pool(self) -> bool:
        """Refresh the proxy pool by fetching new proxies from external source."""
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
                if self._parse_and_add_proxy(proxy_line.strip()):
                    added_count += 1
            
            logger.info(f"Added {added_count} new proxies to the pool")
            return added_count > 0
            
        except Exception as e:
            logger.error(f"Failed to refresh proxy pool: {e}")
            return False
    
    def _parse_and_add_proxy(self, proxy_line: str) -> bool:
        """Parse and add a proxy to the database."""
        try:
            # Expected format: IP:PORT or IP:PORT:USERNAME:PASSWORD
            parts = proxy_line.strip().split(':')
            
            if len(parts) < 2:
                return False
            
            ip_address = parts[0]
            port = int(parts[1])
            
            username = parts[2] if len(parts) > 2 else self.proxy_username
            password = parts[3] if len(parts) > 3 else self.proxy_password
            
            # Try to determine country from IP (basic check)
            country_code = self._guess_country_from_ip(ip_address)
            
            return self.add_proxy_to_pool(ip_address, port, username, password, country_code)
            
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
    
    def test_proxy_connectivity(self, proxy_config: ProxyConfig) -> bool:
        """Test if a proxy is working by attempting a basic connection."""
        try:
            # Simple connectivity test
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((proxy_config.host, proxy_config.port))
            sock.close()
            
            is_working = result == 0
            logger.info(f"Proxy {proxy_config.host}:{proxy_config.port} connectivity test: {'PASS' if is_working else 'FAIL'}")
            return is_working
                    
        except Exception as e:
            logger.warning(f"Proxy test failed for {proxy_config.host}:{proxy_config.port}: {e}")
            return False
    
    def get_proxy_stats(self) -> Dict[str, Any]:
        """Get statistics about the proxy pool."""
        db = None
        try:
            db = get_db_session()
            return ProxyService.get_proxy_stats(db)
        except Exception as e:
            logger.error(f"Failed to get proxy stats: {e}")
            return {}
        finally:
            if db:
                close_db_session(db)
    
    def perform_health_check(self) -> Dict[str, Any]:
        """Perform health check on proxy pool and return results."""
        current_time = datetime.now(timezone.utc)
        
        # Only perform health check if enough time has passed
        if self.last_health_check and (current_time - self.last_health_check).seconds < self.health_check_interval:
            return {"status": "skipped", "reason": "too_soon"}
        
        self.last_health_check = current_time
        
        try:
            db = get_db_session()
            stats = ProxyService.get_proxy_stats(db)
            
            # Test a few random proxies
            proxies = ProxyService.get_all_proxies(db)
            tested_count = min(5, len(proxies))  # Test up to 5 proxies
            working_count = 0
            
            if tested_count > 0:
                test_proxies = random.sample(proxies, tested_count)
                for proxy_record in test_proxies:
                    proxy_config = ProxyConfig(
                        proxy_type='HTTP',
                        host=proxy_record.ip_address,
                        port=proxy_record.port,
                        username=proxy_record.username,
                        password=proxy_record.password
                    )
                    
                    if self.test_proxy_connectivity(proxy_config):
                        working_count += 1
                    else:
                        # Mark as inactive if test fails
                        ProxyService.deactivate_proxy(db, proxy_record.id, "Health check failed")
            
            close_db_session(db)
            
            return {
                "status": "completed",
                "total_proxies": stats.get('total_proxies', 0),
                "active_proxies": stats.get('active_proxies', 0),
                "tested_count": tested_count,
                "working_count": working_count,
                "success_rate": working_count / tested_count if tested_count > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            if 'db' in locals():
                close_db_session(db)
            return {"status": "error", "error": str(e)}
    
    def rotate_daily_proxies(self) -> Dict[str, Any]:
        """Perform daily proxy rotation - deactivate old proxies and refresh pool."""
        try:
            db = get_db_session()
            
            # Clean up old proxies (not used for 7 days)
            cleaned_count = ProxyService.cleanup_old_proxies(db, days_inactive=7)
            
            # Refresh proxy pool from external source
            refresh_success = self.refresh_proxy_pool()
            
            # Get updated stats
            stats = ProxyService.get_proxy_stats(db)
            
            close_db_session(db)
            
            logger.info(f"Daily proxy rotation completed: cleaned {cleaned_count} old proxies, refresh {'successful' if refresh_success else 'failed'}")
            
            return {
                "status": "completed",
                "cleaned_proxies": cleaned_count,
                "refresh_success": refresh_success,
                "current_stats": stats
            }
            
        except Exception as e:
            logger.error(f"Daily proxy rotation failed: {e}")
            if 'db' in locals():
                close_db_session(db)
            return {"status": "error", "error": str(e)}

    def add_proxy_to_pool(self, ip_address: str, port: int, username: str = None, 
                         password: str = None, country_code: str = None) -> bool:
        """Add a new proxy to the database pool."""
        db = None
        try:
            db = get_db_session()
            ProxyService.add_proxy(db, ip_address, port, username, password, country_code)
            logger.info(f"Added proxy to pool: {ip_address}:{port}")
            return True
        except Exception as e:
            logger.error(f"Failed to add proxy {ip_address}:{port}: {e}")
            return False
        finally:
            if db:
                close_db_session(db)

# Global proxy manager instance
proxy_manager = ProxyManager()
