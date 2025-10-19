"""
Notification Service
Handles sending notifications to users for various events
"""
import logging
from datetime import datetime
from typing import Optional
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications to users"""
    
    def __init__(self, bot: Bot):
        """
        Initialize notification service
        
        Args:
            bot: Telegram Bot instance
        """
        self.bot = bot
    
    async def notify_sale_approved(
        self,
        user_telegram_id: int,
        phone_number: str,
        sale_price: float,
        admin_notes: Optional[str] = None
    ) -> bool:
        """
        Notify user when their sale is approved
        
        Args:
            user_telegram_id: Telegram user ID to notify
            phone_number: Phone number of sold account
            sale_price: Sale price
            admin_notes: Optional admin notes
            
        Returns:
            bool: True if notification sent successfully
        """
        message = f"""
✅ **Sale Approved!**

📱 **Account:** `{phone_number}`
💰 **Amount:** ${sale_price:.2f}

🎉 **Congratulations!** Your account sale has been approved by an administrator.

**What happens next:**
• Payment will be processed shortly
• Funds will be added to your balance
• You can withdraw once payment clears

**Transaction Details:**
• Status: ✅ Approved
• Processing Time: 1-24 hours
"""
        
        if admin_notes:
            message += f"\n📝 **Admin Note:** {admin_notes}\n"
        
        message += "\n💡 **Tip:** Keep selling accounts to maximize your earnings!"
        
        return await self._send_notification(user_telegram_id, message)
    
    async def notify_sale_rejected(
        self,
        user_telegram_id: int,
        phone_number: str,
        rejection_reason: str,
        admin_notes: Optional[str] = None
    ) -> bool:
        """
        Notify user when their sale is rejected
        
        Args:
            user_telegram_id: Telegram user ID to notify
            phone_number: Phone number of account
            rejection_reason: Reason for rejection
            admin_notes: Optional admin notes
            
        Returns:
            bool: True if notification sent successfully
        """
        message = f"""
❌ **Sale Rejected**

📱 **Account:** `{phone_number}`
🚫 **Reason:** {rejection_reason}

Your account sale has been reviewed and rejected by an administrator.

**Common rejection reasons:**
• Account doesn't meet quality standards
• Incomplete or incorrect information
• Policy violations
• Security concerns
"""
        
        if admin_notes:
            message += f"\n📝 **Admin Note:** {admin_notes}\n"
        
        message += """
**What you can do:**
• Review the rejection reason
• Ensure account meets all requirements
• Try selling a different account
• Contact support if you have questions
"""
        
        return await self._send_notification(user_telegram_id, message)
    
    async def notify_account_frozen(
        self,
        user_telegram_id: int,
        phone_number: str,
        freeze_reason: str,
        freeze_duration_hours: Optional[int] = None,
        freeze_until: Optional[datetime] = None
    ) -> bool:
        """
        Notify user when their account is frozen
        
        Args:
            user_telegram_id: Telegram user ID to notify
            phone_number: Phone number of frozen account
            freeze_reason: Reason for freeze
            freeze_duration_hours: Optional duration in hours
            freeze_until: Optional freeze end datetime
            
        Returns:
            bool: True if notification sent successfully
        """
        message = f"""
❄️ **Account Frozen**

📱 **Account:** `{phone_number}`
🔒 **Status:** Temporarily Frozen
📋 **Reason:** {freeze_reason}

Your account has been placed under a temporary security hold.

**Duration:**
"""
        
        if freeze_until:
            message += f"⏰ Frozen until: {freeze_until.strftime('%Y-%m-%d %H:%M UTC')}\n"
        elif freeze_duration_hours:
            message += f"⏰ Duration: {freeze_duration_hours} hours\n"
        else:
            message += "⏰ Duration: Until manual review\n"
        
        message += """
**What this means:**
• ❌ You cannot sell this account during freeze period
• 🔒 Account is secured for your protection
• ⏳ Freeze will be automatically lifted when time expires
• 💼 You can still sell other accounts

