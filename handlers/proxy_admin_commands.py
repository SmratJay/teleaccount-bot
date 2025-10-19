"""
Admin proxy management commands.
Provides commands for managing the proxy pool, health monitoring, and rotation.
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from services.proxy_manager import proxy_manager
from services.daily_proxy_rotator import force_proxy_rotation, get_proxy_rotation_status
from services.proxy_health_monitor import get_proxy_health_report, get_unhealthy_proxies
from database.operations import ProxyService
from database import get_db_session, close_db_session

logger = logging.getLogger(__name__)

async def proxy_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show proxy pool statistics."""
    try:
        db = get_db_session()
        stats = ProxyService.get_proxy_stats(db)
        close_db_session(db)
        
        rotation_status = get_proxy_rotation_status()
        health_report = get_proxy_health_report()
        
        message = "🔄 **Proxy Pool Statistics**\n\n"
        message += f"📊 **Pool Status:**\n"
        message += f"• Total proxies: {stats.get('total_proxies', 0)}\n"
        message += f"• Active proxies: {stats.get('active_proxies', 0)}\n"
        message += f"• Inactive proxies: {stats.get('inactive_proxies', 0)}\n"
        message += f"• Recently used (24h): {stats.get('recently_used_24h', 0)}\n\n"
        
        message += f"🌍 **Country Distribution:**\n"
        for country, count in stats.get('country_distribution', {}).items():
            message += f"• {country}: {count}\n"
        
        message += f"\n⏰ **Rotation Status:**\n"
        message += f"• Running: {'✅' if rotation_status.get('is_running') else '❌'}\n"
        message += f"• Last rotation: {rotation_status.get('last_rotation', 'Never')}\n"
        message += f"• Next rotation: {rotation_status.get('next_rotation', 'Unknown')}\n\n"
        
        summary = health_report.get('summary', {})
        message += f"🏥 **Health Summary:**\n"
        message += f"• Healthy proxies: {summary.get('healthy_proxies', 0)}\n"
        message += f"• Unhealthy proxies: {summary.get('unhealthy_proxies', 0)}\n"
        message += f"• Average success rate: {summary.get('average_success_rate', 0):.1%}\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Proxy stats command failed: {e}")
        await update.message.reply_text("❌ Failed to get proxy statistics")

async def add_proxy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a new proxy to the pool. Usage: /add_proxy <ip> <port> [username] [password] [country]"""
    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text(
                "Usage: /add_proxy <ip> <port> [username] [password] [country]\n"
                "Example: /add_proxy 192.168.1.1 8080 user pass US"
            )
            return
        
        ip_address = args[0]
        port = int(args[1])
        username = args[2] if len(args) > 2 else None
        password = args[3] if len(args) > 3 else None
        country_code = args[4] if len(args) > 4 else None
        
        success = proxy_manager.add_proxy_to_pool(ip_address, port, username, password, country_code)
        
        if success:
            await update.message.reply_text(
                f"✅ Proxy added successfully!\n"
                f"📍 {ip_address}:{port}\n"
                f"🌍 Country: {country_code or 'Auto-detect'}"
            )
        else:
            await update.message.reply_text("❌ Failed to add proxy")
            
    except ValueError:
        await update.message.reply_text("❌ Invalid port number")
    except Exception as e:
        logger.error(f"Add proxy command failed: {e}")
        await update.message.reply_text("❌ Failed to add proxy")

async def test_proxy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test a proxy's connectivity. Usage: /test_proxy <proxy_id>"""
    try:
        if not context.args:
            await update.message.reply_text("Usage: /test_proxy <proxy_id>")
            return
        
        proxy_id = int(context.args[0])
        
        db = get_db_session()
        proxy_record = ProxyService.get_proxy_by_id(db, proxy_id)
        close_db_session(db)
        
        if not proxy_record:
            await update.message.reply_text("❌ Proxy not found")
            return
        
        from services.proxy_manager import ProxyConfig
        proxy_config = ProxyConfig(
            proxy_type='HTTP',
            host=proxy_record.ip_address,
            port=proxy_record.port,
            username=proxy_record.username,
            password=proxy_record.password
        )
        
        is_working = proxy_manager.test_proxy_connectivity(proxy_config)
        
        status = "✅ Working" if is_working else "❌ Not working"
        await update.message.reply_text(
            f"🧪 **Proxy Test Result**\n\n"
            f"📍 {proxy_record.ip_address}:{proxy_record.port}\n"
            f"🌍 {proxy_record.country_code or 'Unknown'}\n"
            f"📊 Status: {status}"
        )
        
    except ValueError:
        await update.message.reply_text("❌ Invalid proxy ID")
    except Exception as e:
        logger.error(f"Test proxy command failed: {e}")
        await update.message.reply_text("❌ Failed to test proxy")

