"""
Account Configuration Service
Handles automatic account modifications after sale:
- Change account name
- Change username  
- Set new profile photo
- Setup new 2FA
"""
import logging
import random
import os
import asyncio
from typing import Dict, Any, Optional, List
from telethon import TelegramClient
from telethon.tl.functions.account import UpdateProfileRequest, UpdateUsernameRequest
from telethon.tl.functions.photos import UploadProfilePhotoRequest, DeletePhotosRequest
from telethon.tl.functions.account import UpdatePasswordSettingsRequest
from telethon.tl.types import InputFile
from telethon.errors import FloodWaitError, UsernameOccupiedError
from database.operations import ActivityLogService
from database import get_db_session, close_db_session

logger = logging.getLogger(__name__)

class AccountConfigurationService:
    """Service for automatically configuring sold accounts"""
    
    def __init__(self):
        self.random_names = [
            "Alex Johnson", "Sam Wilson", "Jordan Davis", "Taylor Brown", "Casey Miller",
            "Morgan Taylor", "Riley Anderson", "Cameron White", "Avery Martin", "Quinn Thompson",
            "Blake Garcia", "Sage Rodriguez", "River Martinez", "Phoenix Clark", "Sky Walker",
            "Nova Phillips", "Luna Carter", "Echo Evans", "Zara Turner", "Kai Parker",
            "Drew Campbell", "Lane Foster", "Ryan Hayes", "Sage Cooper", "Blaze Reed"
        ]
        
        self.random_bios = [
            "Living my best life 🌟", "Adventure seeker 🗺️", "Coffee lover ☕", 
            "Just exploring 🌍", "Making memories 📸", "Stay positive ✨",
            "Dream big 💫", "Life is beautiful 🌸", "Always learning 📚",
            "Grateful daily 🙏", "Chasing sunsets 🌅", "Music lover 🎵",
            "Foodie adventures 🍕", "Travel enthusiast ✈️", "Art and creativity 🎨"
        ]
        
        # Profile photos directory
        self.photos_dir = "assets/profile_photos"
        self._ensure_photos_directory()
    
    def _ensure_photos_directory(self):
        """Ensure profile photos directory exists"""
        if not os.path.exists(self.photos_dir):
            os.makedirs(self.photos_dir)
            logger.info(f"Created profile photos directory: {self.photos_dir}")
    
    async def configure_account_after_sale(self, client: TelegramClient, user_id: int, 
                                         session_key: str) -> Dict[str, Any]:
        """
        Complete account configuration after successful sale
        Returns configuration results
        """
        results = {
            'success': True,
            'changes_made': [],
            'errors': [],
            'new_settings': {}
        }
        
        db = get_db_session()
        try:
            # Step 1: Change account name
            name_result = await self._change_account_name(client, user_id)
            if name_result['success']:
                results['changes_made'].append('name_changed')
                results['new_settings']['name'] = name_result['new_name']
                ActivityLogService.log_action(
                    db, user_id, "ACCOUNT_NAME_CHANGED", 
                    f"Changed account name to: {name_result['new_name']}"
                )
            else:
                results['errors'].append(f"Name change failed: {name_result['error']}")
            
            # Step 2: Change username  
            username_result = await self._change_username(client, user_id)
            if username_result['success']:
                results['changes_made'].append('username_changed')
                results['new_settings']['username'] = username_result['new_username']
                ActivityLogService.log_action(
                    db, user_id, "USERNAME_CHANGED",
                    f"Changed username to: @{username_result['new_username']}"
                )
            else:
                results['errors'].append(f"Username change failed: {username_result['error']}")
            
            # Step 3: Set new profile photo
            photo_result = await self._set_new_profile_photo(client, user_id)
            if photo_result['success']:
                results['changes_made'].append('photo_changed')
                results['new_settings']['photo'] = photo_result['photo_info']
                ActivityLogService.log_action(
                    db, user_id, "PROFILE_PHOTO_CHANGED",
                    "Set new random profile photo"
                )
            else:
                results['errors'].append(f"Photo change failed: {photo_result['error']}")
            
            # Step 4: Update bio
            bio_result = await self._update_bio(client, user_id)
            if bio_result['success']:
                results['changes_made'].append('bio_changed')
                results['new_settings']['bio'] = bio_result['new_bio']
                ActivityLogService.log_action(
                    db, user_id, "BIO_UPDATED",
                    f"Updated bio to: {bio_result['new_bio']}"
                )
            
            # Log overall configuration completion
            ActivityLogService.log_action(
                db, user_id, "ACCOUNT_CONFIGURED",
                f"Account configuration completed. Changes: {', '.join(results['changes_made'])}"
            )
            
            # Determine overall success
            results['success'] = len(results['changes_made']) > 0
            
            return results
            
        except Exception as e:
            logger.error(f"Error in account configuration: {e}")
            results['success'] = False
            results['errors'].append(f"Configuration error: {str(e)}")
            return results
            
        finally:
            close_db_session(db)
    
    async def _change_account_name(self, client: TelegramClient, user_id: int) -> Dict[str, Any]:
        """Change account display name"""
        try:
            # Pick random name
            new_name = random.choice(self.random_names)
            first_name, last_name = new_name.split(" ", 1)
            
            # Update profile name
            await client(UpdateProfileRequest(
                first_name=first_name,
                last_name=last_name
            ))
            
            logger.info(f"Changed account name to: {new_name}")
            return {
                'success': True,
                'new_name': new_name,
                'first_name': first_name,
                'last_name': last_name
            }
            
        except FloodWaitError as e:
            logger.warning(f"Flood wait for name change: {e.seconds} seconds")
            await asyncio.sleep(e.seconds)
            return await self._change_account_name(client, user_id)
            
        except Exception as e:
            logger.error(f"Error changing account name: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _change_username(self, client: TelegramClient, user_id: int) -> Dict[str, Any]:
        """Change account username"""
        try:
            # Generate random username
            base_names = ["alex", "sam", "jordan", "taylor", "casey", "morgan", "riley", "cameron"]
            base_name = random.choice(base_names)
            random_num = random.randint(1000, 9999)
            new_username = f"{base_name}_{random_num}"
            
            # Try to set username
            try:
                await client(UpdateUsernameRequest(new_username))
                logger.info(f"Changed username to: @{new_username}")
                return {'success': True, 'new_username': new_username}
                
            except UsernameOccupiedError:
                # Try with additional random number if occupied
                new_username = f"{base_name}_{random_num}_{random.randint(10, 99)}"
                await client(UpdateUsernameRequest(new_username))
                logger.info(f"Changed username to: @{new_username} (second attempt)")
                return {'success': True, 'new_username': new_username}
                
        except FloodWaitError as e:
            logger.warning(f"Flood wait for username change: {e.seconds} seconds")
            await asyncio.sleep(e.seconds)
            return await self._change_username(client, user_id)
            
        except Exception as e:
            logger.error(f"Error changing username: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _set_new_profile_photo(self, client: TelegramClient, user_id: int) -> Dict[str, Any]:
        """Set new random profile photo"""
        try:
            # Get available photos
            photo_files = self._get_available_photos()
            
            if not photo_files:
                return {'success': False, 'error': 'No profile photos available'}
            
            # Pick random photo
            selected_photo = random.choice(photo_files)
            photo_path = os.path.join(self.photos_dir, selected_photo)
            
            # Delete current photos first
            try:
                me = await client.get_me()
                if me.photo:
                    await client(DeletePhotosRequest([me.photo]))
                    logger.info("Deleted existing profile photo")
            except Exception as e:
                logger.warning(f"Could not delete existing photo: {e}")
            
            # Upload new photo
            uploaded_file = await client.upload_file(photo_path)
            await client(UploadProfilePhotoRequest(uploaded_file))
            
            logger.info(f"Set new profile photo: {selected_photo}")
            return {
                'success': True,
                'photo_info': selected_photo,
                'photo_path': photo_path
            }
            
        except FloodWaitError as e:
            logger.warning(f"Flood wait for photo upload: {e.seconds} seconds")
            await asyncio.sleep(e.seconds)
            return await self._set_new_profile_photo(client, user_id)
            
        except Exception as e:
            logger.error(f"Error setting profile photo: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _update_bio(self, client: TelegramClient, user_id: int) -> Dict[str, Any]:
        """Update account bio"""
        try:
            new_bio = random.choice(self.random_bios)
            
            # Update bio via profile update
            await client(UpdateProfileRequest(about=new_bio))
            
            logger.info(f"Updated bio to: {new_bio}")
            return {'success': True, 'new_bio': new_bio}
            
        except FloodWaitError as e:
            logger.warning(f"Flood wait for bio update: {e.seconds} seconds")
            await asyncio.sleep(e.seconds)
            return await self._update_bio(client, user_id)
            
        except Exception as e:
            logger.error(f"Error updating bio: {e}")
            return {'success': False, 'error': str(e)}
    
    def _get_available_photos(self) -> List[str]:
        """Get list of available profile photos"""
        try:
            if not os.path.exists(self.photos_dir):
                return []
            
            # Look for common image formats
            photo_extensions = ['.jpg', '.jpeg', '.png', '.webp']
            photos = []
            
            for file in os.listdir(self.photos_dir):
                if any(file.lower().endswith(ext) for ext in photo_extensions):
                    photos.append(file)
            
            return photos
            
        except Exception as e:
            logger.error(f"Error getting available photos: {e}")
            return []
    
    async def setup_new_2fa(self, client: TelegramClient, user_id: int, 
                           old_password: str = None) -> Dict[str, Any]:
        """
        Setup new 2FA password after user removes their existing one
        This should be called after user confirms they've disabled their 2FA
        """
        try:
            # Generate strong random password
            import secrets
            import string
            
            # Create a strong password
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
            new_password = ''.join(secrets.choice(alphabet) for _ in range(12))
            
            # Setup new 2FA
            await client(UpdatePasswordSettingsRequest(
                current_password_hash=b'',  # No current password
                new_settings={
                    'new_algo': {
                        '_': 'passwordKdfAlgoSHA256SHA256PBKDF2HMACSHA512iter100000SHA256ModPow',
                        'salt1': os.urandom(32),
                        'salt2': os.urandom(32),
                        'g': 3,
                        'p': bytes.fromhex('C71CAEB9C6B1C9048E6C522F70F13F73980D40238E3E21C14934D037563D930F48198A0AA7C14058229493D22530F4DBFA336F6E0AC925139543AED44CCE7C3720FD51F69458705AC68CD4FE6B6B13ABDC9746512969328454F18FAF8C595F642477FE96BB2A941D5BCD1D4AC8CC49880708FA9B378E3C4F3A9060BEE67CF9A4A4A695811051907E162753B56B0F6B410DBA74D8A84B2A14B3144E0EF1284754FD17ED1D0B85E1186F0CF6A8B3727C9E4DC8468C2D4017EB03EC9EEC3F84A2FD546C888C4345B0F8BDA28624D551E758D12E8')
                    },
                    'new_password_hash': new_password.encode(),
                    'hint': "Auto-generated secure password"
                }
            ))
            
            logger.info("Successfully set up new 2FA")
            
            db = get_db_session()
            try:
                ActivityLogService.log_action(
                    db, user_id, "2FA_SETUP",
                    "New 2FA password configured automatically"
                )
            finally:
                close_db_session(db)
            
            return {
                'success': True,
                'new_password': new_password,
                'hint': "Auto-generated secure password"
            }
            
        except Exception as e:
            logger.error(f"Error setting up 2FA: {e}")
            return {'success': False, 'error': str(e)}

# Global instance
account_config_service = AccountConfigurationService()