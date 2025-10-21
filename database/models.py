"""
Database models for the Telegram Account Bot.
Properly mapped to actual database schema.
"""
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Boolean, Text, Float, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

Base = declarative_base()

# =============================================================================
# ENUMS - Status definitions
# =============================================================================

class AccountStatus(str, enum.Enum):
    """Telegram account status enum."""
    AVAILABLE = 'AVAILABLE'
    HELD = 'HELD'
    SOLD = 'SOLD'
    FROZEN = 'FROZEN'
    BANNED = 'BANNED'
    ACTIVE = 'ACTIVE'  # Legacy
    INACTIVE = 'INACTIVE'  # Legacy
    PENDING = 'PENDING'  # Legacy
    TWENTY_FOUR_HOUR_HOLD = 'TWENTY_FOUR_HOUR_HOLD'

class WithdrawalStatus(str, enum.Enum):
    """Withdrawal request status enum."""
    PENDING = 'PENDING'
    APPROVED = 'APPROVED'
    COMPLETED = 'COMPLETED'
    REJECTED = 'REJECTED'
    FAILED = 'FAILED'

class UserStatus(str, enum.Enum):
    """User account status enum."""
    ACTIVE = 'ACTIVE'
    BANNED = 'BANNED'
    SUSPENDED = 'SUSPENDED'

class SaleStatus(str, enum.Enum):
    """Account sale status enum."""
    PENDING = 'PENDING'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'

class SaleStatus(str, enum.Enum):
    """Account sale status enum."""
    PENDING = 'PENDING'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'

# =============================================================================
# MODELS - Actual database tables
# =============================================================================

class User(Base):
    """User model - maps to 'users' table."""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    language_code = Column(String(10), default='en')
    balance = Column(Float, default=0.0)
    status = Column(String(20), default='ACTIVE')
    is_admin = Column(Boolean, default=False)
    is_leader = Column(Boolean, default=False)
    region = Column(String(100), nullable=True)
    captcha_completed = Column(Boolean, default=False)
    captcha_answer = Column(String(255), nullable=True)  # Store CAPTCHA answer for persistence
    captcha_type = Column(String(50), nullable=True)    # 'visual' or 'text'
    captcha_image_path = Column(String(500), nullable=True)  # Path to CAPTCHA image file
    verification_step = Column(Integer, default=0)      # Current verification step (0=none, 1=captcha, 2=channels, 3=complete)
    channels_joined = Column(Boolean, default=False)
    verification_completed = Column(Boolean, default=False)
    total_accounts_sold = Column(Integer, default=0)
    total_earnings = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    telegram_accounts = relationship("TelegramAccount", back_populates="seller", foreign_keys="[TelegramAccount.seller_id]")
    withdrawals = relationship("Withdrawal", back_populates="user")
    activity_logs = relationship("ActivityLog", back_populates="user")
    verifications = relationship("UserVerification", back_populates="user")
    sales = relationship("AccountSale", back_populates="seller", foreign_keys="[AccountSale.seller_id]")

    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_user_id}, username={self.username})>"


class TelegramAccount(Base):
    """Telegram Account model - maps to 'telegram_accounts' table."""
    __tablename__ = 'telegram_accounts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    seller_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    phone_number = Column(String(20), nullable=False, unique=True, index=True)
    country_code = Column(String(10), nullable=True)
    status = Column(String(21), default='AVAILABLE')  # AVAILABLE, HELD, SOLD, FROZEN, BANNED
    
    # Original account details (before sale)
    original_account_name = Column(String(255), nullable=True)
    original_username = Column(String(255), nullable=True)
    original_bio = Column(Text, nullable=True)
    
    # Current account details (after modifications)
    current_account_name = Column(String(255), nullable=True)
    current_username = Column(String(255), nullable=True)
    current_bio = Column(Text, nullable=True)
    
    # Session and security
    session_string = Column(Text, nullable=True)
    two_fa_password = Column(String(255), nullable=True)
    
    # Proxy configuration
    assigned_proxy_ip = Column(String(255), nullable=True)
    assigned_proxy_port = Column(Integer, nullable=True)
    last_ip_rotation = Column(DateTime, nullable=True)
    
    # Activity tracking
    active_sessions_count = Column(Integer, default=0)
    last_activity_at = Column(DateTime, nullable=True)
    multi_device_detected = Column(Boolean, default=False)
    multi_device_last_detected = Column(DateTime, nullable=True)
    
    # Hold and sale tracking
    hold_until = Column(DateTime, nullable=True)
    sale_price = Column(Float, nullable=True)
    sold_at = Column(DateTime, nullable=True)
    
    # Freeze management
    is_frozen = Column(Boolean, default=False)
    freeze_reason = Column(Text, nullable=True)
    freeze_timestamp = Column(DateTime, nullable=True)
    freeze_duration_hours = Column(Integer, nullable=True)
    frozen_by_admin_id = Column(Integer, nullable=True)
    can_be_sold = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    seller = relationship("User", back_populates="telegram_accounts", foreign_keys=[seller_id])
    sales = relationship("AccountSale", back_populates="account")

    def __repr__(self):
        return f"<TelegramAccount(id={self.id}, phone={self.phone_number}, status={self.status})>"


