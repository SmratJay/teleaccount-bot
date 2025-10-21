"""
Account Manipulation Service
Provides comprehensive control over sold Telegram accounts including:
- Chat history deletion
- Name and username changes
- Profile photo management
- 2FA setup and manipulation
"""

import logging
import os
import asyncio
from typing import Optional, Dict, List, Any
from pathlib import Path
from telethon import TelegramClient
from telethon.tl.functions.account import UpdateProfileRequest, UpdateUsernameRequest
from telethon.tl.functions.photos import UploadProfilePhotoRequest, DeletePhotosRequest
from telethon.tl.functions.messages import DeleteHistoryRequest
from telethon.tl.types import InputPhoto, InputPhotoEmpty
from telethon.errors import UsernameOccupiedError, UsernameInvalidError, FloodWaitError

logger = logging.getLogger(__name__)


class AccountManipulationService:
    """Service for manipulating Telegram account settings and data."""
    
    def __init__(self):
        self.profile_photos_dir = Path("profile_photos")
        self.profile_photos_dir.mkdir(exist_ok=True)
        logger.info("✅ Account Manipulation Service initialized")
    
    async def delete_all_chat_history(
        self, 
        client: TelegramClient,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Delete all chat history for the account.
        
        Args:
            client: Authenticated Telethon client
            progress_callback: Optional callback for progress updates
        
        Returns:
            Dict with success status and details
        """
        try:
            logger.info("🗑️ Starting chat history deletion...")
            
            # Get all dialogs (chats)
            dialogs = await client.get_dialogs()
            total_dialogs = len(dialogs)
            deleted_count = 0
            failed_count = 0
            errors = []
            
            logger.info(f"Found {total_dialogs} dialogs to process")
            
            for i, dialog in enumerate(dialogs):
                try:
                    # Delete history for this dialog
                    await client(DeleteHistoryRequest(
                        peer=dialog.entity,
                        max_id=0,  # Delete all messages
                        just_clear=False,  # Actually delete, don't just clear
                        revoke=True  # Revoke for both sides if possible
                    ))
                    deleted_count += 1
                    
                    # Progress callback
                    if progress_callback:
                        await progress_callback(i + 1, total_dialogs)
                    
                    # Small delay to avoid flood limits
                    await asyncio.sleep(0.5)
                    
                except FloodWaitError as e:
                    wait_time = e.seconds
                    logger.warning(f"FloodWait: waiting {wait_time}s")
                    await asyncio.sleep(wait_time)
                    # Retry after waiting
                    try:
                        await client(DeleteHistoryRequest(
                            peer=dialog.entity,
                            max_id=0,
                            just_clear=False,
                            revoke=True
                        ))
                        deleted_count += 1
                    except Exception as retry_error:
                        failed_count += 1
                        errors.append(f"Dialog {dialog.name}: {str(retry_error)[:50]}")
                        
                except Exception as e:
                    failed_count += 1
                    error_msg = f"Dialog {dialog.name}: {str(e)[:50]}"
                    errors.append(error_msg)
                    logger.error(f"Failed to delete history: {error_msg}")
            
            logger.info(f"✅ Chat history deletion complete: {deleted_count} deleted, {failed_count} failed")
            
            return {
                'success': True,
                'total_dialogs': total_dialogs,
                'deleted_count': deleted_count,
                'failed_count': failed_count,
                'errors': errors
            }
            
        except Exception as e:
            logger.error(f"Error deleting chat history: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def change_account_name(
        self,
        client: TelegramClient,
        first_name: str,
        last_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Change account display name.
        
        Args:
            client: Authenticated Telethon client
            first_name: New first name
            last_name: New last name (optional)
        
        Returns:
            Dict with success status
        """
        try:
            # Update profile (omit about to keep bio unchanged)
            await client(UpdateProfileRequest(
                first_name=first_name,
                last_name=last_name or ""
            ))
            
            logger.info(f"✅ Account name changed to: {first_name} {last_name or ''}")
            
            return {
                'success': True,
                'first_name': first_name,
                'last_name': last_name
            }
            
        except Exception as e:
            logger.error(f"Error changing account name: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def change_username(
        self,
        client: TelegramClient,
        new_username: str
    ) -> Dict[str, Any]:
        """
        Change account username (@handle).
        
        Args:
            client: Authenticated Telethon client
            new_username: New username (without @)
        
        Returns:
            Dict with success status
        """
        try:
            # Remove @ if provided
            new_username = new_username.lstrip('@')
            
            # Validate username format
            if not new_username.replace('_', '').isalnum():
                return {
                    'success': False,
                    'error': 'Username can only contain letters, numbers, and underscores'
                }
            
            if len(new_username) < 5:
                return {
                    'success': False,
                    'error': 'Username must be at least 5 characters long'
                }
            
            # Update username
            await client(UpdateUsernameRequest(new_username))
            
            logger.info(f"✅ Username changed to: @{new_username}")
            
            return {
                'success': True,
                'username': new_username
            }
            
        except UsernameOccupiedError:
            return {
                'success': False,
                'error': 'Username is already taken'
            }
        except UsernameInvalidError:
            return {
                'success': False,
                'error': 'Username is invalid'
            }
        except Exception as e:
            logger.error(f"Error changing username: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def remove_username(self, client: TelegramClient) -> Dict[str, Any]:
        """Remove username from account."""
        try:
            await client(UpdateUsernameRequest(""))
            logger.info("✅ Username removed")
            return {'success': True}
        except Exception as e:
            logger.error(f"Error removing username: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_available_profile_photos(self) -> List[str]:
        """
        Get list of available profile photos from local directory.
        
        Returns:
            List of photo filenames
        """
        try:
            valid_extensions = {'.jpg', '.jpeg', '.png'}
            photos = []
            
            for file in self.profile_photos_dir.iterdir():
                if file.is_file() and file.suffix.lower() in valid_extensions:
                    photos.append(file.name)
            
            logger.info(f"Found {len(photos)} profile photos")
            return sorted(photos)
            
        except Exception as e:
            logger.error(f"Error getting profile photos: {e}")
            return []
    
    async def upload_profile_photo(
        self,
        client: TelegramClient,
        photo_filename: str
    ) -> Dict[str, Any]:
        """
        Upload a profile photo to the account.
        
        Args:
            client: Authenticated Telethon client
            photo_filename: Filename from profile_photos directory
        
        Returns:
            Dict with success status
        """
        try:
            photo_path = self.profile_photos_dir / photo_filename
            
            if not photo_path.exists():
                return {
                    'success': False,
                    'error': f'Photo file not found: {photo_filename}'
                }
            
            # Upload the photo
            result = await client.upload_file(str(photo_path))
            await client(UploadProfilePhotoRequest(file=result))
            
            logger.info(f"✅ Profile photo uploaded: {photo_filename}")
            
            return {
                'success': True,
                'photo_filename': photo_filename
            }
            
        except Exception as e:
            logger.error(f"Error uploading profile photo: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def delete_profile_photos(self, client: TelegramClient) -> Dict[str, Any]:
        """
        Delete all profile photos from the account.
        
        Args:
            client: Authenticated Telethon client
        
        Returns:
            Dict with success status
        """
        try:
            # Get current photos
            photos = await client.get_profile_photos('me')
            
            if not photos:
                return {
                    'success': True,
                    'message': 'No profile photos to delete'
                }
            
            # Delete all photos
            photo_ids = []
            for photo in photos:
                photo_ids.append(InputPhoto(
                    id=photo.id,
                    access_hash=photo.access_hash,
                    file_reference=photo.file_reference
                ))
            
            await client(DeletePhotosRequest(id=photo_ids))
            
            logger.info(f"✅ Deleted {len(photos)} profile photos")
            
            return {
                'success': True,
                'deleted_count': len(photos)
            }
            
        except Exception as e:
            logger.error(f"Error deleting profile photos: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def setup_2fa(
        self,
        client: TelegramClient,
        password: str,
        hint: Optional[str] = None,
        email: Optional[str] = None,
        current_password: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Setup or change 2FA password using proper SRP protocol.
        
        Args:
            client: Authenticated Telethon client
            password: New 2FA password
            hint: Password hint (optional)
            email: Recovery email (optional)
            current_password: Current password if changing (optional)
        
        Returns:
            Dict with success status
        """
        try:
            # Use Telethon's built-in password editing
            # This handles all the SRP crypto correctly
            await client.edit_2fa(
                new_password=password,
                hint=hint or "",
                email=email or "",
                current_password=current_password
            )
            
            logger.info("✅ 2FA password configured")
            
            return {
                'success': True,
                'hint': hint
            }
            
        except Exception as e:
            logger.error(f"Error setting up 2FA: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def disable_2fa(
        self,
        client: TelegramClient,
        current_password: str
    ) -> Dict[str, Any]:
        """
        Disable 2FA on the account.
        
        Args:
            client: Authenticated Telethon client
            current_password: Current 2FA password (required for authentication)
        
        Returns:
            Dict with success status
        """
        try:
            # Use Telethon's built-in method to remove 2FA
            # This properly authenticates with current password
            await client.edit_2fa(
                current_password=current_password,
                new_password=None  # Setting to None disables 2FA
            )
            
            logger.info("✅ 2FA disabled")
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Error disabling 2FA: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_account_info(self, client: TelegramClient) -> Dict[str, Any]:
        """
        Get current account information.
        
        Args:
            client: Authenticated Telethon client
        
        Returns:
            Dict with account details
        """
        try:
            me = await client.get_me()
            
            return {
                'success': True,
                'id': me.id,
                'first_name': me.first_name,
                'last_name': me.last_name,
                'username': me.username,
                'phone': me.phone,
                'is_verified': me.verified,
                'is_restricted': me.restricted,
                'is_bot': me.bot
            }
            
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Global instance
account_manipulation_service = AccountManipulationService()
