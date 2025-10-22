"""
Database operations for the Telegram Account Bot - Proxy Service.
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from .models import ProxyPool
from . import get_db_session, close_db_session

logger = logging.getLogger(__name__)


class ProxyService:
    """Service for proxy-related database operations."""

    @staticmethod
    def add_proxy(
        db: Session,
        ip_address: str,
        port: int,
        username: str = None,
        password: str = None,
        country_code: str = None,
        provider: str = 'free'
    ) -> ProxyPool:
        """Add a new proxy to the pool with encrypted password."""
        try:
            proxy = ProxyPool(
                ip_address=ip_address,
                port=port,
                username=username,
                country_code=country_code,
                provider=provider,
                is_active=True
            )
            
            # Set encrypted password
            if password:
                proxy.set_encrypted_password(password)
            
            # Set default proxy_type manually (avoid constructor param)
            proxy.proxy_type = 'datacenter'
            
            db.add(proxy)
            db.commit()
            db.refresh(proxy)
            logger.info(f"Added new proxy: {ip_address}:{port} (provider: {provider})")
            return proxy
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to add proxy {ip_address}:{port}: {e}")
            raise

    @staticmethod
    def get_available_proxy(db: Session, country_code: str = None) -> Optional[ProxyPool]:
        """Get an available proxy from the pool, optionally filtered by country."""
        try:
            query = db.query(ProxyPool).filter(ProxyPool.is_active == True)

            if country_code:
                query = query.filter(ProxyPool.country_code == country_code)

            # Order by last_used_at (nulls first, then oldest first) to rotate usage
            proxy = query.order_by(ProxyPool.last_used_at.asc().nullsfirst()).first()

            if proxy:
                # Mark as used
                proxy.last_used_at = datetime.now(timezone.utc)
                db.commit()
                logger.info(f"Selected proxy: {proxy.ip_address}:{proxy.port} for country {country_code or 'any'}")
                return proxy

            return None
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to get available proxy: {e}")
            return None

    @staticmethod
    def get_proxy_by_id(db: Session, proxy_id: int) -> Optional[ProxyPool]:
        """Get a proxy by its ID."""
        try:
            return db.query(ProxyPool).filter(ProxyPool.id == proxy_id).first()
        except Exception as e:
            logger.error(f"Failed to get proxy {proxy_id}: {e}")
            return None

    @staticmethod
    def get_proxy_stats(db: Session) -> Dict[str, Any]:
        """Get statistics about the proxy pool."""
        try:
            total_proxies = db.query(func.count(ProxyPool.id)).scalar()
            active_proxies = db.query(func.count(ProxyPool.id)).filter(ProxyPool.is_active == True).scalar()
            inactive_proxies = total_proxies - active_proxies

            # Country distribution
            country_stats = db.query(
                ProxyPool.country_code,
                func.count(ProxyPool.id)
            ).filter(ProxyPool.is_active == True).group_by(ProxyPool.country_code).all()

            # Recently used proxies (last 24 hours)
            recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            recently_used = db.query(func.count(ProxyPool.id)).filter(
                and_(ProxyPool.last_used_at >= recent_cutoff, ProxyPool.is_active == True)
            ).scalar()

            return {
                'total_proxies': total_proxies or 0,
                'active_proxies': active_proxies or 0,
                'inactive_proxies': inactive_proxies or 0,
                'country_distribution': dict(country_stats) if country_stats else {},
                'recently_used_24h': recently_used or 0
            }
        except Exception as e:
            logger.error(f"Failed to get proxy stats: {e}")
            return {
                'total_proxies': 0,
                'active_proxies': 0,
                'inactive_proxies': 0,
                'country_distribution': {},
                'recently_used_24h': 0
            }

    @staticmethod
    def deactivate_proxy(db: Session, proxy_id: int, reason: str = None) -> bool:
        """Deactivate a proxy (mark as inactive)."""
        try:
            proxy = db.query(ProxyPool).filter(ProxyPool.id == proxy_id).first()
            if proxy:
                proxy.is_active = False
                db.commit()
                logger.warning(f"Deactivated proxy {proxy_id} ({proxy.ip_address}:{proxy.port}) - Reason: {reason}")
                return True
            return False
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to deactivate proxy {proxy_id}: {e}")
            return False

    @staticmethod
    def get_all_proxies(db: Session, include_inactive: bool = False) -> List[ProxyPool]:
        """Get all proxies, optionally including inactive ones."""
        try:
            query = db.query(ProxyPool)
            if not include_inactive:
                query = query.filter(ProxyPool.is_active == True)
            return query.order_by(ProxyPool.created_at.desc()).all()
        except Exception as e:
            logger.error(f"Failed to get all proxies: {e}")
            return []

    @staticmethod
    def cleanup_old_proxies(db: Session, days_inactive: int = 30) -> int:
        """Clean up proxies that haven't been used for a specified number of days."""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_inactive)
            old_proxies = db.query(ProxyPool).filter(
                and_(ProxyPool.last_used_at < cutoff_date, ProxyPool.is_active == True)
            ).all()

            deactivated_count = 0
            for proxy in old_proxies:
                proxy.is_active = False
                deactivated_count += 1

            db.commit()
            logger.info(f"Deactivated {deactivated_count} old proxies (not used for {days_inactive} days)")
            return deactivated_count
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to cleanup old proxies: {e}")
            return 0

    @staticmethod
    def remove_free_proxies(db: Session) -> int:
        """
        Remove all free proxies (non-WebShare proxies) from the database.
        Only keeps proxies with provider='webshare'.
        """
        try:
            # Find all proxies that are NOT from WebShare
            free_proxies = db.query(ProxyPool).filter(
                or_(ProxyPool.provider != 'webshare', ProxyPool.provider == None)
            ).all()

            removed_count = len(free_proxies)
            
            # Delete them
            for proxy in free_proxies:
                db.delete(proxy)

            db.commit()
            logger.info(f"✅ Removed {removed_count} free proxies (kept only WebShare)")
            return removed_count
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to remove free proxies: {e}")
            return 0


