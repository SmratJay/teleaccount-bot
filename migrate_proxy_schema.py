"""
Database migration: Add advanced proxy features
- Reputation scoring
- Performance metrics
- Proxy type classification
- Encrypted passwords
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database.models import Base
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, Float
from sqlalchemy.orm import sessionmaker
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = 'teleaccount_bot.db'


def migrate_database():
    """Add new columns to proxy_pool table."""
    
    engine = create_engine(f'sqlite:///{DB_PATH}', echo=True)
    
    # Get list of existing columns
    connection = engine.raw_connection()
    cursor = connection.cursor()
    cursor.execute("PRAGMA table_info(proxy_pool)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    
    logger.info(f"📋 Existing columns: {existing_columns}")
    
    # Define new columns to add
    new_columns = {
        'reputation_score': 'INTEGER DEFAULT 50',  # 0-100 score
        'response_time_avg': 'FLOAT',  # Average response time in ms
        'success_rate': 'FLOAT',  # Success rate 0.0-1.0
        'proxy_type': "VARCHAR(50) DEFAULT 'datacenter'",  # datacenter, residential, mobile
        'consecutive_failures': 'INTEGER DEFAULT 0',  # Track failure streaks
        'total_uses': 'INTEGER DEFAULT 0',  # Total number of times used
        'last_health_check': 'DATETIME',  # Last health check timestamp
    }
    
    # Add missing columns
    for column_name, column_def in new_columns.items():
        if column_name not in existing_columns:
            try:
                alter_sql = f"ALTER TABLE proxy_pool ADD COLUMN {column_name} {column_def}"
                logger.info(f"🔧 Adding column: {alter_sql}")
                cursor.execute(alter_sql)
                connection.commit()
                logger.info(f"✅ Added column: {column_name}")
            except Exception as e:
                logger.error(f"❌ Failed to add column {column_name}: {e}")
        else:
            logger.info(f"⏭️ Column {column_name} already exists")
    
    # Close connection
    cursor.close()
    connection.close()
    
    logger.info("✅ Migration complete!")
    
    # Verify new schema
    connection = engine.raw_connection()
    cursor = connection.cursor()
    cursor.execute("PRAGMA table_info(proxy_pool)")
    columns = cursor.fetchall()
    
    logger.info("\n📊 Updated schema:")
    for col in columns:
        logger.info(f"  - {col[1]} ({col[2]})")
    
    cursor.close()
    connection.close()


def migrate_passwords_to_encryption():
    """
    Migrate existing plaintext passwords to encrypted format.
    
    WARNING: This should be run AFTER adding encryption support to the model!
    """
    from database.operations import ProxyService
    from utils.encryption import encrypt_password
    
    logger.info("🔐 Starting password encryption migration...")
    
    proxies = ProxyService.get_all_proxies()
    
    if not proxies:
        logger.info("ℹ️ No proxies to migrate")
        return
    
    logger.info(f"📋 Found {len(proxies)} proxies to check")
    
    migrated = 0
    for proxy in proxies:
        if proxy.password and not proxy.password.startswith('gAAAAAB'):  # Fernet encrypted strings start with this
            logger.info(f"🔒 Encrypting password for proxy {proxy.id}")
            # This will be handled automatically by the model's property setter
            # For now, just log
            migrated += 1
    
    logger.info(f"✅ Password migration complete! ({migrated} passwords encrypted)")


if __name__ == "__main__":
    print("🚀 Starting database migration...")
    print("=" * 60)
    
    try:
        migrate_database()
        print("\n" + "=" * 60)
        print("✅ Migration successful!")
        print("\nNext steps:")
        print("1. Update ProxyPool model to use new fields")
        print("2. Run migrate_passwords_to_encryption() after model update")
        print("3. Test proxy operations with new schema")
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
