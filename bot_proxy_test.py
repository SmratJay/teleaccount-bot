"""
Simple Bot Test - Proxy System Only
Tests the proxy ecosystem without account selling features
"""
import logging
import asyncio
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Import proxy system
from services.proxy_manager import proxy_manager, OperationType
from services.webshare_provider import WebShareProvider
from database import get_db_session, close_db_session
from database.models import ProxyPool

# Admin command handlers
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    await update.message.reply_text(
        "🤖 *Proxy System Test Bot*\n\n"
        "Available commands:\n"
        "/proxy\\_stats \\- View proxy statistics\n"
        "/proxy\\_health \\- Check proxy health\n"
        "/proxy\\_test \\- Test proxy selection\n"
        "/proxy\\_providers \\- View providers\n"
        "/proxy\\_strategy <name> \\- Change strategy\n"
        "/fetch\\_webshare \\- Fetch WebShare\\.io proxies\n"
        "/webshare\\_info \\- View WebShare account info",
        parse_mode='MarkdownV2'
    )

async def proxy_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show proxy statistics"""
    try:
        db = get_db_session()
        total_proxies = db.query(ProxyPool).count()
        active_proxies = db.query(ProxyPool).filter(ProxyPool.is_active == True).count()
        
        stats = proxy_manager.get_statistics()
        
        message = f"""📊 *Proxy Statistics*

Total Proxies: {total_proxies}
Active Proxies: {active_proxies}
Current Strategy: {stats.get('current_strategy', 'N/A')}
Last Refresh: {stats.get('last_refresh', 'N/A')}

