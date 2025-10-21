"""
Migration to add CAPTCHA fields to users table.
Run this script to add the necessary columns for persistent CAPTCHA storage.
"""
import sqlite3
import os

def migrate_captcha_fields():
    """Add CAPTCHA-related fields to the users table."""
    db_path = 'teleaccount_bot.db'

    if not os.path.exists(db_path):
        print("Database file not found!")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]

        columns_to_add = []

        if 'captcha_answer' not in columns:
            columns_to_add.append("ALTER TABLE users ADD COLUMN captcha_answer TEXT")

        if 'captcha_type' not in columns:
            columns_to_add.append("ALTER TABLE users ADD COLUMN captcha_type TEXT")

        if 'captcha_image_path' not in columns:
            columns_to_add.append("ALTER TABLE users ADD COLUMN captcha_image_path TEXT")

        if 'verification_step' not in columns:
            columns_to_add.append("ALTER TABLE users ADD COLUMN verification_step INTEGER DEFAULT 0")

        # Execute the ALTER TABLE statements
        for sql in columns_to_add:
            print(f"Executing: {sql}")
            cursor.execute(sql)

        conn.commit()
        print(f"✅ Migration completed! Added {len(columns_to_add)} columns to users table.")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_captcha_fields()