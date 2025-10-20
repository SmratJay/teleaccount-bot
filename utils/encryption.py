"""
Encryption utilities for sensitive data storage.

This module provides AES-256 encryption for proxy credentials and other sensitive data.
"""
import os
from typing import Optional
from cryptography.fernet import Fernet
import logging

logger = logging.getLogger(__name__)


class EncryptionManager:
    """Manages encryption and decryption of sensitive data using AES-256."""
    
    _instance = None
    _encryption_key: Optional[bytes] = None
    _fernet: Optional[Fernet] = None
    
    def __new__(cls):
        """Singleton pattern to ensure single encryption key across app."""
        if cls._instance is None:
            cls._instance = super(EncryptionManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize encryption manager."""
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._load_or_generate_key()
    
    def _load_or_generate_key(self):
        """Load encryption key from environment or generate new one."""
        # Try to load from environment variable
        env_key = os.getenv('ENCRYPTION_KEY')
        
        if env_key:
            try:
                # Validate the key
                self._encryption_key = env_key.encode()
                self._fernet = Fernet(self._encryption_key)
                logger.info("✅ Loaded encryption key from environment")
            except Exception as e:
                logger.warning(f"⚠️ Invalid encryption key in environment: {e}")
                self._generate_new_key()
        else:
            # Load from file or generate
            self._load_from_file_or_generate()
    
    def _load_from_file_or_generate(self):
        """Load encryption key from file or generate new one."""
        key_file = os.path.join(os.path.dirname(__file__), '..', '.encryption_key')
        
        if os.path.exists(key_file):
            try:
                with open(key_file, 'rb') as f:
                    self._encryption_key = f.read()
                self._fernet = Fernet(self._encryption_key)
                logger.info("✅ Loaded encryption key from file")
            except Exception as e:
                logger.error(f"❌ Failed to load encryption key from file: {e}")
                self._generate_new_key()
        else:
            self._generate_new_key()
            # Save to file
            try:
                with open(key_file, 'wb') as f:
                    f.write(self._encryption_key)
                logger.info(f"💾 Saved encryption key to {key_file}")
            except Exception as e:
                logger.error(f"❌ Failed to save encryption key: {e}")
    
    def _generate_new_key(self):
        """Generate a new encryption key."""
        self._encryption_key = Fernet.generate_key()
        self._fernet = Fernet(self._encryption_key)
        logger.warning("🔑 Generated new encryption key")
    
    def encrypt(self, plaintext: Optional[str]) -> Optional[str]:
        """
        Encrypt plaintext string.
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Base64-encoded encrypted string, or None if input is None
        """
        if plaintext is None:
            return None
        
        if not plaintext:
            return plaintext
        
        try:
            encrypted_bytes = self._fernet.encrypt(plaintext.encode())
            return encrypted_bytes.decode()
        except Exception as e:
            logger.error(f"❌ Encryption failed: {e}")
            raise
    
    def decrypt(self, ciphertext: Optional[str]) -> Optional[str]:
        """
        Decrypt encrypted string.
        
        Args:
            ciphertext: Base64-encoded encrypted string
            
        Returns:
            Decrypted plaintext string, or None if input is None
        """
        if ciphertext is None:
            return None
        
        if not ciphertext:
            return ciphertext
        
        try:
            decrypted_bytes = self._fernet.decrypt(ciphertext.encode())
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"❌ Decryption failed: {e}")
            raise
    
    def get_key_string(self) -> str:
        """
        Get the encryption key as a string for environment variable storage.
        
        Returns:
            Base64-encoded encryption key
        """
        return self._encryption_key.decode()
    
    def rotate_key(self, old_key: Optional[str] = None):
        """
        Rotate encryption key (for security maintenance).
        
        WARNING: This requires re-encrypting all existing encrypted data!
        
        Args:
            old_key: Optional old key for data migration
        """
        old_fernet = None
        if old_key:
            try:
                old_fernet = Fernet(old_key.encode())
            except Exception as e:
                logger.error(f"❌ Invalid old key provided: {e}")
                raise
        
        # Generate new key
        new_key = Fernet.generate_key()
        new_fernet = Fernet(new_key)
        
        logger.info("🔄 Encryption key rotation initiated")
        
        # Update instance
        self._encryption_key = new_key
        self._fernet = new_fernet
        
        # Save new key
        key_file = os.path.join(os.path.dirname(__file__), '..', '.encryption_key')
        try:
            with open(key_file, 'wb') as f:
                f.write(self._encryption_key)
            logger.info("✅ New encryption key saved")
        except Exception as e:
            logger.error(f"❌ Failed to save new encryption key: {e}")
            raise
        
        return old_fernet


# Global instance
encryption_manager = EncryptionManager()


# Convenience functions
def encrypt_password(password: Optional[str]) -> Optional[str]:
    """Encrypt a password string."""
    return encryption_manager.encrypt(password)


def decrypt_password(encrypted_password: Optional[str]) -> Optional[str]:
    """Decrypt a password string."""
    return encryption_manager.decrypt(encrypted_password)


def get_encryption_key() -> str:
    """Get the current encryption key for environment storage."""
    return encryption_manager.get_key_string()


if __name__ == "__main__":
    # Test encryption
    import sys
    
    print("🔒 Encryption Manager Test")
    print("=" * 50)
    
    # Test data
    test_password = "super_secret_password_123!"
    print(f"Original: {test_password}")
    
    # Encrypt
    encrypted = encrypt_password(test_password)
    print(f"Encrypted: {encrypted}")
    
    # Decrypt
    decrypted = decrypt_password(encrypted)
    print(f"Decrypted: {decrypted}")
    
    # Verify
    if decrypted == test_password:
        print("✅ Encryption/Decryption works correctly!")
    else:
        print("❌ Encryption/Decryption FAILED!")
        sys.exit(1)
    
    # Test None handling
    assert encrypt_password(None) is None
    assert decrypt_password(None) is None
    print("✅ None handling works correctly!")
    
    # Test empty string
    assert encrypt_password("") == ""
    assert decrypt_password("") == ""
    print("✅ Empty string handling works correctly!")
    
    print("\n🔑 Current encryption key (for .env):")
    print(f"ENCRYPTION_KEY={get_encryption_key()}")