Operation Counts:
"""
        for op_type, count in stats.get('operation_counts', {}).items():
            message += f"  • {op_type}: {count}\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        close_db_session(db)
    except Exception as e:
        logger.error(f"Error in proxy_stats: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def proxy_health_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check proxy health"""
    try:
        health = proxy_manager.get_health_status()
        
        message = f"""🏥 *Proxy Health*

Status: {health.get('status', 'Unknown')}
Healthy Proxies: {health.get('healthy_count', 0)}
Unhealthy Proxies: {health.get('unhealthy_count', 0)}
Average Success Rate: {health.get('avg_success_rate', 0):.1f}%
"""
        
        await update.message.reply_text(message, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in proxy_health: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def proxy_test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test proxy selection for different operations"""
    try:
        message = "🧪 *Proxy Selection Test*\n\n"
        
        # Test different operation types
        operations = [
            (OperationType.ACCOUNT_CREATION, "US"),
            (OperationType.LOGIN, "GB"),
            (OperationType.OTP_RETRIEVAL, "FR")
        ]
        
        for op_type, country in operations:
            proxy = proxy_manager.get_proxy_for_operation(op_type, country_code=country)
            if proxy:
                message += f"✅ {op_type.value}:\n"
                message += f"   {proxy.ip_address}:{proxy.port} ({proxy.protocol.upper()})\n"
                message += f"   Success: {proxy.success_rate:.1f}% | Country: {proxy.country_code or 'Unknown'}\n\n"
            else:
                message += f"❌ {op_type.value}: No proxy available\n\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in proxy_test: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def proxy_providers_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show proxy providers"""
    try:
        db = get_db_session()
        
        # Group by provider
        providers = {}
        proxies = db.query(ProxyPool).all()
        
        for proxy in proxies:
            provider = proxy.provider or "Unknown"
            if provider not in providers:
                providers[provider] = {"total": 0, "active": 0}
            providers[provider]["total"] += 1
            if proxy.is_active:
                providers[provider]["active"] += 1
        
        message = "🌐 *Proxy Providers*\n\n"
        for provider, stats in providers.items():
            message += f"📍 {provider}\n"
            message += f"   Total: {stats['total']} | Active: {stats['active']}\n\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        close_db_session(db)
    except Exception as e:
        logger.error(f"Error in proxy_providers: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def proxy_strategy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Change proxy selection strategy"""
    try:
        if not context.args:
            strategies = ["round_robin", "least_used", "weighted", "reputation_based", "random", "fastest"]
            message = "⚙️ *Available Strategies*\n\n"
            for strategy in strategies:
                current = "✅" if proxy_manager.load_balancer.current_strategy == strategy else "  "
                message += f"{current} {strategy}\n"
            message += "\nUsage: /proxy_strategy <strategy_name>"
            await update.message.reply_text(message, parse_mode='Markdown')
            return
        
        strategy = context.args[0].lower()
        proxy_manager.load_balancer.set_strategy(strategy)
        await update.message.reply_text(f"✅ Strategy changed to: {strategy}")
    except Exception as e:
        logger.error(f"Error in proxy_strategy: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def fetch_webshare_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetch proxies from WebShare.io"""
    try:
        await update.message.reply_text("🔄 Fetching proxies from WebShare.io...")
        
        # Check if WebShare is enabled
        webshare_enabled = os.getenv('WEBSHARE_ENABLED', 'false').lower() == 'true'
        if not webshare_enabled:
            await update.message.reply_text(
                "⚠️ WebShare.io is not enabled.\n\n"
                "To enable:\n"
                "1. Add WEBSHARE_API_TOKEN to .env\n"
                "2. Set WEBSHARE_ENABLED=true\n"
                "3. Restart the bot"
            )
            return
        
        # Get API token
        api_token = os.getenv('WEBSHARE_API_TOKEN')
        if not api_token or api_token == 'your_webshare_token_here':
            await update.message.reply_text(
                "❌ WebShare API token not configured.\n\n"
                "Get your token from: https://proxy.webshare.io/userapi/\n"
                "Add it to .env as WEBSHARE_API_TOKEN"
            )
            return
        
        # Initialize WebShare provider
        webshare = WebShareProvider(api_token)
        
        # Fetch proxies
        proxy_count = int(os.getenv('WEBSHARE_PROXY_COUNT', '100'))
        success = await webshare.fetch_and_store_proxies(limit=proxy_count)
        
        if success:
            # Get updated stats
            db = get_db_session()
            webshare_proxies = db.query(ProxyPool).filter(
                ProxyPool.provider == 'webshare'
            ).count()
            close_db_session(db)
            
            await update.message.reply_text(
                f"✅ Successfully fetched WebShare proxies!\n\n"
                f"WebShare proxies in database: {webshare_proxies}\n"
                f"Provider: WebShare.io Premium"
            )
        else:
            await update.message.reply_text("❌ Failed to fetch WebShare proxies. Check logs for details.")
    except Exception as e:
        logger.error(f"Error in fetch_webshare: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def webshare_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show WebShare account information"""
    try:
        # Check if WebShare is enabled
        webshare_enabled = os.getenv('WEBSHARE_ENABLED', 'false').lower() == 'true'
        if not webshare_enabled:
            await update.message.reply_text(
                "⚠️ WebShare.io is not enabled.\n\n"
                "Configure WEBSHARE_API_TOKEN and set WEBSHARE_ENABLED=true"
            )
            return
        
        # Get API token
        api_token = os.getenv('WEBSHARE_API_TOKEN')
        if not api_token or api_token == 'your_webshare_token_here':
            await update.message.reply_text(
                "❌ WebShare API token not configured.\n\n"
                "Get your token from: https://proxy.webshare.io/userapi/"
            )
            return
        
        await update.message.reply_text("🔄 Fetching account info...")
        
        # Initialize WebShare provider
        webshare = WebShareProvider(api_token)
        
        # Get account info
        info = await webshare.get_account_info()
        
        if info:
            message = f"""💎 *WebShare Account Info*

Email: {info.get('email', 'N/A')}
Available Proxies: {info.get('proxy_count', 0)}
Bandwidth: {info.get('bandwidth_gb', 0):.2f} GB
Account Type: {info.get('account_type', 'Free')}

Status: ✅ Active
"""
            # Get database stats
            db = get_db_session()
            webshare_proxies = db.query(ProxyPool).filter(
                ProxyPool.provider == 'webshare'
            ).count()
            close_db_session(db)
            
            message += f"\nProxies in Database: {webshare_proxies}"
            
            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Failed to fetch account info. Check your API token.")
    except Exception as e:
        logger.error(f"Error in webshare_info: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")

def main():
    """Main function to run the bot"""
    # Get bot token
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        logger.error("BOT_TOKEN not found in environment variables!")
        return
    
    logger.info("Starting Proxy Test Bot...")
    
    # Create application
    application = Application.builder().token(bot_token).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("proxy_stats", proxy_stats_command))
    application.add_handler(CommandHandler("proxy_health", proxy_health_command))
    application.add_handler(CommandHandler("proxy_test", proxy_test_command))
    application.add_handler(CommandHandler("proxy_providers", proxy_providers_command))
    application.add_handler(CommandHandler("proxy_strategy", proxy_strategy_command))
    application.add_handler(CommandHandler("fetch_webshare", fetch_webshare_command))
    application.add_handler(CommandHandler("webshare_info", webshare_info_command))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    logger.info("✅ Bot started successfully!")
    logger.info("Press Ctrl+C to stop")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
