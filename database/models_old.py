"""
Database models for the Telegram Account Bot.
"""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
import uuid

Base = declarative_base()

class User(Base):
    """User model for bot users."""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    language_code = Column(String(10), default='en')
    balance = Column(Float, default=0.0)
    status = Column(String(20), default='ACTIVE')  # User status: ACTIVE, BANNED, SUSPENDED
    is_admin = Column(Boolean, default=False)  # Admin privileges
    is_leader = Column(Boolean, default=False)  # Leader privileges (super admin)
    region = Column(String(100), nullable=True)
    captcha_completed = Column(Boolean, default=False)
    channels_joined = Column(Boolean, default=False)
    verification_completed = Column(Boolean, default=False)
    total_accounts_sold = Column(Integer, default=0)
    total_earnings = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    accounts = relationship("Account", back_populates="user")
    withdrawals = relationship("Withdrawal", back_populates="user")

class Account(Base):
    """Account model for Telegram accounts managed by users."""
    __tablename__ = 'accounts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    phone_number = Column(String(20), unique=True, nullable=False)
    country_code = Column(String(5), nullable=True)
    session_file_path = Column(String(500), nullable=False)
    proxy_config = Column(Text, nullable=True)  # JSON string of proxy configuration
    
    # Account status: ACTIVE, FROZEN, BANNED, 24_HOUR_HOLD
    status = Column(String(50), default='ACTIVE')
    
    # 2FA Configuration
    two_fa_enabled = Column(Boolean, default=False)
    two_fa_password_hash = Column(String(255), nullable=True)
    
    # Account Details
    telegram_user_id = Column(Integer, nullable=True)  # The actual Telegram user ID of the account
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    profile_photo_path = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_login_at = Column(DateTime, nullable=True)
    last_activity_at = Column(DateTime, nullable=True)
    
    # Security flags
    logout_other_sessions = Column(Boolean, default=False)
    otp_reported = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="accounts")

class Withdrawal(Base):
    """Withdrawal model for user withdrawal requests."""
    __tablename__ = 'withdrawals'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Withdrawal details
    amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False)  # USDT, TRX, etc.
    withdrawal_address = Column(String(500), nullable=False)  # Actual DB column
    withdrawal_method = Column(String(50), nullable=False)  # Actual DB column (TRX, USDT-BEP20, Binance Pay)
    
    # Status: PENDING, COMPLETED, REJECTED, FAILED
    status = Column(String(15), default='PENDING')
    
    # Leader assignment
    assigned_leader_id = Column(Integer, nullable=True)
    leader_notes = Column(Text, nullable=True)
    payment_proof = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    processed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="withdrawals")

class SystemSettings(Base):
    """System settings for the bot."""
    __tablename__ = 'system_settings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class ProxyPool(Base):
    """Proxy pool for managing proxies."""
    __tablename__ = 'proxy_pool'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    proxy_type = Column(String(20), nullable=False)  # HTTP, SOCKS4, SOCKS5
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    username = Column(String(255), nullable=True)
    password = Column(String(255), nullable=True)
    
    # Status tracking
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)
    failure_count = Column(Integer, default=0)
    
    # Geographic info
    country_code = Column(String(5), nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))