"""
Account Management Service
Handles freezing/unfreezing accounts, checking freeze status, and logging actions
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from database.models import TelegramAccount, User, AccountStatus, ActivityLog
from database import get_db_session, close_db_session
from database.operations import ActivityLogService
import json

logger = logging.getLogger(__name__)

class AccountManagementService:
    """Service for managing account freeze/unfreeze operations"""
    
    @staticmethod
    def freeze_account(
        db: Session,
        account_id: int,
        reason: str,
        admin_id: int,
        duration_hours: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Freeze an account with a specific reason and duration.
        
        Args:
            db: Database session
            account_id: ID of the account to freeze
            reason: Reason for freezing
            admin_id: ID of the admin performing the freeze
            duration_hours: Duration in hours (None = indefinite)
        
        Returns:
            Dict with success status and message
        """
        try:
            account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id).first()
            if not account:
                return {
                    'success': False,
                    'error': 'account_not_found',
                    'message': f'Account with ID {account_id} not found'
                }
            
            # Check if already frozen
            if account.status == AccountStatus.FROZEN:
                return {
                    'success': False,
                    'error': 'already_frozen',
                    'message': f'Account {account.phone_number} is already frozen'
                }
            
            # Freeze the account
            account.status = AccountStatus.FROZEN
            account.can_be_sold = False
            account.freeze_reason = reason
            account.frozen_by_admin_id = admin_id
            account.freeze_timestamp = datetime.utcnow()
            account.freeze_duration_hours = duration_hours
            account.updated_at = datetime.utcnow()
            
            # Get admin info for logging
            admin = db.query(User).filter(User.id == admin_id).first()
            admin_name = admin.first_name or admin.username or f"Admin #{admin_id}"
            
            # Log the freeze action
            ActivityLogService.log_action(
                db=db,
                user_id=admin_id,
                action_type="ACCOUNT_FROZEN",
                description=f"Account {account.phone_number} frozen by {admin_name}",
                extra_data=json.dumps({
                    'account_id': account_id,
                    'account_phone': account.phone_number,
                    'reason': reason,
                    'duration_hours': duration_hours,
                    'admin_id': admin_id,
                    'admin_name': admin_name
                })
            )
            
            db.commit()
            
            logger.info(f"Account {account_id} ({account.phone_number}) frozen by admin {admin_id}")
            
            expiry_text = f"{duration_hours} hours" if duration_hours else "indefinite"
            return {
                'success': True,
                'account_id': account_id,
                'account_phone': account.phone_number,
                'reason': reason,
                'duration': expiry_text,
                'frozen_at': account.freeze_timestamp.isoformat(),
                'message': f'Account {account.phone_number} successfully frozen for {expiry_text}'
            }
            
        except Exception as e:
            logger.error(f"Error freezing account {account_id}: {e}")
            db.rollback()
            return {
                'success': False,
                'error': 'freeze_failed',
                'message': f'Failed to freeze account: {str(e)}'
            }
    
    @staticmethod
    def unfreeze_account(
        db: Session,
        account_id: int,
        admin_id: int,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Unfreeze an account.
        
        Args:
            db: Database session
            account_id: ID of the account to unfreeze
            admin_id: ID of the admin performing the unfreeze
            notes: Optional notes about the unfreeze
        
        Returns:
            Dict with success status and message
        """
        try:
            account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id).first()
            if not account:
                return {
                    'success': False,
                    'error': 'account_not_found',
                    'message': f'Account with ID {account_id} not found'
                }
            
            # Check if frozen
            if account.status != AccountStatus.FROZEN:
                return {
                    'success': False,
                    'error': 'not_frozen',
                    'message': f'Account {account.phone_number} is not frozen'
                }
            
            # Store freeze history before unfreezing
            freeze_history = {
                'freeze_reason': account.freeze_reason,
                'frozen_by': account.frozen_by_admin_id,
                'freeze_timestamp': account.freeze_timestamp.isoformat() if account.freeze_timestamp else None,
                'freeze_duration': account.freeze_duration_hours,
                'unfrozen_by': admin_id,
                'unfreeze_notes': notes
            }
            
            # Unfreeze the account
            account.status = AccountStatus.AVAILABLE
            account.can_be_sold = True
            account.freeze_reason = None
            account.frozen_by_admin_id = None
            account.freeze_timestamp = None
            account.freeze_duration_hours = None
            account.updated_at = datetime.utcnow()
            
            # Get admin info for logging
            admin = db.query(User).filter(User.id == admin_id).first()
            admin_name = admin.first_name or admin.username or f"Admin #{admin_id}"
            
            # Log the unfreeze action
            ActivityLogService.log_action(
                db=db,
                user_id=admin_id,
                action_type="ACCOUNT_UNFROZEN",
                description=f"Account {account.phone_number} unfrozen by {admin_name}",
                extra_data=json.dumps({
                    'account_id': account_id,
                    'account_phone': account.phone_number,
                    'admin_id': admin_id,
                    'admin_name': admin_name,
                    'notes': notes,
                    'freeze_history': freeze_history
                })
            )
            
            db.commit()
            
            logger.info(f"Account {account_id} ({account.phone_number}) unfrozen by admin {admin_id}")
            
            return {
                'success': True,
                'account_id': account_id,
                'account_phone': account.phone_number,
                'unfrozen_at': datetime.utcnow().isoformat(),
                'message': f'Account {account.phone_number} successfully unfrozen'
            }
            
        except Exception as e:
            logger.error(f"Error unfreezing account {account_id}: {e}")
            db.rollback()
            return {
                'success': False,
                'error': 'unfreeze_failed',
                'message': f'Failed to unfreeze account: {str(e)}'
            }
    
    @staticmethod
    def check_freeze_status(db: Session, account_id: int) -> Dict[str, Any]:
        """
        Check if an account is frozen and get freeze details.
        
        Args:
            db: Database session
            account_id: ID of the account to check
        
        Returns:
            Dict with freeze status and details
        """
        try:
            account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id).first()
            if not account:
                return {
                    'success': False,
                    'error': 'account_not_found',
                    'message': f'Account with ID {account_id} not found'
                }
            
            is_frozen = account.status == AccountStatus.FROZEN
            
            result = {
                'success': True,
                'account_id': account_id,
                'account_phone': account.phone_number,
                'is_frozen': is_frozen,
                'can_be_sold': account.can_be_sold,
                'status': account.status.value
            }
            
            if is_frozen:
                # Calculate remaining freeze time
                remaining_hours = None
                if account.freeze_duration_hours and account.freeze_timestamp:
                    freeze_end = account.freeze_timestamp + timedelta(hours=account.freeze_duration_hours)
                    remaining = freeze_end - datetime.utcnow()
                    remaining_hours = max(0, remaining.total_seconds() / 3600)
                
                result.update({
                    'freeze_reason': account.freeze_reason,
                    'frozen_by_admin_id': account.frozen_by_admin_id,
                    'freeze_timestamp': account.freeze_timestamp.isoformat() if account.freeze_timestamp else None,
                    'freeze_duration_hours': account.freeze_duration_hours,
                    'remaining_hours': remaining_hours,
                    'is_indefinite': account.freeze_duration_hours is None
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error checking freeze status for account {account_id}: {e}")
            return {
                'success': False,
                'error': 'check_failed',
                'message': f'Failed to check freeze status: {str(e)}'
            }
    
    @staticmethod
    def get_frozen_accounts(db: Session, limit: int = 50) -> List[TelegramAccount]:
        """
        Get all currently frozen accounts.
        
        Args:
            db: Database session
            limit: Maximum number of accounts to return
        
        Returns:
            List of frozen TelegramAccount objects
        """
        try:
            frozen_accounts = db.query(TelegramAccount).filter(
                TelegramAccount.status == AccountStatus.FROZEN
            ).order_by(TelegramAccount.freeze_timestamp.desc()).limit(limit).all()
            
            return frozen_accounts
            
        except Exception as e:
            logger.error(f"Error getting frozen accounts: {e}")
            return []
    
    @staticmethod
    def check_and_release_expired_freezes(db: Session) -> Dict[str, Any]:
        """
        Check for accounts with expired freeze durations and automatically release them.
        
        Args:
            db: Database session
        
        Returns:
            Dict with count of released accounts
        """
        released_count = 0
        errors = []
        
        try:
            # Find accounts that are frozen with a duration that has expired
            frozen_accounts = db.query(TelegramAccount).filter(
                TelegramAccount.status == AccountStatus.FROZEN,
                TelegramAccount.freeze_duration_hours.isnot(None),
                TelegramAccount.freeze_timestamp.isnot(None)
            ).all()
            
            for account in frozen_accounts:
                try:
                    freeze_end = account.freeze_timestamp + timedelta(hours=account.freeze_duration_hours)
                    
                    if datetime.utcnow() >= freeze_end:
                        # Freeze period expired, release account
                        account.status = AccountStatus.AVAILABLE
                        account.can_be_sold = True
                        old_reason = account.freeze_reason
                        account.freeze_reason = None
                        account.frozen_by_admin_id = None
                        account.freeze_timestamp = None
                        account.freeze_duration_hours = None
                        account.updated_at = datetime.utcnow()
                        
                        # Log auto-release
                        ActivityLogService.log_action(
                            db=db,
                            user_id=account.seller_id,
                            action_type="ACCOUNT_AUTO_UNFROZEN",
                            description=f"Account {account.phone_number} automatically unfrozen after freeze period expired",
                            extra_data=json.dumps({
                                'account_id': account.id,
                                'account_phone': account.phone_number,
                                'previous_freeze_reason': old_reason
                            })
                        )
                        
                        released_count += 1
                        logger.info(f"Auto-released account {account.id} ({account.phone_number}) after freeze expiry")
                        
                except Exception as e:
                    errors.append(f"Error releasing account {account.id}: {str(e)}")
                    logger.error(f"Error releasing account {account.id}: {e}")
            
            db.commit()
            
            return {
                'success': True,
                'released_count': released_count,
                'errors': errors
            }
            
        except Exception as e:
            logger.error(f"Error checking expired freezes: {e}")
            db.rollback()
            return {
                'success': False,
                'error': str(e),
                'released_count': 0,
                'errors': [str(e)]
            }

# Global instance
account_manager = AccountManagementService()