async def rotate_proxies_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Force immediate proxy rotation."""
    try:
        await update.message.reply_text("🔄 Starting proxy rotation...")
        
        # Run rotation in background
        import asyncio
        result = await force_proxy_rotation()
        
        if result.get("status") == "completed":
            rotation = result.get("rotation", {})
            health = result.get("health_check", {})
            
            message = "✅ **Proxy Rotation Completed**\n\n"
            message += f"🧹 Cleaned proxies: {rotation.get('cleaned_proxies', 0)}\n"
            message += f"🔄 Refresh successful: {'✅' if rotation.get('refresh_success') else '❌'}\n\n"
            message += f"📊 **Current Stats:**\n"
            stats = rotation.get('current_stats', {})
            message += f"• Total: {stats.get('total_proxies', 0)}\n"
            message += f"• Active: {stats.get('active_proxies', 0)}\n"
            message += f"• Recently used: {stats.get('recently_used_24h', 0)}\n\n"
            message += f"🏥 **Health Check:**\n"
            message += f"• Tested: {health.get('tested_count', 0)}\n"
            message += f"• Working: {health.get('working_count', 0)}\n"
            message += f"• Success rate: {health.get('success_rate', 0):.1%}"
            
            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ Rotation failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"Rotate proxies command failed: {e}")
        await update.message.reply_text("❌ Failed to rotate proxies")

async def proxy_health_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed proxy health information."""
    try:
        health_report = get_proxy_health_report()
        unhealthy_ids = get_unhealthy_proxies()
        
        summary = health_report.get('summary', {})
        
        message = "🏥 **Proxy Health Report**\n\n"
        message += f"📊 **Summary:**\n"
        message += f"• Total monitored: {summary.get('total_proxies', 0)}\n"
        message += f"• Healthy: {summary.get('healthy_proxies', 0)}\n"
        message += f"• Unhealthy: {summary.get('unhealthy_proxies', 0)}\n"
        message += f"• Average success rate: {summary.get('average_success_rate', 0):.1%}\n\n"
        
        if unhealthy_ids:
            message += f"⚠️ **Unhealthy Proxies:** {', '.join(map(str, unhealthy_ids))}\n\n"
        
        message += f"💡 Use /proxy_health <id> for detailed proxy info"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Proxy health command failed: {e}")
        await update.message.reply_text("❌ Failed to get health report")

