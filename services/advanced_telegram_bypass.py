"""
Advanced Telegram Security Bypass System
Handles flagged accounts, security blocks, and OTP restrictions
"""

import asyncio
import random
import logging
from telethon import TelegramClient
from telethon.errors import (
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    FloodWaitError,
    SessionPasswordNeededError,
    PhoneNumberInvalidError,
)
from datetime import datetime
import os

from config.bypass_config import (
    BYPASS_OPTIONS,
    DEVICE_PROFILES,
    USER_AGENTS,
    RETRY_STRATEGIES,
    TIMING_PROFILES,
    FLAGGED_INDICATORS,
)

logger = logging.getLogger(__name__)


class AdvancedTelegramBypass:
    """
    Advanced bypass system for Telegram security restrictions
    Handles flagged numbers, code expiry, and security blocks
    """
    
    def __init__(self):
        self.attempt_count = {}
        self.device_rotation_index = {}
        self.last_attempt_time = {}
        self.session_cookies = {}
        
        # Get API credentials
        self.api_id = os.getenv('API_ID')
        self.api_hash = os.getenv('API_HASH')
        
        if not self.api_id or not self.api_hash:
            logger.error("API_ID and API_HASH must be set in environment")
            raise ValueError("Missing Telegram API credentials")
    
    async def send_code_advanced(self, phone_number: str, attempt: int = 1):
        """
        Send OTP code with advanced bypass techniques
        Automatically handles retries, device rotation, and timing
        """
        logger.info(f"[Attempt {attempt}] Sending code to {phone_number} with advanced bypass")
        
        try:
            # Create client with rotating device profile
            client = await self._create_client_with_bypass(phone_number)
            
            # Add realistic pre-request delay
            if BYPASS_OPTIONS['add_realistic_delays']:
                await self._add_pre_request_delay()
            
            # Send code request
            logger.info(f"Requesting code for {phone_number} with device: {self._get_current_device(phone_number)['device_model']}")
            result = await client.send_code_request(phone_number)
            
            logger.info(f"✅ Code sent successfully to {phone_number} (Type: {result.type})")
            
            return {
                'success': True,
                'phone_code_hash': result.phone_code_hash,
                'code_type': str(type(result.type).__name__),
                'message': f'Code sent successfully',
                'client': client,
                'attempt': attempt,
            }
            
        except FloodWaitError as e:
            logger.warning(f"FloodWait: Need to wait {e.seconds} seconds")
            
            if attempt < RETRY_STRATEGIES['FloodWaitError']['max_retries']:
                logger.info(f"Waiting {e.seconds} seconds before retry...")
                await asyncio.sleep(e.seconds + 2)
                return await self.send_code_advanced(phone_number, attempt + 1)
            else:
                return {
                    'success': False,
                    'error': 'flood_wait',
                    'message': f'Too many requests. Please wait {e.seconds} seconds.',
                    'wait_time': e.seconds
                }
        
        except PhoneNumberInvalidError:
            logger.error(f"Invalid phone number format: {phone_number}")
            return {
                'success': False,
                'error': 'invalid_phone',
                'message': 'Invalid phone number format. Include country code (e.g., +1234567890)'
            }
        
        except Exception as e:
            logger.error(f"Error sending code (attempt {attempt}): {str(e)}")
            
            # Retry with different device if possible
            if attempt < BYPASS_OPTIONS['max_retries']:
                logger.info(f"Retrying with different device configuration...")
                self._rotate_device(phone_number)
                
                # Wait before retry
                delay = BYPASS_OPTIONS['retry_delay']
                await asyncio.sleep(delay)
                
                return await self.send_code_advanced(phone_number, attempt + 1)
            else:
                return {
                    'success': False,
                    'error': 'max_retries_exceeded',
                    'message': f'Could not send code after {attempt} attempts. Error: {str(e)}'
                }
    
    async def sign_in_with_bypass(self, client: TelegramClient, phone_number: str, code: str, phone_code_hash: str):
        """
        Sign in with human-like timing and security bypass
        """
        logger.info(f"Signing in {phone_number} with advanced bypass")
        
        try:
            # Add realistic delays before sign-in
            await self._simulate_human_code_entry(code)
            
            # Attempt sign-in
            logger.info(f"Attempting sign-in for {phone_number}...")
            user = await client.sign_in(phone_number, code, phone_code_hash=phone_code_hash)
            
            # Verify authorization (Telegram can silently block)
            await asyncio.sleep(0.5)
            is_authorized = await client.is_user_authorized()
            
            if not is_authorized:
                logger.error(f"❌ Sign-in completed but NOT authorized - security block detected")
                return {
                    'success': False,
                    'error': 'security_block',
                    'message': '⚠️ Telegram security block detected. The code was correct but login was blocked.',
                    'details': 'This happens when Telegram flags the account. Trying alternative methods...'
                }
            
            # Get user info
            me = await client.get_me()
            
            logger.info(f"✅ Successfully signed in: {me.id} ({me.phone})")
            
            return {
                'success': True,
                'user_info': {
                    'id': me.id,
                    'phone': me.phone,
                    'username': me.username,
                    'first_name': me.first_name,
                    'last_name': me.last_name,
                },
                'message': 'Login successful!',
                'client': client
            }
        
        except SessionPasswordNeededError:
            logger.info(f"2FA detected for {phone_number}")
            return {
                'success': False,
                'requires_2fa': True,
                'error': '2fa_required',
                'message': 'This account has Two-Factor Authentication enabled. Password required.',
                'client': client
            }
        
        except PhoneCodeInvalidError:
            logger.warning(f"Invalid code entered for {phone_number}")
            return {
                'success': False,
                'error': 'invalid_code',
                'message': 'The verification code is incorrect. Please check and try again.'
            }
        
        except PhoneCodeExpiredError:
            logger.warning(f"Code expired for {phone_number}")
            return {
                'success': False,
                'error': 'code_expired',
                'message': 'The verification code has expired. Please request a new one.',
                'can_retry': True
            }
        
        except Exception as e:
            logger.error(f"Sign-in error: {str(e)}")
            
            # Check if it's a security block
            error_text = str(e).lower()
            if any(indicator in error_text for indicator in FLAGGED_INDICATORS):
                return {
                    'success': False,
                    'error': 'security_block',
                    'message': '⚠️ Telegram flagged this account. Trying recovery methods...',
                    'flagged': True
                }
            
            return {
                'success': False,
                'error': 'unknown',
                'message': f'Login error: {str(e)}'
            }
    
    async def handle_2fa(self, client: TelegramClient, password: str):
        """
        Handle 2FA password authentication
        """
        try:
            logger.info("Attempting 2FA authentication...")
            await client.sign_in(password=password)
            
            # Verify
            is_authorized = await client.is_user_authorized()
            if is_authorized:
                me = await client.get_me()
                logger.info(f"✅ 2FA authentication successful for {me.phone}")
                
                return {
                    'success': True,
                    'user_info': {
                        'id': me.id,
                        'phone': me.phone,
                        'username': me.username,
                        'first_name': me.first_name,
                        'last_name': me.last_name,
                    },
                    'message': '2FA authentication successful!'
                }
            else:
                return {
                    'success': False,
                    'error': '2fa_failed',
                    'message': '2FA authentication failed - not authorized'
                }
        
        except Exception as e:
            logger.error(f"2FA error: {str(e)}")
            return {
                'success': False,
                'error': '2fa_error',
                'message': f'2FA authentication failed: {str(e)}'
            }
    
    async def _create_client_with_bypass(self, phone_number: str):
        """
        Create Telegram client with device spoofing and security bypass
        """
        # Get device profile for this phone number
        device = self._get_current_device(phone_number)
        
        # Create unique session name
        session_name = f"bypass_{phone_number}_{random.randint(1000, 9999)}"
        
        # Create client with spoofed device info
        client = TelegramClient(
            session_name,
            self.api_id,
            self.api_hash,
            device_model=device['device_model'],
            system_version=device['system_version'],
            app_version=device['app_version'],
            lang_code=device['lang_code'],
            system_lang_code=device['system_lang_code']
        )
        
        # Connect
        await client.connect()
        
        logger.info(f"Created client with device: {device['device_model']} ({device['system_version']})")
        
        return client
    
    def _get_current_device(self, phone_number: str):
        """
        Get current device profile for phone number
        """
        if phone_number not in self.device_rotation_index:
            self.device_rotation_index[phone_number] = 0
        
        index = self.device_rotation_index[phone_number]
        return DEVICE_PROFILES[index % len(DEVICE_PROFILES)]
    
    def _rotate_device(self, phone_number: str):
        """
        Rotate to next device profile
        """
        if phone_number not in self.device_rotation_index:
            self.device_rotation_index[phone_number] = 0
        
        self.device_rotation_index[phone_number] += 1
        new_device = self._get_current_device(phone_number)
        logger.info(f"Rotated to device: {new_device['device_model']}")
    
    async def _add_pre_request_delay(self):
        """
        Add realistic delay before request
        """
        delay = random.uniform(
            BYPASS_OPTIONS['min_delay'],
            BYPASS_OPTIONS['max_delay']
        )
        logger.debug(f"Pre-request delay: {delay:.2f}s")
        await asyncio.sleep(delay)
    
    async def _simulate_human_code_entry(self, code: str):
        """
        Simulate human-like delays when entering code
        Reduced delays to avoid code expiry
        """
        # Reading delay (user opens SMS/Telegram and reads code)
        reading_min, reading_max = TIMING_PROFILES['code_reading']
        reading_delay = random.uniform(reading_min, reading_max)
        logger.debug(f"Code reading delay: {reading_delay:.2f}s")
        await asyncio.sleep(reading_delay)
        
        # Typing delay (character by character)
        typing_min, typing_max = TIMING_PROFILES['typing_per_char']
        total_typing = 0
        for i, char in enumerate(code):
            # Faster typing for later characters (muscle memory)
            if i == 0:
                char_delay = random.uniform(typing_max * 1.5, typing_max * 2)
            elif i < 3:
                char_delay = random.uniform(typing_min, typing_max)
            else:
                char_delay = random.uniform(typing_min * 0.8, typing_max * 0.8)
            
            await asyncio.sleep(char_delay)
            total_typing += char_delay
        
        logger.debug(f"Typing delay: {total_typing:.2f}s")
        
        # Double-check delay (user verifies code before submitting)
        check_min, check_max = TIMING_PROFILES['double_check']
        check_delay = random.uniform(check_min, check_max)
        logger.debug(f"Double-check delay: {check_delay:.2f}s")
        await asyncio.sleep(check_delay)
        
        # Submission delay (clicking submit button)
        submit_min, submit_max = TIMING_PROFILES['submission']
        submit_delay = random.uniform(submit_min, submit_max)
        logger.debug(f"Submission delay: {submit_delay:.2f}s")
        await asyncio.sleep(submit_delay)
        
        total_delay = reading_delay + total_typing + check_delay + submit_delay
        logger.info(f"Total human-like delay: {total_delay:.2f}s")
    
    async def add_realistic_delays(self):
        """
        Public method to add realistic delays
        """
        await self._add_pre_request_delay()


# Singleton instance - lazy initialization
bypass_instance = None

def get_bypass_instance():
    """Get or create bypass instance"""
    global bypass_instance
    if bypass_instance is None:
        bypass_instance = AdvancedTelegramBypass()
    return bypass_instance
