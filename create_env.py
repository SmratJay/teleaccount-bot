#!/usr/bin/env python3
"""
Automatic .env file generator for Telegram Bot
Creates /etc/telegram-bot/.env with all required credentials
"""

import os
import sys

ENV_DIR = "/etc/telegram-bot"
ENV_FILE = "/etc/telegram-bot/.env"

ENV_CONTENT = """TELEGRAM_BOT_TOKEN=8483671369:AAEOTZCDpCPiarfZHdb1Z5CFAZoMvdtmeKs
API_ID=21734417
API_HASH=d64eb98d90eb41b8ba3644e3722a3714
ADMIN_TELEGRAM_ID=6733908384
SECRET_KEY=nQ0&@U*vfBYMqO#B&33bnEb#w$veWi%&
DATABASE_URL=postgresql://neondb_owner:npg_oiTEI2qfeW8j@ep-silent-glade-ae6wc05t.c-2.us-east-2.aws.neon.tech/neondb?sslmode=require
"""

def main():
    if os.geteuid() != 0:
        print("❌ Error: This script must be run with sudo")
        print("   Run: sudo python3 create_env.py")
        sys.exit(1)
    
    try:
        if not os.path.exists(ENV_DIR):
            os.makedirs(ENV_DIR, mode=0o755)
            print(f"✅ Created directory: {ENV_DIR}")
        
        with open(ENV_FILE, 'w') as f:
            f.write(ENV_CONTENT.strip() + '\n')
        
        os.chmod(ENV_FILE, 0o600)
        print(f"✅ Created file: {ENV_FILE}")
        print(f"✅ Set permissions: 600 (read/write for owner only)")
        
        print("\n" + "="*60)
        print("🎉 Environment file created successfully!")
        print("="*60)
        print("\nNext steps:")
        print("1. Start the bot:  sudo systemctl start telebot")
        print("2. Check status:   sudo systemctl status telebot")
        print("3. View logs:      sudo journalctl -u telebot -f")
        print("\n")
        
    except Exception as e:
        print(f"❌ Error creating .env file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