**Common freeze reasons:**
• Multi-device usage detected (security measure)
• Suspicious activity flagged
• Manual admin review required
• Security policy violation

**Need help?**
Contact support if you believe this freeze was made in error.
"""
        
        return await self._send_notification(user_telegram_id, message)
    
    async def notify_account_unfrozen(
        self,
        user_telegram_id: int,
        phone_number: str,
        unfreeze_reason: Optional[str] = None
    ) -> bool:
        """
        Notify user when their account is unfrozen
        
        Args:
            user_telegram_id: Telegram user ID to notify
            phone_number: Phone number of unfrozen account
            unfreeze_reason: Optional reason for unfreeze
            
        Returns:
            bool: True if notification sent successfully
        """
        message = f"""
🔥 **Account Unfrozen!**

📱 **Account:** `{phone_number}`
✅ **Status:** Available for Sale

Good news! Your account freeze has been lifted.

**You can now:**
• ✅ Sell this account again
• 💰 List it on the marketplace
• 🚀 Start earning immediately
"""
        
        if unfreeze_reason:
            message += f"\n📝 **Unfreeze Note:** {unfreeze_reason}\n"
        
        message += "\n🎉 **Happy selling!**"
        
        return await self._send_notification(user_telegram_id, message)
    
    async def notify_multi_device_detected(
        self,
        user_telegram_id: int,
        phone_number: str,
        device_count: int,
        auto_freeze: bool = True
    ) -> bool:
        """
        Notify user when multi-device usage is detected
        
        Args:
            user_telegram_id: Telegram user ID to notify
            phone_number: Phone number of account
            device_count: Number of devices detected
            auto_freeze: Whether account was auto-frozen
            
        Returns:
            bool: True if notification sent successfully
        """
        message = f"""
⚠️ **Security Alert: Multi-Device Usage Detected**

📱 **Account:** `{phone_number}`
🖥️ **Devices Detected:** {device_count}

We detected your Telegram account is active on multiple devices simultaneously.

**Security Action:**
"""
        
        if auto_freeze:
            message += """
• ❄️ Account has been **automatically frozen** for 24-48 hours
• 🔒 This is a standard security measure
• ✅ Freeze will lift automatically after review period

**Why we do this:**
• Protects your account from unauthorized access
• Prevents potential account compromise
• Ensures secure account transfers
• Maintains platform integrity
"""
        else:
            message += """
• ⚠️ Account flagged for review
• 🔍 Admin will review the activity
• 📊 No immediate action required

**Recommendation:**
• Log out from devices you don't recognize
• Ensure only you have access to your account
• Enable 2FA for additional security
"""
        
        message += """
**Need immediate access?**
Contact support if you need this freeze lifted urgently.
"""
        
        return await self._send_notification(user_telegram_id, message)
    
    async def _send_notification(self, user_telegram_id: int, message: str) -> bool:
        """
        Internal method to send notification
        
        Args:
            user_telegram_id: Telegram user ID
            message: Message to send
            
        Returns:
            bool: True if sent successfully
        """
        try:
            await self.bot.send_message(
                chat_id=user_telegram_id,
                text=message,
                parse_mode='Markdown'
            )
            logger.info(f"Notification sent to user {user_telegram_id}")
            return True
        except TelegramError as e:
            logger.error(f"Failed to send notification to user {user_telegram_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending notification to user {user_telegram_id}: {e}")
            return False


# Global notification service instance (will be initialized with bot instance)
_notification_service: Optional[NotificationService] = None


def initialize_notification_service(bot: Bot) -> NotificationService:
    """
    Initialize the global notification service
    
    Args:
        bot: Telegram Bot instance
        
    Returns:
        NotificationService instance
    """
    global _notification_service
    _notification_service = NotificationService(bot)
    return _notification_service


def get_notification_service() -> Optional[NotificationService]:
    """
    Get the global notification service instance
    
    Returns:
        NotificationService instance or None if not initialized
    """
    return _notification_service
