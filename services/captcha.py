"""
Advanced Captcha and Verification Service for the Telegram Account Selling Bot.
"""
import random
import string
import logging
import os
import io
from typing import Dict, Any, List
import json
from captcha.image import ImageCaptcha
from captcha.audio import AudioCaptcha
from PIL import Image, ImageDraw, ImageFont
from utils.runtime_settings import (
    DEFAULT_VERIFICATION_CHANNELS,
    get_verification_channels,
)

logger = logging.getLogger(__name__)

class CaptchaService:
    """Service for generating and managing CAPTCHA challenges with visual and text options."""
    
    def __init__(self):
        # Create captcha directory if not exists
        self.captcha_dir = "temp_captchas"
        os.makedirs(self.captcha_dir, exist_ok=True)
        
        # Initialize image captcha generator - OPTIMIZED for speed
        # Smaller dimensions = faster generation and faster for users to type
        self.image_captcha = ImageCaptcha(width=200, height=70, fonts=None)
        
        # Removed math_questions and text_questions - only using visual captchas now
    
    async def generate_captcha(self) -> Dict[str, Any]:
        """Generate only visual image CAPTCHA challenges."""
        try:
            # Only generate visual captchas - no text or math questions
            return await self.generate_visual_captcha()
            
        except Exception as e:
            logger.error(f"Error generating visual captcha: {e}")
            # Fallback to another visual captcha attempt
            try:
                return await self.generate_visual_captcha()
            except Exception as fallback_error:
                logger.error(f"Fallback captcha generation failed: {fallback_error}")
                # Final fallback - simple visual captcha
                captcha_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
                return {
                    "type": "visual",
                    "question": "Enter the text shown in the image:",
                    "answer": captcha_text.lower(),
                    "image_path": None,  # Will handle image generation in handler
                    "captcha_text": captcha_text
                }

    async def generate_visual_captcha(self) -> Dict[str, Any]:
        """Generate a visual image captcha - optimized for speed."""
        try:
            # Generate random text for captcha (4 chars = faster to type, still secure)
            captcha_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            
            # Generate captcha image (in memory - no disk I/O)
            image = self.image_captcha.generate(captcha_text)
            
            # Return image bytes directly - NO file saving!
            return {
                "type": "visual",
                "question": f"Enter the text shown in the image:",
                "answer": captcha_text.lower(),
                "image_bytes": image.getvalue(),  # Direct bytes, no file
                "image_path": None,  # No file path needed
                "captcha_text": captcha_text
            }
            
        except Exception as e:
            logger.error(f"Error generating visual captcha: {e}")
            # Fallback to simple visual captcha without image file
            captcha_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            return {
                "type": "visual",
                "question": "Enter the text shown in the image:",
                "answer": captcha_text.lower(),
                "image_bytes": None,
                "image_path": None,
                "captcha_text": captcha_text
            }

    def cleanup_captcha_image(self, image_path: str) -> None:
        """Clean up temporary captcha image file."""
        try:
            if image_path and os.path.exists(image_path):
                os.remove(image_path)
                logger.info(f"Cleaned up captcha image: {image_path}")
        except Exception as e:
            logger.error(f"Error cleaning up captcha image {image_path}: {e}")
            
        except Exception as e:
            logger.error(f"Error generating CAPTCHA: {e}")
            # Fallback simple CAPTCHA
            return {
                "type": "fallback",
                "question": "Type 'YES' to continue:",
                "answer": "yes"
            }
    
    def verify_captcha(self, user_answer: str, correct_answer: str) -> bool:
        """Verify if the user's CAPTCHA answer is correct."""
        try:
            return user_answer.lower().strip() == correct_answer.lower().strip()
        except Exception as e:
            logger.error(f"Error verifying CAPTCHA: {e}")
            return False

class VerificationTaskService:
    """Service for managing verification tasks like channel joins."""
    
    def __init__(self):
        channels = get_verification_channels()
        self.required_channels = channels if channels else DEFAULT_VERIFICATION_CHANNELS
        
        self.custom_tasks = [
            {
                "name": "Profile Setup",
                "description": "Set a profile picture on your Telegram account",
                "type": "profile_check",
                "instructions": "Make sure your Telegram account has a profile picture set."
            },
            {
                "name": "Username Required",
                "description": "Set a username for your Telegram account", 
                "type": "username_check",
                "instructions": "Your account must have a username (e.g., @yourusername)."
            }
        ]
    
    def get_required_channels(self) -> List[Dict[str, str]]:
        """Get list of channels users must join."""
        return self.required_channels
    
    def get_custom_tasks(self) -> List[Dict[str, Any]]:
        """Get list of custom verification tasks."""
        return self.custom_tasks
    
    async def check_channel_membership(self, bot, user_id: int, channel_username: str) -> bool:
        """Check if user is a member of the required channel."""
        try:
            # Try to get chat member status
            member = await bot.get_chat_member(chat_id=f"@{channel_username}", user_id=user_id)
            return member.status in ['member', 'administrator', 'creator']
        except Exception as e:
            logger.error(f"Error checking channel membership for {channel_username}: {e}")
            # If we can't check, assume they're not a member
            return False
    
    async def verify_profile_picture(self, bot, user_id: int) -> bool:
        """Check if user has a profile picture."""
        try:
            photos = await bot.get_user_profile_photos(user_id=user_id, limit=1)
            return len(photos.photos) > 0
        except Exception as e:
            logger.error(f"Error checking profile picture: {e}")
            return False
    
    async def verify_username(self, bot, user_id: int) -> bool:
        """Check if user has a username set."""
        try:
            user = await bot.get_chat(chat_id=user_id)
            return user.username is not None and len(user.username) > 0
        except Exception as e:
            logger.error(f"Error checking username: {e}")
            return False

