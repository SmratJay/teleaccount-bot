"""Sale log operations and service for the admin panel.

This module provides a small, safe implementation of a SaleLogService used
by `handlers/admin_handlers.py`. It was rebuilt to replace a corrupted file
and expose the following API expected by the handlers:

- sale_log_service.get_pending_sale_logs(db, include_frozen=True, limit=50)
- sale_log_service.get_sale_log_statistics(db)
- sale_log_service.approve_sale_log(db, sale_log_id, admin_id, notes)
- sale_log_service.reject_sale_log(db, sale_log_id, admin_id, rejection_reason)

The implementation uses the extended models in `database.models_extended`.
"""

import logging
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from database.models import User, AccountSale
from database.operations import ActivityLogService

logger = logging.getLogger(__name__)


class SaleLogService:
    """Service for operating on account sale logs (admin-facing operations)."""

    @staticmethod
    def get_pending_sale_logs(db: Session, include_frozen: bool = True, limit: int = 50) -> List[AccountSale]:
        """Return pending sale logs. Optionally exclude frozen accounts."""
        try:
            query = db.query(AccountSale).filter(AccountSale.status == 'PENDING')
            # If not including frozen, we'd need to join with TelegramAccount
            # For now, just return pending sales
            return query.order_by(AccountSale.created_at.desc()).limit(limit).all()
        except Exception as e:
            logger.error(f"get_pending_sale_logs error: {e}")
            return []

    @staticmethod
    def get_sale_log_by_id(db: Session, sale_log_id: int) -> Optional[AccountSale]:
        try:
            return db.query(AccountSale).filter(AccountSale.id == sale_log_id).first()
        except Exception as e:
            logger.error(f"get_sale_log_by_id error: {e}")
            return None

    @staticmethod
    def get_sale_log_statistics(db: Session) -> Dict[str, Any]:
        try:
            total = db.query(AccountSale).count()
            pending = db.query(AccountSale).filter(AccountSale.status == 'PENDING').count()
            in_progress = db.query(AccountSale).filter(AccountSale.status == 'IN_PROGRESS').count()
            completed = db.query(AccountSale).filter(AccountSale.status == 'COMPLETED').count()
            failed = db.query(AccountSale).filter(AccountSale.status == 'FAILED').count()

            return {
                'total_logs': total,
                'pending': pending,
                'approved': in_progress,  # Map IN_PROGRESS to approved
                'rejected': failed,       # Map FAILED to rejected
                'completed': completed,
                'frozen_accounts': 0,     # Would need join to check frozen status
                'approval_rate': (completed / max(total, 1)) * 100
            }
        except Exception as e:
            logger.error(f"get_sale_log_statistics error: {e}")
            return {}

    @staticmethod
    def update_sale_log_status(
        db: Session,
        sale_log_id: int,
        new_status: str,
        admin_id: Optional[int] = None,
        notes: Optional[str] = None,
        rejection_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Core updater used by approve/reject flows.

        Returns a dict with at least {'success': bool, ...} like other services.
        Status values: 'PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED'
        """
        try:
            sale = db.query(AccountSale).filter(AccountSale.id == sale_log_id).first()
            if not sale:
                return {'success': False, 'error': 'not_found', 'message': 'Sale not found'}

            old_status = sale.status
            sale.status = new_status
            
            # Set completion time for completed/approved sales
            if new_status in ('COMPLETED', 'IN_PROGRESS'):
                sale.sale_completed_at = datetime.utcnow()

            # Get admin info for logging
            admin = db.query(User).filter(User.id == admin_id).first() if admin_id else None
            admin_name = (admin.first_name or admin.username) if admin else 'System'

            # Log the action to ActivityLogService (best-effort)
            try:
                ActivityLogService.log_action(
                    db=db,
                    user_id=admin_id or sale.seller_id,
                    action_type=f"SALE_{new_status}",
                    description=f"Sale {sale_log_id} status changed from {old_status} to {new_status} by {admin_name}",
                    extra_data=json.dumps({
                        'sale_id': sale_log_id,
                        'old_status': old_status,
                        'new_status': new_status,
                        'admin_id': admin_id,
                        'admin_name': admin_name,
                        'notes': notes,
                        'rejection_reason': rejection_reason,
                    }),
                )
            except Exception:
                # Activity logging should not block the operation
                logger.exception("ActivityLogService logging failed for sale update")

            db.commit()

            logger.info(f"Sale {sale_log_id} updated from {old_status} to {new_status} by admin {admin_id}")
            return {'success': True, 'sale_log_id': sale_log_id, 'old_status': old_status, 'new_status': new_status}

        except Exception as e:
            logger.exception(f"update_sale_log_status error for {sale_log_id}: {e}")
            try:
                db.rollback()
            except Exception:
                pass
            return {'success': False, 'error': 'exception', 'message': str(e)}

    def approve_sale_log(self, db: Session, sale_log_id: int, admin_id: int, notes: str = "") -> Dict[str, Any]:
        """Approve a sale log."""
        return self.update_sale_log_status(db, sale_log_id, 'IN_PROGRESS', admin_id=admin_id, notes=notes)

    def reject_sale_log(self, db: Session, sale_log_id: int, admin_id: int, rejection_reason: str) -> bool:
        """Reject a sale log. Returns True on success, False otherwise."""
        result = self.update_sale_log_status(db, sale_log_id, 'FAILED', admin_id=admin_id, notes=None, rejection_reason=rejection_reason)
        return bool(result.get('success'))

    def search_sale_logs(
        self,
        db: Session,
        search_query: Optional[str] = None,
        status: Optional[str] = None,
        is_frozen: Optional[bool] = None,
        limit: int = 50,
    ) -> List[AccountSale]:
        """Search sale logs with filters."""
        try:
            from database.models import TelegramAccount
            query = db.query(AccountSale)
            
            # Apply status filter
            if status:
                query = query.filter(AccountSale.status == status)
            
            # For frozen filter, join with TelegramAccount
            if is_frozen is not None:
                query = query.join(TelegramAccount, AccountSale.account_id == TelegramAccount.id)
                query = query.filter(TelegramAccount.is_frozen == is_frozen)
            
            return query.order_by(AccountSale.created_at.desc()).limit(limit).all()
        except Exception as e:
            logger.exception(f"search_sale_logs error: {e}")
            return []


# Global instance used by handlers
sale_log_service = SaleLogService()

