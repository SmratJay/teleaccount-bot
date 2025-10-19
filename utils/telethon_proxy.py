"""
Telethon Proxy Format Conversion Utilities
Converts database proxy formats to Telethon-compatible formats
"""
import logging
from typing import Optional, Dict, Any, Tuple, Union
from services.proxy_manager import ProxyConfig

logger = logging.getLogger(__name__)


def convert_to_telethon_proxy(proxy: Union[ProxyConfig, Any]) -> Optional[Union[Dict[str, Any], Tuple]]:
    """
    Convert ProxyConfig or ProxyPool model to Telethon-compatible proxy format.
    
    Telethon supports two proxy formats:
    1. Dict format (recommended): {'proxy_type': 'socks5', 'addr': '...', 'port': ..., 'username': '...', 'password': '...'}
    2. Tuple format (legacy): (socks.SOCKS5, 'addr', port, True, 'username', 'password')
    
    Args:
        proxy: ProxyConfig object or ProxyPool database model
        
    Returns:
        Dict or Tuple in Telethon format, or None if invalid
    """
    if not proxy:
        return None
    
    try:
        # Handle both ProxyConfig and ProxyPool model
        # ProxyConfig has 'host', ProxyPool has 'ip_address'
        host = getattr(proxy, 'host', None) or getattr(proxy, 'ip_address', None)
        port = getattr(proxy, 'port', None)
        username = getattr(proxy, 'username', None)
        password = getattr(proxy, 'password', None)
        proxy_type_attr = getattr(proxy, 'proxy_type', 'SOCKS5')
        
        if not host or not port:
            logger.error(f"Proxy missing host or port: {proxy}")
            return None
        
        # Determine proxy type
        proxy_type = proxy_type_attr.upper() if proxy_type_attr else 'SOCKS5'
        
        # Map to Telethon proxy type strings
        type_mapping = {
            'HTTP': 'http',
            'HTTPS': 'http',
            'SOCKS4': 'socks4',
            'SOCKS5': 'socks5',
            'DATACENTER': 'socks5',  # WebShare datacenter proxies are SOCKS5
            'RESIDENTIAL': 'socks5',
            'MOBILE': 'socks5',
            'FREE': 'http'  # Most free proxies are HTTP
        }
        
        telethon_type = type_mapping.get(proxy_type, 'socks5')
        
        # Build dict format (recommended for Telethon)
        proxy_dict = {
            'proxy_type': telethon_type,
            'addr': host,
            'port': port
        }
        
        # Add authentication if available
        if username and password:
            proxy_dict['username'] = username
            proxy_dict['password'] = password
        
        logger.debug(f"Converted proxy {host}:{port} to Telethon format: {telethon_type}")
        return proxy_dict
        
    except Exception as e:
        logger.error(f"Error converting proxy to Telethon format: {e}")
        return None


def convert_to_telethon_tuple(proxy: Union[ProxyConfig, Any]) -> Optional[Tuple]:
    """
    Convert ProxyConfig or ProxyPool model to Telethon tuple format (legacy).
    
    Note: This format requires python-socks library.
    Format: (proxy_type_enum, addr, port, rdns, username, password)
    
    Args:
        proxy: ProxyConfig object or ProxyPool database model
        
    Returns:
        Tuple in Telethon format, or None if invalid
    """
    if not proxy:
        return None
    
    try:
        import socks
        
        # Handle both ProxyConfig and ProxyPool model
        host = getattr(proxy, 'host', None) or getattr(proxy, 'ip_address', None)
        port = getattr(proxy, 'port', None)
        username = getattr(proxy, 'username', None)
        password = getattr(proxy, 'password', None)
        proxy_type_attr = getattr(proxy, 'proxy_type', 'SOCKS5')
        
        if not host or not port:
            logger.error(f"Proxy missing host or port: {proxy}")
            return None
        
        # Map to socks library constants
        type_mapping = {
            'HTTP': socks.HTTP,
            'HTTPS': socks.HTTP,
            'SOCKS4': socks.SOCKS4,
            'SOCKS5': socks.SOCKS5,
            'DATACENTER': socks.SOCKS5,
            'RESIDENTIAL': socks.SOCKS5,
            'MOBILE': socks.SOCKS5
        }
        
        proxy_type = proxy_type_attr.upper() if proxy_type_attr else 'SOCKS5'
        socks_type = type_mapping.get(proxy_type, socks.SOCKS5)
        
        # Build tuple: (type, addr, port, rdns, username, password)
        if username and password:
            proxy_tuple = (
                socks_type,
                host,
                port,
                True,  # rdns
                username,
                password
            )
        else:
            proxy_tuple = (
                socks_type,
                host,
                port,
                True  # rdns
            )
        
        logger.debug(f"Converted proxy {host}:{port} to Telethon tuple format")
        return proxy_tuple
        
    except ImportError:
        logger.error("python-socks library not installed. Install with: pip install python-socks")
        return None
    except Exception as e:
        logger.error(f"Error converting proxy to Telethon tuple format: {e}")
        return None


