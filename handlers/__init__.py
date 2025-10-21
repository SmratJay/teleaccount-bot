"""
Unified Handlers Package - Modular Architecture
Entry point for all bot handlers with proper separation of concerns.
"""
import logging
from telegram.ext import Application

logger = logging.getLogger(__name__)

def setup_all_handlers(application: Application) -> None:
    """
    Unified handler registration - Single entry point for all bot functionality.
    
    Handler Registration Order (CRITICAL for proper functioning):
    1. ConversationHandlers (HIGHEST priority - selling flow)
    2. Command Handlers (/start, /admin, etc.)
    3. CallbackQuery Handlers (button callbacks)
    4. Message Handlers (text input - LOWEST priority)
    
    Modular Architecture:
    - handlers/verification_flow.py: CAPTCHA and channel verification
    - handlers/user_panel.py: Balance, language, account details
    - handlers/selling_flow.py: Account selling conversation
    - handlers/withdrawal_flow.py: Withdrawal approval workflows
    - handlers/admin_handlers.py: Admin panel, sessions, proxy, mailing
    - handlers/leader_handlers.py: Leader panel functionality
    - handlers/analytics_handlers.py: Analytics dashboard
    - handlers/real_handlers.py: Main menu orchestration (slim)
    """
    logger.info("🚀 Initializing modular handler system...")
    
    # Import the main handler orchestrator
    from handlers.real_handlers import setup_real_handlers
    
    # Setup all handlers through the orchestrator
    setup_real_handlers(application)
    
    logger.info("✅ All modular handlers registered successfully")

# Backward compatibility
setup_handlers = setup_all_handlers
