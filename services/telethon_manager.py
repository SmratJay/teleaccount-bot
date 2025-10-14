"""
Telethon client management for Telegram account operations.
"""
import os
import asyncio
import logging
from typing import Optional, Dict, Any, Tuple
from telethon import TelegramClient
from telethon.errors import (
    SessionPasswordNeededError, PhoneCodeInvalidError,
    PhoneNumberInvalidError, FloodWaitError, RPCError
)
from telethon.tl.functions.auth import LogOutRequest
from telethon.tl.functions.account import UpdatePasswordSettingsRequest, GetPasswordRequest
from telethon.tl.types import InputCheckPasswordSRP
from telethon.password import compute_check

from services.proxy_manager import ProxyManager, ProxyConfig
from utils.helpers import SecurityUtils, get_session_file_path
from database import get_db_session, close_db_session
from database.operations import AccountService

logger = logging.getLogger(__name__)

class TelethonManager:
    """Manages Telethon clients for Telegram accounts."""
    
    def __init__(self):
        self.api_id = int(os.getenv('API_ID', 0))
        self.api_hash = os.getenv('API_HASH')
        self.proxy_manager = ProxyManager()
        self.active_clients: Dict[str, TelegramClient] = {}
        
        if not self.api_id or not self.api_hash:
            raise ValueError("API_ID and API_HASH environment variables are required")
    
    async def create_client_with_proxy(self, phone_number: str) -> Tuple[Optional[TelegramClient], Optional[ProxyConfig]]:
        """Create a Telethon client with a unique proxy."""
        try:
            # Get unique proxy
            proxy_config = self.proxy_manager.get_unique_proxy()
            
            if not proxy_config:
                logger.warning(f"No proxy available for {phone_number}, proceeding without proxy")
            
            # Get session file path
            session_path = get_session_file_path(phone_number)
            
            # Configure proxy for Telethon
            proxy_dict = None
            if proxy_config:
                proxy_dict = self.proxy_manager.get_proxy_dict(proxy_config)
                logger.info(f"Using proxy {proxy_config.host}:{proxy_config.port} for {phone_number}")
            
            # Create Telethon client
            client = TelegramClient(
                session_path,
                self.api_id,
                self.api_hash,
                proxy=proxy_dict
            )
            
            # Test connection
            try:
                await client.connect()
                logger.info(f"Successfully connected Telethon client for {phone_number}")
                
                # Store active client
                self.active_clients[phone_number] = client
                
                return client, proxy_config
                
            except Exception as e:
                logger.error(f"Failed to connect Telethon client for {phone_number}: {e}")
                
                # Report proxy failure if using proxy
                if proxy_config:
                    self.proxy_manager.report_proxy_failure(proxy_config)
                
                await client.disconnect()
                return None, None
                
        except Exception as e:
            logger.error(f"Error creating Telethon client for {phone_number}: {e}")
            return None, None
    
    async def send_code_request(self, client: TelegramClient, phone_number: str) -> Optional[str]:
        """Send authentication code request."""
        try:
            result = await client.send_code_request(phone_number)
            phone_code_hash = result.phone_code_hash
            logger.info(f"Code request sent for {phone_number}")
            return phone_code_hash
        except PhoneNumberInvalidError:
            logger.error(f"Invalid phone number: {phone_number}")
            return None
        except FloodWaitError as e:
            logger.error(f"Flood wait error for {phone_number}: {e.seconds} seconds")
            return None
        except Exception as e:
            logger.error(f"Error sending code request for {phone_number}: {e}")
            return None
    
    async def sign_in_with_code(self, client: TelegramClient, phone_number: str, 
                               code: str, phone_code_hash: str) -> Tuple[bool, Optional[str]]:
        """Sign in with authentication code."""
        try:
            user = await client.sign_in(phone_number, code, phone_code_hash=phone_code_hash)
            logger.info(f"Successfully signed in user {user.id} for {phone_number}")
            return True, None
            
        except SessionPasswordNeededError:
            logger.info(f"2FA password required for {phone_number}")
            return False, "2FA_REQUIRED"
            
        except PhoneCodeInvalidError:
            logger.error(f"Invalid code for {phone_number}")
            return False, "INVALID_CODE"
            
        except Exception as e:
            logger.error(f"Error signing in for {phone_number}: {e}")
            return False, f"ERROR: {str(e)}"
    
    async def sign_in_with_password(self, client: TelegramClient, password: str) -> bool:
        """Sign in with 2FA password."""
        try:
            await client.sign_in(password=password)
            logger.info("Successfully signed in with 2FA password")
            return True
        except Exception as e:
            logger.error(f"Error signing in with password: {e}")
            return False
    
    async def setup_2fa(self, client: TelegramClient) -> Optional[str]:
        """Set up 2FA for the account."""
        try:
            # Generate a strong password
            password = SecurityUtils.generate_password(20)
            
            # Get current password state
            password_info = await client(GetPasswordRequest())
            
            if password_info.has_password:
                logger.info("Account already has 2FA enabled")
                return None
            
            # Set up 2FA
            from telethon.tl.functions.account import UpdatePasswordSettingsRequest
            from telethon.tl.types import account
            
            # Create new password settings
            new_settings = account.PasswordInputSettings(
                new_algo=password_info.new_algo,
                new_password_hash=password.encode(),
                hint="Bot generated password"
            )
            
            await client(UpdatePasswordSettingsRequest(
                password=InputCheckPasswordSRP(srp_id=0, A=b'', M1=b''),
                new_settings=new_settings
            ))
            
            logger.info("2FA successfully set up")
            return password
            
        except Exception as e:
            logger.error(f"Error setting up 2FA: {e}")
            return None
    
    async def logout_other_sessions(self, client: TelegramClient) -> bool:
        """Logout from all other sessions."""
        try:
            from telethon.tl.functions.auth import ResetAuthorizationsRequest
            await client(ResetAuthorizationsRequest())
            logger.info("Successfully logged out from other sessions")
            return True
        except Exception as e:
            logger.error(f"Error logging out other sessions: {e}")
            return False
    
    async def get_account_info(self, client: TelegramClient) -> Optional[Dict[str, Any]]:
        """Get account information."""
        try:
            me = await client.get_me()
            
            account_info = {
                'user_id': me.id,
                'username': me.username,
                'first_name': me.first_name,
                'last_name': me.last_name,
                'phone': me.phone,
                'is_premium': getattr(me, 'premium', False),
                'is_verified': getattr(me, 'verified', False)
            }
            
            logger.info(f"Retrieved account info for user {me.id}")
            return account_info
            
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return None
    
    async def update_profile(self, client: TelegramClient, first_name: str = None, 
                           last_name: str = None, about: str = None) -> bool:
        """Update account profile."""
        try:
            from telethon.tl.functions.account import UpdateProfileRequest
            
            await client(UpdateProfileRequest(
                first_name=first_name or "",
                last_name=last_name or "",
                about=about or ""
            ))
            
            logger.info("Profile updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error updating profile: {e}")
            return False
    
    async def set_username(self, client: TelegramClient, username: str) -> bool:
        """Set account username."""
        try:
            from telethon.tl.functions.account import UpdateUsernameRequest
            
            await client(UpdateUsernameRequest(username=username))
            logger.info(f"Username set to: {username}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting username: {e}")
            return False
    
    async def upload_profile_photo(self, client: TelegramClient, photo_path: str) -> bool:
        """Upload profile photo."""
        try:
            from telethon.tl.functions.photos import UploadProfilePhotoRequest
            
            result = await client(UploadProfilePhotoRequest(
                await client.upload_file(photo_path)
            ))
            
            logger.info("Profile photo uploaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading profile photo: {e}")
            return False
    
    async def disconnect_client(self, phone_number: str) -> None:
        """Disconnect and remove client from active clients."""
        try:
            if phone_number in self.active_clients:
                client = self.active_clients[phone_number]
                await client.disconnect()
                del self.active_clients[phone_number]
                logger.info(f"Disconnected client for {phone_number}")
        except Exception as e:
            logger.error(f"Error disconnecting client for {phone_number}: {e}")
    
    async def disconnect_all_clients(self) -> None:
        """Disconnect all active clients."""
        for phone_number in list(self.active_clients.keys()):
            await self.disconnect_client(phone_number)
    
    def get_client(self, phone_number: str) -> Optional[TelegramClient]:
        """Get active client for phone number."""
        return self.active_clients.get(phone_number)

# Global Telethon manager instance
telethon_manager = TelethonManager()