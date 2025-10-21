sale_log_service = SaleLogService()                seller_username=seller.username,
sale_log_service = SaleLogService()
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

from database.models_extended import AccountSaleLog, SaleLogStatus
from database.models import User
from database.operations import ActivityLogService

logger = logging.getLogger(__name__)


class SaleLogService:
    """Service for operating on account sale logs (admin-facing operations)."""

    @staticmethod
    def get_pending_sale_logs(db: Session, include_frozen: bool = True, limit: int = 50) -> List[AccountSaleLog]:
        """Return pending sale logs. Optionally exclude frozen accounts."""
        try:
            query = db.query(AccountSaleLog).filter(AccountSaleLog.status == SaleLogStatus.PENDING)
            if not include_frozen:
                query = query.filter(AccountSaleLog.account_is_frozen == False)
            return query.order_by(AccountSaleLog.created_at.desc()).limit(limit).all()
        except Exception as e:
            logger.error(f"get_pending_sale_logs error: {e}")
            return []

    @staticmethod
    def get_sale_log_by_id(db: Session, sale_log_id: int) -> Optional[AccountSaleLog]:
        try:
            return db.query(AccountSaleLog).filter(AccountSaleLog.id == sale_log_id).first()
        except Exception as e:
            logger.error(f"get_sale_log_by_id error: {e}")
            return None

    @staticmethod
    def get_sale_log_statistics(db: Session) -> Dict[str, Any]:
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
            logger.error(f"get_sale_log_statistics error: {e}")
            return {}

    @staticmethod
    def update_sale_log_status(
        db: Session,
        sale_log_id: int,
        new_status: SaleLogStatus,
        admin_id: Optional[int] = None,
        notes: Optional[str] = None,
        rejection_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Core updater used by approve/reject flows.

        Returns a dict with at least {'success': bool, ...} like other services.
        """
        try:
            sale_log = db.query(AccountSaleLog).filter(AccountSaleLog.id == sale_log_id).first()
            if not sale_log:
                return {'success': False, 'error': 'not_found', 'message': 'Sale log not found'}

            # Prevent approving frozen accounts
            if new_status == SaleLogStatus.ADMIN_APPROVED and sale_log.account_is_frozen:
                return {'success': False, 'error': 'account_frozen', 'message': 'Account is frozen'}

            old_status = sale_log.status
            sale_log.status = new_status
            sale_log.reviewed_by_admin_id = admin_id
            sale_log.admin_action_notes = notes
            sale_log.admin_action_timestamp = datetime.utcnow()
            if new_status == SaleLogStatus.ADMIN_REJECTED and rejection_reason:
                sale_log.rejection_reason = rejection_reason
            if new_status in (SaleLogStatus.COMPLETED, SaleLogStatus.ADMIN_APPROVED):
                sale_log.sale_completed_at = datetime.utcnow()
            sale_log.updated_at = datetime.utcnow()

            # Get admin info for logging
            admin = db.query(User).filter(User.id == admin_id).first() if admin_id else None
            admin_name = (admin.first_name or admin.username) if admin else 'System'

            # Log the action to ActivityLogService (best-effort)
            try:
                ActivityLogService.log_action(
                    db=db,
                    user_id=admin_id or sale_log.seller_id,
                    action_type=f"SALE_LOG_{new_status.name}",
                    description=f"Sale log {sale_log_id} status changed from {getattr(old_status, 'name', str(old_status))} to {new_status.name} by {admin_name}",
                    extra_data=json.dumps({
                        'sale_log_id': sale_log_id,
                        'old_status': getattr(old_status, 'name', str(old_status)),
                        'new_status': new_status.name,
                        'admin_id': admin_id,
                        'admin_name': admin_name,
                        'notes': notes,
                        'rejection_reason': rejection_reason,
                    }),
                )
            except Exception:
                # Activity logging should not block the operation
                logger.exception("ActivityLogService logging failed for sale log update")

            db.commit()

            logger.info(f"Sale log {sale_log_id} updated from {old_status} to {new_status} by admin {admin_id}")
            return {'success': True, 'sale_log_id': sale_log_id, 'old_status': getattr(old_status, 'name', str(old_status)), 'new_status': new_status.name}

        except Exception as e:
            logger.exception(f"update_sale_log_status error for {sale_log_id}: {e}")
            try:
                db.rollback()
            except Exception:
                pass
            return {'success': False, 'error': 'exception', 'message': str(e)}

    def approve_sale_log(self, db: Session, sale_log_id: int, admin_id: int, notes: str = "") -> Dict[str, Any]:
        """Approve a sale log after performing freeze checks."""
        return self.update_sale_log_status(db, sale_log_id, SaleLogStatus.ADMIN_APPROVED, admin_id=admin_id, notes=notes)

    def reject_sale_log(self, db: Session, sale_log_id: int, admin_id: int, rejection_reason: str) -> bool:
        """Reject a sale log. Returns True on success, False otherwise."""
        result = self.update_sale_log_status(db, sale_log_id, SaleLogStatus.ADMIN_REJECTED, admin_id=admin_id, notes=None, rejection_reason=rejection_reason)
        return bool(result.get('success'))

    def search_sale_logs(
        self,
        db: Session,
        search_query: Optional[str] = None,
        status: Optional[SaleLogStatus] = None,
        is_frozen: Optional[bool] = None,
        limit: int = 50,
    ) -> List[AccountSaleLog]:
        try:
            query = db.query(AccountSaleLog)
            if search_query:
                # simple text search across few columns
                like_q = f"%{search_query}%"
                query = query.filter(
                    (AccountSaleLog.account_phone.ilike(like_q)) |
                    (AccountSaleLog.seller_username.ilike(like_q)) |
                    (AccountSaleLog.seller_name.ilike(like_q))
                )
            if status:
                query = query.filter(AccountSaleLog.status == status)
            if is_frozen is not None:
                query = query.filter(AccountSaleLog.account_is_frozen == is_frozen)
            return query.order_by(AccountSaleLog.created_at.desc()).limit(limit).all()
        except Exception as e:
            logger.exception(f"search_sale_logs error: {e}")
            return []


# Global instance used by handlers
sale_log_service = SaleLogService()

