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
from telethon.errors import (
    FloodWaitError, 
    PhoneNumberInvalidError,
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    PhoneCodeHashEmptyError
)
# import aiohttp  # Optional - only needed for proxy testing
# import user_agents  # Optional - for user agent rotation
from services.proxy_manager import proxy_manager, ProxyConfig, OperationType

logger = logging.getLogger(__name__)

class SecurityBypassManager:
    """Advanced security bypass techniques for Telegram login"""
    
    def __init__(self):
        self.proxy_manager = proxy_manager
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
    
    async def get_secure_proxy(self, phone_number: str, operation: OperationType = OperationType.LOGIN) -> Optional[ProxyConfig]:
        """
        Get a secure, phone-specific proxy using operation-based selection.
        
        Args:
            phone_number: Phone number for proxy assignment
            operation: Type of operation (LOGIN, ACCOUNT_CREATION, OTP_RETRIEVAL, etc.)
        
        Returns:
            ProxyConfig or None
        """
        try:
            # Generate consistent proxy for same phone to maintain IP consistency
            phone_hash = hashlib.md5(phone_number.encode()).hexdigest()
            
            # Check if we have a cached proxy for this phone
            if phone_hash in self.session_cache:
                cached_data = self.session_cache[phone_hash]
                if datetime.now() - cached_data['assigned_at'] < timedelta(hours=24):
                    logger.debug(f"Using cached proxy for {phone_number}")
                    return cached_data['proxy']
            
            # Extract country code from phone number (first 1-3 digits)
            country_code = None
            if phone_number.startswith('+'):
                # Try to extract country code
                clean_number = phone_number[1:]
                if clean_number[:2] in ['1', '7', '20', '27', '30', '31', '32', '33', '34', '36', '39', '40', '41', '43', '44', '45', '46', '47', '48', '49', '51', '52', '53', '54', '55', '56', '57', '58', '60', '61', '62', '63', '64', '65', '66', '81', '82', '84', '86', '90', '91', '92', '93', '94', '95', '98']:
                    country_code = clean_number[:2]
                elif clean_number[:1] in ['1', '7']:
                    country_code = clean_number[:1]
                elif clean_number[:3] in ['351', '352', '353', '354', '355', '356', '357', '358', '359', '370', '371', '372', '373', '374', '375', '376', '377', '378', '380', '381', '382', '383', '385', '386', '387', '389', '420', '421', '423']:
                    country_code = clean_number[:3]
            
            # Get proxy using operation-based selection
            logger.info(f"Getting proxy for operation: {operation.value}, phone: {phone_number[:5]}***")
            proxy = self.proxy_manager.get_proxy_for_operation(operation, country_code)
            
            if proxy:
                # Verify proxy works
                if await self._test_proxy_connectivity(proxy):
                    # Cache for consistency
                    self.session_cache[phone_hash] = {
                        'proxy': proxy,
                        'assigned_at': datetime.now(),
                        'operation': operation.value
                    }
                    logger.info(f"Assigned {proxy.host}:{proxy.port} to {phone_number[:5]}*** for {operation.value}")
                    return proxy
                else:
                    logger.warning(f"Proxy {proxy.host}:{proxy.port} failed connectivity test")
                    
            logger.warning(f"No suitable proxy found for operation {operation.value}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting secure proxy: {e}", exc_info=True)
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
    
    async def create_secure_client(self, phone_number: str, api_id: int, api_hash: str, operation: OperationType = OperationType.LOGIN) -> Optional[TelegramClient]:
        """
        Create a secure Telethon client with anti-detection measures.
        
        Args:
            phone_number: Phone number for the client
            api_id: Telegram API ID
            api_hash: Telegram API hash
            operation: Type of operation (affects proxy selection)
        
        Returns:
            TelegramClient or None
        """
        try:
            # Get secure proxy with operation-based selection
            proxy = await self.get_secure_proxy(phone_number, operation)
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
                logger.info(f"Using proxy {proxy.host}:{proxy.port} (type: {proxy.proxy_type}) for {operation.value}")
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
            else:
                logger.warning(f"No proxy available for {operation.value}, using direct connection")
            
            client = TelegramClient(session_name, **client_kwargs)
            
            # Test connection with retry logic
            for attempt in range(3):
                try:
                    await client.connect()
                    if client.is_connected():
                        logger.info(f"Secure client created for {phone_number} ({operation.value})")
                        return client
                except Exception as e:
                    if attempt < 2:
                        await asyncio.sleep(self.login_patterns['retry_delays'][attempt])
                        continue
                    raise e
                    
            return None
            
        except Exception as e:
            logger.error(f"Error creating secure client: {e}", exc_info=True)
            return None
    
    async def human_like_otp_request(self, client: TelegramClient, phone_number: str, force_sms: bool = True) -> Dict[str, Any]:
        """
        Send OTP request with human-like behavior
        
        Args:
            client: Telegram client
            phone_number: Phone number to send OTP to
            force_sms: If True, forces SMS delivery instead of Telegram app (RECOMMENDED to avoid security blocks)
        """
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
                    # CRITICAL: Force SMS delivery to avoid "code was shared" detection
                    # When force_sms=True, Telegram sends code via SMS, not to Telegram app
                    # This prevents Telegram from seeing the code was "exposed/shared"
                    if force_sms:
                        logger.info(f"Forcing SMS delivery for {phone_number} (security bypass)")
                        result = await client.send_code_request(phone_number, force_sms=True)
                    else:
                        result = await client.send_code_request(phone_number)
                    
                    # Log successful request
                    self._log_otp_request(phone_number)
                    
                    delivery_method = "SMS" if force_sms else result.type.__class__.__name__
                    logger.info(f"OTP sent to {phone_number} via {delivery_method}")
                    
                    return {
                        'success': True,
                        'phone_code_hash': result.phone_code_hash,
                        'type': delivery_method,
                        'message': f'OTP sent via {delivery_method}',
                        'force_sms': force_sms
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
        """Enter OTP code with ULTRA-realistic human-like timing to bypass security"""
        try:
            # 1. REALISTIC PRE-READING DELAY (REDUCED to avoid code expiry)
            # Simulate user opening SMS app, finding the code, and focusing
            pre_reading_delay = random.uniform(1.0, 2.5)  # Reduced from 3.0-7.5 to avoid code expiry
            logger.debug(f"Simulating code reading time: {pre_reading_delay:.2f}s")
            await asyncio.sleep(pre_reading_delay)
            
            # 2. REALISTIC CHARACTER-BY-CHARACTER TYPING (FASTER)
            # Humans don't type at constant speed - they have variations
            total_delay = 0
            code_length = len(code)
            
            for i, digit in enumerate(code):
                # Base typing speed with natural variation (FASTER to avoid expiry)
                if i == 0:
                    # First digit: slower (user just started typing)
                    base_delay = random.uniform(0.15, 0.28)  # Was 0.25-0.45
                elif i < 3:
                    # First few digits: medium speed
                    base_delay = random.uniform(0.12, 0.22)  # Was 0.18-0.32
                else:
                    # Later digits: faster (muscle memory kicks in)
                    base_delay = random.uniform(0.08, 0.15)  # Was 0.12-0.22
                
                # Add micro-pauses (humans aren't perfectly consistent)
                micro_pause = random.uniform(-0.03, 0.05)  # Reduced variation
                final_delay = max(0.06, base_delay + micro_pause)
                
                await asyncio.sleep(final_delay)
                total_delay += final_delay
            
            # 3. REALISTIC DOUBLE-CHECK PAUSE (REDUCED)
            # User looks at what they typed, compares with code
            double_check_pause = random.uniform(0.5, 1.5)  # Was 1.2-3.5
            logger.debug(f"Simulating double-check pause: {double_check_pause:.2f}s")
            await asyncio.sleep(double_check_pause)
            
            # 4. REALISTIC SUBMISSION DELAY
            # User moves mouse/finger to submit button
            submission_delay = random.uniform(0.2, 0.6)  # Was 0.3-0.9
            await asyncio.sleep(submission_delay)
            
            total_time = pre_reading_delay + total_delay + double_check_pause + submission_delay
            logger.info(f"Total realistic timing: {total_time:.2f}s (reading={pre_reading_delay:.2f}s, typing={total_delay:.2f}s, checking={double_check_pause:.2f}s)")
            
            # 5. ATTEMPT LOGIN WITH THE CODE
            try:
                result = await client.sign_in(phone_number, code, phone_code_hash=phone_code_hash)
                
                # CRITICAL: Verify session is ACTUALLY authorized
                # Telegram might complete sign_in but block authorization server-side
                await asyncio.sleep(0.5)  # Small delay for server to process
                
                is_authorized = await client.is_user_authorized()
                if not is_authorized:
                    logger.error(f"Sign-in completed but user NOT authorized for {phone_number}")
                    logger.error("This indicates Telegram's security system blocked the login")
                    return {
                        'success': False,
                        'error': 'security_block',
                        'message': '⚠️ Security Check Failed\n\n'
                                   'Telegram blocked this login attempt. This can happen when:\n'
                                   '• The verification code was viewed in Telegram app\n'
                                   '• The code was shared or copied\n'
                                   '• Multiple login attempts detected\n\n'
                                   '💡 Try receiving the code via SMS instead of Telegram app.',
                        'security_blocked': True
                    }
                
                # Get user info
                me = await client.get_me()
                
                logger.info(f"Successfully authorized user {me.id} ({me.phone})")
                
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
                        'reading_time': pre_reading_delay,
                        'typing_time': total_delay,
                        'checking_time': double_check_pause,
                        'total_time': total_time
                    }
                }
                
            except SessionPasswordNeededError:
                # Account has 2FA enabled
                logger.info(f"2FA detected for {phone_number}")
                return {
                    'success': False,
                    'error': '2fa_required',
                    'message': 'This account has Two-Factor Authentication enabled. Password required.',
                    'requires_2fa': True
                }
                
            except PhoneCodeInvalidError:
                logger.warning(f"Invalid code entered for {phone_number}")
                return {
                    'success': False,
                    'error': 'invalid_code',
                    'message': 'The verification code you entered is incorrect.'
                }
                
            except PhoneCodeExpiredError:
                logger.warning(f"Expired code for {phone_number}")
                return {
                    'success': False,
                    'error': 'code_expired',
                    'message': 'The verification code has expired. Please request a new one.'
                }
                
            except PhoneCodeHashEmptyError:
                logger.error(f"Code hash empty for {phone_number}")
                return {
                    'success': False,
                    'error': 'session_error',
                    'message': 'Session error. Please start the process again.'
                }
            
        except Exception as e:
            logger.error(f"Error in human-like code entry: {type(e).__name__}: {e}")
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