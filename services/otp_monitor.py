"""
OTP monitoring and security event detection system.
"""
import os
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from telegram.ext import ContextTypes
from telethon.events import NewMessage
from telethon.tl.types import UpdateLoginToken
from database import get_db_session, close_db_session
from database.operations import AccountService
from services.telethon_manager import telethon_manager

logger = logging.getLogger(__name__)

class OTPMonitor:
    """Monitor OTP requests and security events for managed accounts."""
    
    def __init__(self, bot_application):
        self.bot_application = bot_application
        self.admin_chat_id = os.getenv('ADMIN_CHAT_ID')
        self.admin_user_id = int(os.getenv('ADMIN_USER_ID', 0))
        self.monitoring_active = {}
        
    async def start_monitoring_account(self, phone_number: str, account_id: int) -> bool:
        """Start monitoring an account for OTP requests."""
        try:
            client = telethon_manager.get_client(phone_number)
            if not client:
                logger.warning(f"No active client found for monitoring: {phone_number}")
                return False
            
            # Add event handlers for security events
            client.add_event_handler(
                self._handle_login_attempt,
                NewMessage(pattern=r'.*login.*code.*|.*verification.*code.*', incoming=True)
            )
            
            # Store monitoring info
            self.monitoring_active[phone_number] = {
                'account_id': account_id,
                'started_at': datetime.now(timezone.utc),
                'client': client
            }
            
            logger.info(f"Started OTP monitoring for account: {phone_number}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting OTP monitoring for {phone_number}: {e}")
            return False
    
    async def stop_monitoring_account(self, phone_number: str) -> None:
        """Stop monitoring an account."""
        try:
            if phone_number in self.monitoring_active:
                client = self.monitoring_active[phone_number]['client']
                
                # Remove event handlers
                client.remove_event_handler(self._handle_login_attempt)
                
                del self.monitoring_active[phone_number]
                logger.info(f"Stopped OTP monitoring for account: {phone_number}")
                
        except Exception as e:
            logger.error(f"Error stopping OTP monitoring for {phone_number}: {e}")
    
    async def _handle_login_attempt(self, event) -> None:
        """Handle detected login attempt."""
        try:
            # Get the phone number from the client
            phone_number = None
            for phone, info in self.monitoring_active.items():
                if info['client'] == event.client:
                    phone_number = phone
                    break
            
            if not phone_number:
                return
            
            # Extract message details
            message_text = event.message.message if event.message else ""
            sender_id = event.sender_id if hasattr(event, 'sender_id') else None
            
            # Check if this looks like an external login attempt
            suspicious_indicators = [
                'login code',
                'verification code', 
                'authentication code',
                'security code',
                'confirm',
                'verify'
            ]
            
            message_lower = message_text.lower()
            is_suspicious = any(indicator in message_lower for indicator in suspicious_indicators)
            
            if is_suspicious:
                await self._report_suspicious_activity(phone_number, {
                    'type': 'EXTERNAL_LOGIN_ATTEMPT',
                    'message': message_text,
                    'sender_id': sender_id,
                    'detected_at': datetime.now(timezone.utc),
                    'source': 'message_monitor'
                })
                
        except Exception as e:
            logger.error(f"Error handling login attempt: {e}")
    
    async def _report_suspicious_activity(self, phone_number: str, activity_details: Dict[str, Any]) -> None:
        """Report suspicious activity to admin."""
        try:
            account_id = self.monitoring_active.get(phone_number, {}).get('account_id')
            
            # Update database
            if account_id:
                db = get_db_session()
                try:
                    AccountService.update_account_details(
                        db=db,
                        account_id=account_id,
                        otp_reported=True
                    )
                except Exception as e:
                    logger.error(f"Error updating account OTP flag: {e}")
                finally:
                    close_db_session(db)
            
            # Prepare alert message
            alert_text = f"""
🚨 **CRITICAL SECURITY ALERT** 🚨

⚠️ **External Login Attempt Detected**

📱 **Phone Number:** `{phone_number}`
🆔 **Account ID:** {account_id or 'Unknown'}
🕒 **Time:** {activity_details['detected_at'].strftime('%Y-%m-%d %H:%M:%S UTC')}
📋 **Type:** {activity_details['type']}

📨 **Message Details:**
```
{activity_details.get('message', 'N/A')[:500]}
```

👤 **Sender ID:** {activity_details.get('sender_id', 'Unknown')}
🔍 **Source:** {activity_details.get('source', 'Unknown')}

**IMMEDIATE ACTION REQUIRED:**
• Check account status immediately
• Verify if login is authorized
• Consider temporary account freeze
• Review security settings

#SecurityAlert #OTPDetected
            """
            
            # Send to admin
            if self.admin_chat_id:
                try:
                    await self.bot_application.bot.send_message(
                        chat_id=self.admin_chat_id,
                        text=alert_text,
                        parse_mode='Markdown'
                    )
                    logger.critical(f"Security alert sent for {phone_number}")
                    
                except Exception as e:
                    logger.error(f"Failed to send security alert: {e}")
            
            # Also send to admin user directly if different from chat
            if self.admin_user_id and str(self.admin_user_id) != self.admin_chat_id:
                try:
                    await self.bot_application.bot.send_message(
                        chat_id=self.admin_user_id,
                        text=alert_text,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.error(f"Failed to send direct alert to admin user: {e}")
                    
        except Exception as e:
            logger.error(f"Error reporting suspicious activity: {e}")
    
    async def check_account_health(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Check the health status of a monitored account."""
        try:
            if phone_number not in self.monitoring_active:
                return None
            
            client = self.monitoring_active[phone_number]['client']
            
            # Try to get account info to verify connection
            try:
                me = await client.get_me()
                return {
                    'status': 'healthy',
                    'user_id': me.id,
                    'username': me.username,
                    'phone': me.phone,
                    'last_check': datetime.now(timezone.utc)
                }
            except Exception as e:
                logger.warning(f"Account health check failed for {phone_number}: {e}")
                return {
                    'status': 'unhealthy',
                    'error': str(e),
                    'last_check': datetime.now(timezone.utc)
                }
                
        except Exception as e:
            logger.error(f"Error checking account health for {phone_number}: {e}")
            return None
    
    async def periodic_health_check(self) -> None:
        """Perform periodic health checks on all monitored accounts."""
        try:
            for phone_number in list(self.monitoring_active.keys()):
                health_status = await self.check_account_health(phone_number)
                
                if health_status and health_status['status'] == 'unhealthy':
                    await self._report_account_issue(phone_number, health_status)
                    
                # Add delay between checks
                await asyncio.sleep(5)
                
        except Exception as e:
            logger.error(f"Error in periodic health check: {e}")
    
    async def _report_account_issue(self, phone_number: str, health_status: Dict[str, Any]) -> None:
        """Report account health issues to admin."""
        try:
            account_id = self.monitoring_active.get(phone_number, {}).get('account_id')
            
            alert_text = f"""
⚠️ **Account Health Alert**

📱 **Phone:** `{phone_number}`
🆔 **Account ID:** {account_id or 'Unknown'}
📊 **Status:** {health_status['status']}
🕒 **Check Time:** {health_status['last_check'].strftime('%Y-%m-%d %H:%M:%S UTC')}

❌ **Error Details:**
```
{health_status.get('error', 'Unknown error')}
```

**Recommended Actions:**
• Check account status
• Verify connection
• Review recent activity
• Consider account recovery

#AccountHealth #ConnectionIssue
            """
            
            if self.admin_chat_id:
                await self.bot_application.bot.send_message(
                    chat_id=self.admin_chat_id,
                    text=alert_text,
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Error reporting account issue: {e}")
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status."""
        return {
            'active_accounts': len(self.monitoring_active),
            'accounts': {
                phone: {
                    'account_id': info['account_id'],
                    'started_at': info['started_at'].isoformat(),
                    'duration_minutes': (datetime.now(timezone.utc) - info['started_at']).total_seconds() / 60
                }
                for phone, info in self.monitoring_active.items()
            }
        }

# Background task for periodic monitoring
async def run_periodic_monitoring(otp_monitor: OTPMonitor) -> None:
    """Run periodic monitoring tasks."""
    while True:
        try:
            await asyncio.sleep(300)  # Check every 5 minutes
            await otp_monitor.periodic_health_check()
        except Exception as e:
            logger.error(f"Error in periodic monitoring: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retry