class Withdrawal(Base):
    """Withdrawal model - maps to 'withdrawals' table."""
    __tablename__ = 'withdrawals'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False)
    withdrawal_address = Column(String(500), nullable=False)
    withdrawal_method = Column(String(50), nullable=False)  # TRX, USDT-TRC20, USDT-BEP20, Binance Pay
    status = Column(String(15), default='PENDING')  # PENDING, APPROVED, COMPLETED, REJECTED
    assigned_leader_id = Column(Integer, nullable=True)
    leader_notes = Column(Text, nullable=True)
    payment_proof = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    processed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="withdrawals")

    def __repr__(self):
        return f"<Withdrawal(id={self.id}, user_id={self.user_id}, amount={self.amount}, status={self.status})>"


class SystemSettings(Base):
    """System Settings model - maps to 'system_settings' table."""
    __tablename__ = 'system_settings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(255), nullable=False, unique=True, index=True)
    value = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<SystemSettings(key={self.key}, value={self.value})>"


class ProxyPool(Base):
    """Proxy pool for managing proxies used in Telegram connections."""
    __tablename__ = 'proxy_pool'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ip_address = Column(String(255), nullable=False)  # The proxy IP address
    port = Column(Integer, nullable=False)  # The proxy port
    username = Column(String(255), nullable=True)  # Proxy authentication username
    password = Column(String(255), nullable=True)  # Encrypted proxy authentication password
    country_code = Column(String(10), nullable=True)  # Country code (e.g., 'US', 'GB', 'IN')
    provider = Column(String(50), default='free', nullable=True)  # Proxy provider: 'webshare', 'free', etc.
    is_active = Column(Boolean, default=True)  # Whether this proxy is active and usable
    last_used_at = Column(DateTime, nullable=True)  # Last time this proxy was used
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))  # Creation timestamp
    
    # Advanced metrics
    reputation_score = Column(Integer, default=50)  # 0-100 reputation score
    response_time_avg = Column(Float, nullable=True)  # Average response time in ms
    success_rate = Column(Float, nullable=True)  # Success rate 0.0-1.0
    proxy_type = Column(String(50), default='datacenter')  # datacenter, residential, mobile
    consecutive_failures = Column(Integer, default=0)  # Track failure streaks
    total_uses = Column(Integer, default=0)  # Total number of times used
    last_health_check = Column(DateTime, nullable=True)  # Last health check timestamp

    def __repr__(self):
        return f"<ProxyPool(id={self.id}, ip={self.ip_address}:{self.port}, country={self.country_code}, active={self.is_active}, reputation={self.reputation_score})>"

    def get_decrypted_password(self) -> str | None:
        """Get decrypted password for use in connections."""
        if not self.password:
            return None
        
        try:
            from utils.encryption import decrypt_password
            return decrypt_password(self.password)
        except Exception as e:
            # If decryption fails, assume it's plaintext (for backward compatibility)
            if not self.password.startswith('gAAAAAB'):  # Not Fernet encrypted
                return self.password
            raise
    
    def set_encrypted_password(self, plaintext_password: str | None):
        """Set password with automatic encryption."""
        if not plaintext_password:
            self.password = None
            return
        
        from utils.encryption import encrypt_password
        self.password = encrypt_password(plaintext_password)

    def to_dict(self, include_password: bool = False) -> dict:
        """Convert to dictionary for API responses"""
        result = {
            'id': self.id,
            'ip_address': self.ip_address,
            'port': self.port,
            'username': self.username,
            'country_code': self.country_code,
            'is_active': self.is_active,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'reputation_score': self.reputation_score,
            'response_time_avg': self.response_time_avg,
            'success_rate': self.success_rate,
            'proxy_type': self.proxy_type,
            'consecutive_failures': self.consecutive_failures,
            'total_uses': self.total_uses,
            'last_health_check': self.last_health_check.isoformat() if self.last_health_check else None,
        }
        
        if include_password:
            result['password'] = self.get_decrypted_password()
        
        return result

    @property
    def is_working(self) -> bool:
        """Check if proxy is working (basic check)"""
        return self.is_active and self.consecutive_failures < 3
    
    @property
    def is_healthy(self) -> bool:
        """Check if proxy is healthy based on reputation and metrics."""
        if not self.is_active:
            return False
        if self.consecutive_failures >= 3:
            return False
        if self.reputation_score and self.reputation_score < 30:
            return False
        return True

    def mark_used(self):
        """Mark proxy as recently used"""
        self.last_used_at = datetime.now(timezone.utc)
        self.total_uses = (self.total_uses or 0) + 1
    
    def update_health_metrics(self, success: bool, response_time: float = None):
        """
        Update health metrics after a connection attempt.
        
        Args:
            success: Whether the connection was successful
            response_time: Response time in milliseconds (if successful)
        """
        self.last_health_check = datetime.now(timezone.utc)
        
        # Update consecutive failures
        if success:
            self.consecutive_failures = 0
        else:
            self.consecutive_failures = (self.consecutive_failures or 0) + 1
        
        # Update response time (exponential moving average)
        if response_time is not None and success:
            if self.response_time_avg is None:
                self.response_time_avg = response_time
            else:
                # EMA with alpha=0.3 (30% weight to new value)
                self.response_time_avg = 0.3 * response_time + 0.7 * self.response_time_avg
        
        # Update success rate (exponential moving average)
        success_value = 1.0 if success else 0.0
        if self.success_rate is None:
            self.success_rate = success_value
        else:
            # EMA with alpha=0.2 (20% weight to new value)
            self.success_rate = 0.2 * success_value + 0.8 * self.success_rate
        
        # Update reputation score based on metrics
        self._calculate_reputation()
    
    def _calculate_reputation(self):
        """Calculate reputation score (0-100) based on all metrics."""
        score = 50  # Start at neutral
        
        # Success rate contribution (±30 points)
        if self.success_rate is not None:
            score += (self.success_rate - 0.5) * 60
        
        # Response time contribution (±15 points)
        if self.response_time_avg is not None:
            # Good: <500ms = +15, Medium: 500-2000ms = 0, Bad: >2000ms = -15
            if self.response_time_avg < 500:
                score += 15
            elif self.response_time_avg > 2000:
                score -= 15
            else:
                score += 15 * (1 - (self.response_time_avg - 500) / 1500)
        
        # Consecutive failures penalty (-5 per failure)
        score -= self.consecutive_failures * 5
        
        # Usage bonus (active proxies are valuable, +1 per 10 uses, max +10)
        if self.total_uses:
            score += min(self.total_uses / 10, 10)
        
        # Clamp to 0-100
        self.reputation_score = max(0, min(100, int(score)))


