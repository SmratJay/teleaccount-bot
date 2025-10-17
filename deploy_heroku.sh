#!/bin/bash

# =============================================================================
# HEROKU DEPLOYMENT SCRIPT - TELEACCOUNT BOT
# =============================================================================
# This script will deploy your Telegram bot to Heroku automatically
# Make sure you have Heroku CLI installed: https://devcenter.heroku.com/articles/heroku-cli
# =============================================================================

echo "🚀 Starting Heroku deployment for TeleAccount Bot..."

# Check if Heroku CLI is installed
if ! command -v heroku &> /dev/null; then
    echo "❌ Heroku CLI is not installed!"
    echo "🔗 Please install it from: https://devcenter.heroku.com/articles/heroku-cli"
    exit 1
fi

# Check if user is logged in to Heroku
echo "🔐 Checking Heroku authentication..."
if ! heroku auth:whoami &> /dev/null; then
    echo "❌ Not logged in to Heroku!"
    echo "🔑 Please run: heroku login"
    exit 1
fi

echo "✅ Heroku CLI detected and authenticated"

# Get app name from user
echo ""
read -p "📝 Enter your Heroku app name (must be unique): " APP_NAME

if [ -z "$APP_NAME" ]; then
    echo "❌ App name cannot be empty!"
    exit 1
fi

echo ""
echo "🎯 App name: $APP_NAME"
echo "🌐 Your bot will be available at: https://$APP_NAME.herokuapp.com"
echo ""

# Confirm deployment
read -p "🚀 Continue with deployment? (y/N): " CONFIRM
if [[ $CONFIRM != [yY] && $CONFIRM != [yY][eE][sS] ]]; then
    echo "❌ Deployment cancelled"
    exit 0
fi

echo ""
echo "🚀 Starting deployment process..."

# Initialize git repository if not exists
if [ ! -d ".git" ]; then
    echo "📦 Initializing git repository..."
    git init
    git add .
    git commit -m "Initial commit for Heroku deployment"
else
    echo "📦 Git repository already exists"
    # Stage current changes
    git add .
    if git diff --staged --quiet; then
        echo "📦 No changes to commit"
    else
        git commit -m "Updates for Heroku deployment"
    fi
fi

# Create Heroku app
echo "🏗️  Creating Heroku app: $APP_NAME"
if heroku create $APP_NAME; then
    echo "✅ Heroku app created successfully!"
else
    echo "❌ Failed to create Heroku app (name might be taken)"
    echo "💡 Try a different app name"
    exit 1
fi

# Add PostgreSQL addon
echo "🐘 Adding PostgreSQL database..."
if heroku addons:create heroku-postgresql:essential-0 --app $APP_NAME; then
    echo "✅ PostgreSQL database added!"
else
    echo "❌ Failed to add PostgreSQL addon"
    exit 1
fi

# Set config vars
echo "⚙️  Setting up environment variables..."

# IMPORTANT: Update these values with your actual tokens!
echo "🔑 IMPORTANT: You need to set these environment variables manually:"
echo ""
echo "Required variables to set in Heroku dashboard or via CLI:"
echo "heroku config:set BOT_TOKEN='your_bot_token_here' --app $APP_NAME"
echo "heroku config:set API_ID='your_api_id' --app $APP_NAME"
echo "heroku config:set API_HASH='your_api_hash' --app $APP_NAME"
echo "heroku config:set TELEGRAM_API_ID='your_api_id' --app $APP_NAME"
echo "heroku config:set TELEGRAM_API_HASH='your_api_hash' --app $APP_NAME"
echo "heroku config:set ADMIN_CHAT_ID='6733908384' --app $APP_NAME"
echo "heroku config:set ADMIN_USER_ID='6733908384' --app $APP_NAME"
echo "heroku config:set LEADER_CHANNEL_ID='-1001234567890' --app $APP_NAME"
echo ""

# Set basic config vars
heroku config:set DB_USER='postgres' --app $APP_NAME
heroku config:set DEBUG='False' --app $APP_NAME
heroku config:set ENVIRONMENT='production' --app $APP_NAME
heroku config:set FLASK_ENV='production' --app $APP_NAME
heroku config:set PORT='8080' --app $APP_NAME

# Generate secret key
SECRET_KEY=$(openssl rand -hex 32)
heroku config:set SECRET_KEY="$SECRET_KEY" --app $APP_NAME

# Generate encryption key
ENCRYPTION_KEY=$(openssl rand -hex 32)
heroku config:set ENCRYPTION_KEY="$ENCRYPTION_KEY" --app $APP_NAME

echo "✅ Basic config vars set!"

# Deploy to Heroku
echo "🚀 Deploying to Heroku..."
if git push heroku main; then
    echo "✅ Deployment successful!"
else
    echo "❌ Deployment failed"
    echo "📋 Check the logs with: heroku logs --tail --app $APP_NAME"
    exit 1
fi

# Wait for release
echo "⏳ Waiting for release to complete..."
sleep 10

# Check app status
echo "🔍 Checking app status..."
heroku ps --app $APP_NAME

echo ""
echo "🎉 DEPLOYMENT COMPLETE!"
echo ""
echo "📱 Your bot is now live at: https://$APP_NAME.herokuapp.com"
echo "🔗 Heroku dashboard: https://dashboard.heroku.com/apps/$APP_NAME"
echo ""
echo "📋 Next steps:"
echo "1. Go to Heroku dashboard: https://dashboard.heroku.com/apps/$APP_NAME/settings"
echo "2. Click 'Reveal Config Vars'"
echo "3. Set these REQUIRED variables:"
echo "   - BOT_TOKEN (from @BotFather)"
echo "   - API_ID (from my.telegram.org)" 
echo "   - API_HASH (from my.telegram.org)"
echo "   - TELEGRAM_API_ID (same as API_ID)"
echo "   - TELEGRAM_API_HASH (same as API_HASH)"
echo "4. Update ADMIN_CHAT_ID and ADMIN_USER_ID with your Telegram user ID"
echo "5. Update LEADER_CHANNEL_ID with your channel ID"
echo ""
echo "🔧 Useful commands:"
echo "heroku logs --tail --app $APP_NAME          # View live logs"
echo "heroku ps --app $APP_NAME                   # Check app status"
echo "heroku config --app $APP_NAME               # View config vars"
echo "heroku restart --app $APP_NAME              # Restart app"
echo ""
echo "✅ Bot deployment completed successfully!"