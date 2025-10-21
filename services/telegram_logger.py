"""
Telegram Channel Logger
Sends withdrawal requests and system logs to dedicated Telegram channel/topic
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


class TelegramChannelLogger:
    """Logs events to Telegram channel topics"""
    
    # Channel ID: https://t.me/c/3159890098/2
    # Convert to proper format: -100 + channel_id
    WITHDRAWAL_CHANNEL_ID = -1003159890098
    WITHDRAWAL_TOPIC_ID = 2  # Thread/topic ID from URL
    
    def __init__(self, bot_token: str):
        """
        Initialize Telegram logger
        
        Args:
            bot_token: Telegram bot token
        """
        self.bot = Bot(token=bot_token)
        self.bot_token = bot_token
        logger.info("TelegramChannelLogger initialized")
    
    async def log_withdrawal_request(
        self,
        user_id: int,
        username: Optional[str],
        amount: float,
        payment_method: str,
        payment_details: str,
        status: str = "pending",
        request_id: Optional[int] = None,
        additional_info: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Log withdrawal request to Telegram channel
        
        Args:
            user_id: Telegram user ID
            username: Username (optional)
            amount: Withdrawal amount
            payment_method: Payment method (e.g., 'UPI', 'Bank Transfer', 'Crypto')
            payment_details: Payment details (account number, UPI ID, etc.)
            status: Request status ('pending', 'approved', 'rejected', 'completed')
            request_id: Internal request ID
            additional_info: Additional metadata
        
        Returns:
            True if logged successfully
        """
        try:
            # Format message
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Escape special characters for Markdown
            username_display = username if username else "N/A"
            
            message = f"""
🔔 WITHDRAWAL REQUEST
━━━━━━━━━━━━━━━━━━━━━━

User Information:
• User ID: {user_id}
• Username: {username_display}
• Request ID: {request_id if request_id else 'N/A'}

Withdrawal Details:
• Amount: ₹{amount:,.2f}
• Method: {payment_method}
• Details: {payment_details}

Status:
{self._get_status_emoji(status)} {status.upper()}

Timestamp: {timestamp}
"""
            
            # Add additional info if provided
            if additional_info:
                message += "\n*Additional Information*\n"
                for key, value in additional_info.items():
                    message += f"{key}: {value}\n"
                message += "━━━━━━━━━━━━━━━━━━━━━━"
            
            # Send to channel topic (no parse mode to avoid formatting issues)
            await self.bot.send_message(
                chat_id=self.WITHDRAWAL_CHANNEL_ID,
                text=message,
                message_thread_id=self.WITHDRAWAL_TOPIC_ID
            )
            
            logger.info(f"✅ Withdrawal request logged to channel: User {user_id}, Amount ₹{amount}")
            return True
            
        except TelegramError as e:
            logger.error(f"❌ Telegram error logging withdrawal: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error logging withdrawal request: {e}", exc_info=True)
            return False
    
    async def log_withdrawal_update(
        self,
        request_id: int,
        old_status: str,
        new_status: str,
        updated_by: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Log withdrawal status update
        
        Args:
            request_id: Request ID
            old_status: Previous status
            new_status: New status
            updated_by: Admin who updated (optional)
            notes: Update notes (optional)
        
        Returns:
            True if logged successfully
        """
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            message = f"""
📝 *WITHDRAWAL STATUS UPDATE*
━━━━━━━━━━━━━━━━━━━━━━

Request ID: #{request_id}

Status Change:
{self._get_status_emoji(old_status)} {old_status.upper()} → {self._get_status_emoji(new_status)} *{new_status.upper()}*
"""
            
            if updated_by:
                message += f"\nUpdated by: {updated_by}"
            
            if notes:
                message += f"\n\nNotes:\n{notes}"
            
            message += f"\n\n🕐 {timestamp}"
            
            await self.bot.send_message(
                chat_id=self.WITHDRAWAL_CHANNEL_ID,
                text=message,
                parse_mode='Markdown',
                message_thread_id=self.WITHDRAWAL_TOPIC_ID
            )
            
            logger.info(f"✅ Withdrawal update logged: #{request_id} {old_status} → {new_status}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error logging withdrawal update: {e}")
            return False
    
    async def log_account_sale(
        self,
        phone: str,
        country_code: str,
        buyer_id: int,
        buyer_username: Optional[str],
        price: float,
        session_info: Dict[str, Any]
    ) -> bool:
        """
        Log account sale transaction
        
        Args:
            phone: Sold phone number
            country_code: Country code
            buyer_id: Buyer's user ID
            buyer_username: Buyer's username
            price: Sale price
            session_info: Session file information
        
        Returns:
            True if logged successfully
        """
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            buyer_username_display = f"@{buyer_username}" if buyer_username else "N/A"
            
            message = f"""
💼 *ACCOUNT SOLD*
━━━━━━━━━━━━━━━━━━━━━━

📱 *Account Details*
Phone: {phone}
Country: 🇮🇳 {country_code}
Session: {session_info.get('session_file', 'N/A')}

👤 *Buyer Information*
User ID: `{buyer_id}`
Username: {buyer_username_display}

💰 *Transaction*
Price: *₹{price:,.2f}*
Status: ✅ *COMPLETED*

📁 *Files*
Session: {session_info.get('session_file', 'N/A')}
Metadata: {session_info.get('metadata_file', 'N/A')}
Cookies: {'Available' if session_info.get('cookies_file') else 'N/A'}

🕐 *Timestamp*
{timestamp}
━━━━━━━━━━━━━━━━━━━━━━
"""
            
            await self.bot.send_message(
                chat_id=self.WITHDRAWAL_CHANNEL_ID,
                text=message,
                parse_mode='Markdown',
                message_thread_id=self.WITHDRAWAL_TOPIC_ID
            )
            
            logger.info(f"✅ Account sale logged: {phone} → User {buyer_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error logging account sale: {e}")
            return False
    
    async def log_system_event(
        self,
        event_type: str,
        description: str,
        severity: str = "info",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Log general system events
        
        Args:
            event_type: Event type (e.g., 'error', 'warning', 'info')
            description: Event description
            severity: Severity level ('info', 'warning', 'error', 'critical')
            metadata: Additional metadata
        
        Returns:
            True if logged successfully
        """
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            severity_emojis = {
                'info': 'ℹ️',
                'warning': '⚠️',
                'error': '❌',
                'critical': '🚨'
            }
            
            emoji = severity_emojis.get(severity.lower(), 'ℹ️')
            
            message = f"""
{emoji} *SYSTEM EVENT*
━━━━━━━━━━━━━━━━━━━━━━

Type: *{event_type.upper()}*
Severity: *{severity.upper()}*

Description:
{description}
"""
            
            if metadata:
                message += "\n\nMetadata:\n"
                for key, value in metadata.items():
                    message += f"{key}: {value}\n"
            
            message += f"\n🕐 {timestamp}"
            
            await self.bot.send_message(
                chat_id=self.WITHDRAWAL_CHANNEL_ID,
                text=message,
                parse_mode='Markdown',
                message_thread_id=self.WITHDRAWAL_TOPIC_ID
            )
            
            logger.info(f"✅ System event logged: {event_type}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error logging system event: {e}")
            return False
    
    def _get_status_emoji(self, status: str) -> str:
        """
        Get emoji for status
        
        Args:
            status: Status string
        
        Returns:
            Emoji character
        """
        status_emojis = {
            'pending': '⏳',
            'approved': '✅',
            'rejected': '❌',
            'completed': '✔️',
            'processing': '🔄',
            'cancelled': '🚫',
            'failed': '❌',
        }
        return status_emojis.get(status.lower(), '•')
    
    async def test_connection(self) -> bool:
        """
        Test connection to Telegram channel
        
        Returns:
            True if connection successful
        """
        try:
            # Try to send a test message
            test_message = f"""
✅ *CONNECTION TEST*
━━━━━━━━━━━━━━━━━━━━━━

TelegramChannelLogger is operational!

🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            await self.bot.send_message(
                chat_id=self.WITHDRAWAL_CHANNEL_ID,
                text=test_message,
                parse_mode='Markdown',
                message_thread_id=self.WITHDRAWAL_TOPIC_ID
            )
            
            logger.info("✅ Telegram channel connection test successful")
            return True
            
        except TelegramError as e:
            logger.error(f"❌ Telegram connection test failed: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Connection test error: {e}", exc_info=True)
            return False


# Convenience function
async def send_withdrawal_log(
    bot_token: str,
    user_id: int,
    username: Optional[str],
    amount: float,
    payment_method: str,
    payment_details: str,
    **kwargs
) -> bool:
    """
    Quick function to send withdrawal log
    
    Args:
        bot_token: Bot token
        user_id: User ID
        username: Username
        amount: Amount
        payment_method: Payment method
        payment_details: Payment details
        **kwargs: Additional parameters
    
    Returns:
        True if successful
    """
    logger_instance = TelegramChannelLogger(bot_token)
    return await logger_instance.log_withdrawal_request(
        user_id=user_id,
        username=username,
        amount=amount,
        payment_method=payment_method,
        payment_details=payment_details,
        **kwargs
    )