class ActivityLog(Base):
    """Activity Log model - maps to 'activity_logs' table."""
    __tablename__ = 'activity_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    action_type = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=False)
    extra_data = Column(Text, nullable=True)  # JSON string for additional data
    ip_address = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    # Relationships
    user = relationship("User", back_populates="activity_logs")

    def __repr__(self):
        return f"<ActivityLog(id={self.id}, action={self.action_type}, user_id={self.user_id})>"


class VerificationTask(Base):
    """Verification Task model - maps to 'verification_tasks' table."""
    __tablename__ = 'verification_tasks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_type = Column(String(50), nullable=False)
    task_name = Column(String(255), nullable=False)
    task_description = Column(Text, nullable=False)
    task_data = Column(Text, nullable=True)  # JSON string for task configuration
    is_active = Column(Boolean, default=True)
    order_priority = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user_verifications = relationship("UserVerification", back_populates="task")

    def __repr__(self):
        return f"<VerificationTask(id={self.id}, name={self.task_name}, type={self.task_type})>"


class UserVerification(Base):
    """User Verification model - maps to 'user_verifications' table."""
    __tablename__ = 'user_verifications'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey('verification_tasks.id'), nullable=False, index=True)
    completed = Column(Boolean, default=False)
    completion_data = Column(Text, nullable=True)  # JSON string for completion details
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user = relationship("User", back_populates="verifications")
    task = relationship("VerificationTask", back_populates="user_verifications")

    def __repr__(self):
        return f"<UserVerification(id={self.id}, user_id={self.user_id}, task_id={self.task_id}, completed={self.completed})>"


class AccountSale(Base):
    """Account Sale model - maps to 'account_sales' table."""
    __tablename__ = 'account_sales'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey('telegram_accounts.id'), nullable=False, index=True)
    seller_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    sale_price = Column(Float, nullable=False)
    status = Column(String(11), default='PENDING')  # PENDING, IN_PROGRESS, COMPLETED, FAILED
    
    # Configuration tracking
    name_changed = Column(Boolean, default=False)
    username_changed = Column(Boolean, default=False)
    profile_photo_set = Column(Boolean, default=False)
    two_fa_setup = Column(Boolean, default=False)
    sessions_terminated = Column(Boolean, default=False)
    
    # Buyer information
    buyer_telegram_id = Column(BigInteger, nullable=True)
    sale_completed_at = Column(DateTime, nullable=True)
    configuration_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    account = relationship("TelegramAccount", back_populates="sales")
    seller = relationship("User", back_populates="sales", foreign_keys=[seller_id])

    def __repr__(self):
        return f"<AccountSale(id={self.id}, account_id={self.account_id}, status={self.status}, price={self.sale_price})>"


# =============================================================================
# LEGACY COMPATIBILITY - Keep these for backward compatibility with existing code
# =============================================================================

# Alias for backward compatibility
AccountSaleLog = AccountSale