# Database service classes for handlers
# These are placeholders until full user/account system is implemented

class UserService:
    """Service for user database operations."""
    
    @staticmethod
    def get_or_create_user(db: Session, telegram_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Get existing user or create new one."""
        from database.models import User
        
        user = db.query(User).filter(User.telegram_user_id == telegram_id).first()
        
        if not user:
            user = User(
                telegram_user_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"Created new user {telegram_id}")
        else:
            # Update username if changed
            if username and user.username != username:
                user.username = username
                db.commit()
                
        return user
    
    @staticmethod
    def get_user_by_telegram_id(db: Session, telegram_id: int):
        """Get user by telegram ID from database."""
        from database.models import User
        
        user = db.query(User).filter(User.telegram_user_id == telegram_id).first()
        return user
    
    @staticmethod
    def update_user(db: Session, user_id: int, **kwargs):
        """Update user fields by database ID."""
        from database.models import User
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning(f"User {user_id} not found for update")
            return False
        
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        db.commit()
        db.refresh(user)
        logger.info(f"Updated user {user_id}: {kwargs}")
        return True
    
    @staticmethod
    def update_balance(db: Session, user_id: int, amount: float):
        """Update user balance by database ID."""
        from database.models import User
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning(f"User {user_id} not found for balance update")
            return False
        
        user.balance = amount
        db.commit()
        logger.info(f"Updated user {user_id} balance to {amount}")
        return True
    
    @staticmethod
    def get_user(db: Session, user_id: int):
        """Get user by database ID."""
        from database.models import User
        
        user = db.query(User).filter(User.id == user_id).first()
        return user


class TelegramAccountService:
    """Service for telegram account operations."""
    
    @staticmethod
    def create_account(db: Session, seller_id: int, phone: str, **kwargs):
        """
        Create a new Telegram account record.
        
        Args:
            db: Database session
            seller_id: User ID of the seller
            phone: Phone number
            **kwargs: Additional account fields
            
        Returns:
            TelegramAccount object
        """
        from database.models import TelegramAccount, AccountStatus
        
        account = TelegramAccount(
            seller_id=seller_id,
            phone_number=phone,
            country_code=kwargs.get('country_code'),
            status=kwargs.get('status', AccountStatus.AVAILABLE.value),
            session_string=kwargs.get('session_string'),
            two_fa_password=kwargs.get('two_fa_password'),
            original_account_name=kwargs.get('original_account_name'),
            original_username=kwargs.get('original_username'),
            original_bio=kwargs.get('original_bio'),
            sale_price=kwargs.get('sale_price', 0.0)
        )
        
        db.add(account)
        db.commit()
        db.refresh(account)
        logger.info(f"Created account {account.id} for phone {phone}")
        return account
    
    @staticmethod
    def get_user_accounts(db: Session, user_id: int):
        """Get all accounts owned by a user."""
        from database.models import TelegramAccount
        
        accounts = db.query(TelegramAccount).filter(
            TelegramAccount.seller_id == user_id
        ).all()
        
        return accounts
    
    @staticmethod
    def get_account(db: Session, account_id: int):
        """Get account by ID."""
        from database.models import TelegramAccount
        
        account = db.query(TelegramAccount).filter(
            TelegramAccount.id == account_id
        ).first()
        
        return account
    
    @staticmethod
    def get_account_by_phone(db: Session, phone: str):
        """Get account by phone number."""
        from database.models import TelegramAccount
        
        account = db.query(TelegramAccount).filter(
            TelegramAccount.phone_number == phone
        ).first()
        
        return account

    @staticmethod
    def set_account_hold(db: Session, account_id: int, hold_hours: int = 24, reason: str | None = None):
        """Place an account on timed hold and record metadata."""
        from database.models import TelegramAccount, AccountStatus

        try:
            account = db.query(TelegramAccount).filter(
                TelegramAccount.id == account_id
            ).with_for_update().first()

            if not account:
                logger.warning("Account %s not found for hold", account_id)
                return {'success': False, 'error': 'account_not_found'}

            now = datetime.utcnow()
            hold_until = None
            if hold_hours and hold_hours > 0:
                hold_until = now + timedelta(hours=hold_hours)

            account.status = AccountStatus.TWENTY_FOUR_HOUR_HOLD
            account.hold_until = hold_until
            account.multi_device_detected = True
            if reason:
                account.freeze_reason = reason
            account.updated_at = now

            db.commit()

            return {
                'success': True,
                'account_id': account_id,
                'hold_until': hold_until,
                'hold_hours': hold_hours
            }
        except Exception as exc:
            logger.error("Failed to place account %s on hold: %s", account_id, exc)
            db.rollback()
            return {'success': False, 'error': str(exc)}
    
    @staticmethod
    def update_account(db: Session, account_id: int, **kwargs):
        """Update account fields."""
        from database.models import TelegramAccount
        
        account = db.query(TelegramAccount).filter(
            TelegramAccount.id == account_id
        ).first()
        
        if not account:
            logger.warning(f"Account {account_id} not found")
            return False
        
        # Update fields
        for key, value in kwargs.items():
            if hasattr(account, key):
                setattr(account, key, value)
        
        db.commit()
        db.refresh(account)
        logger.info(f"Updated account {account_id}")
        return True
    
    @staticmethod
    def get_available_accounts(db: Session, limit: int = 10):
        """Get available accounts for sale."""
        from database.models import TelegramAccount, AccountStatus
        
        accounts = db.query(TelegramAccount).filter(
            TelegramAccount.status == AccountStatus.AVAILABLE.value,
            TelegramAccount.can_be_sold == True
        ).limit(limit).all()
        
        return accounts
    
    @staticmethod
    def mark_as_sold(db: Session, account_id: int, buyer_telegram_id: int = None):
        """Mark account as sold."""
        from database.models import TelegramAccount, AccountStatus
        from datetime import datetime, timezone
        
        account = db.query(TelegramAccount).filter(
            TelegramAccount.id == account_id
        ).first()
        
        if not account:
            return False
        
        account.status = AccountStatus.SOLD.value
        account.sold_at = datetime.now(timezone.utc)
        
        db.commit()
        logger.info(f"Marked account {account_id} as sold")
        return True
    
    @staticmethod
    async def enable_2fa(session_file: str, api_id: int, api_hash: str, password: str, hint: str = "", email: str = None):
        """
        Enable 2FA on account using session file
        
        Args:
            session_file: Path to .session file (without .session extension)
            api_id: Telegram API ID
            api_hash: Telegram API hash
            password: New password
            hint: Password hint
            email: Recovery email
        
        Returns:
            True if successful
        """
        from telethon import TelegramClient
        from services.session_manager import enable_2fa
        
        try:
            client = TelegramClient(session_file, api_id, api_hash)
            await client.connect()
            
            if not await client.is_user_authorized():
                logger.error("Session not authorized")
                return False
            
            result = await enable_2fa(client, password, hint, email)
            await client.disconnect()
            
            return result
        except Exception as e:
            logger.error(f"Error enabling 2FA: {e}")
            return False
    
    @staticmethod
    async def change_username(session_file: str, api_id: int, api_hash: str, new_username: str):
        """
        Change username on account
        
        Args:
            session_file: Path to .session file (without .session extension)
            api_id: Telegram API ID
            api_hash: Telegram API hash
            new_username: New username (without @)
        
        Returns:
            True if successful
        """
        from telethon import TelegramClient
        from services.session_manager import change_username as change_username_func
        
        try:
            client = TelegramClient(session_file, api_id, api_hash)
            await client.connect()
            
            if not await client.is_user_authorized():
                logger.error("Session not authorized")
                return False
            
            result = await change_username_func(client, new_username)
            await client.disconnect()
            
            return result
        except Exception as e:
            logger.error(f"Error changing username: {e}")
            return False
    
    @staticmethod
    async def set_profile_photo(session_file: str, api_id: int, api_hash: str, photo_path: str):
        """
        Set profile photo
        
        Args:
            session_file: Path to .session file (without .session extension)
            api_id: Telegram API ID
            api_hash: Telegram API hash
            photo_path: Path to photo file
        
        Returns:
            True if successful
        """
        from telethon import TelegramClient
        from services.session_manager import set_profile_photo as set_photo_func
        
        try:
            client = TelegramClient(session_file, api_id, api_hash)
            await client.connect()
            
            if not await client.is_user_authorized():
                logger.error("Session not authorized")
                return False
            
            result = await set_photo_func(client, photo_path)
            await client.disconnect()
            
            return result
        except Exception as e:
            logger.error(f"Error setting profile photo: {e}")
            return False
    
    @staticmethod
    async def update_profile(session_file: str, api_id: int, api_hash: str, first_name: str = None, last_name: str = None, about: str = None):
        """
        Update profile information
        
        Args:
            session_file: Path to .session file (without .session extension)
            api_id: Telegram API ID
            api_hash: Telegram API hash
            first_name: New first name
            last_name: New last name
            about: New bio
        
        Returns:
            True if successful
        """
        from telethon import TelegramClient
        from services.session_manager import update_profile as update_profile_func
        
        try:
            client = TelegramClient(session_file, api_id, api_hash)
            await client.connect()
            
            if not await client.is_user_authorized():
                logger.error("Session not authorized")
                return False
            
            result = await update_profile_func(client, first_name, last_name, about)
            await client.disconnect()
            
            return result
        except Exception as e:
            logger.error(f"Error updating profile: {e}")
            return False


class SystemSettingsService:
    """Service for system settings operations."""
    
    @staticmethod
    def get_setting(db: Session, key: str, default=None):
        """Get a system setting by key."""
        try:
            from database.models import SystemSettings
            setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
            if setting:
                # Try to convert to appropriate type
                value = setting.value
                if value is None:
                    return default
                # Try to parse as JSON first (for complex types)
                try:
                    import json
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    # Return as string
                    return value
            return default
        except Exception as e:
            logger.error(f"Error getting setting '{key}': {e}")
            return default
    
    @staticmethod
    def set_setting(db: Session, key: str, value, description: str = None):
        """Set a system setting."""
        try:
            from database.models import SystemSettings
            import json
            
            # Convert value to string (JSON for complex types)
            if isinstance(value, (dict, list)):
                value_str = json.dumps(value)
            elif isinstance(value, bool):
                value_str = json.dumps(value)  # Store as "true" or "false"
            else:
                value_str = str(value)
            
            setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
            if setting:
                setting.value = value_str
                if description:
                    setting.description = description
                setting.updated_at = datetime.now(timezone.utc)
            else:
                setting = SystemSettings(
                    key=key,
                    value=value_str,
                    description=description or f"System setting: {key}"
                )
                db.add(setting)
            
            db.commit()
            logger.info(f"✅ System setting '{key}' set to: {value}")
            return True
        except Exception as e:
            logger.error(f"Error setting '{key}': {e}")
            db.rollback()
            return False
    
    @staticmethod
    def get_all_settings(db: Session):
        """Get all system settings as a dictionary."""
        try:
            from database.models import SystemSettings
            settings_list = db.query(SystemSettings).all()
            # Convert to dictionary
            settings_dict = {}
            for setting in settings_list:
                # Parse value from JSON if needed
                try:
                    import json
                    settings_dict[setting.key] = json.loads(setting.value)
                except (json.JSONDecodeError, TypeError):
                    settings_dict[setting.key] = setting.value
            return settings_dict
        except Exception as e:
            logger.error(f"Error getting all settings: {e}")
            return {}
    
    @staticmethod
    def delete_setting(db: Session, key: str):
        """Delete a system setting."""
        try:
            from database.models import SystemSettings
            setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
            if setting:
                db.delete(setting)
                db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting setting '{key}': {e}")
            db.rollback()
            return False


class WithdrawalService:
    """Service for withdrawal database operations."""
    
    @staticmethod
    def create_withdrawal(db: Session, user_id: int, amount: float, **kwargs):
        """Create a new withdrawal request."""
        from database.models import Withdrawal, WithdrawalStatus
        
        # Default status if not provided
        if 'status' not in kwargs:
            kwargs['status'] = WithdrawalStatus.PENDING
        
        withdrawal = Withdrawal(user_id=user_id, amount=amount, **kwargs)
        db.add(withdrawal)
        db.commit()
        db.refresh(withdrawal)
        logger.info(f"Created withdrawal {withdrawal.id} for user {user_id}: {amount}")
        return withdrawal
    
    @staticmethod
    def get_user_withdrawals(db: Session, user_id: int, limit: int = 50):
        """Get all withdrawal requests for a user."""
        from database.models import Withdrawal
        
        withdrawals = db.query(Withdrawal).filter(
            Withdrawal.user_id == user_id
        ).order_by(Withdrawal.created_at.desc()).limit(limit).all()
        
        return withdrawals
    
    @staticmethod
    def get_withdrawal(db: Session, withdrawal_id: int):
        """Get withdrawal by ID."""
        from database.models import Withdrawal
        return db.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).first()
    
    @staticmethod
    def update_withdrawal_status(db: Session, withdrawal_id: int, status, admin_notes: str = None):
        """Update withdrawal status."""
        from database.models import Withdrawal
        
        withdrawal = db.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).first()
        if not withdrawal:
            logger.warning(f"Withdrawal {withdrawal_id} not found")
            return False
        
        withdrawal.status = status
        if admin_notes:
            withdrawal.admin_notes = admin_notes
        
        db.commit()
        logger.info(f"Updated withdrawal {withdrawal_id} status to {status}")
        return True
    
    @staticmethod
    def get_pending_withdrawals(db: Session, limit: int = 100):
        """Get all pending withdrawal requests."""
        from database.models import Withdrawal, WithdrawalStatus
        
        return db.query(Withdrawal).filter(
            Withdrawal.status == WithdrawalStatus.PENDING
        ).order_by(Withdrawal.created_at.asc()).limit(limit).all()


class ActivityLogService:
    """Service for activity logging operations."""
    
    @staticmethod
    def log_activity(db: Session, user_id: int, action: str, details: str = None, **kwargs):
        """Log user activity to database."""
        from database.models import ActivityLog
        
        try:
            activity = ActivityLog(
                user_id=user_id,
                action=action,
                details=details,
                **kwargs
            )
            db.add(activity)
            db.commit()
            logger.debug(f"Logged activity: user={user_id}, action={action}")
            return True
        except Exception as e:
            logger.error(f"Error logging activity: {e}")
            db.rollback()
            return False
    
    @staticmethod
    def log_action(db: Session, user_id: int, action: str, description: str = None, **kwargs):
        """Alias for log_activity. Accepts description or details."""
        details = description or kwargs.get('details')
        return ActivityLogService.log_activity(db, user_id, action, details, **kwargs)
    
    @staticmethod
    def get_user_activity(db: Session, user_id: int, limit: int = 50):
        """Get user activity logs."""
        from database.models import ActivityLog
        
        return db.query(ActivityLog).filter(
            ActivityLog.user_id == user_id
        ).order_by(ActivityLog.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_all_activity(db: Session, limit: int = 100):
        """Get all activity logs for admin review."""
        from database.models import ActivityLog
        
        return db.query(ActivityLog).order_by(
            ActivityLog.created_at.desc()
        ).limit(limit).all()


class SessionLogService:
    """Service for session logging and tracking operations."""
    
    @staticmethod
    def create_session_log(db: Session, user_id: int = None, account_id: int = None, 
                          session_data: Dict[str, Any] = None) -> Optional[Any]:
        """Create a new session log entry."""
        from database.models import SessionLog
        
        try:
            session_log = SessionLog(
                user_id=user_id,
                account_id=account_id,
                session_hash=session_data.get('session_hash') if session_data else None,
                auth_key_id=session_data.get('auth_key_id') if session_data else None,
                device_model=session_data.get('device_model') if session_data else None,
                system_version=session_data.get('system_version') if session_data else None,
                app_name=session_data.get('app_name') if session_data else None,
                app_version=session_data.get('app_version') if session_data else None,
                ip_address=session_data.get('ip_address') if session_data else None,
                country=session_data.get('country') if session_data else None,
                region=session_data.get('region') if session_data else None,
                status=session_data.get('status', 'ACTIVE') if session_data else 'ACTIVE',
                session_type=session_data.get('session_type') if session_data else None,
                is_official_app=session_data.get('is_official_app', True) if session_data else True,
                is_current=session_data.get('is_current', False) if session_data else False,
                extra_data=session_data.get('extra_data') if session_data else None
            )
            db.add(session_log)
            db.commit()
            db.refresh(session_log)
            logger.info(f"Created session log {session_log.id} for user {user_id}, account {account_id}")
            return session_log
        except Exception as e:
            logger.error(f"Error creating session log: {e}")
            db.rollback()
            return None
    
    @staticmethod
    def get_user_sessions(db: Session, user_id: int, active_only: bool = False, limit: int = 50):
        """Get all sessions for a specific user."""
        from database.models import SessionLog
        
        query = db.query(SessionLog).filter(SessionLog.user_id == user_id)
        
        if active_only:
            query = query.filter(SessionLog.status == 'ACTIVE')
        
        return query.order_by(SessionLog.session_start.desc()).limit(limit).all()
    
    @staticmethod
    def get_account_sessions(db: Session, account_id: int, active_only: bool = False, limit: int = 50):
        """Get all sessions for a specific account."""
        from database.models import SessionLog
        
        query = db.query(SessionLog).filter(SessionLog.account_id == account_id)
        
        if active_only:
            query = query.filter(SessionLog.status == 'ACTIVE')
        
        return query.order_by(SessionLog.session_start.desc()).limit(limit).all()
    
    @staticmethod
    def get_recent_sessions(db: Session, limit: int = 100, hours: int = 24):
        """Get recent session logs within specified hours."""
        from database.models import SessionLog
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        return db.query(SessionLog).filter(
            SessionLog.session_start >= cutoff_time
        ).order_by(SessionLog.session_start.desc()).limit(limit).all()
    
    @staticmethod
    def get_active_sessions_count(db: Session, user_id: int = None, account_id: int = None) -> int:
        """Get count of active sessions for user or account."""
        from database.models import SessionLog
        
        query = db.query(func.count(SessionLog.id)).filter(SessionLog.status == 'ACTIVE')
        
        if user_id:
            query = query.filter(SessionLog.user_id == user_id)
        if account_id:
            query = query.filter(SessionLog.account_id == account_id)
        
        return query.scalar() or 0
    
    @staticmethod
    def terminate_session(db: Session, session_id: int) -> bool:
        """Mark a session as terminated."""
        from database.models import SessionLog
        
        try:
            session = db.query(SessionLog).filter(SessionLog.id == session_id).first()
            if not session:
                logger.warning(f"Session {session_id} not found")
                return False
            
            session.status = 'TERMINATED'
            session.session_end = datetime.now(timezone.utc)
            db.commit()
            logger.info(f"Terminated session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error terminating session {session_id}: {e}")
            db.rollback()
            return False
    
    @staticmethod
    def terminate_user_sessions(db: Session, user_id: int, exclude_session_ids: List[int] = None) -> int:
        """Terminate all active sessions for a user, optionally excluding specific sessions."""
        from database.models import SessionLog
        
        try:
            query = db.query(SessionLog).filter(
                and_(SessionLog.user_id == user_id, SessionLog.status == 'ACTIVE')
            )
            
            if exclude_session_ids:
                query = query.filter(SessionLog.id.notin_(exclude_session_ids))
            
            sessions = query.all()
            terminated_count = 0
            
            for session in sessions:
                session.status = 'TERMINATED'
                session.session_end = datetime.now(timezone.utc)
                terminated_count += 1
            
            db.commit()
            logger.info(f"Terminated {terminated_count} sessions for user {user_id}")
            return terminated_count
        except Exception as e:
            logger.error(f"Error terminating user sessions: {e}")
            db.rollback()
            return 0
    
    @staticmethod
    def update_session_activity(db: Session, session_id: int) -> bool:
        """Update last_active timestamp for a session."""
        from database.models import SessionLog
        
        try:
            session = db.query(SessionLog).filter(SessionLog.id == session_id).first()
            if session:
                session.last_active = datetime.now(timezone.utc)
                db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating session activity: {e}")
            db.rollback()
            return False
    
    @staticmethod
    def get_multi_session_users(db: Session) -> List[Dict[str, Any]]:
        """Get users with multiple active sessions (potential security risk)."""
        from database.models import SessionLog
        
        multi_session_data = db.query(
            SessionLog.user_id,
            func.count(SessionLog.id).label('session_count')
        ).filter(
            SessionLog.status == 'ACTIVE'
        ).group_by(SessionLog.user_id).having(
            func.count(SessionLog.id) > 1
        ).all()
        
        return [{'user_id': uid, 'session_count': count} for uid, count in multi_session_data]


class VerificationService:
    """Service for verification task operations."""
    
    @staticmethod
    def create_verification(db: Session, user_id: int, verification_type: str, **kwargs):
        """Create a new verification task."""
        from database.models import VerificationTask
        
        verification = VerificationTask(
            user_id=user_id,
            task_type=verification_type,
            **kwargs
        )
        db.add(verification)
        db.commit()
        db.refresh(verification)
        logger.info(f"Created verification task {verification.id} for user {user_id}")
        return verification
    
    @staticmethod
    def get_user_verifications(db: Session, user_id: int, limit: int = 50):
        """Get all verification tasks for a user."""
        from database.models import VerificationTask
        
        return db.query(VerificationTask).filter(
            VerificationTask.user_id == user_id
        ).order_by(VerificationTask.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def update_verification_status(db: Session, verification_id: int, status: str, **kwargs):
        """Update verification status."""
        from database.models import VerificationTask
        
        verification = db.query(VerificationTask).filter(
            VerificationTask.id == verification_id
        ).first()
        
        if not verification:
            logger.warning(f"Verification {verification_id} not found")
            return False
        
        verification.status = status
        for key, value in kwargs.items():
            if hasattr(verification, key):
                setattr(verification, key, value)
        
        db.commit()
        logger.info(f"Updated verification {verification_id} status to {status}")
        return True



