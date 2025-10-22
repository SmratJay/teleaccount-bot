#!/usr/bin/env python3
"""
Migration script to add captcha_verified_at column to users table.
Run this on EC2 after pulling the latest code.
"""

import os
from sqlalchemy import create_engine, text

# Read DATABASE_URL from .env file
database_url = None
env_path = '/etc/telegram-bot/.env'

if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        for line in f:
            if line.startswith('DATABASE_URL='):
                database_url = line.strip().split('=', 1)[1]
                break
else:
    # Fallback to environment variable
    database_url = os.getenv('DATABASE_URL')

if not database_url:
    print("❌ DATABASE_URL not found in .env file or environment")
    exit(1)

print("✅ Found DATABASE_URL")

# Create engine and run migration
try:
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        # Add the column if it doesn't exist
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS captcha_verified_at TIMESTAMP;"))
        conn.commit()
        print("✅ Column 'captcha_verified_at' added successfully!")
        print("✅ Migration complete!")
        
except Exception as e:
    print(f"❌ Migration failed: {e}")
    exit(1)
