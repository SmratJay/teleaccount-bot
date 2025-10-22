# Database Migration Guide for EC2 Deployment

## Overview

This guide explains how to manage database schema changes when deploying code updates from Replit to your EC2 instance.

## What is Alembic?

Alembic is a database migration tool for SQLAlchemy. It tracks changes to your database schema and applies them safely without losing data.

## When You Make Code Changes on Replit

### Step 1: Add the New Database Field (Already Done)

The `captcha_verified_at` field has been added to `database/models.py`:

```python
captcha_verified_at = Column(DateTime, nullable=True)  # 7-day CAPTCHA cache
```

### Step 2: Deploy to EC2

```bash
# SSH to your EC2 instance
ssh -i your-key.pem ubuntu@13.53.80.228

# Navigate to project directory
cd TelegramAccountSellingBot

# Pull latest changes from Replit
git pull origin main
```

### Step 3: Run Database Migration on EC2

You have **two options** to add the new column:

#### Option A: Manual SQL (Quick & Simple)
```bash
# Connect to your PostgreSQL database
psql $DATABASE_URL

# Add the column manually
ALTER TABLE users ADD COLUMN IF NOT EXISTS captcha_verified_at TIMESTAMP;

# Exit psql
\q
```

#### Option B: Alembic Migration (Recommended for Future)
```bash
# Create migration from model changes
alembic revision --autogenerate -m "Add captcha_verified_at field"

# Review the migration file (optional)
cat alembic/versions/*.py

# Apply the migration
alembic upgrade head
```

### Step 4: Restart the Bot
```bash
sudo systemctl restart telebot
sudo systemctl status telebot
```

### Step 5: Verify
```bash
# Check if the column exists
psql $DATABASE_URL -c "SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='captcha_verified_at';"

# Check logs
sudo journalctl -u telebot -f
```

## Future Database Changes Workflow

1. **On Replit**: Modify `database/models.py`
2. **Push to Git**: `git push origin main`
3. **On EC2**: 
   ```bash
   git pull
   alembic revision --autogenerate -m "Description of change"
   alembic upgrade head
   sudo systemctl restart telebot
   ```

## Important Notes

⚠️ **DO NOT** manually edit migration files unless you know what you're doing  
✅ **ALWAYS** test migrations on a backup database first in production  
✅ **ALWAYS** backup your database before running migrations:
   ```bash
   pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
   ```

## Troubleshooting

### "Column already exists" Error
```bash
# Safe: This will not throw error if column exists
psql $DATABASE_URL -c "ALTER TABLE users ADD COLUMN IF NOT EXISTS captcha_verified_at TIMESTAMP;"
```

### Migration Conflicts
```bash
# Check current migration status
alembic current

# Show migration history
alembic history

# If stuck, stamp the current state
alembic stamp head
```

### Database Connection Issues
```bash
# Verify DATABASE_URL is set
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT version();"
```

## What Changed in This Update

### New Features:
1. **7-Day CAPTCHA Cache**: Users who verify CAPTCHA are cached for 7 days
   - On `/start`, bot checks `captcha_verified_at` timestamp
   - If verified < 7 days ago → skip to main menu
   - If expired/missing → show CAPTCHA verification

2. **Faster CAPTCHA**: 
   - Image size reduced: 280x90 → 200x70 pixels
   - Character count: 5 → 4 characters
   - Faster generation and easier for users

3. **Alembic Setup**: Database migrations are now version-controlled

### Database Schema Change:
- **Table**: `users`
- **Column**: `captcha_verified_at` (TIMESTAMP, nullable)
- **Purpose**: Store when user last verified CAPTCHA

### Code Changes:
- `handlers/real_handlers.py`: `/start` checks CAPTCHA cache
- `handlers/verification_flow.py`: Sets `captcha_verified_at` on success
- `services/captcha.py`: Optimized image generation
- `database/models.py`: Added `captcha_verified_at` field

## Quick Reference

```bash
# Complete deployment workflow
ssh -i your-key.pem ubuntu@13.53.80.228
cd TelegramAccountSellingBot
git pull
psql $DATABASE_URL -c "ALTER TABLE users ADD COLUMN IF NOT EXISTS captcha_verified_at TIMESTAMP;"
sudo systemctl restart telebot
sudo journalctl -u telebot -f
```

That's it! Your database is now updated and the bot will use the 7-day CAPTCHA cache.
