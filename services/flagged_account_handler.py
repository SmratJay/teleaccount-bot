"""
Flagged Account Handler
Specialized handling for Telegram-flagged accounts with multiple recovery strategies
"""

import asyncio
import logging
from telethon import TelegramClient
from telethon.errors import *
from datetime import datetime, timedelta

from services.advanced_telegram_bypass import AdvancedTelegramBypass
from config.bypass_config import BYPASS_OPTIONS, FLAGGED_INDICATORS

logger = logging.getLogger(__name__)


class FlaggedAccountHandler:
    """
    Handles accounts that have been flagged by Telegram
    Implements multiple recovery and bypass strategies
    """
    
    def __init__(self):
        self.bypass = AdvancedTelegramBypass()
        self.flagged_accounts = {}  # Track flagged numbers
        self.recovery_attempts = {}  # Track recovery attempts
    
    async def check_if_flagged(self, phone_number: str) -> bool:
        """
        Check if a phone number is flagged by Telegram
        """
        logger.info(f"Checking if {phone_number} is flagged...")
        
        # Check our internal records
        if phone_number in self.flagged_accounts:
            flagged_info = self.flagged_accounts[phone_number]
            logger.warning(f"Number {phone_number} was previously flagged: {flagged_info}")
            return True
        
        # Try a quick test login to detect flags
        try:
            result = await self._quick_flag_test(phone_number)
            return result['is_flagged']
        
        except Exception as e:
            logger.error(f"Error checking flag status: {str(e)}")
            return False
    
    async def _quick_flag_test(self, phone_number: str):
        """
        Quick test to detect if number is flagged
        """
        try:
            # Try to send code
            result = await self.bypass.send_code_advanced(phone_number, attempt=1)
            
            if not result['success']:
                error = result.get('error', '')
                message = result.get('message', '').lower()
                
                # Check for flagging indicators
                is_flagged = any(indicator in message for indicator in FLAGGED_INDICATORS)
                
                if is_flagged:
                    logger.warning(f"🚨 Detected flagging for {phone_number}")
                    self._mark_as_flagged(phone_number, error, message)
                    
                    return {
                        'is_flagged': True,
                        'reason': message
                    }
            
            return {
                'is_flagged': False
            }
        
        except Exception as e:
            logger.error(f"Quick flag test error: {str(e)}")
            return {
                'is_flagged': False  # Assume not flagged if test fails
            }
    
    def _mark_as_flagged(self, phone_number: str, error: str, message: str):
        """
        Mark a phone number as flagged
        """
        self.flagged_accounts[phone_number] = {
            'flagged_at': datetime.now(),
            'error': error,
            'message': message,
            'recovery_attempts': 0
        }
        logger.info(f"Marked {phone_number} as flagged")
    
    async def handle_flagged_login(self, phone_number: str, password: str = None):
        """
        Handle login for flagged account with multiple strategies
        """
        logger.info(f"🔄 Handling flagged login for {phone_number}")
        
        # Track recovery attempts
        if phone_number not in self.recovery_attempts:
            self.recovery_attempts[phone_number] = 0
        
        self.recovery_attempts[phone_number] += 1
        attempt = self.recovery_attempts[phone_number]
        
        logger.info(f"Recovery attempt #{attempt} for {phone_number}")
        
        # Strategy 1: Multiple device rotation (attempts 1-3)
        if attempt <= 3:
            logger.info(f"Strategy 1: Device rotation (attempt {attempt})")
            result = await self._strategy_device_rotation(phone_number, attempt)
            if result['success']:
                return result
        
        # Strategy 2: Extended delays + device rotation (attempts 4-6)
        if attempt <= 6:
            logger.info(f"Strategy 2: Extended delays + rotation (attempt {attempt})")
            result = await self._strategy_extended_delays(phone_number, attempt)
            if result['success']:
                return result
        
        # Strategy 3: 2FA fallback (if password provided)
        if password and attempt <= 8:
            logger.info(f"Strategy 3: 2FA fallback (attempt {attempt})")
            result = await self._strategy_2fa_fallback(phone_number, password, attempt)
            if result['success']:
                return result
        
        # Strategy 4: Cool-down period recommendation
        if attempt <= 10:
            logger.info(f"Strategy 4: Cool-down recommendation (attempt {attempt})")
            return await self._strategy_cooldown(phone_number)
        
        # All strategies exhausted
        logger.error(f"❌ All recovery strategies exhausted for {phone_number}")
        return {
            'success': False,
            'error': 'recovery_failed',
            'message': f'Unable to recover flagged account after {attempt} attempts. '
                      'The account may need manual intervention or a longer cool-down period.',
            'suggestions': [
                '1. Wait 24-48 hours before trying again',
                '2. Try from a different IP address/location',
                '3. Contact Telegram support if this persists',
                '4. Ensure you are the legitimate account owner',
            ]
        }
    
    async def _strategy_device_rotation(self, phone_number: str, attempt: int):
        """
        Strategy 1: Aggressive device rotation
        """
        try:
            # Rotate device multiple times
            for i in range(attempt):
                self.bypass._rotate_device(phone_number)
            
            # Try to send code with new device
            result = await self.bypass.send_code_advanced(phone_number, attempt=1)
            
            if result['success']:
                logger.info(f"✅ Device rotation successful for {phone_number}")
                return result
            
            return result
        
        except Exception as e:
            logger.error(f"Device rotation strategy failed: {str(e)}")
            return {
                'success': False,
                'error': 'strategy_failed',
                'message': str(e)
            }
    
    async def _strategy_extended_delays(self, phone_number: str, attempt: int):
        """
        Strategy 2: Extended delays between attempts
        """
        try:
            # Wait longer based on attempt number
            delay = 15 * attempt  # 15, 30, 45 seconds...
            logger.info(f"Waiting {delay} seconds before retry...")
            await asyncio.sleep(delay)
            
            # Rotate device
            self.bypass._rotate_device(phone_number)
            
            # Try again
            result = await self.bypass.send_code_advanced(phone_number, attempt=1)
            
            if result['success']:
                logger.info(f"✅ Extended delay strategy successful for {phone_number}")
                return result
            
            return result
        
        except Exception as e:
            logger.error(f"Extended delay strategy failed: {str(e)}")
            return {
                'success': False,
                'error': 'strategy_failed',
                'message': str(e)
            }
    
    async def _strategy_2fa_fallback(self, phone_number: str, password: str, attempt: int):
        """
        Strategy 3: Try 2FA if available
        """
        try:
            logger.info(f"Attempting 2FA fallback for {phone_number}")
            
            # First send code
            code_result = await self.bypass.send_code_advanced(phone_number, attempt=1)
            
            if code_result['success']:
                # If we got code, user needs to enter it
                # Then we can try 2FA
                return {
                    'success': True,
                    'requires_user_code': True,
                    'message': 'Code sent. After entering code, 2FA password will be requested.',
                    **code_result
                }
            
            return code_result
        
        except Exception as e:
            logger.error(f"2FA fallback strategy failed: {str(e)}")
            return {
                'success': False,
                'error': 'strategy_failed',
                'message': str(e)
            }
    
    async def _strategy_cooldown(self, phone_number: str):
        """
        Strategy 4: Recommend cool-down period
        """
        logger.info(f"Recommending cool-down for {phone_number}")
        
        # Calculate recommended wait time
        if phone_number in self.flagged_accounts:
            flagged_at = self.flagged_accounts[phone_number]['flagged_at']
            time_since_flag = datetime.now() - flagged_at
            hours_since = time_since_flag.total_seconds() / 3600
            
            if hours_since < 24:
                recommended_wait = 24 - hours_since
                return {
                    'success': False,
                    'error': 'cooldown_needed',
                    'message': f'This account was flagged {hours_since:.1f} hours ago. '
                              f'Recommended wait time: {recommended_wait:.1f} more hours.',
                    'recommended_wait_hours': recommended_wait,
                    'can_retry_at': (datetime.now() + timedelta(hours=recommended_wait)).isoformat()
                }
        
        return {
            'success': False,
            'error': 'cooldown_needed',
            'message': 'Multiple attempts failed. Please wait 24-48 hours before trying again.',
            'recommended_wait_hours': 24
        }
    
    def reset_recovery_attempts(self, phone_number: str):
        """
        Reset recovery attempt counter for a phone number
        """
        if phone_number in self.recovery_attempts:
            del self.recovery_attempts[phone_number]
            logger.info(f"Reset recovery attempts for {phone_number}")
    
    def get_flagged_status(self, phone_number: str):
        """
        Get detailed flagged status for a phone number
        """
        if phone_number in self.flagged_accounts:
            info = self.flagged_accounts[phone_number]
            flagged_at = info['flagged_at']
            time_since = datetime.now() - flagged_at
            
            return {
                'is_flagged': True,
                'flagged_at': flagged_at.isoformat(),
                'hours_since_flag': time_since.total_seconds() / 3600,
                'error': info['error'],
                'message': info['message'],
                'recovery_attempts': info.get('recovery_attempts', 0)
            }
        
        return {
            'is_flagged': False
        }


# Singleton instance - lazy initialization
flagged_handler_instance = None

def get_flagged_handler_instance():
    """Get or create flagged handler instance"""
    global flagged_handler_instance
    if flagged_handler_instance is None:
        flagged_handler_instance = FlaggedAccountHandler()
    return flagged_handler_instance
