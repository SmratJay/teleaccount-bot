#!/bin/bash

# Telegram Bot AWS EC2 Setup Script
# This script automates the installation of all dependencies for your Telegram bot

set -e  # Exit on any error

echo "======================================"
echo "🚀 Telegram Bot Setup for AWS EC2"
echo "======================================"
echo ""

# Update system
echo "📦 Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install Python 3.11
echo "🐍 Installing Python 3.11..."
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Set Python 3.11 as default
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Install PostgreSQL
echo "🗄️  Installing PostgreSQL..."
sudo apt install -y postgresql postgresql-contrib

# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Install system dependencies
echo "📚 Installing system dependencies..."
sudo apt install -y \
    git \
    build-essential \
    libpq-dev \
    libssl-dev \
    libffi-dev \
    libjpeg-dev \
    zlib1g-dev \
    wget \
    curl \
    unzip

# Install Python packages
echo "🎨 Installing Python packages..."
pip3 install --upgrade pip
pip3 install wheel setuptools

# Configure PostgreSQL
echo "🔧 Configuring PostgreSQL..."
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"

# Create bot directory
echo "📁 Creating bot directory..."
sudo mkdir -p /var/log/telegram-bot
sudo chown -R ubuntu:ubuntu /var/log/telegram-bot

# Install firewall
echo "🔒 Setting up firewall..."
sudo apt install -y ufw
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

echo ""
echo "======================================"
echo "✅ Setup Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Clone your bot repository: git clone https://github.com/YOUR_USERNAME/teleaccount-bot.git"
echo "2. Install Python dependencies: cd teleaccount-bot && pip3 install -r requirements.txt"
echo "3. Configure environment variables: python3 aws_setup_helper.py"
echo "4. Create database: sudo -u postgres createdb telegrambot"
echo "5. Initialize database: python3 -c 'from database import init_db; init_db()'"
echo "6. Start the bot: sudo systemctl start telebot"
echo ""
echo "📖 See AWS_DEPLOYMENT.md for detailed instructions"
echo ""
