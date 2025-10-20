"""
Database Migration Script for Account Freeze System
Adds necessary fields to telegram_accounts table
"""
import sys
import os
import logging

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, parent_dir)

from database import get_db_session, close_db_session
from database.models import TelegramAccount
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_database():
    """Add freeze-related fields to telegram_accounts table"""
    db = get_db_session()
    
    try:
        logger.info("Starting database migration for account freeze system...")
        
        # Check if fields already exist (SQLite compatible)
        result = db.execute(text("PRAGMA table_info(telegram_accounts)"))
        columns_info = result.fetchall()
        existing_columns = [col[1] for col in columns_info]  # col[1] is column name
        
        logger.info(f"Existing columns in telegram_accounts: {len(existing_columns)} columns")
        logger.info(f"Existing freeze columns: {[c for c in existing_columns if 'freeze' in c or c in ['is_frozen', 'can_be_sold', 'multi_device_last_detected']]}")
        
        migrations_needed = []
        
        # Check each required field
        if 'is_frozen' not in existing_columns:
            migrations_needed.append("""
                ALTER TABLE telegram_accounts 
                ADD COLUMN is_frozen BOOLEAN DEFAULT FALSE
            """)
        
        if 'freeze_reason' not in existing_columns:
            migrations_needed.append("""
                ALTER TABLE telegram_accounts 
                ADD COLUMN freeze_reason TEXT
            """)
        
        if 'freeze_timestamp' not in existing_columns:
            migrations_needed.append("""
                ALTER TABLE telegram_accounts 
                ADD COLUMN freeze_timestamp TIMESTAMP
            """)
        
        if 'freeze_duration_hours' not in existing_columns:
            migrations_needed.append("""
                ALTER TABLE telegram_accounts 
                ADD COLUMN freeze_duration_hours INTEGER
            """)
        
        if 'frozen_by_admin_id' not in existing_columns:
            migrations_needed.append("""
                ALTER TABLE telegram_accounts 
                ADD COLUMN frozen_by_admin_id INTEGER
            """)
        
        if 'can_be_sold' not in existing_columns:
            migrations_needed.append("""
                ALTER TABLE telegram_accounts 
                ADD COLUMN can_be_sold BOOLEAN DEFAULT TRUE
            """)
        
        if 'multi_device_last_detected' not in existing_columns:
            migrations_needed.append("""
                ALTER TABLE telegram_accounts 
                ADD COLUMN multi_device_last_detected TIMESTAMP
            """)
        
        if not migrations_needed:
            logger.info("✅ All required columns already exist. No migration needed.")
            return True
        
        # Execute migrations
        logger.info(f"Executing {len(migrations_needed)} migrations...")
        
        for i, migration in enumerate(migrations_needed, 1):
            try:
                logger.info(f"Migration {i}/{len(migrations_needed)}: {migration.strip()[:50]}...")
                db.execute(text(migration))
                db.commit()
                logger.info(f"✅ Migration {i} completed")
            except Exception as e:
                logger.error(f"❌ Migration {i} failed: {e}")
                db.rollback()
                return False
        
        # Note: SQLite doesn't support adding foreign keys to existing tables
        # The relationship will be enforced at the application level
        
        logger.info("🎉 Database migration completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        db.rollback()
        return False
        
    finally:
        close_db_session(db)


def verify_migration():
    """Verify all fields were added correctly"""
    db = get_db_session()
    
    try:
        # SQLite compatible verification
        result = db.execute(text("PRAGMA table_info(telegram_accounts)"))
        all_columns = result.fetchall()
        
        # Filter for freeze-related columns
        freeze_columns = [
            col for col in all_columns 
            if col[1] in (
                'is_frozen', 'freeze_reason', 'freeze_timestamp',
                'freeze_duration_hours', 'frozen_by_admin_id', 
                'can_be_sold', 'multi_device_last_detected'
            )
        ]
        
        if not freeze_columns:
            logger.error("❌ No freeze columns found! Migration may have failed.")
            return False
        
        logger.info("\n✅ Migration Verification:")
        logger.info("-" * 60)
        for col in freeze_columns:
            col_id, col_name, col_type, not_null, default_val, pk = col
            logger.info(f"  {col_name:30} {col_type:20} {default_val or 'NULL'}")
        logger.info("-" * 60)
        
        expected_columns = {
            'is_frozen', 'freeze_reason', 'freeze_timestamp',
            'freeze_duration_hours', 'frozen_by_admin_id',
            'can_be_sold', 'multi_device_last_detected'
        }
        
        found_columns = {col[1] for col in freeze_columns}
        missing = expected_columns - found_columns
        
        if missing:
            logger.error(f"❌ Missing columns: {missing}")
            return False
        
        logger.info("✅ All columns verified successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False
        
    finally:
        close_db_session(db)


if __name__ == '__main__':
    print("\n" + "="*60)
    print("  ACCOUNT FREEZE SYSTEM - DATABASE MIGRATION")
    print("="*60 + "\n")
    
    # Run migration
    if migrate_database():
        print("\n" + "="*60)
        print("  VERIFYING MIGRATION")
        print("="*60 + "\n")
        
        # Verify
        if verify_migration():
            print("\n" + "="*60)
            print("  ✅ MIGRATION COMPLETE AND VERIFIED")
            print("="*60 + "\n")
            print("Next steps:")
            print("1. Test account freezing in the bot")
            print("2. Check admin panel for new buttons")
            print("3. Simulate multi-device detection")
            print("4. Verify notifications are sent\n")
            sys.exit(0)
        else:
            print("\n❌ Verification failed. Check logs above.\n")
            sys.exit(1)
    else:
        print("\n❌ Migration failed. Check logs above.\n")
        sys.exit(1)