def validate_telethon_proxy(proxy_dict: Dict[str, Any]) -> bool:
    """
    Validate that a proxy dict is in correct Telethon format.
    
    Args:
        proxy_dict: Proxy configuration dict
        
    Returns:
        True if valid, False otherwise
    """
    try:
        # Check required fields
        required_fields = ['proxy_type', 'addr', 'port']
        for field in required_fields:
            if field not in proxy_dict:
                logger.error(f"Missing required field: {field}")
                return False
        
        # Check proxy type is valid
        valid_types = ['http', 'socks4', 'socks5']
        if proxy_dict['proxy_type'] not in valid_types:
            logger.error(f"Invalid proxy type: {proxy_dict['proxy_type']}")
            return False
        
        # Check port is integer
        if not isinstance(proxy_dict['port'], int):
            logger.error(f"Port must be integer, got: {type(proxy_dict['port'])}")
            return False
        
        # Check port range
        if not (1 <= proxy_dict['port'] <= 65535):
            logger.error(f"Invalid port number: {proxy_dict['port']}")
            return False
        
        # Check authentication consistency
        has_username = 'username' in proxy_dict and proxy_dict['username']
        has_password = 'password' in proxy_dict and proxy_dict['password']
        
        if has_username != has_password:
            logger.warning("Username and password must both be present or both absent")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error validating proxy: {e}")
        return False


def get_proxy_info(proxy: Union[ProxyConfig, Any]) -> Dict[str, Any]:
    """
    Get human-readable proxy information.
    
    Args:
        proxy: ProxyConfig object or ProxyPool database model
        
    Returns:
        Dict with proxy details
    """
    if not proxy:
        return {"status": "no_proxy", "message": "No proxy configured"}
    
    # Handle both ProxyConfig and ProxyPool model
    host = getattr(proxy, 'host', None) or getattr(proxy, 'ip_address', None)
    port = getattr(proxy, 'port', None)
    username = getattr(proxy, 'username', None)
    password = getattr(proxy, 'password', None)
    proxy_type = getattr(proxy, 'proxy_type', 'SOCKS5')
    country_code = getattr(proxy, 'country_code', 'Unknown')
    
    info = {
        "host": host,
        "port": port,
        "type": proxy_type or "SOCKS5",
        "authenticated": bool(username and password),
        "country": country_code or "Unknown"
    }
    
    if username:
        # Mask password for security
        info["username"] = username
        info["password_set"] = True
    
    return info


# Convenience functions
def proxy_to_dict(proxy: ProxyConfig) -> Optional[Dict[str, Any]]:
    """Alias for convert_to_telethon_proxy (dict format)"""
    return convert_to_telethon_proxy(proxy)


def proxy_to_tuple(proxy: ProxyConfig) -> Optional[Tuple]:
    """Alias for convert_to_telethon_tuple (tuple format)"""
    return convert_to_telethon_tuple(proxy)


# Example usage
if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    
    from services.proxy_manager import ProxyManager, OperationType
    
    print("🧪 Testing Telethon Proxy Format Conversion")
    print("=" * 60)
    
    # Get a test proxy
    manager = ProxyManager()
    proxy = manager.get_proxy_for_operation(OperationType.TESTING)
    
    if proxy:
        print(f"\n📊 Original Proxy:")
        print(f"   Host: {proxy.host}")
        print(f"   Port: {proxy.port}")
        print(f"   Type: {proxy.proxy_type}")
        print(f"   Country: {proxy.country_code}")
        
        # Convert to dict format
        print(f"\n📦 Telethon Dict Format:")
        proxy_dict = convert_to_telethon_proxy(proxy)
        if proxy_dict:
            for key, value in proxy_dict.items():
                print(f"   {key}: {value}")
            
            # Validate
            is_valid = validate_telethon_proxy(proxy_dict)
            print(f"\n✅ Validation: {'PASS' if is_valid else 'FAIL'}")
        
        # Try tuple format
        print(f"\n📦 Telethon Tuple Format:")
        proxy_tuple = convert_to_telethon_tuple(proxy)
        if proxy_tuple:
            print(f"   {proxy_tuple}")
        else:
            print(f"   ⚠️  Tuple format requires python-socks library")
        
        # Get info
        print(f"\n📋 Proxy Info:")
        info = get_proxy_info(proxy)
        for key, value in info.items():
            print(f"   {key}: {value}")
    else:
        print("\n❌ No proxy available for testing")
