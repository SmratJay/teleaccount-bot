"""
Database models for the Telegram Account Bot.
"""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timezone
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

Base = declarative_base()

class ProxyPool(Base):
    """Proxy pool for managing proxies used in Telegram connections."""
    __tablename__ = 'proxy_pool'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ip_address = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    username = Column(String(255), nullable=True)
    password = Column(String(255), nullable=True)
    country_code = Column(String(10), nullable=True)
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Advanced metrics
    reputation_score = Column(Integer, default=50)
    response_time_avg = Column(Float, nullable=True)
    success_rate = Column(Float, nullable=True)
    proxy_type = Column(String(50), default='datacenter')
    consecutive_failures = Column(Integer, default=0)
    total_uses = Column(Integer, default=0)
    last_health_check = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<ProxyPool(id={self.id}, ip={self.ip_address}:{self.port}, country={self.country_code}, active={self.is_active}, reputation={self.reputation_score})>"

    def get_decrypted_password(self):
        """Get decrypted password for use in connections."""
        if not self.password:
            return None
        
        try:
            from utils.encryption import decrypt_password
            return decrypt_password(self.password)
        except Exception as e:
            # If decryption fails, assume it's plaintext (for backward compatibility)
            if not self.password.startswith('gAAAAAB'):
                return self.password
            raise
    
    def set_encrypted_password(self, plaintext_password):
        """Set password with automatic encryption."""
        if not plaintext_password:
            self.password = None
            return
        
        from utils.encryption import encrypt_password
        self.password = encrypt_password(plaintext_password)

    def to_dict(self, include_password=False):
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
    def is_working(self):
        """Check if proxy is working (basic check)"""
        return self.is_active and self.consecutive_failures < 3
    
    @property
    def is_healthy(self):
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
    
    def update_health_metrics(self, success, response_time=None):
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
                self.response_time_avg = 0.3 * response_time + 0.7 * self.response_time_avg
        
        # Update success rate (exponential moving average)
        success_value = 1.0 if success else 0.0
        if self.success_rate is None:
            self.success_rate = success_value
        else:
            self.success_rate = 0.2 * success_value + 0.8 * self.success_rate
        
        # Update reputation score based on metrics
        self._calculate_reputation()
    
    def _calculate_reputation(self):
        """Calculate reputation score (0-100) based on all metrics."""
        score = 50
        
        # Success rate contribution (±30 points)
        if self.success_rate is not None:
            score += (self.success_rate - 0.5) * 60
        
        # Response time contribution (±15 points)
        if self.response_time_avg is not None:
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


# Stub models for real_handlers.py compatibility
class User:
    def __init__(self, telegram_id, username=None):
        self.id = 1
        self.telegram_id = telegram_id
        self.username = username
        self.balance = 0.0
        self.language = 'en'

class TelegramAccount:
    def __init__(self, phone_number, user_id=1):
        self.id = 1
        self.phone_number = phone_number
        self.user_id = user_id
        self.status = 'active'

class AccountStatus:
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    PENDING = 'pending'
    SOLD = 'sold'

class Withdrawal:
    def __init__(self, user_id, amount):
        self.id = 1
        self.user_id = user_id
        self.amount = amount
        self.status = 'pending'

class WithdrawalStatus:
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    COMPLETED = 'completed'


class ActivityLog:
    def __init__(self, user_id, action, details=None):
        self.id = 1
        self.user_id = user_id
        self.action = action
        self.details = details
        self.timestamp = None


class UserStatus:
    ACTIVE = 'active'
    BANNED = 'banned'
    SUSPENDED = 'suspended'

