"""
Add provider column to proxy_pool table
"""
import os
import sys
import sqlite3

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def add_provider_column():
    """Add provider column to proxy_pool table."""
    
    db_path = os.path.join(os.path.dirname(__file__), 'teleaccount_bot.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return False
    
    print(f"📊 Migrating database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(proxy_pool)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'provider' in columns:
            print("✅ Column 'provider' already exists")
        else:
            print("➕ Adding 'provider' column...")
            cursor.execute("ALTER TABLE proxy_pool ADD COLUMN provider VARCHAR(50) DEFAULT 'free'")
            print("✅ Column added successfully")
        
        # Set all existing proxies to 'free' provider
        cursor.execute("UPDATE proxy_pool SET provider = 'free' WHERE provider IS NULL")
        updated = cursor.rowcount
        print(f"✅ Updated {updated} existing proxies to 'free' provider")
        
        conn.commit()
        conn.close()
        
        print("\n" + "=" * 80)
        print("✅ MIGRATION COMPLETE!")
        print("=" * 80)
        print("Next step: Run configure_webshare_only.py to fetch WebShare proxies")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    add_provider_column()
