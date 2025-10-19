"""
Sale Log Operations
Database operations for AccountSaleLog management and admin approval system
"""
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from datetime import datetime
import json

from database.models import AccountSaleLog, TelegramAccount, User, SaleLogStatus, AccountStatus
from database.operations import ActivityLogService

logger = logging.getLogger(__name__)

class SaleLogService:
    """Service for managing account sale logs and admin approvals"""
    
    @staticmethod
    def create_sale_log(
        db: Session,
        account_id: int,
        seller_id: int,
        sale_price: float,
        buyer_telegram_id: Optional[int] = None
    ) -> Optional[AccountSaleLog]:
        """
        Create a new sale log entry when an account sale is initiated.
        
        Args:
            db: Database session
            account_id: ID of the account being sold
            seller_id: ID of the seller (User)
            sale_price: Price of the sale
            buyer_telegram_id: Optional buyer's telegram ID
        
        Returns:
            AccountSaleLog object or None if failed
        """
        try:
            # Get account and seller details
            account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id).first()
            seller = db.query(User).filter(User.id == seller_id).first()
            
            if not account or not seller:
                logger.error(f"Account {account_id} or Seller {seller_id} not found")
                return None
            
            # Create sale log with snapshot of current state
            sale_log = AccountSaleLog(
                account_id=account_id,
                seller_id=seller_id,
                sale_price=sale_price,
                status=SaleLogStatus.PENDING,
                
                # Account snapshot
                account_phone=account.phone_number,
                account_original_name=account.original_account_name,
                account_original_username=account.original_username,
                account_is_frozen=(account.status == AccountStatus.FROZEN),
                account_freeze_reason=account.freeze_reason if account.status == AccountStatus.FROZEN else None,
                
                # Seller info
                seller_telegram_id=seller.telegram_user_id,
                seller_username=seller.username,
                seller_name=f"{seller.first_name or ''} {seller.last_name or ''}".strip(),
                
                # Buyer info
                buyer_telegram_id=buyer_telegram_id,
                
                sale_initiated_at=datetime.utcnow()
            )
            
            db.add(sale_log)
            db.commit()
            db.refresh(sale_log)
            
            # Log the creation
            ActivityLogService.log_action(
                db=db,
                user_id=seller_id,
                action_type="SALE_LOG_CREATED",
                description=f"Sale log created for account {account.phone_number}",
                extra_data=json.dumps({
                    'sale_log_id': sale_log.id,
                    'account_id': account_id,
                    'account_phone': account.phone_number,
                    'sale_price': sale_price,
                    'is_frozen': sale_log.account_is_frozen
                })
            )
            
            logger.info(f"Sale log {sale_log.id} created for account {account_id} by seller {seller_id}")
            
            return sale_log
            
        except Exception as e:
            logger.error(f"Error creating sale log: {e}")
            db.rollback()
            return None
    
    @staticmethod
    def get_pending_sale_logs(db: Session, limit: int = 50) -> List[AccountSaleLog]:
        """
        Get all pending sale logs awaiting admin review.
        
        Args:
            db: Database session
            limit: Maximum number of logs to return
        
        Returns:
            List of pending AccountSaleLog objects
        """
        try:
            pending_logs = db.query(AccountSaleLog).filter(
                AccountSaleLog.status == SaleLogStatus.PENDING
            ).order_by(AccountSaleLog.sale_initiated_at.asc()).limit(limit).all()
            
            return pending_logs
            
        except Exception as e:
            logger.error(f"Error getting pending sale logs: {e}")
            return []
    
    @staticmethod
    def get_sale_logs_by_status(
        db: Session,
        status: SaleLogStatus,
        limit: int = 50
    ) -> List[AccountSaleLog]:
        """
        Get sale logs filtered by status.
        
        Args:
            db: Database session
            status: SaleLogStatus to filter by
            limit: Maximum number of logs to return
        
        Returns:
            List of AccountSaleLog objects
        """
        try:
            logs = db.query(AccountSaleLog).filter(
                AccountSaleLog.status == status
            ).order_by(AccountSaleLog.created_at.desc()).limit(limit).all()
            
            return logs
            
        except Exception as e:
            logger.error(f"Error getting sale logs by status: {e}")
            return []
    
    @staticmethod
    def get_frozen_account_sale_logs(db: Session, limit: int = 50) -> List[AccountSaleLog]:
        """
        Get all sale logs for frozen accounts.
        
        Args:
            db: Database session
            limit: Maximum number of logs to return
        
        Returns:
            List of AccountSaleLog objects for frozen accounts
        """
        try:
            frozen_logs = db.query(AccountSaleLog).filter(
                AccountSaleLog.account_is_frozen == True
            ).order_by(AccountSaleLog.created_at.desc()).limit(limit).all()
            
            return frozen_logs
            
        except Exception as e:
            logger.error(f"Error getting frozen account sale logs: {e}")
            return []
    
    @staticmethod
    def get_user_sale_history(
        db: Session,
        user_id: int,
        limit: int = 20
    ) -> List[AccountSaleLog]:
        """
        Get sale history for a specific user.
        
        Args:
            db: Database session
            user_id: User ID (seller)
            limit: Maximum number of logs to return
        
        Returns:
            List of AccountSaleLog objects for the user
        """
        try:
            user_logs = db.query(AccountSaleLog).filter(
                AccountSaleLog.seller_id == user_id
            ).order_by(AccountSaleLog.created_at.desc()).limit(limit).all()
            
            return user_logs
            
        except Exception as e:
            logger.error(f"Error getting user sale history: {e}")
            return []
    
    @staticmethod
    def update_sale_log_status(
        db: Session,
        sale_log_id: int,
        new_status: SaleLogStatus,
        admin_id: Optional[int] = None,
        notes: Optional[str] = None,
        rejection_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update the status of a sale log (approve/reject).
        
        Args:
            db: Database session
            sale_log_id: ID of the sale log to update
            new_status: New SaleLogStatus
            admin_id: ID of admin performing the action
            notes: Optional admin notes
            rejection_reason: Reason for rejection (if rejecting)
        
        Returns:
            Dict with success status and message
        """
        try:
            sale_log = db.query(AccountSaleLog).filter(AccountSaleLog.id == sale_log_id).first()
            if not sale_log:
                return {
                    'success': False,
                    'error': 'sale_log_not_found',
                    'message': f'Sale log {sale_log_id} not found'
                }
            
            # Check if account is frozen when approving
            if new_status == SaleLogStatus.ADMIN_APPROVED and sale_log.account_is_frozen:
                return {
                    'success': False,
                    'error': 'account_frozen',
                    'message': f'Cannot approve sale for frozen account {sale_log.account_phone}. Reason: {sale_log.account_freeze_reason}'
                }
            
            # Update sale log
            old_status = sale_log.status
            sale_log.status = new_status
            sale_log.reviewed_by_admin_id = admin_id
            sale_log.admin_action_notes = notes
            sale_log.admin_action_timestamp = datetime.utcnow()
            sale_log.updated_at = datetime.utcnow()
            
            if new_status == SaleLogStatus.ADMIN_REJECTED:
                sale_log.rejection_reason = rejection_reason
            
            if new_status in [SaleLogStatus.COMPLETED, SaleLogStatus.ADMIN_APPROVED]:
                sale_log.sale_completed_at = datetime.utcnow()
            
            # Get admin info for logging
            admin = db.query(User).filter(User.id == admin_id).first() if admin_id else None
            admin_name = admin.first_name or admin.username if admin else "System"
            
            # Log the action
            action_type = f"SALE_LOG_{new_status.value}"
            ActivityLogService.log_action(
                db=db,
                user_id=admin_id or sale_log.seller_id,
                action_type=action_type,
                description=f"Sale log {sale_log_id} status changed from {old_status.value} to {new_status.value} by {admin_name}",
                extra_data=json.dumps({
                    'sale_log_id': sale_log_id,
                    'account_id': sale_log.account_id,
                    'account_phone': sale_log.account_phone,
                    'old_status': old_status.value,
                    'new_status': new_status.value,
                    'admin_id': admin_id,
                    'admin_name': admin_name,
                    'notes': notes,
                    'rejection_reason': rejection_reason
                })
            )
            
            db.commit()
            
            logger.info(f"Sale log {sale_log_id} updated to {new_status.value} by admin {admin_id}")
            
            return {
                'success': True,
                'sale_log_id': sale_log_id,
                'old_status': old_status.value,
                'new_status': new_status.value,
                'admin_name': admin_name,
                'message': f'Sale log successfully updated to {new_status.value}'
            }
            
        except Exception as e:
            logger.error(f"Error updating sale log {sale_log_id}: {e}")
            db.rollback()
            return {
                'success': False,
                'error': 'update_failed',
                'message': f'Failed to update sale log: {str(e)}'
            }
    
    @staticmethod
    def get_sale_log_by_id(db: Session, sale_log_id: int) -> Optional[AccountSaleLog]:
        """
        Get a specific sale log by ID.
        
        Args:
            db: Database session
            sale_log_id: ID of the sale log
        
        Returns:
            AccountSaleLog object or None
        """
        try:
            return db.query(AccountSaleLog).filter(AccountSaleLog.id == sale_log_id).first()
        except Exception as e:
            logger.error(f"Error getting sale log {sale_log_id}: {e}")
            return None
    
    @staticmethod
    def search_sale_logs(
        db: Session,
        search_query: Optional[str] = None,
        status: Optional[SaleLogStatus] = None,
        is_frozen: Optional[bool] = None,
        limit: int = 50
    ) -> List[AccountSaleLog]:
        """
        Search sale logs with filters.
        
        Args:
            db: Database session
            search_query: Search in phone, username, seller name
            status: Filter by SaleLogStatus
            is_frozen: Filter by freeze status
            limit: Maximum number of results
        
        Returns:
            List of matching AccountSaleLog objects
        """
        try:
            query = db.query(AccountSaleLog)
            
            # Apply filters
            if search_query:
                query = query.filter(
                    or_(
                        AccountSaleLog.account_phone.ilike(f'%{search_query}%'),
                        AccountSaleLog.seller_username.ilike(f'%{search_query}%'),
                        AccountSaleLog.seller_name.ilike(f'%{search_query}%')
                    )
                )
            
            if status:
                query = query.filter(AccountSaleLog.status == status)
            
            if is_frozen is not None:
                query = query.filter(AccountSaleLog.account_is_frozen == is_frozen)
            
            results = query.order_by(AccountSaleLog.created_at.desc()).limit(limit).all()
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching sale logs: {e}")
            return []
    
    @staticmethod
    def get_sale_log_statistics(db: Session) -> Dict[str, Any]:
        """
        Get statistics about sale logs.
        
        Returns:
            Dict with various statistics
        """
        try:
            total = db.query(AccountSaleLog).count()
            pending = db.query(AccountSaleLog).filter(AccountSaleLog.status == SaleLogStatus.PENDING).count()
            approved = db.query(AccountSaleLog).filter(AccountSaleLog.status == SaleLogStatus.ADMIN_APPROVED).count()
            rejected = db.query(AccountSaleLog).filter(AccountSaleLog.status == SaleLogStatus.ADMIN_REJECTED).count()
            completed = db.query(AccountSaleLog).filter(AccountSaleLog.status == SaleLogStatus.COMPLETED).count()
            frozen = db.query(AccountSaleLog).filter(AccountSaleLog.account_is_frozen == True).count()
            
            return {
                'total_logs': total,
                'pending': pending,
                'approved': approved,
                'rejected': rejected,
                'completed': completed,
                'frozen_accounts': frozen,
                'approval_rate': (approved / max(total, 1)) * 100
            }

        except Exception as e:
            logger.error(f"Error getting sale log statistics: {e}")
            return {}
    
    @staticmethod
    def approve_sale_log(db: Session, sale_log_id: int, admin_id: int, notes: str = "") -> Dict[str, Any]:
        """
        Approve a sale log (admin action) with freeze check
        
        Args:
            db: Database session
            sale_log_id: ID of the sale log to approve
            admin_id: ID of the admin approving
            notes: Optional admin notes
            
        Returns:
            Dict with success status, error details, and account info
        """
        try:
            sale_log = db.query(AccountSaleLog).filter(AccountSaleLog.id == sale_log_id).first()
            if not sale_log:
                return {'success': False, 'error': 'not_found', 'message': 'Sale log not found'}
            
            # CRITICAL: Check if account is frozen
            if sale_log.account_is_frozen:
                logger.warning(f"Cannot approve sale {sale_log_id}: account is frozen")
                return {
                    'success': False,
                    'error': 'account_frozen',
                    'blocked': True,
                    'account_phone': sale_log.account_phone,
                    'freeze_reason': sale_log.account_freeze_reason or 'Unknown reason',
                    'message': 'Account is frozen - cannot approve sale'
                }
            
            # Approve the sale
            success = SaleLogService.update_sale_log_status(
                db, sale_log_id, SaleLogStatus.ADMIN_APPROVED, admin_id, notes
            )
            
            if success:
                # Get admin info
                from database.operations import UserService
                admin = UserService.get_user_by_id(db, admin_id)
                admin_name = admin.first_name or admin.username if admin else 'Admin'
                
                return {
                    'success': True,
                    'account_phone': sale_log.account_phone,
                    'approved_by': admin_name,
                    'notes': notes
                }
            else:
                return {'success': False, 'error': 'update_failed', 'message': 'Failed to update sale status'}
                
        except Exception as e:
            logger.error(f"Error approving sale: {e}")
            return {'success': False, 'error': 'exception', 'message': str(e)}
    
    @staticmethod
    def reject_sale_log(db: Session, sale_log_id: int, admin_id: int, rejection_reason: str) -> bool:
        """
        Reject a sale log (admin action)
        
        Args:
            db: Database session
            sale_log_id: ID of the sale log to reject
            admin_id: ID of the admin rejecting
            rejection_reason: Reason for rejection
            
        Returns:
            bool: True if rejection was successful
        """
        try:
            sale_log = db.query(AccountSaleLog).filter(AccountSaleLog.id == sale_log_id).first()
            if not sale_log:
                logger.error(f"Sale log {sale_log_id} not found")
                return False
            
            # Update sale log with rejection
            sale_log.log_status = SaleLogStatus.ADMIN_REJECTED
            sale_log.reviewed_by_admin_id = admin_id
            sale_log.review_timestamp = datetime.utcnow()
            sale_log.review_notes = rejection_reason
            sale_log.updated_at = datetime.utcnow()
            
            db.commit()
            logger.info(f"Sale log {sale_log_id} rejected by admin {admin_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error rejecting sale: {e}")
            db.rollback()
            return False

# Global instance
sale_log_service = SaleLogService()
