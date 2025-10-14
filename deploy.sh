#!/bin/bash

# Telegram Account Bot Deployment Script
# Run this script to deploy the bot to your server

set -e  # Exit on any error

echo "🚀 Telegram Account Bot Deployment"
echo "=================================="

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Please don't run this script as root for security reasons"
    exit 1
fi

# Update system packages
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install system dependencies
echo "📋 Installing system dependencies..."
sudo apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib nginx redis-server git

# Create application directory
APP_DIR="/opt/teleaccount_bot"
echo "📁 Creating application directory: $APP_DIR"
sudo mkdir -p $APP_DIR
sudo chown $USER:$USER $APP_DIR

# Clone or copy application
if [ -d ".git" ]; then
    echo "📥 Copying application files..."
    cp -r . $APP_DIR/
else
    echo "📥 Cloning from repository..."
    git clone <your-repo-url> $APP_DIR
fi

cd $APP_DIR

# Create virtual environment
echo "🐍 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "📦 Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# Database setup
echo "🗄️ Setting up PostgreSQL database..."
sudo -u postgres psql -c "CREATE DATABASE teleaccount_bot;" || true
sudo -u postgres psql -c "CREATE USER bot_user WITH PASSWORD 'change_this_password';" || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE teleaccount_bot TO bot_user;" || true

# Environment file setup
echo "⚙️ Setting up environment configuration..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "📝 Please edit .env file with your configuration:"
    echo "   - BOT_TOKEN (from @BotFather)"
    echo "   - API_ID and API_HASH (from my.telegram.org)"
    echo "   - ADMIN_USER_ID (your Telegram user ID)"
    echo "   - Database password (change from default)"
    echo ""
    echo "Press Enter when ready..."
    read
fi

# Initialize database
echo "🔧 Initializing database tables..."
python -c "from database import create_tables; create_tables()"

# Create systemd service
echo "🔄 Creating systemd service..."
sudo tee /etc/systemd/system/teleaccount-bot.service > /dev/null <<EOF
[Unit]
Description=Telegram Account Bot
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
ExecStart=$APP_DIR/venv/bin/python main.py
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ReadWritePaths=$APP_DIR
ProtectHome=yes

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
echo "🚀 Starting bot service..."
sudo systemctl daemon-reload
sudo systemctl enable teleaccount-bot
sudo systemctl start teleaccount-bot

# Setup log rotation
echo "📋 Setting up log rotation..."
sudo tee /etc/logrotate.d/teleaccount-bot > /dev/null <<EOF
$APP_DIR/logs/*.log {
    weekly
    rotate 4
    compress
    delaycompress
    missingok
    notifempty
    create 644 $USER $USER
    postrotate
        systemctl reload teleaccount-bot
    endscript
}
EOF

# Create backup script
echo "💾 Creating backup script..."
sudo tee /usr/local/bin/backup-teleaccount-bot > /dev/null <<EOF
#!/bin/bash
# Backup script for Telegram Account Bot

BACKUP_DIR="/var/backups/teleaccount-bot"
DATE=\$(date +%Y%m%d_%H%M%S)

mkdir -p \$BACKUP_DIR

# Backup database
pg_dump -h localhost -U bot_user teleaccount_bot | gzip > \$BACKUP_DIR/database_\$DATE.sql.gz

# Backup application files
tar -czf \$BACKUP_DIR/app_\$DATE.tar.gz -C $APP_DIR .

# Keep only last 7 days of backups
find \$BACKUP_DIR -name "*.gz" -mtime +7 -delete

echo "Backup completed: \$DATE"
EOF

sudo chmod +x /usr/local/bin/backup-teleaccount-bot

# Add to crontab for daily backups
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/backup-teleaccount-bot") | crontab -

# Setup basic firewall
echo "🔒 Configuring firewall..."
sudo ufw --force enable
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443

# Final checks
echo "✅ Running deployment tests..."
python test_bot.py

echo ""
echo "🎉 Deployment Complete!"
echo "======================"
echo ""
echo "📊 Service Status:"
sudo systemctl status teleaccount-bot --no-pager

echo ""
echo "📋 Next Steps:"
echo "1. Edit $APP_DIR/.env with your bot configuration"
echo "2. Restart the service: sudo systemctl restart teleaccount-bot"
echo "3. Check logs: sudo journalctl -u teleaccount-bot -f"
echo "4. Test your bot in Telegram with /start"
echo ""
echo "📚 Management Commands:"
echo "• View logs: sudo journalctl -u teleaccount-bot -f"
echo "• Restart bot: sudo systemctl restart teleaccount-bot"
echo "• Stop bot: sudo systemctl stop teleaccount-bot"
echo "• Run backup: sudo /usr/local/bin/backup-teleaccount-bot"
echo ""
echo "🔒 Security Notes:"
echo "• Change default database password in .env"
echo "• Keep your bot token secure"
echo "• Regular backups are configured (daily at 2 AM)"
echo "• Monitor logs for security events"