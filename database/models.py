"""
Database models for the Telegram Account Selling Bot.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()

class UserStatus(enum.Enum):
    PENDING_VERIFICATION = "PENDING_VERIFICATION"  # User needs to complete captcha/tasks
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN" 
    BANNED = "BANNED"
    SUSPENDED = "SUSPENDED"

class AccountStatus(enum.Enum):
    AVAILABLE = "AVAILABLE"  # Ready to be sold
    SOLD = "SOLD"           # Already sold
    FROZEN = "FROZEN"       # Banned/frozen account
    SPAM = "SPAM"          # Detected as spam account
    TWENTY_FOUR_HOUR_HOLD = "24_HOUR_HOLD"  # Multi-device detection hold

class WithdrawalStatus(enum.Enum):
    PENDING = "PENDING"        # Awaiting leader review
    LEADER_APPROVED = "LEADER_APPROVED"  # Leader approved, awaiting payment
    COMPLETED = "COMPLETED"    # Payment sent
    REJECTED = "REJECTED"      # Rejected by leader
    FAILED = "FAILED"         # Payment failed

class SaleStatus(enum.Enum):
    INITIATED = "INITIATED"    # Sale process started
    CONFIGURING = "CONFIGURING"  # Changing name, username, photo, 2FA
    COMPLETED = "COMPLETED"    # Sale finished
    FAILED = "FAILED"         # Sale failed

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_user_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    language_code = Column(String(10), default='en')
    balance = Column(Float, default=0.0)
    status = Column(Enum(UserStatus), default=UserStatus.PENDING_VERIFICATION)
    is_admin = Column(Boolean, default=False)
    is_leader = Column(Boolean, default=False)
    region = Column(String(100), nullable=True)  # For regional leaders
    
    # Verification status
    captcha_completed = Column(Boolean, default=False)
    channels_joined = Column(Boolean, default=False)
    verification_completed = Column(Boolean, default=False)
    
    # Statistics
    total_accounts_sold = Column(Integer, default=0)
    total_earnings = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    accounts = relationship("TelegramAccount", back_populates="seller", cascade="all, delete-orphan")
    withdrawals = relationship("Withdrawal", back_populates="user", cascade="all, delete-orphan", foreign_keys="Withdrawal.user_id")
    sales = relationship("AccountSale", back_populates="seller", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_user_id}, username='{self.username}')>"

class TelegramAccount(Base):
    __tablename__ = 'telegram_accounts'
    
    id = Column(Integer, primary_key=True)
    seller_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    phone_number = Column(String(20), unique=True, nullable=False)
    country_code = Column(String(10), nullable=True)
    status = Column(Enum(AccountStatus), default=AccountStatus.AVAILABLE)
    
    # Original account details (before sale)
    original_account_name = Column(String(255), nullable=True)
    original_username = Column(String(255), nullable=True)
    original_bio = Column(Text, nullable=True)
    
    # Current account details (after configuration)
    current_account_name = Column(String(255), nullable=True)
    current_username = Column(String(255), nullable=True)
    current_bio = Column(Text, nullable=True)
    
    # Security and session data
    session_string = Column(Text, nullable=True)
    two_fa_password = Column(String(255), nullable=True)
    
    # Proxy and IP management
    assigned_proxy_ip = Column(String(255), nullable=True)
    assigned_proxy_port = Column(Integer, nullable=True)
    last_ip_rotation = Column(DateTime, nullable=True)
    
    # Activity and device tracking
    active_sessions_count = Column(Integer, default=0)
    last_activity_at = Column(DateTime, nullable=True)
    multi_device_detected = Column(Boolean, default=False)
    hold_until = Column(DateTime, nullable=True)  # For 24-48 hour holds
    
    # Sale information
    sale_price = Column(Float, nullable=True)
    sold_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    seller = relationship("User", back_populates="accounts")
    sales = relationship("AccountSale", back_populates="account", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<TelegramAccount(id={self.id}, phone='{self.phone_number}', status='{self.status}')>"

class AccountSale(Base):
    __tablename__ = 'account_sales'
    
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('telegram_accounts.id'), nullable=False)
    seller_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    sale_price = Column(Float, nullable=False)
    status = Column(Enum(SaleStatus), default=SaleStatus.INITIATED)
    
    # Configuration steps tracking
    name_changed = Column(Boolean, default=False)
    username_changed = Column(Boolean, default=False)
    profile_photo_set = Column(Boolean, default=False)
    two_fa_setup = Column(Boolean, default=False)
    sessions_terminated = Column(Boolean, default=False)
    
    # Sale details
    buyer_telegram_id = Column(Integer, nullable=True)
    sale_completed_at = Column(DateTime, nullable=True)
    configuration_notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    account = relationship("TelegramAccount", back_populates="sales")
    seller = relationship("User", back_populates="sales")
    
    def __repr__(self):
        return f"<AccountSale(id={self.id}, account_id={self.account_id}, price={self.sale_price})>"

class Withdrawal(Base):
    __tablename__ = 'withdrawals'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False)  # TRX, USDT, BNB
    withdrawal_address = Column(String(500), nullable=False)  # TRX address, Binance ID, etc.
    withdrawal_method = Column(String(50), nullable=False)  # TRX, Binance, USDT-BEP20
    status = Column(Enum(WithdrawalStatus), default=WithdrawalStatus.PENDING)
    
    # Leader management
    assigned_leader_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    leader_notes = Column(Text, nullable=True)
    payment_proof = Column(Text, nullable=True)  # URL to payment screenshot
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="withdrawals", foreign_keys=[user_id])
    assigned_leader = relationship("User", foreign_keys=[assigned_leader_id])
    
    def __repr__(self):
        return f"<Withdrawal(id={self.id}, user_id={self.user_id}, amount={self.amount}, status='{self.status}')>"

class SystemSettings(Base):
    __tablename__ = 'system_settings'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(255), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<SystemSettings(key='{self.key}', value='{self.value}')>"

class ProxyPool(Base):
    __tablename__ = 'proxy_pool'
    
    id = Column(Integer, primary_key=True)
    ip_address = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    username = Column(String(255), nullable=True)
    password = Column(String(255), nullable=True)
    country_code = Column(String(10), nullable=True)
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<ProxyPool(id={self.id}, ip='{self.ip_address}:{self.port}', country='{self.country_code}')>"

class ActivityLog(Base):
    __tablename__ = 'activity_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    action_type = Column(String(100), nullable=False)  # SALE, WITHDRAWAL, IP_ROTATION, SESSION_TERMINATION, etc.
    description = Column(Text, nullable=False)
    extra_data = Column(Text, nullable=True)  # JSON string for additional data (renamed from metadata)
    ip_address = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
    
    def __repr__(self):
        return f"<ActivityLog(id={self.id}, action='{self.action_type}', user_id={self.user_id})>"

class VerificationTask(Base):
    __tablename__ = 'verification_tasks'
    
    id = Column(Integer, primary_key=True)
    task_type = Column(String(50), nullable=False)  # CAPTCHA, JOIN_CHANNEL, CUSTOM
    task_name = Column(String(255), nullable=False)
    task_description = Column(Text, nullable=False)
    task_data = Column(Text, nullable=True)  # JSON data for task parameters
    is_active = Column(Boolean, default=True)
    order_priority = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<VerificationTask(id={self.id}, type='{self.task_type}', name='{self.task_name}')>"

class UserVerification(Base):
    __tablename__ = 'user_verifications'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    task_id = Column(Integer, ForeignKey('verification_tasks.id'), nullable=False)
    completed = Column(Boolean, default=False)
    completion_data = Column(Text, nullable=True)  # JSON data for completion proof
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
    task = relationship("VerificationTask")
    
    def __repr__(self):
        return f"<UserVerification(user_id={self.user_id}, task_id={self.task_id}, completed={self.completed})>"