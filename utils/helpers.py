"""
Utility functions for the Telegram Account Bot.
"""
import os
import json
import hashlib
import secrets
import string
from typing import Dict, Optional, Tuple
from cryptography.fernet import Fernet
import phonenumbers
import logging

logger = logging.getLogger(__name__)

class SecurityUtils:
    """Security utility functions."""
    
    @staticmethod
    def generate_password(length: int = 16) -> str:
        """Generate a secure password."""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        return password
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def encrypt_text(text: str, key: str) -> str:
        """Encrypt text using Fernet encryption."""
        f = Fernet(key.encode())
        encrypted = f.encrypt(text.encode())
        return encrypted.decode()
    
    @staticmethod
    def decrypt_text(encrypted_text: str, key: str) -> str:
        """Decrypt text using Fernet encryption."""
        f = Fernet(key.encode())
        decrypted = f.decrypt(encrypted_text.encode())
        return decrypted.decode()
    
    @staticmethod
    def generate_encryption_key() -> str:
        """Generate a new Fernet encryption key."""
        return Fernet.generate_key().decode()

class PhoneUtils:
    """Phone number utility functions."""
    
    @staticmethod
    def validate_phone_number(phone: str) -> Tuple[bool, Optional[str]]:
        """Validate and format phone number."""
        try:
            # Parse the phone number
            parsed_number = phonenumbers.parse(phone, None)
            
            # Check if it's valid
            if phonenumbers.is_valid_number(parsed_number):
                # Format as E.164
                formatted = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
                return True, formatted
            else:
                return False, None
                
        except phonenumbers.NumberParseException:
            return False, None
    
    @staticmethod
    def get_country_code(phone: str) -> Optional[str]:
        """Get country code from phone number."""
        try:
            parsed_number = phonenumbers.parse(phone, None)
            if phonenumbers.is_valid_number(parsed_number):
                region_code = phonenumbers.region_code_for_number(parsed_number)
                return region_code
            return None
        except phonenumbers.NumberParseException:
            return None

class FileUtils:
    """File utility functions."""
    
    @staticmethod
    def ensure_directory_exists(directory: str) -> None:
        """Ensure a directory exists, create if it doesn't."""
        os.makedirs(directory, exist_ok=True)
    
    @staticmethod
    def save_json(data: dict, file_path: str) -> bool:
        """Save data as JSON file."""
        try:
            FileUtils.ensure_directory_exists(os.path.dirname(file_path))
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Failed to save JSON to {file_path}: {e}")
            return False
    
    @staticmethod
    def load_json(file_path: str) -> Optional[dict]:
        """Load data from JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load JSON from {file_path}: {e}")
            return None

class MessageUtils:
    """Message utility functions."""
    
    @staticmethod
    def format_user_info(user) -> str:
        """Format user information for display."""
        info = f"👤 User ID: `{user.telegram_user_id}`\n"
        if user.username:
            info += f"📝 Username: @{user.username}\n"
        if user.first_name:
            info += f"👋 Name: {user.first_name}"
            if user.last_name:
                info += f" {user.last_name}"
            info += "\n"
        info += f"💰 Balance: {user.balance:.2f}\n"
        info += f"📅 Joined: {user.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
        return info
    
    @staticmethod
    def format_account_info(account) -> str:
        """Format account information for display."""
        status_emoji = {
            'ACTIVE': '✅',
            'FROZEN': '❄️',
            'BANNED': '🚫',
            '24_HOUR_HOLD': '⏳'
        }
        
        info = f"{status_emoji.get(account.status, '❓')} Status: {account.status}\n"
        info += f"📱 Phone: {account.phone_number}\n"
        if account.country_code:
            info += f"🌍 Country: {account.country_code}\n"
        if account.username:
            info += f"📝 Username: @{account.username}\n"
        if account.first_name:
            info += f"👋 Name: {account.first_name}"
            if account.last_name:
                info += f" {account.last_name}"
            info += "\n"
        info += f"🔐 2FA: {'✅ Enabled' if account.two_fa_enabled else '❌ Disabled'}\n"
        info += f"📅 Created: {account.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
        
        if account.last_activity_at:
            info += f"\n🕒 Last Activity: {account.last_activity_at.strftime('%Y-%m-%d %H:%M:%S')}"
        
        return info
    
    @staticmethod
    def format_withdrawal_info(withdrawal) -> str:
        """Format withdrawal information for display."""
        status_emoji = {
            'PENDING': '⏳',
            'COMPLETED': '✅',
            'REJECTED': '❌',
            'FAILED': '💥'
        }
        
        info = f"{status_emoji.get(withdrawal.status, '❓')} Status: {withdrawal.status}\n"
        info += f"💰 Amount: {withdrawal.amount} {withdrawal.currency}\n"
        info += f"🎯 Destination: `{withdrawal.destination_address}`\n"
        info += f"📅 Requested: {withdrawal.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
        
        if withdrawal.processed_at:
            info += f"\n✅ Processed: {withdrawal.processed_at.strftime('%Y-%m-%d %H:%M:%S')}"
        
        if withdrawal.admin_notes:
            info += f"\n📝 Notes: {withdrawal.admin_notes}"
        
        return info

class CaptchaUtils:
    """Simple captcha utility functions."""
    
    @staticmethod
    def generate_math_captcha() -> Tuple[str, int]:
        """Generate a simple math captcha."""
        # Generate two random numbers between 1 and 20
        num1 = secrets.randbelow(20) + 1
        num2 = secrets.randbelow(20) + 1
        
        # Choose operation randomly
        operations = ['+', '-', '*']
        operation = secrets.choice(operations)
        
        if operation == '+':
            question = f"{num1} + {num2}"
            answer = num1 + num2
        elif operation == '-':
            # Ensure positive result
            if num1 < num2:
                num1, num2 = num2, num1
            question = f"{num1} - {num2}"
            answer = num1 - num2
        else:  # multiplication
            # Use smaller numbers for multiplication
            num1 = secrets.randbelow(10) + 1
            num2 = secrets.randbelow(10) + 1
            question = f"{num1} × {num2}"
            answer = num1 * num2
        
        return question, answer
    
    @staticmethod
    def generate_text_captcha() -> Tuple[str, str]:
        """Generate a simple text captcha."""
        # Simple word/number combinations
        captchas = [
            ("What is the color of grass?", "green"),
            ("How many days in a week?", "7"),
            ("What comes after 9?", "10"),
            ("Type 'YES' to confirm", "YES"),
            ("What is 2+2?", "4"),
            ("Type the word 'HELLO'", "HELLO"),
            ("How many fingers on one hand?", "5"),
            ("What is the first letter of the alphabet?", "A")
        ]
        
        question, answer = secrets.choice(captchas)
        return question, answer.lower()

def get_session_file_path(phone_number: str) -> str:
    """Get the session file path for a phone number."""
    sessions_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'sessions')
    FileUtils.ensure_directory_exists(sessions_dir)
    
    # Clean phone number for filename
    clean_phone = ''.join(filter(str.isdigit, phone_number))
    session_file = f"{clean_phone}.session"
    
    return os.path.join(sessions_dir, session_file)