async def deactivate_proxy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Deactivate a proxy. Usage: /deactivate_proxy <proxy_id> [reason]"""
    try:
        if not context.args:
            await update.message.reply_text("Usage: /deactivate_proxy <proxy_id> [reason]")
            return
        
        proxy_id = int(context.args[0])
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Manual deactivation"
        
        db = get_db_session()
        success = ProxyService.deactivate_proxy(db, proxy_id, reason)
        close_db_session(db)
        
        if success:
            await update.message.reply_text(f"✅ Proxy {proxy_id} deactivated\nReason: {reason}")
        else:
            await update.message.reply_text("❌ Proxy not found or already inactive")
            
    except ValueError:
        await update.message.reply_text("❌ Invalid proxy ID")
    except Exception as e:
        logger.error(f"Deactivate proxy command failed: {e}")
        await update.message.reply_text("❌ Failed to deactivate proxy")

async def refresh_proxies_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Refresh proxy pool from all enabled sources (WebShare + free sources)."""
    try:
        await update.message.reply_text("🔄 Refreshing proxy pool from all sources...")
        
        # Use the scheduler's refresh function for comprehensive refresh
        from services.proxy_scheduler import refresh_proxies_now
        
        results = await refresh_proxies_now()
        
        if 'error' in results:
            await update.message.reply_text(f"❌ Refresh failed: {results['error']}")
            return
        
        # Build results message
        message = "✅ **Proxy Pool Refresh Complete**\n\n"
        
        # WebShare results
        webshare = results.get('webshare', {})
        if webshare.get('enabled'):
            if webshare.get('success'):
                message += f"🌐 **WebShare.io:** ✅\n"
                message += f"  • New proxies: {webshare.get('count', 0)}\n"
            else:
                message += f"🌐 **WebShare.io:** ❌\n"
                message += f"  • Error: {webshare.get('error', 'Unknown')}\n"
        else:
            message += f"🌐 **WebShare.io:** ⏸️ Disabled\n"
        
        # Free sources results
        free_sources = results.get('free_sources', {})
        if free_sources.get('enabled'):
            if free_sources.get('success'):
                message += f"🆓 **Free Sources:** ✅\n"
                message += f"  • New proxies: {free_sources.get('count', 0)}\n"
            else:
                message += f"🆓 **Free Sources:** ❌\n"
                message += f"  • Error: {free_sources.get('error', 'Unknown')}\n"
        else:
            message += f"🆓 **Free Sources:** ⏸️ Disabled\n"
        
        # Cleanup results
        cleanup = results.get('cleanup', {})
        message += f"\n🧹 **Cleanup:**\n"
        if cleanup.get('error'):
            message += f"  • Error: {cleanup.get('error')}\n"
        else:
            message += f"  • Removed: {cleanup.get('removed', 0)} old proxies\n"
        
        # Get updated stats
        db = get_db_session()
        stats = ProxyService.get_proxy_stats(db)
        close_db_session(db)
        
        message += f"\n📊 **Current Pool:**\n"
        message += f"• Total: {stats.get('total_proxies', 0)}\n"
        message += f"• Active: {stats.get('active_proxies', 0)}"
        
        await update.message.reply_text(message, parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"Refresh proxies command failed: {e}")
        await update.message.reply_text("❌ Failed to refresh proxies")

