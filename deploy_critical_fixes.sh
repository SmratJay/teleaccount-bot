#!/bin/bash
# CRITICAL FIX DEPLOYMENT SCRIPT
# Deploys the 3 critical fixes to production EC2
# Run this on your EC2 instance as ubuntu user

set -e  # Exit on error

echo "=================================="
echo "🚀 TELEACCOUNT BOT - CRITICAL FIXES"
echo "=================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   echo -e "${RED}❌ Do not run as root. Run as ubuntu user.${NC}"
   exit 1
fi

echo -e "${YELLOW}📋 Pre-Deployment Checklist:${NC}"
echo "1. Have you revoked old credentials? (BotFather, Neon, my.telegram.org)"
echo "2. Have you created /etc/telegram-bot/.env with NEW credentials?"
echo "3. Have you secured SSH (changed 0.0.0.0/0 to your IP)?"
echo ""
read -p "All checks complete? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo -e "${RED}❌ Please complete security checklist first!${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Starting deployment...${NC}"
echo ""

# Stop the service first
echo "1️⃣ Stopping telebot service..."
sudo systemctl stop telebot
echo -e "${GREEN}   ✅ Service stopped${NC}"

# Backup current code
echo "2️⃣ Creating backup..."
BACKUP_DIR="/home/ubuntu/telebot-backup-$(date +%Y%m%d-%H%M%S)"
cp -r "$(pwd)" "$BACKUP_DIR"
echo -e "${GREEN}   ✅ Backup created: $BACKUP_DIR${NC}"

# Pull latest code
echo "3️⃣ Pulling latest code from git..."
git fetch origin
git reset --hard origin/main
echo -e "${GREEN}   ✅ Code updated${NC}"

# Reinstall dependencies (fixes ImportError)
echo "4️⃣ Reinstalling Python dependencies..."
pip3 install -r requirements.txt --upgrade --quiet
echo -e "${GREEN}   ✅ Dependencies updated${NC}"

# Verify .env file exists
echo "5️⃣ Verifying environment configuration..."
if [ ! -f "/etc/telegram-bot/.env" ]; then
    echo -e "${RED}   ❌ ERROR: /etc/telegram-bot/.env not found!${NC}"
    echo "   Create it with:"
    echo "   sudo nano /etc/telegram-bot/.env"
    exit 1
fi

# Check for required variables
required_vars=("TELEGRAM_BOT_TOKEN" "DATABASE_URL" "API_ID" "API_HASH")
missing_vars=0

for var in "${required_vars[@]}"; do
    if ! sudo grep -q "^${var}=" /etc/telegram-bot/.env; then
        echo -e "${RED}   ❌ Missing: $var${NC}"
        missing_vars=1
    fi
done

if [ $missing_vars -eq 1 ]; then
    echo -e "${RED}   ❌ ERROR: Missing required environment variables${NC}"
    exit 1
fi

echo -e "${GREEN}   ✅ Environment configuration OK${NC}"

# Start the service
echo "6️⃣ Starting telebot service..."
sudo systemctl start telebot
sleep 3
echo -e "${GREEN}   ✅ Service started${NC}"

# Check service status
echo "7️⃣ Verifying service health..."
sleep 2

if sudo systemctl is-active --quiet telebot; then
    echo -e "${GREEN}   ✅ Service is ACTIVE${NC}"
else
    echo -e "${RED}   ❌ Service failed to start!${NC}"
    echo ""
    echo "Last 30 lines of logs:"
    sudo journalctl -u telebot -n 30 --no-pager
    exit 1
fi

# Check for critical errors in logs
echo "8️⃣ Checking for errors in logs..."
sleep 2

ERROR_COUNT=$(sudo journalctl -u telebot --since "1 minute ago" | grep -c "ImportError\|SSL connection has been closed\|CRITICAL" || true)

if [ $ERROR_COUNT -gt 0 ]; then
    echo -e "${YELLOW}   ⚠️  Found $ERROR_COUNT potential errors${NC}"
    echo "   Review logs with: sudo journalctl -u telebot -f"
else
    echo -e "${GREEN}   ✅ No critical errors detected${NC}"
fi

echo ""
echo "=================================="
echo -e "${GREEN}🎉 DEPLOYMENT COMPLETE!${NC}"
echo "=================================="
echo ""
echo "📊 Next Steps:"
echo "1. Monitor logs:  sudo journalctl -u telebot -f"
echo "2. Test bot:      Send /start to your bot on Telegram"
echo "3. Watch for:     No ImportError, no SSL errors"
echo ""
echo "📝 Backup location: $BACKUP_DIR"
echo ""
echo "🔍 Quick Health Check:"
echo "   Service status:  sudo systemctl status telebot"
echo "   View logs:       sudo journalctl -u telebot -f"
echo "   Restart service: sudo systemctl restart telebot"
echo ""

# Offer to show logs
read -p "Would you like to view live logs now? (yes/no): " view_logs

if [ "$view_logs" = "yes" ]; then
    echo ""
    echo "Opening live logs (Ctrl+C to exit)..."
    echo ""
    sleep 1
    sudo journalctl -u telebot -f
fi
