"""
Database operations for the Telegram Account Selling Bot.
Completely rebuilt to match new specifications.
"""
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from datetime import datetime, timedelta
import json

from .models import (
    User, TelegramAccount, AccountSale, Withdrawal, SystemSettings, 
    ProxyPool, ActivityLog, VerificationTask, UserVerification,
    UserStatus, AccountStatus, WithdrawalStatus, SaleStatus
)

logger = logging.getLogger(__name__)

class UserService:
    @staticmethod
    def get_or_create_user(db: Session, telegram_user_id: int, username: str = None, 
                          first_name: str = None, last_name: str = None, 
                          language_code: str = 'en') -> User:
        """Get existing user or create new one."""
        try:
            user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
            
            if not user:
                user = User(
                    telegram_user_id=telegram_user_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    language_code=language_code,
                    status=UserStatus.PENDING_VERIFICATION
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                logger.info(f"Created new user: {telegram_user_id}")
            else:
                # Update user info if changed
                updated = False
                if user.username != username:
                    user.username = username
                    updated = True
                if user.first_name != first_name:
                    user.first_name = first_name
                    updated = True
                if user.last_name != last_name:
                    user.last_name = last_name
                    updated = True
                
                if updated:
                    user.updated_at = datetime.utcnow()
                    db.commit()
            
            return user
            
        except Exception as e:
            logger.error(f"Error in get_or_create_user: {e}")
            db.rollback()
            raise

    @staticmethod
    def get_user_by_telegram_id(db: Session, telegram_user_id: int) -> Optional[User]:
        """Get user by Telegram ID."""
        try:
            return db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
        except Exception as e:
            logger.error(f"Error getting user by telegram_id: {e}")
            return None

    @staticmethod
    def update_user_status(db: Session, user_id: int, status: UserStatus) -> bool:
        """Update user status."""
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.status = status
                user.updated_at = datetime.utcnow()
                db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating user status: {e}")
            db.rollback()
            return False

    @staticmethod
    def complete_user_verification(db: Session, user_id: int) -> bool:
        """Mark user verification as completed."""
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.verification_completed = True
                user.captcha_completed = True
                user.channels_joined = True
                user.status = UserStatus.ACTIVE
                user.updated_at = datetime.utcnow()
                db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error completing user verification: {e}")
            db.rollback()
            return False

    @staticmethod
    def add_earnings(db: Session, user_id: int, amount: float) -> bool:
        """Add earnings to user balance."""
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.balance += amount
                user.total_earnings += amount
                user.updated_at = datetime.utcnow()
                db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error adding earnings: {e}")
            db.rollback()
            return False

    @staticmethod
    def deduct_balance(db: Session, user_id: int, amount: float) -> bool:
        """Deduct amount from user balance."""
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user and user.balance >= amount:
                user.balance -= amount
                user.updated_at = datetime.utcnow()
                db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deducting balance: {e}")
            db.rollback()
            return False

class TelegramAccountService:
    @staticmethod
    def create_account(db: Session, seller_id: int, phone_number: str, 
                      country_code: str = None, session_string: str = None) -> TelegramAccount:
        """Create a new Telegram account entry."""
        try:
            account = TelegramAccount(
                seller_id=seller_id,
                phone_number=phone_number,
                country_code=country_code,
                session_string=session_string,
                status=AccountStatus.AVAILABLE
            )
            db.add(account)
            db.commit()
            db.refresh(account)
            return account
        except Exception as e:
            logger.error(f"Error creating account: {e}")
            db.rollback()
            raise

    @staticmethod
    def get_user_accounts(db: Session, user_id: int) -> List[TelegramAccount]:
        """Get all accounts for a user."""
        try:
            return db.query(TelegramAccount).filter(TelegramAccount.seller_id == user_id).all()
        except Exception as e:
            logger.error(f"Error getting user accounts: {e}")
            return []

    @staticmethod
    def get_user_accounts_count(db: Session, user_id: int) -> int:
        """Get count of user's accounts."""
        try:
            return db.query(TelegramAccount).filter(TelegramAccount.seller_id == user_id).count()
        except Exception as e:
            logger.error(f"Error getting accounts count: {e}")
            return 0

    @staticmethod
    def get_available_accounts(db: Session, user_id: int) -> List[TelegramAccount]:
        """Get user's available accounts for selling."""
        try:
            return db.query(TelegramAccount).filter(
                and_(
                    TelegramAccount.seller_id == user_id,
                    TelegramAccount.status == AccountStatus.AVAILABLE
                )
            ).all()
        except Exception as e:
            logger.error(f"Error getting available accounts: {e}")
            return []

    @staticmethod
    def update_account_status(db: Session, account_id: int, status: AccountStatus) -> bool:
        """Update account status."""
        try:
            account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id).first()
            if account:
                account.status = status
                account.updated_at = datetime.utcnow()
                db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating account status: {e}")
            db.rollback()
            return False

    @staticmethod
    def set_account_hold(db: Session, account_id: int, hold_hours: int = 24) -> bool:
        """Set account on hold for multi-device detection."""
        try:
            account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id).first()
            if account:
                account.status = AccountStatus.TWENTY_FOUR_HOUR_HOLD
                account.hold_until = datetime.utcnow() + timedelta(hours=hold_hours)
                account.multi_device_detected = True
                account.updated_at = datetime.utcnow()
                db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error setting account hold: {e}")
            db.rollback()
            return False

