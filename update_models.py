"""Update User and TelegramAccount models with missing attributes."""
import re

# Read the file
with open('d:/teleaccount_bot/database/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Update User class
old_user = """class User:
    \"\"\"Stub User model.\"\"\"
    def __init__(self, telegram_id, username=None):
        self.id = 1
        self.telegram_id = telegram_id
        self.username = username
        self.balance = 0.0
        self.language = 'en'"""

new_user = """class User:
    \"\"\"Stub User model.\"\"\"
    def __init__(self, telegram_id, username=None):
        self.id = 1
        self.telegram_id = telegram_id
        self.username = username
        self.balance = 0.0
        self.language = 'en'
        self.status = 'active'
        self.is_admin = False
        self.is_leader = False
        self.verified = False
        self.created_at = None
        self.last_activity = None
        self.captcha_verified = True
        self.referral_code = None
        self.referred_by = None"""

content = content.replace(old_user, new_user)

# Update TelegramAccount class
old_account = """class TelegramAccount:
    \"\"\"Stub TelegramAccount model.\"\"\"
    def __init__(self, phone_number, user_id=1):
        self.id = 1
        self.phone_number = phone_number
        self.user_id = user_id
        self.status = 'active'"""

new_account = """class TelegramAccount:
    \"\"\"Stub TelegramAccount model.\"\"\"
    def __init__(self, phone_number, user_id=1):
        self.id = 1
        self.phone_number = phone_number
        self.user_id = user_id
        self.status = 'active'
        self.session_string = None
        self.api_id = None
        self.api_hash = None
        self.created_at = None
        self.sold_at = None
        self.price = 10.0
        self.buyer_id = None
        self.freeze_until = None"""

content = content.replace(old_account, new_account)

# Write back
with open('d:/teleaccount_bot/database/models.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ Models updated with missing attributes')
