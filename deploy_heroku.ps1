# =============================================================================
# HEROKU DEPLOYMENT SCRIPT - TELEACCOUNT BOT (PowerShell)
# =============================================================================
# This script will deploy your Telegram bot to Heroku automatically
# Make sure you have Heroku CLI installed: https://devcenter.heroku.com/articles/heroku-cli
# =============================================================================

Write-Host "🚀 Starting Heroku deployment for TeleAccount Bot..." -ForegroundColor Green

# Check if Heroku CLI is installed
try {
    heroku --version | Out-Null
    Write-Host "✅ Heroku CLI detected" -ForegroundColor Green
} catch {
    Write-Host "❌ Heroku CLI is not installed!" -ForegroundColor Red
    Write-Host "🔗 Please install it from: https://devcenter.heroku.com/articles/heroku-cli" -ForegroundColor Yellow
    exit 1
}

# Check if user is logged in to Heroku
try {
    heroku auth:whoami | Out-Null
    Write-Host "✅ Heroku authentication verified" -ForegroundColor Green
} catch {
    Write-Host "❌ Not logged in to Heroku!" -ForegroundColor Red
    Write-Host "🔑 Please run: heroku login" -ForegroundColor Yellow
    exit 1
}

# Get app name from user
Write-Host ""
$APP_NAME = Read-Host "📝 Enter your Heroku app name (must be unique)"