class AccountSaleService:
    @staticmethod
    def create_sale(db: Session, account_id: int, seller_id: int, sale_price: float) -> AccountSale:
        """Create a new account sale."""
        try:
            sale = AccountSale(
                account_id=account_id,
                seller_id=seller_id,
                sale_price=sale_price,
                status=SaleStatus.INITIATED
            )
            db.add(sale)
            db.commit()
            db.refresh(sale)
            return sale
        except Exception as e:
            logger.error(f"Error creating sale: {e}")
            db.rollback()
            raise

    @staticmethod
    def update_sale_progress(db: Session, sale_id: int, **kwargs) -> bool:
        """Update sale configuration progress."""
        try:
            sale = db.query(AccountSale).filter(AccountSale.id == sale_id).first()
            if sale:
                for key, value in kwargs.items():
                    if hasattr(sale, key):
                        setattr(sale, key, value)
                sale.updated_at = datetime.utcnow()
                db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating sale progress: {e}")
            db.rollback()
            return False

    @staticmethod
    def complete_sale(db: Session, sale_id: int, buyer_telegram_id: int = None) -> bool:
        """Mark sale as completed."""
        try:
            sale = db.query(AccountSale).filter(AccountSale.id == sale_id).first()
            if sale:
                sale.status = SaleStatus.COMPLETED
                sale.buyer_telegram_id = buyer_telegram_id
                sale.sale_completed_at = datetime.utcnow()
                sale.updated_at = datetime.utcnow()
                
                # Update account status
                account = db.query(TelegramAccount).filter(TelegramAccount.id == sale.account_id).first()
                if account:
                    account.status = AccountStatus.SOLD
                    account.sold_at = datetime.utcnow()
                    account.sale_price = sale.sale_price
                
                # Update seller statistics
                seller = db.query(User).filter(User.id == sale.seller_id).first()
                if seller:
                    seller.total_accounts_sold += 1
                    UserService.add_earnings(db, seller.id, sale.sale_price)
                
                db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error completing sale: {e}")
            db.rollback()
            return False

class WithdrawalService:
    @staticmethod
    def create_withdrawal(db: Session, user_id: int, amount: float, currency: str,
                         withdrawal_address: str, withdrawal_method: str) -> Withdrawal:
        """Create a new withdrawal request."""
        try:
            withdrawal = Withdrawal(
                user_id=user_id,
                amount=amount,
                currency=currency,
                withdrawal_address=withdrawal_address,
                withdrawal_method=withdrawal_method,
                status=WithdrawalStatus.PENDING
            )
            db.add(withdrawal)
            db.commit()
            db.refresh(withdrawal)
            return withdrawal
        except Exception as e:
            logger.error(f"Error creating withdrawal: {e}")
            db.rollback()
            raise

    @staticmethod
    def get_user_withdrawals(db: Session, user_id: int, limit: int = 10) -> List[Withdrawal]:
        """Get user's withdrawal history."""
        try:
            return db.query(Withdrawal).filter(
                Withdrawal.user_id == user_id
            ).order_by(desc(Withdrawal.created_at)).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting user withdrawals: {e}")
            return []

    @staticmethod
    def get_pending_withdrawals(db: Session, leader_id: int = None) -> List[Withdrawal]:
        """Get pending withdrawals for leader review."""
        try:
            query = db.query(Withdrawal).filter(Withdrawal.status == WithdrawalStatus.PENDING)
            if leader_id:
                query = query.filter(Withdrawal.assigned_leader_id == leader_id)
            return query.order_by(Withdrawal.created_at).all()
        except Exception as e:
            logger.error(f"Error getting pending withdrawals: {e}")
            return []

    @staticmethod
    def update_withdrawal_status(db: Session, withdrawal_id: int, status: WithdrawalStatus,
                                leader_notes: str = None, payment_proof: str = None) -> bool:
        """Update withdrawal status."""
        try:
            withdrawal = db.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).first()
            if withdrawal:
                withdrawal.status = status
                if leader_notes:
                    withdrawal.leader_notes = leader_notes
                if payment_proof:
                    withdrawal.payment_proof = payment_proof
                if status in [WithdrawalStatus.COMPLETED, WithdrawalStatus.REJECTED]:
                    withdrawal.processed_at = datetime.utcnow()
                withdrawal.updated_at = datetime.utcnow()
                db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating withdrawal status: {e}")
            db.rollback()
            return False

