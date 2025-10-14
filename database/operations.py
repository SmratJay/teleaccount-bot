"""
Database operations and queries.
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from .models import User, Account, Withdrawal, SystemSettings, ProxyPool
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class UserService:
    """Service for user-related database operations."""
    
    @staticmethod
    def create_user(db: Session, telegram_user_id: int, username: str = None, 
                   first_name: str = None, last_name: str = None, language_code: str = 'en') -> User:
        """Create a new user."""
        user = User(
            telegram_user_id=telegram_user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Created new user: {telegram_user_id}")
        return user
    
    @staticmethod
    def get_user_by_telegram_id(db: Session, telegram_user_id: int) -> User:
        """Get user by Telegram user ID."""
        return db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
    
    @staticmethod
    def get_or_create_user(db: Session, telegram_user_id: int, username: str = None,
                          first_name: str = None, last_name: str = None, language_code: str = 'en') -> User:
        """Get existing user or create new one."""
        user = UserService.get_user_by_telegram_id(db, telegram_user_id)
        if not user:
            user = UserService.create_user(db, telegram_user_id, username, first_name, last_name, language_code)
        return user
    
    @staticmethod
    def update_user_balance(db: Session, user_id: int, amount: float) -> bool:
        """Update user balance."""
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.balance += amount
            user.updated_at = datetime.now(timezone.utc)
            db.commit()
            logger.info(f"Updated balance for user {user_id}: {amount}")
            return True
        return False
    
    @staticmethod
    def get_all_active_users(db: Session):
        """Get all active users."""
        return db.query(User).filter(User.is_active == True).all()

class AccountService:
    """Service for account-related database operations."""
    
    @staticmethod
    def create_account(db: Session, user_id: int, phone_number: str, 
                      session_file_path: str, country_code: str = None,
                      proxy_config: str = None) -> Account:
        """Create a new account."""
        account = Account(
            user_id=user_id,
            phone_number=phone_number,
            session_file_path=session_file_path,
            country_code=country_code,
            proxy_config=proxy_config,
            last_login_at=datetime.now(timezone.utc)
        )
        db.add(account)
        db.commit()
        db.refresh(account)
        logger.info(f"Created new account for user {user_id}: {phone_number}")
        return account
    
    @staticmethod
    def get_account_by_phone(db: Session, phone_number: str) -> Account:
        """Get account by phone number."""
        return db.query(Account).filter(Account.phone_number == phone_number).first()
    
    @staticmethod
    def get_user_accounts(db: Session, user_id: int):
        """Get all accounts for a user."""
        return db.query(Account).filter(Account.user_id == user_id).all()
    
    @staticmethod
    def update_account_status(db: Session, account_id: int, status: str) -> bool:
        """Update account status."""
        account = db.query(Account).filter(Account.id == account_id).first()
        if account:
            account.status = status
            account.updated_at = datetime.now(timezone.utc)
            db.commit()
            logger.info(f"Updated account {account_id} status to {status}")
            return True
        return False
    
    @staticmethod
    def enable_2fa(db: Session, account_id: int, password_hash: str) -> bool:
        """Enable 2FA for an account."""
        account = db.query(Account).filter(Account.id == account_id).first()
        if account:
            account.two_fa_enabled = True
            account.two_fa_password_hash = password_hash
            account.updated_at = datetime.now(timezone.utc)
            db.commit()
            logger.info(f"Enabled 2FA for account {account_id}")
            return True
        return False
    
    @staticmethod
    def update_account_details(db: Session, account_id: int, **kwargs) -> bool:
        """Update account details."""
        account = db.query(Account).filter(Account.id == account_id).first()
        if account:
            for key, value in kwargs.items():
                if hasattr(account, key):
                    setattr(account, key, value)
            account.updated_at = datetime.now(timezone.utc)
            db.commit()
            logger.info(f"Updated account {account_id} details")
            return True
        return False

class WithdrawalService:
    """Service for withdrawal-related database operations."""
    
    @staticmethod
    def create_withdrawal(db: Session, user_id: int, amount: float, 
                         currency: str, destination_address: str) -> Withdrawal:
        """Create a new withdrawal request."""
        withdrawal = Withdrawal(
            user_id=user_id,
            amount=amount,
            currency=currency,
            destination_address=destination_address
        )
        db.add(withdrawal)
        db.commit()
        db.refresh(withdrawal)
        logger.info(f"Created withdrawal request for user {user_id}: {amount} {currency}")
        return withdrawal
    
    @staticmethod
    def get_pending_withdrawals(db: Session):
        """Get all pending withdrawals."""
        return db.query(Withdrawal).filter(Withdrawal.status == 'PENDING').order_by(desc(Withdrawal.created_at)).all()
    
    @staticmethod
    def get_user_withdrawals(db: Session, user_id: int):
        """Get all withdrawals for a user."""
        return db.query(Withdrawal).filter(Withdrawal.user_id == user_id).order_by(desc(Withdrawal.created_at)).all()
    
    @staticmethod
    def update_withdrawal_status(db: Session, withdrawal_id: int, status: str, 
                               admin_id: int = None, admin_notes: str = None) -> bool:
        """Update withdrawal status."""
        withdrawal = db.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).first()
        if withdrawal:
            withdrawal.status = status
            withdrawal.updated_at = datetime.now(timezone.utc)
            if status in ['COMPLETED', 'REJECTED']:
                withdrawal.processed_at = datetime.now(timezone.utc)
                withdrawal.processed_by_admin_id = admin_id
            if admin_notes:
                withdrawal.admin_notes = admin_notes
            db.commit()
            logger.info(f"Updated withdrawal {withdrawal_id} status to {status}")
            return True
        return False

class SystemSettingsService:
    """Service for system settings operations."""
    
    @staticmethod
    def get_setting(db: Session, key: str) -> str:
        """Get a system setting value."""
        setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
        return setting.value if setting else None
    
    @staticmethod
    def set_setting(db: Session, key: str, value: str, description: str = None) -> bool:
        """Set a system setting value."""
        setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
        if setting:
            setting.value = value
            setting.updated_at = datetime.now(timezone.utc)
            if description:
                setting.description = description
        else:
            setting = SystemSettings(key=key, value=value, description=description)
            db.add(setting)
        
        db.commit()
        logger.info(f"Set system setting {key}: {value}")
        return True
    
    @staticmethod
    def is_withdrawal_enabled(db: Session, currency: str) -> bool:
        """Check if withdrawals are enabled for a currency."""
        setting_key = f"withdrawal_{currency.lower()}_enabled"
        value = SystemSettingsService.get_setting(db, setting_key)
        return value == 'true' if value else False

class ProxyService:
    """Service for proxy-related database operations."""
    
    @staticmethod
    def add_proxy(db: Session, proxy_type: str, host: str, port: int, 
                 username: str = None, password: str = None, country_code: str = None) -> ProxyPool:
        """Add a new proxy to the pool."""
        proxy = ProxyPool(
            proxy_type=proxy_type,
            host=host,
            port=port,
            username=username,
            password=password,
            country_code=country_code
        )
        db.add(proxy)
        db.commit()
        db.refresh(proxy)
        logger.info(f"Added new proxy: {host}:{port}")
        return proxy
    
    @staticmethod
    def get_available_proxy(db: Session) -> ProxyPool:
        """Get an available proxy from the pool."""
        return db.query(ProxyPool).filter(
            and_(ProxyPool.is_active == True, ProxyPool.failure_count < 5)
        ).order_by(ProxyPool.last_used_at.asc().nullsfirst()).first()
    
    @staticmethod
    def mark_proxy_used(db: Session, proxy_id: int) -> bool:
        """Mark a proxy as used."""
        proxy = db.query(ProxyPool).filter(ProxyPool.id == proxy_id).first()
        if proxy:
            proxy.last_used_at = datetime.now(timezone.utc)
            db.commit()
            return True
        return False
    
    @staticmethod
    def mark_proxy_failed(db: Session, proxy_id: int) -> bool:
        """Mark a proxy as failed."""
        proxy = db.query(ProxyPool).filter(ProxyPool.id == proxy_id).first()
        if proxy:
            proxy.failure_count += 1
            if proxy.failure_count >= 5:
                proxy.is_active = False
            db.commit()
            logger.warning(f"Marked proxy {proxy_id} as failed (count: {proxy.failure_count})")
            return True
        return False