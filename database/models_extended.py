"""
Extended Database models for Telegram Account Selling Bot
Adds: AccountSaleLog model, extended freeze management fields
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .models import Base

class SaleLogStatus(enum.Enum):
    """Status for account sale logs requiring admin approval"""
    PENDING = "PENDING"              # Awaiting admin review
    ADMIN_APPROVED = "ADMIN_APPROVED"  # Admin approved the sale
    ADMIN_REJECTED = "ADMIN_REJECTED"  # Admin rejected the sale
    COMPLETED = "COMPLETED"          # Sale completed successfully
    CANCELLED = "CANCELLED"          # Sale cancelled by user

class AccountSaleLog(Base):
    """
    Comprehensive log of all account sales requiring admin approval.
    Tracks seller, buyer, account details, admin actions, and freeze status.
    """
    __tablename__ = 'account_sale_logs'
    
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('telegram_accounts.id'), nullable=False)
    seller_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Sale details
    sale_price = Column(Float, nullable=False)
    status = Column(Enum(SaleLogStatus), default=SaleLogStatus.PENDING)
    
    # Account information at time of sale
    account_phone = Column(String(20), nullable=False)
    account_original_name = Column(String(255), nullable=True)
    account_original_username = Column(String(255), nullable=True)
    account_is_frozen = Column(Boolean, default=False)
    account_freeze_reason = Column(Text, nullable=True)
    
    # Seller information
    seller_telegram_id = Column(Integer, nullable=False)
    seller_username = Column(String(255), nullable=True)
    seller_name = Column(String(255), nullable=True)
    
    # Buyer information (if applicable)
    buyer_telegram_id = Column(Integer, nullable=True)
    buyer_username = Column(String(255), nullable=True)
    buyer_name = Column(String(255), nullable=True)
    
    # Admin action tracking
    reviewed_by_admin_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    admin_action_notes = Column(Text, nullable=True)
    admin_action_timestamp = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Timestamps
    sale_initiated_at = Column(DateTime, default=datetime.utcnow)
    sale_completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    account = relationship("TelegramAccount", back_populates="sale_logs")
    seller = relationship("User", foreign_keys=[seller_id])
    admin_reviewer = relationship("User", foreign_keys=[reviewed_by_admin_id])
    
    def __repr__(self):
        return f"<AccountSaleLog(id={self.id}, account_id={self.account_id}, status='{self.status}', seller_id={self.seller_id})>"
    
    def is_frozen(self) -> bool:
        """Check if the associated account is frozen"""
        return self.account_is_frozen
    
    def can_be_approved(self) -> bool:
        """Check if this sale can be approved (not frozen, pending status)"""
        return self.status == SaleLogStatus.PENDING and not self.account_is_frozen
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'account_id': self.account_id,
            'account_phone': self.account_phone,
            'seller_id': self.seller_id,
            'seller_name': self.seller_name,
            'seller_username': self.seller_username,
            'sale_price': self.sale_price,
            'status': self.status.value,
            'is_frozen': self.account_is_frozen,
            'freeze_reason': self.account_freeze_reason,
            'admin_notes': self.admin_action_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'reviewed_at': self.admin_action_timestamp.isoformat() if self.admin_action_timestamp else None
        }