async def proxy_providers_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show status of all proxy providers."""
    try:
        import os
        
        message = "🌐 **Proxy Provider Status**\n\n"
        
        # WebShare.io status
        webshare_enabled = os.getenv('WEBSHARE_ENABLED', 'false').lower() == 'true'
        webshare_token = os.getenv('WEBSHARE_API_TOKEN')
        
        message += f"🌐 **WebShare.io**\n"
        message += f"• Status: {'✅ Enabled' if webshare_enabled else '⏸️ Disabled'}\n"
        message += f"• API Token: {'✅ Configured' if webshare_token else '❌ Missing'}\n"
        
        if webshare_enabled and webshare_token:
            try:
                from services.webshare_provider import get_webshare_account_info
                account_info = await get_webshare_account_info()
                
                if account_info:
                    message += f"• Bandwidth: {account_info.get('bandwidth_usage', 'N/A')}\n"
                    message += f"• Valid until: {account_info.get('valid_until', 'N/A')}\n"
                else:
                    message += f"• ⚠️ Could not fetch account info\n"
            except Exception as e:
                message += f"• ⚠️ Error: {str(e)[:50]}...\n"
        
        message += "\n"
        
        # Free sources status
        free_sources_enabled = os.getenv('FREE_PROXY_SOURCES_ENABLED', 'true').lower() == 'true'
        
        message += f"🆓 **Free Proxy Sources**\n"
        message += f"• Status: {'✅ Enabled' if free_sources_enabled else '⏸️ Disabled'}\n"
        
        if free_sources_enabled:
            db = get_db_session()
            stats = ProxyService.get_proxy_stats(db)
            close_db_session(db)
            
            # Count free proxies (assume proxy_type 'FREE' or no username)
            free_count = stats.get('active_proxies', 0)  # Approximation
            message += f"• Active proxies: {free_count}\n"
        
        message += "\n"
        
        # Scheduler status
        from services.proxy_scheduler import get_scheduler_status
        scheduler = get_scheduler_status()
        
        message += f"⏰ **Auto-Refresh Scheduler**\n"
        message += f"• Status: {'✅ Running' if scheduler.get('running') else '❌ Stopped'}\n"
        
        if scheduler.get('running'):
            last_refresh = scheduler.get('last_refresh')
            next_refresh = scheduler.get('next_refresh')
            message += f"• Last refresh: {last_refresh or 'Never'}\n"
            message += f"• Next refresh: {next_refresh or 'Unknown'}\n"
        
        stats_data = scheduler.get('stats', {})
        message += f"• Total refreshes: {stats_data.get('total_refreshes', 0)}\n"
        message += f"• Successful: {stats_data.get('successful_refreshes', 0)}\n"
        message += f"• Failed: {stats_data.get('failed_refreshes', 0)}\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Proxy providers command failed: {e}")
        await update.message.reply_text("❌ Failed to get provider status")

async def proxy_strategy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Change load balancing strategy. Usage: /proxy_strategy [strategy_name]"""
    try:
        if not context.args:
            # Show current strategy and available options
            current = proxy_manager.get_current_strategy()
            strategies = ['round_robin', 'least_used', 'random', 'weighted', 'country_based', 'reputation_based']
            
            message = f"🎯 **Current Strategy:** `{current}`\n\n"
            message += f"📋 **Available Strategies:**\n"
            for strategy in strategies:
                emoji = "✅" if strategy == current else "○"
                message += f"{emoji} `{strategy}`\n"
            
            message += f"\n💡 Usage: `/proxy_strategy <strategy_name>`"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            return
        
        new_strategy = context.args[0].lower()
        valid_strategies = ['round_robin', 'least_used', 'random', 'weighted', 'country_based', 'reputation_based']
        
        if new_strategy not in valid_strategies:
            await update.message.reply_text(
                f"❌ Invalid strategy. Choose from:\n" + 
                ", ".join(f"`{s}`" for s in valid_strategies),
                parse_mode='Markdown'
            )
            return
        
        proxy_manager.set_strategy(new_strategy)
        
        await update.message.reply_text(
            f"✅ Load balancing strategy changed to: `{new_strategy}`",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Proxy strategy command failed: {e}")
        await update.message.reply_text("❌ Failed to change strategy")

async def fetch_webshare_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually fetch proxies from WebShare.io."""
    try:
        import os
        
        webshare_enabled = os.getenv('WEBSHARE_ENABLED', 'false').lower() == 'true'
        webshare_token = os.getenv('WEBSHARE_API_TOKEN')
        
        if not webshare_enabled:
            await update.message.reply_text("❌ WebShare.io is disabled. Set WEBSHARE_ENABLED=true in .env")
            return
        
        if not webshare_token:
            await update.message.reply_text("❌ WebShare API token not configured. Set WEBSHARE_API_TOKEN in .env")
            return
        
        await update.message.reply_text("🔄 Fetching proxies from WebShare.io...")
        
        from services.webshare_provider import refresh_webshare_proxies
        
        stats = await refresh_webshare_proxies()
        
        message = "✅ **WebShare.io Sync Complete**\n\n"
        message += f"📥 New proxies: {stats.get('new', 0)}\n"
        message += f"🔄 Updated proxies: {stats.get('updated', 0)}\n"
        message += f"❌ Failed: {stats.get('failed', 0)}\n"
        message += f"⏱️ Duration: {stats.get('duration', 0):.2f}s\n\n"
        
        # Get total count
        db = get_db_session()
        pool_stats = ProxyService.get_proxy_stats(db)
        close_db_session(db)
        
        message += f"📊 Total active proxies: {pool_stats.get('active_proxies', 0)}"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Fetch WebShare command failed: {e}")
        await update.message.reply_text(f"❌ Failed to fetch from WebShare.io: {str(e)}")


# Command registry for easy access
PROXY_COMMANDS = {
    'proxy_stats': proxy_stats_command,
    'add_proxy': add_proxy_command,
    'test_proxy': test_proxy_command,
    'rotate_proxies': rotate_proxies_command,
    'proxy_health': proxy_health_command,
    'deactivate_proxy': deactivate_proxy_command,
    'refresh_proxies': refresh_proxies_command,
    'proxy_providers': proxy_providers_command,
    'proxy_strategy': proxy_strategy_command,
    'fetch_webshare': fetch_webshare_command,
}