class AntiSpamService:
    """Service for detecting and preventing spam/bot behavior."""
    
    def __init__(self):
        self.suspicious_patterns = [
            # Common bot/spam account patterns
            r'^[a-z]+\d{4,}$',  # letters followed by many numbers
            r'^\d{8,}$',        # only numbers, 8+ digits
            r'^user\d+$',       # "user" followed by numbers
            r'^telegram\d+$',   # "telegram" followed by numbers
        ]
        
        self.blocked_domains = [
            'temp-mail.org',
            '10minutemail.com',
            'guerrillamail.com'
        ]
    
    async def analyze_user_account(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze user account for suspicious activity."""
        risk_score = 0
        risk_factors = []
        
        # Check username patterns
        if user_data.get('username'):
            import re
            username = user_data['username'].lower()
            for pattern in self.suspicious_patterns:
                if re.match(pattern, username):
                    risk_score += 30
                    risk_factors.append(f"Suspicious username pattern: {username}")
        
        # Check account age (if available)
        if user_data.get('account_created'):
            # If account is very new (less than 7 days), increase risk
            from datetime import datetime, timedelta
            created = datetime.fromisoformat(user_data['account_created'])
            if datetime.now() - created < timedelta(days=7):
                risk_score += 20
                risk_factors.append("Very new account (< 7 days)")
        
        # Check for profile picture
        if not user_data.get('has_profile_picture'):
            risk_score += 15
            risk_factors.append("No profile picture")
        
        # Check for bio/description
        if not user_data.get('bio'):
            risk_score += 10
            risk_factors.append("No bio/description")
        
        return {
            'risk_score': risk_score,
            'risk_level': self._get_risk_level(risk_score),
            'risk_factors': risk_factors,
            'should_require_additional_verification': risk_score > 50
        }
    
    def _get_risk_level(self, score: int) -> str:
        """Get risk level based on score."""
        if score <= 20:
            return "LOW"
        elif score <= 50:
            return "MEDIUM"
        elif score <= 80:
            return "HIGH"
        else:
            return "VERY_HIGH"

class ChannelJoinVerifier:
    """Service for verifying channel joins and managing verification flow."""
    
    def __init__(self):
        self.verification_timeout = 300  # 5 minutes
    
    async def create_join_verification_message(self, channels: List[Dict]) -> Dict[str, Any]:
        """Create message with channel join buttons."""
        text = """
🔒 **Step 2/3: Channel Verification**

Please join ALL the required channels below, then click 'Verify Membership':

**Required Channels:**
        """
        
        buttons = []
        for i, channel in enumerate(channels, 1):
            text += f"\\n{i}. **{channel['name']}** - {channel['description']}"
            buttons.append([{
                "text": f"📢 Join {channel['name']}", 
                "url": channel['link']
            }])
        
        text += """

⚠️ **Important:** You MUST join all channels above for verification to succeed.

After joining all channels, click the button below:
        """
        
        buttons.append([{"text": "✅ Verify Membership", "callback_data": "verify_channels"}])
        buttons.append([{"text": "← Back to CAPTCHA", "callback_data": "start_verification"}])
        
        return {
            "text": text,
            "buttons": buttons
        }
    
    async def verify_all_channels(self, bot, user_id: int, required_channels: List[Dict]) -> Dict[str, Any]:
        """Verify user membership in all required channels."""
        verification_results = []
        all_joined = True
        
        task_service = VerificationTaskService()
        
        for channel in required_channels:
            is_member = await task_service.check_channel_membership(
                bot, user_id, channel['username']
            )
            
            verification_results.append({
                'channel': channel['name'],
                'username': channel['username'],
                'joined': is_member
            })
            
            if not is_member:
                all_joined = False
        
        return {
            'all_joined': all_joined,
            'results': verification_results,
            'missing_channels': [r for r in verification_results if not r['joined']]
        }
