"""
Advanced Captcha and Verification Service for the Telegram Account Selling Bot.
"""
import random
import string
import logging
from typing import Dict, Any, List
import json
import os
import io
from captcha.image import ImageCaptcha
from PIL import Image

logger = logging.getLogger(__name__)

class CaptchaService:
    """Service for generating and managing CAPTCHA challenges."""
    
    def __init__(self):
        self.math_questions = [
            {"question": "What is 15 + 27?", "answer": "42"},
            {"question": "What is 8 × 7?", "answer": "56"},
            {"question": "What is 100 - 23?", "answer": "77"},
            {"question": "What is 144 ÷ 12?", "answer": "12"},
            {"question": "What is 25 + 18?", "answer": "43"},
            {"question": "What is 9 × 6?", "answer": "54"},
            {"question": "What is 85 - 31?", "answer": "54"},
            {"question": "What is 72 ÷ 8?", "answer": "9"}
        ]
        
        self.text_questions = [
            {"question": "Type the word 'TELEGRAM' in uppercase:", "answer": "TELEGRAM"},
            {"question": "What comes after 'A, B, C'?", "answer": "D"},
            {"question": "Type 'BOT' backwards:", "answer": "TOB"},
            {"question": "What is the first letter of 'VERIFICATION'?", "answer": "V"},
            {"question": "Type 'HUMAN' in lowercase:", "answer": "human"}
        ]
    
    async def generate_captcha(self) -> Dict[str, str]:
        """Generate a random CAPTCHA challenge."""
        try:
            captcha_type = random.choice(['math', 'text'])
            
            if captcha_type == 'math':
                challenge = random.choice(self.math_questions)
            else:
                challenge = random.choice(self.text_questions)
            
            return {
                "type": captcha_type,
                "question": challenge["question"],
                "answer": challenge["answer"].lower().strip()
            }
            
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


class ImageCaptchaService:
    """Service for generating image-based CAPTCHA challenges."""
    
    def __init__(self):
        self.image_captcha = ImageCaptcha(width=280, height=90, fonts=None)
        self.captcha_dir = "captcha_images"
        if not os.path.exists(self.captcha_dir):
            os.makedirs(self.captcha_dir)
    
    def generate_captcha_text(self, length: int = 6) -> str:
        """Generate random text for CAPTCHA (numbers and letters)."""
        characters = string.ascii_uppercase + string.digits
        excluded = ['0', 'O', '1', 'I', 'l']
        characters = ''.join(char for char in characters if char not in excluded)
        return ''.join(random.choice(characters) for _ in range(length))
    
    async def generate_image_captcha(self) -> Dict[str, Any]:
        """
        Generate an image-based CAPTCHA.
        Returns: dict with 'image_bytes', 'answer', and 'filepath'
        """
        try:
            captcha_text = self.generate_captcha_text()
            
            data = self.image_captcha.generate(captcha_text)
            
            image_bytes = io.BytesIO()
            image_bytes.write(data.getvalue())
            image_bytes.seek(0)
            
            filepath = os.path.join(self.captcha_dir, f"captcha_{random.randint(1000, 9999)}.png")
            with open(filepath, 'wb') as f:
                f.write(image_bytes.getvalue())
            
            image_bytes.seek(0)
            
            return {
                "type": "image",
                "image_bytes": image_bytes,
                "answer": captcha_text,
                "filepath": filepath,
                "question": "Please type the characters you see in the image above (case-insensitive):"
            }
            
        except Exception as e:
            logger.error(f"Error generating image CAPTCHA: {e}")
            return None
    
    def verify_image_captcha(self, user_answer: str, correct_answer: str) -> bool:
        """Verify if the user's answer matches the image CAPTCHA."""
        try:
            return user_answer.upper().strip() == correct_answer.upper().strip()
        except Exception as e:
            logger.error(f"Error verifying image CAPTCHA: {e}")
            return False
    
    def cleanup_captcha_image(self, filepath: str) -> None:
        """Delete the captcha image after verification."""
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Cleaned up CAPTCHA image: {filepath}")
        except Exception as e:
            logger.error(f"Error cleaning up CAPTCHA image: {e}")


class VerificationTaskService:
    """Service for managing verification tasks like channel joins."""
    
    def __init__(self):
        self.required_channels = [
            {
                "name": "📢 Bot Updates",
                "username": "telegram_account_bot_updates", 
                "description": "Get the latest bot updates and announcements",
                "link": "https://t.me/telegram_account_bot_updates"
            },
            {
                "name": "💰 Selling Community", 
                "username": "telegram_selling_community",
                "description": "Join our community of account sellers",
                "link": "https://t.me/telegram_selling_community"
            },
            {
                "name": "🆘 Support Channel",
                "username": "telegram_bot_support_channel", 
                "description": "Get help and support from our team",
                "link": "https://t.me/telegram_bot_support_channel"
            }
        ]
        
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