class SystemSettingsService:
    @staticmethod
    def get_setting(db: Session, key: str, default_value: str = None) -> str:
        """Get system setting value."""
        try:
            setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
            return setting.value if setting else default_value
        except Exception as e:
            logger.error(f"Error getting setting {key}: {e}")
            return default_value

    @staticmethod
    def set_setting(db: Session, key: str, value: str, description: str = None) -> bool:
        """Set system setting value."""
        try:
            setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
            if setting:
                setting.value = value
                if description:
                    setting.description = description
                setting.updated_at = datetime.utcnow()
            else:
                setting = SystemSettings(
                    key=key,
                    value=value,
                    description=description
                )
                db.add(setting)
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Error setting {key}: {e}")
            db.rollback()
            return False

class ActivityLogService:
    @staticmethod
    def log_action(db: Session, user_id: int, action_type: str, description: str,
                  extra_data: str = None, ip_address: str = None) -> bool:
        """Log user activity."""
        try:
            log = ActivityLog(
                user_id=user_id,
                action_type=action_type,
                description=description,
                extra_data=extra_data,
                ip_address=ip_address
            )
            db.add(log)
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Error logging activity: {e}")
            db.rollback()
            return False

    @staticmethod
    def get_user_activity(db: Session, user_id: int, limit: int = 50) -> List[ActivityLog]:
        """Get user activity logs."""
        try:
            return db.query(ActivityLog).filter(
                ActivityLog.user_id == user_id
            ).order_by(desc(ActivityLog.created_at)).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting user activity: {e}")
            return []

class VerificationService:
    @staticmethod
    def create_verification_task(db: Session, task_type: str, task_name: str,
                               task_description: str, task_data: str = None) -> VerificationTask:
        """Create a verification task."""
        try:
            task = VerificationTask(
                task_type=task_type,
                task_name=task_name,
                task_description=task_description,
                task_data=task_data
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            return task
        except Exception as e:
            logger.error(f"Error creating verification task: {e}")
            db.rollback()
            raise

    @staticmethod
    def get_active_tasks(db: Session) -> List[VerificationTask]:
        """Get all active verification tasks."""
        try:
            return db.query(VerificationTask).filter(
                VerificationTask.is_active == True
            ).order_by(VerificationTask.order_priority).all()
        except Exception as e:
            logger.error(f"Error getting active tasks: {e}")
            return []

    @staticmethod
    def complete_user_task(db: Session, user_id: int, task_id: int, 
                          completion_data: str = None) -> bool:
        """Mark user task as completed."""
        try:
            verification = db.query(UserVerification).filter(
                and_(
                    UserVerification.user_id == user_id,
                    UserVerification.task_id == task_id
                )
            ).first()
            
            if verification:
                verification.completed = True
                verification.completion_data = completion_data
                verification.completed_at = datetime.utcnow()
            else:
                verification = UserVerification(
                    user_id=user_id,
                    task_id=task_id,
                    completed=True,
                    completion_data=completion_data,
                    completed_at=datetime.utcnow()
                )
                db.add(verification)
            
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Error completing user task: {e}")
            db.rollback()
            return False

    @staticmethod
    def check_user_verification_status(db: Session, user_id: int) -> Dict[str, Any]:
        """Check user's verification progress."""
        try:
            active_tasks = VerificationService.get_active_tasks(db)
            completed_tasks = db.query(UserVerification).filter(
                and_(
                    UserVerification.user_id == user_id,
                    UserVerification.completed == True
                )
            ).all()
            
            completed_task_ids = [t.task_id for t in completed_tasks]
            pending_tasks = [t for t in active_tasks if t.id not in completed_task_ids]
            
            return {
                'total_tasks': len(active_tasks),
                'completed_tasks': len(completed_tasks),
                'pending_tasks': len(pending_tasks),
                'is_fully_verified': len(pending_tasks) == 0,
                'completion_percentage': (len(completed_tasks) / max(len(active_tasks), 1)) * 100
            }
        except Exception as e:
            logger.error(f"Error checking verification status: {e}")
            return {
                'total_tasks': 0,
                'completed_tasks': 0,
                'pending_tasks': 0,
                'is_fully_verified': False,
                'completion_percentage': 0
            }