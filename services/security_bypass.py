"""
Advanced Telegram Security Bypass System
This module implements sophisticated techniques to avoid Telegram's security blocks
"""
import asyncio
import random
import logging
import time
import json
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from telethon import TelegramClient
from telethon.errors import FloodWaitError, PhoneNumberInvalidError
# import aiohttp  # Optional - only needed for proxy testing
# import user_agents  # Optional - for user agent rotation
from services.proxy_manager import ProxyManager, ProxyConfig

logger = logging.getLogger(__name__)

class SecurityBypassManager:
    """Advanced security bypass techniques for Telegram login"""
    
    def __init__(self):
        self.proxy_manager = ProxyManager()
        self.device_profiles = self._load_device_profiles()
        self.login_patterns = self._load_behavioral_patterns()
        self.session_cache = {}
        
    def _load_device_profiles(self) -> List[Dict[str, Any]]:
        """Load realistic device profiles for fingerprinting"""
        return [
            {
                "platform": "android",
                "device_model": "SM-G991B",
                "app_version": "10.2.5",
                "system_version": "13",
                "lang_code": "en",
                "system_lang_code": "en-US"
            },
            {
                "platform": "ios", 
                "device_model": "iPhone14,2",
                "app_version": "10.2.5", 
                "system_version": "17.1.1",
                "lang_code": "en",
                "system_lang_code": "en-US"
            },
            {
                "platform": "android",
                "device_model": "Pixel 7",
                "app_version": "10.2.5",
                "system_version": "14", 
                "lang_code": "en",
                "system_lang_code": "en-US"
            }
        ]
    
    def _load_behavioral_patterns(self) -> Dict[str, Any]:
        """Load human-like behavioral patterns"""
        return {
            "typing_delays": [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4],
            "thinking_pauses": [1.0, 1.5, 2.0, 2.5, 3.0],
            "retry_delays": [5, 10, 15, 30, 60, 120, 300],
            "session_gaps": [300, 600, 900, 1800]  # Gaps between sessions
        }
    
    async def get_secure_proxy(self, phone_number: str) -> Optional[ProxyConfig]:
        """Get a secure, phone-specific proxy"""
        try:
            # Generate consistent proxy for same phone to maintain IP consistency
            phone_hash = hashlib.md5(phone_number.encode()).hexdigest()
            
            # Check if we have a cached proxy for this phone
            if phone_hash in self.session_cache:
                cached_data = self.session_cache[phone_hash]
                if datetime.now() - cached_data['assigned_at'] < timedelta(hours=24):
                    return cached_data['proxy']
            
            # Get new unique proxy
            proxy = self.proxy_manager.get_unique_proxy()
            if proxy:
                # Verify proxy works
                if await self._test_proxy_connectivity(proxy):
                    # Cache for consistency
                    self.session_cache[phone_hash] = {
                        'proxy': proxy,
                        'assigned_at': datetime.now()
                    }
                    return proxy
                    
            return None
            
        except Exception as e:
            logger.error(f"Error getting secure proxy: {e}")
            return None
    
    async def _test_proxy_connectivity(self, proxy: ProxyConfig) -> bool:
        """Test if proxy is working and has good reputation"""
        try:
            # Simple connectivity test without aiohttp dependency
            import socket
            
            # Test basic socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((proxy.host, proxy.port))
            sock.close()
            
            return result == 0  # 0 means successful connection
                    
        except Exception as e:
            logger.warning(f"Proxy test failed: {e}")
            return False
    
    def get_device_profile(self, phone_number: str) -> Dict[str, Any]:
        """Get consistent device profile for phone number"""
        phone_hash = hashlib.md5(phone_number.encode()).hexdigest()
        profile_index = int(phone_hash[:2], 16) % len(self.device_profiles)
        return self.device_profiles[profile_index].copy()
    
    async def create_secure_client(self, phone_number: str, api_id: int, api_hash: str) -> Optional[TelegramClient]:
        """Create a secure Telethon client with anti-detection measures"""
        try:
            # Get secure proxy
            proxy = await self.get_secure_proxy(phone_number)
            device_profile = self.get_device_profile(phone_number)
            
            # Create session name with device info
            session_name = f"secure_{hashlib.md5(phone_number.encode()).hexdigest()[:8]}"
            
            # Configure client with security measures
            client_kwargs = {
                'api_id': api_id,
                'api_hash': api_hash,
                'device_model': device_profile['device_model'],
                'system_version': device_profile['system_version'],
                'app_version': device_profile['app_version'],
                'lang_code': device_profile['lang_code'],
                'system_lang_code': device_profile['system_lang_code'],
                'use_ipv6': False,
                'auto_reconnect': True,
                'connection_retries': 5,
                'retry_delay': 2,
                'timeout': 30
            }
            
            # Add proxy if available
            if proxy:
                if proxy.proxy_type.upper() == 'HTTP':
                    client_kwargs['proxy'] = (proxy.host, proxy.port, proxy.username, proxy.password)
                else:
                    client_kwargs['proxy'] = {
                        'proxy_type': proxy.proxy_type.lower(),
                        'addr': proxy.host,
                        'port': proxy.port,
                        'username': proxy.username,
                        'password': proxy.password
                    }
            
            client = TelegramClient(session_name, **client_kwargs)
            
            # Test connection with retry logic
            for attempt in range(3):
                try:
                    await client.connect()
                    if client.is_connected():
                        logger.info(f"Secure client created for {phone_number}")
                        return client
                except Exception as e:
                    if attempt < 2:
                        await asyncio.sleep(self.login_patterns['retry_delays'][attempt])
                        continue
                    raise e
                    
            return None
            
        except Exception as e:
            logger.error(f"Error creating secure client: {e}")
            return None
    
    async def human_like_otp_request(self, client: TelegramClient, phone_number: str) -> Dict[str, Any]:
        """Send OTP request with human-like behavior"""
        try:
            # Add random delay to simulate user thinking
            thinking_delay = random.choice(self.login_patterns['thinking_pauses'])
            await asyncio.sleep(thinking_delay)
            
            # Check for recent requests to avoid flood
            if self._check_flood_risk(phone_number):
                wait_time = random.choice(self.login_patterns['session_gaps'])
                logger.warning(f"Flood risk detected, waiting {wait_time} seconds")
                await asyncio.sleep(wait_time)
            
            # Send OTP with retry logic
            for attempt in range(3):
                try:
                    result = await client.send_code_request(phone_number)
                    
                    # Log successful request
                    self._log_otp_request(phone_number)
                    
                    return {
                        'success': True,
                        'phone_code_hash': result.phone_code_hash,
                        'type': result.type.__class__.__name__,
                        'message': 'OTP sent successfully'
                    }
                    
                except FloodWaitError as e:
                    if attempt < 2:
                        wait_time = e.seconds + random.randint(5, 15)
                        logger.warning(f"Flood wait: {wait_time} seconds")
                        await asyncio.sleep(wait_time)
                        continue
                    return {
                        'success': False,
                        'error': 'flood_wait',
                        'message': f'Too many requests. Wait {e.seconds} seconds.'
                    }
                    
                except Exception as e:
                    if attempt < 2:
                        await asyncio.sleep(self.login_patterns['retry_delays'][attempt])
                        continue
                    raise e
            
            return {
                'success': False,
                'error': 'max_retries',
                'message': 'Failed after maximum retries'
            }
            
        except Exception as e:
            logger.error(f"Error in human-like OTP request: {e}")
            return {
                'success': False,
                'error': 'unknown',
                'message': str(e)
            }
    
    async def human_like_code_entry(self, client: TelegramClient, phone_number: str, 
                                   phone_code_hash: str, code: str) -> Dict[str, Any]:
        """Enter OTP code with human-like timing"""
        try:
            # Simulate human typing delays
            total_delay = 0
            for digit in code:
                delay = random.choice(self.login_patterns['typing_delays'])
                await asyncio.sleep(delay)
                total_delay += delay
            
            # Add final thinking pause before submission
            final_pause = random.choice(self.login_patterns['thinking_pauses'])
            await asyncio.sleep(final_pause)
            
            # Attempt login with the code
            result = await client.sign_in(phone_number, code, phone_code_hash=phone_code_hash)
            
            # Get user info
            me = await client.get_me()
            
            return {
                'success': True,
                'user_info': {
                    'id': me.id,
                    'phone': me.phone,
                    'username': me.username,
                    'first_name': me.first_name,
                    'last_name': me.last_name,
                },
                'message': 'Login successful',
                'timing_info': {
                    'typing_time': total_delay,
                    'thinking_time': final_pause
                }
            }
            
        except Exception as e:
            logger.error(f"Error in human-like code entry: {e}")
            return {
                'success': False,
                'error': str(type(e).__name__),
                'message': str(e)
            }
    
    def _check_flood_risk(self, phone_number: str) -> bool:
        """Check if there's flood risk for this phone number"""
        # Implementation would check recent request history
        # For now, return False (no risk)
        return False
    
    def _log_otp_request(self, phone_number: str):
        """Log OTP request for flood detection"""
        # Implementation would log to database
        logger.info(f"OTP request logged for {phone_number}")
    
    async def get_location_matched_proxy(self, phone_number: str) -> Optional[ProxyConfig]:
        """Get proxy that matches phone number's country"""
        try:
            # Extract country code from phone number
            if phone_number.startswith('+1'):
                target_country = 'US'
            elif phone_number.startswith('+44'):
                target_country = 'GB'
            elif phone_number.startswith('+91'):
                target_country = 'IN'
            # Add more country mappings as needed
            else:
                target_country = 'US'  # Default fallback
            
            # Get proxy from same region
            proxy = self.proxy_manager.get_country_specific_proxy(target_country)
            return proxy
            
        except Exception as e:
            logger.error(f"Error getting location-matched proxy: {e}")
            return None
    
    async def monitor_security_events(self, client: TelegramClient, phone_number: str):
        """Monitor for security-related events"""
        try:
            # Add event handlers for security notifications
            @client.on(events.NewMessage(incoming=True))
            async def security_handler(event):
                message = event.message.message.lower()
                
                # Check for security-related keywords
                security_keywords = [
                    'login attempt', 'security code', 'suspicious activity',
                    'blocked', 'verification', 'unusual activity'
                ]
                
                if any(keyword in message for keyword in security_keywords):
                    logger.warning(f"Security event detected for {phone_number}: {message}")
                    
                    # Implement automatic response if needed
                    await self._handle_security_event(event, phone_number)
            
        except Exception as e:
            logger.error(f"Error setting up security monitoring: {e}")
    
    async def _handle_security_event(self, event, phone_number: str):
        """Handle detected security events"""
        try:
            message = event.message.message
            
            # Check if it's a login block notification
            if 'login attempt blocked' in message.lower():
                logger.error(f"Login blocked for {phone_number}")
                
                # Wait and retry with different strategy
                await asyncio.sleep(random.randint(1800, 3600))  # Wait 30-60 minutes
                
                # Could trigger alternative login flow here
                
            elif 'verification code' in message.lower():
                # Extract and use the verification code automatically
                import re
                code_match = re.search(r'\b(\d{5})\b', message)
                if code_match:
                    code = code_match.group(1)
                    logger.info(f"Auto-extracted code: {code}")
                    # Store for automatic use
                    
        except Exception as e:
            logger.error(f"Error handling security event: {e}")

# Global instance
security_bypass = SecurityBypassManager()