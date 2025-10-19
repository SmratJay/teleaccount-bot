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


# Stub services for real_handlers.py compatibility
# These are placeholders until full user/account system is implemented

class UserService:
    """Stub service for user operations."""
    
    @staticmethod
    def get_or_create_user(db: Session, telegram_id: int, username: str = None):
        """Stub: Returns a mock user object."""
        logger.warning("UserService.get_or_create_user called - using stub implementation")
        from database.models import User
        return User(telegram_id=telegram_id, username=username)
    
    @staticmethod
    def get_user_by_telegram_id(db: Session, telegram_id: int):
        """Stub: Returns a mock user object."""
        logger.warning("UserService.get_user_by_telegram_id called - using stub implementation")
        from database.models import User
        return User(telegram_id=telegram_id, username=None)
    
    @staticmethod
    def update_user(db: Session, user_id: int, **kwargs):
        """Stub: Does nothing."""
        logger.warning("UserService.update_user called - using stub implementation")
        return True
    
    @staticmethod
    def update_balance(db: Session, user_id: int, amount: float):
        """Stub: Does nothing."""
        logger.warning("UserService.update_balance called - using stub implementation")
        return True
    
    @staticmethod
    def get_user(db: Session, user_id: int):
        """Stub: Returns mock user."""
        logger.warning("UserService.get_user called - using stub implementation")
        from database.models import User
        return User(telegram_id=user_id, username=None)


class TelegramAccountService:
    """Stub service for telegram account operations."""
    
    @staticmethod
    def create_account(db: Session, user_id: int, phone: str, **kwargs):
        """Stub: Returns mock account."""
        logger.warning("TelegramAccountService.create_account called - using stub implementation")
        from database.models import TelegramAccount
        return TelegramAccount(phone_number=phone, user_id=user_id)
    
    @staticmethod
    def get_user_accounts(db: Session, user_id: int):
        """Stub: Returns empty list."""
        logger.warning("TelegramAccountService.get_user_accounts called - using stub implementation")
        return []
    
    @staticmethod
    def get_account(db: Session, account_id: int):
        """Stub: Returns mock account."""
        logger.warning("TelegramAccountService.get_account called - using stub implementation")
        from database.models import TelegramAccount
        return TelegramAccount(phone_number="+1234567890", user_id=1)
    
    @staticmethod
    def update_account(db: Session, account_id: int, **kwargs):
        """Stub: Does nothing."""
        logger.warning("TelegramAccountService.update_account called - using stub implementation")
        return True
    
    @staticmethod
    def get_available_accounts(db: Session, limit: int = 10):
        """Stub: Returns empty list."""
        logger.warning("TelegramAccountService.get_available_accounts called - using stub implementation")
        return []


class SystemSettingsService:
    """Stub service for system settings."""
    
    @staticmethod
    def get_setting(db: Session, key: str, default=None):
        """Stub: Returns default value."""
        logger.warning(f"SystemSettingsService.get_setting called for '{key}' - using stub implementation")
        settings = {
            'account_price': 10.0,
            'min_withdrawal': 5.0,
            'admin_chat_id': None
        }
        return settings.get(key, default)
    
    @staticmethod
    def set_setting(db: Session, key: str, value):
        """Stub: Does nothing."""
        logger.warning(f"SystemSettingsService.set_setting called for '{key}' - using stub implementation")
        return True


class WithdrawalService:
    """Stub service for withdrawal operations."""
    
    @staticmethod
    def create_withdrawal(db: Session, user_id: int, amount: float, **kwargs):
        """Stub: Returns mock withdrawal."""
        logger.warning("WithdrawalService.create_withdrawal called - using stub implementation")
        return type('Withdrawal', (), {
            'id': 1,
            'user_id': user_id,
            'amount': amount,
            'status': 'pending'
        })()
    
    @staticmethod
    def get_user_withdrawals(db: Session, user_id: int):
        """Stub: Returns empty list."""
        logger.warning("WithdrawalService.get_user_withdrawals called - using stub implementation")
        return []


class ActivityLogService:
    """Stub service for activity logging."""
    
    @staticmethod
    def log_activity(db: Session, user_id: int, action: str, details: str = None):
        """Stub: Does nothing."""
        logger.debug(f"ActivityLogService.log_activity: user={user_id}, action={action}")
        return True


class VerificationService:
    @staticmethod
    def create_verification(db, user_id, verification_type, **kwargs):
        logger.warning('VerificationService.create_verification called - using stub')
        return type('Verification', (), {'id': 1, 'user_id': user_id, 'status': 'pending'})()
    @staticmethod
    def get_user_verifications(db, user_id):
        logger.warning('VerificationService.get_user_verifications called - using stub')
        return []

