"""
Ultra-Aggressive Bypass for Heavily Flagged Accounts
Implements additional verification and session persistence techniques
"""

import asyncio
import logging
from telethon import TelegramClient
from telethon.errors import *
from telethon.tl.functions.account import GetPasswordRequest
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty

from services.advanced_telegram_bypass import AdvancedTelegramBypass
from config.bypass_config import BYPASS_OPTIONS

logger = logging.getLogger(__name__)


class UltraAggressiveBypass(AdvancedTelegramBypass):
    """
    Enhanced bypass for accounts that get "code was previously shared" error
    even with correct code entry
    """
    
    async def sign_in_ultra_aggressive(self, client: TelegramClient, phone_number: str, 
                                       code: str, phone_code_hash: str):
        """
        Ultra-aggressive sign-in with multiple validation steps
        """
        logger.info(f"🚨 ULTRA-AGGRESSIVE BYPASS for {phone_number}")
        
        try:
            # Step 1: Extra long pre-sign-in delay (appear as human double-checking)
            logger.info("Step 1: Simulating careful code verification...")
            await asyncio.sleep(2.5)  # Human double-checking code
            
            # Step 2: Simulate typing the code slowly
            await self._simulate_ultra_slow_typing(code)
            
            # Step 3: Add a pause (human hesitation before pressing Enter)
            logger.info("Step 2: Adding human hesitation...")
            await asyncio.sleep(1.8)
            
            # Step 4: Attempt sign-in
            logger.info(f"Step 3: Attempting sign-in for {phone_number}...")
            user = await client.sign_in(phone_number, code, phone_code_hash=phone_code_hash)
            
            # Step 5: Wait before checking authorization (give Telegram time to process)
            await asyncio.sleep(2.0)
            
            # Step 6: Check authorization multiple times (sometimes it takes a moment)
            logger.info("Step 4: Verifying authorization...")
            for attempt in range(3):
                is_authorized = await client.is_user_authorized()
                
                if is_authorized:
                    logger.info(f"✅ Authorization confirmed on attempt {attempt + 1}")
                    break
                
                logger.warning(f"Not yet authorized, waiting... (attempt {attempt + 1}/3)")
                await asyncio.sleep(2.0)
            
            if not is_authorized:
                logger.error(f"❌ Sign-in completed but NOT authorized after 3 checks")
                
                # Try to trigger authorization by making a legitimate API call
                logger.info("Step 5: Attempting to trigger authorization with API call...")
                try:
                    # Get dialogs (this sometimes triggers authorization)
                    await client(GetDialogsRequest(
                        offset_date=None,
                        offset_id=0,
                        offset_peer=InputPeerEmpty(),
                        limit=1,
                        hash=0
                    ))
                    
                    # Check again
                    await asyncio.sleep(1.0)
                    is_authorized = await client.is_user_authorized()
                    
                    if is_authorized:
                        logger.info("✅ Authorization triggered by API call!")
                    else:
                        logger.error("❌ Still not authorized after API call")
                        return {
                            'success': False,
                            'error': 'security_block_persistent',
                            'message': '⚠️ Telegram persistent security block. Code was correct but login blocked.',
                            'details': 'Your number is heavily flagged. This may require:\n'
                                      '1. Waiting 24-48 hours\n'
                                      '2. Trying from a different IP/location\n'
                                      '3. Using a VPN\n'
                                      '4. Contacting Telegram support',
                            'suggestion': 'wait_24_hours'
                        }
                
                except Exception as api_error:
                    logger.error(f"API call failed: {str(api_error)}")
                    return {
                        'success': False,
                        'error': 'security_block',
                        'message': '⚠️ Telegram security block detected.',
                        'details': str(api_error)
                    }
            
            # Step 7: Perform additional verification steps to appear legitimate
            logger.info("Step 6: Performing legitimacy checks...")
            try:
                # Get user info
                me = await client.get_me()
                
                # Get password info (2FA check)
                await asyncio.sleep(0.5)
                password_info = await client(GetPasswordRequest())
                
                # Small delay (human reviewing their account)
                await asyncio.sleep(1.0)
                
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
                    'has_2fa': password_info.has_password,
                    'message': 'Login successful with ultra-aggressive bypass!',
                    'client': client,
                    'bypass_level': 'ultra_aggressive'
                }
            
            except Exception as verify_error:
                logger.error(f"Verification failed: {str(verify_error)}")
                return {
                    'success': False,
                    'error': 'verification_failed',
                    'message': f'Verification error: {str(verify_error)}'
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
            logger.error(f"Ultra-aggressive sign-in error: {str(e)}")
            logger.error(f"Full traceback:", exc_info=True)
            
            return {
                'success': False,
                'error': 'unknown',
                'message': f'Login error: {str(e)}',
                'suggestion': 'This account may be permanently flagged. Consider waiting 24-48 hours.'
            }
    
    async def _simulate_ultra_slow_typing(self, code: str):
        """
        Simulate very slow, careful typing (human being extra careful)
        """
        logger.info(f"Simulating ultra-careful code entry...")
        
        # Reading time (longer - human being extra careful with flagged account)
        reading_delay = 2.0 + (len(code) * 0.3)  # ~2.0-3.5s for 5-digit code
        await asyncio.sleep(reading_delay)
        
        # Type each digit with longer pauses
        for i, digit in enumerate(code):
            char_delay = 0.15 + (0.1 * (i % 2))  # 0.15-0.25s per character
            await asyncio.sleep(char_delay)
            logger.debug(f"Typed character {i+1}/{len(code)}")
        
        # Final verification pause (human double-checking before submit)
        verification_pause = 2.5
        await asyncio.sleep(verification_pause)
        
        total_time = reading_delay + (len(code) * 0.2) + verification_pause
        logger.info(f"Code entry completed in {total_time:.1f}s (ultra-slow mode)")
    
    async def sign_in_with_session_persistence(self, client: TelegramClient, phone_number: str,
                                               code: str, phone_code_hash: str, session_file: str = None):
        """
        Sign in with session file persistence for future use
        """
        logger.info(f"🔐 Attempting session-persistent login for {phone_number}")
        
        # Use ultra-aggressive bypass
        result = await self.sign_in_ultra_aggressive(client, phone_number, code, phone_code_hash)
        
        if result['success'] and session_file:
            try:
                # Save session for future use
                logger.info(f"Saving session to {session_file}")
                # Session is automatically saved by Telethon when using file-based session
                result['session_saved'] = True
                result['session_file'] = session_file
            
            except Exception as e:
                logger.error(f"Failed to save session: {str(e)}")
                result['session_saved'] = False
        
        return result


# Create ultra-aggressive instance
ultra_bypass = UltraAggressiveBypass()