if ([string]::IsNullOrEmpty($APP_NAME)) {
    Write-Host "❌ App name cannot be empty!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "🎯 App name: $APP_NAME" -ForegroundColor Cyan
Write-Host "🌐 Your bot will be available at: https://$APP_NAME.herokuapp.com" -ForegroundColor Cyan
Write-Host ""

# Confirm deployment
$CONFIRM = Read-Host "🚀 Continue with deployment? (y/N)"
if ($CONFIRM -ne "y" -and $CONFIRM -ne "Y" -and $CONFIRM -ne "yes" -and $CONFIRM -ne "YES") {
    Write-Host "❌ Deployment cancelled" -ForegroundColor Red
    exit 0
}

Write-Host ""
Write-Host "🚀 Starting deployment process..." -ForegroundColor Green

# Initialize git repository if not exists
if (-not (Test-Path ".git")) {
    Write-Host "📦 Initializing git repository..." -ForegroundColor Yellow
    git init
    git add .
    git commit -m "Initial commit for Heroku deployment"
} else {
    Write-Host "📦 Git repository already exists" -ForegroundColor Yellow
    # Stage current changes
    git add .
    $status = git status --porcelain
    if ($status) {
        git commit -m "Updates for Heroku deployment"
    } else {
        Write-Host "📦 No changes to commit" -ForegroundColor Yellow
    }
}

# Create Heroku app
Write-Host "🏗️ Creating Heroku app: $APP_NAME" -ForegroundColor Yellow
try {
    heroku create $APP_NAME
    Write-Host "✅ Heroku app created successfully!" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to create Heroku app (name might be taken)" -ForegroundColor Red
    Write-Host "💡 Try a different app name" -ForegroundColor Yellow
    exit 1
}

# Add PostgreSQL addon
Write-Host "🐘 Adding PostgreSQL database..." -ForegroundColor Yellow
try {
    heroku addons:create heroku-postgresql:essential-0 --app $APP_NAME
    Write-Host "✅ PostgreSQL database added!" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to add PostgreSQL addon" -ForegroundColor Red
    exit 1
}

# Set config vars
Write-Host "⚙️ Setting up environment variables..." -ForegroundColor Yellow

Write-Host ""
Write-Host "🔑 IMPORTANT: You need to set these environment variables manually:" -ForegroundColor Red
Write-Host ""
Write-Host "Required variables to set in Heroku dashboard or via CLI:" -ForegroundColor Cyan
Write-Host "heroku config:set BOT_TOKEN='your_bot_token_here' --app $APP_NAME" -ForegroundColor White
Write-Host "heroku config:set API_ID='your_api_id' --app $APP_NAME" -ForegroundColor White
Write-Host "heroku config:set API_HASH='your_api_hash' --app $APP_NAME" -ForegroundColor White
Write-Host "heroku config:set TELEGRAM_API_ID='your_api_id' --app $APP_NAME" -ForegroundColor White
Write-Host "heroku config:set TELEGRAM_API_HASH='your_api_hash' --app $APP_NAME" -ForegroundColor White
Write-Host "heroku config:set ADMIN_CHAT_ID='6733908384' --app $APP_NAME" -ForegroundColor White
Write-Host "heroku config:set ADMIN_USER_ID='6733908384' --app $APP_NAME" -ForegroundColor White
Write-Host "heroku config:set LEADER_CHANNEL_ID='-1001234567890' --app $APP_NAME" -ForegroundColor White
Write-Host ""

# Set basic config vars
heroku config:set DB_USER='postgres' --app $APP_NAME
heroku config:set DEBUG='False' --app $APP_NAME
heroku config:set ENVIRONMENT='production' --app $APP_NAME
heroku config:set FLASK_ENV='production' --app $APP_NAME
heroku config:set PORT='8080' --app $APP_NAME

# Generate secret keys
$SECRET_KEY = -join ((1..64) | ForEach {Get-Random -input ([char[]]('0123456789abcdef'))})
$ENCRYPTION_KEY = -join ((1..64) | ForEach {Get-Random -input ([char[]]('0123456789abcdef'))})

heroku config:set SECRET_KEY="$SECRET_KEY" --app $APP_NAME
heroku config:set ENCRYPTION_KEY="$ENCRYPTION_KEY" --app $APP_NAME

Write-Host "✅ Basic config vars set!" -ForegroundColor Green

# Deploy to Heroku
Write-Host "🚀 Deploying to Heroku..." -ForegroundColor Yellow
try {
    git push heroku main
    Write-Host "✅ Deployment successful!" -ForegroundColor Green
} catch {
    Write-Host "❌ Deployment failed" -ForegroundColor Red
    Write-Host "📋 Check the logs with: heroku logs --tail --app $APP_NAME" -ForegroundColor Yellow
    exit 1
}

# Wait for release
Write-Host "⏳ Waiting for release to complete..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Check app status
Write-Host "🔍 Checking app status..." -ForegroundColor Yellow
heroku ps --app $APP_NAME

Write-Host ""
Write-Host "🎉 DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host ""
Write-Host "📱 Your bot is now live at: https://$APP_NAME.herokuapp.com" -ForegroundColor Cyan
Write-Host "🔗 Heroku dashboard: https://dashboard.heroku.com/apps/$APP_NAME" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Yellow
Write-Host "1. Go to Heroku dashboard: https://dashboard.heroku.com/apps/$APP_NAME/settings" -ForegroundColor White
Write-Host "2. Click 'Reveal Config Vars'" -ForegroundColor White
Write-Host "3. Set these REQUIRED variables:" -ForegroundColor White
Write-Host "   - BOT_TOKEN (from @BotFather)" -ForegroundColor White
Write-Host "   - API_ID (from my.telegram.org)" -ForegroundColor White
Write-Host "   - API_HASH (from my.telegram.org)" -ForegroundColor White
Write-Host "   - TELEGRAM_API_ID (same as API_ID)" -ForegroundColor White
Write-Host "   - TELEGRAM_API_HASH (same as API_HASH)" -ForegroundColor White
Write-Host "4. Update ADMIN_CHAT_ID and ADMIN_USER_ID with your Telegram user ID" -ForegroundColor White
Write-Host "5. Update LEADER_CHANNEL_ID with your channel ID" -ForegroundColor White
Write-Host ""
Write-Host "🔧 Useful commands:" -ForegroundColor Yellow
Write-Host "heroku logs --tail --app $APP_NAME          # View live logs" -ForegroundColor White
Write-Host "heroku ps --app $APP_NAME                   # Check app status" -ForegroundColor White
Write-Host "heroku config --app $APP_NAME               # View config vars" -ForegroundColor White
Write-Host "heroku restart --app $APP_NAME              # Restart app" -ForegroundColor White
Write-Host ""
Write-Host "✅ Bot deployment completed successfully!" -ForegroundColor Green