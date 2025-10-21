# Telegram Account Selling Bot

## Overview

A comprehensive Telegram bot platform for selling Telegram accounts with advanced security features, multi-language support, and automated account configuration. The system handles the complete lifecycle from account verification and sale through to post-sale configuration and withdrawal processing.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes

**October 21, 2025 - Admin Panel Bug Fixes & Enhancements:**
- **Fixed Reports & Logs System:**
  - Corrected all field references from `sale_timestamp` to `created_at` in AccountSale queries
  - Revenue metrics now use correct `created_at` field for time-based filtering
  - All statistics display real-time data from database with no hardcoded values
  
- **Fixed Sale Log Operations:**
  - Completely migrated from non-existent `AccountSaleLog` model to `AccountSale`
  - Updated all status references from enum to string values ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED')
  - Fixed approve/reject handlers to use correct database models
  - Added proper activity logging for all sale status changes
  
- **Enhanced Security & Access Control:**
  - Implemented "View All Admins" button - displays all admin users from database
  - Implemented "View All Leaders" button - displays all leader users from database
  - Added "Add Admin" conversation handler with user ID validation and activity logging
  - Added "Remove Admin" conversation handler with self-removal protection
  - All security operations now properly log to ActivityLog for audit trails
  
- **Fixed Language Persistence:**
  - Main menu now loads user's language from database on every display
  - Language preferences persist correctly across sessions
  - Translation service automatically applies saved language_code from User model

**October 21, 2025 - Reports & Logs + System Settings Implementation:**
- Removed "Activity Tracker" button from admin panel (redundant with Reports & Logs)
- Implemented comprehensive **Reports & Logs** system with 5 modules:
  - Main Dashboard: Real-time statistics from database (users, accounts, sales, revenue)
  - Activity Logs: Recent user actions and system events
  - Sales Report: Top sellers, recent sales, performance metrics
  - User Report: User statistics, balance distribution, language breakdown
  - Revenue Report: Revenue by time period, average sale price, performance metrics
- Implemented **System Settings** panel with 4 categories:
  - Bot Configuration: Verification settings, CAPTCHA, channel join, freeze duration, daily limits
  - Financial Settings: Minimum withdrawal, commission rate, price limits
  - Security & Access: Admin/leader management, login attempts, session timeout
  - System Maintenance: Database cleanup, statistics, optimization tools
- All features use real-time database queries with zero hardcoded data
- Settings stored in `system_settings` table for persistence across sessions
- Added `is_admin()` and `is_leader()` utility functions to utils/helpers.py

**October 21, 2025 - Proxy System Cleanup:**
- Disabled free proxy sources by default (FREE_PROXY_SOURCES_ENABLED = 'false')
- Removed 579 free proxies from database
- Added admin control to clean free proxies
- WebShare.io now the primary proxy source

## System Architecture

### Core Technology Stack

**Backend Framework:**
- Python 3.11+ with asyncio for concurrent operations
- python-telegram-bot (v20.7) for bot interface
- Telethon (v1.34.0) for direct Telegram API integration
- SQLAlchemy 2.0 for database ORM with PostgreSQL/SQLite support

**Design Pattern:**
- Modular handler architecture with separation of concerns
- Service layer pattern for business logic isolation
- Repository pattern through database operations layer
- Conversation handler pattern for multi-step user flows

**Architecture Decision Rationale:**
The bot uses a dual-library approach (python-telegram-bot + Telethon) because python-telegram-bot provides excellent conversation flow management and user interface handling, while Telethon enables direct Telegram account manipulation (session management, 2FA setup, account configuration). This combination allows the bot to both interact with users and programmatically control sold accounts.

### Database Architecture

**ORM Layer:**
- SQLAlchemy 2.0 declarative models in `database/models.py`
- Separate service layer in `database/operations.py` for CRUD operations
- Support for both PostgreSQL (production) and SQLite (development)

**Key Models:**
- `User` - Bot users with balance tracking, verification status, admin/leader privileges
- `TelegramAccount` - Accounts for sale with status, freeze tracking, and proxy assignment
- `Withdrawal` - Financial withdrawal requests with approval workflow
- `ProxyPool` - Proxy management with health metrics and encrypted credentials
- `AccountSale` - Transaction records linking sellers, buyers, and configuration changes
- `ActivityLog` - Comprehensive audit trail for security and compliance

**Design Decision:**
The database uses a service layer pattern to abstract all database operations. This prevents direct model access from handlers, making it easier to swap databases or add caching layers. The separation also allows for comprehensive activity logging without cluttering handler code.

### Handler System

**Modular Architecture:**
The bot uses a unified modular handler system that eliminates code duplication and maintains single responsibility:

- `handlers/real_handlers.py` - Main menu orchestration and routing (403 lines, down from 3,594)
- `handlers/verification_flow.py` - CAPTCHA and channel verification workflow
- `handlers/user_panel.py` - Balance, language settings, account details
- `handlers/selling_flow.py` - Complete account selling conversation flow
- `handlers/withdrawal_flow.py` - Withdrawal requests and leader approval
- `handlers/admin_handlers.py` - Administrative functions and system controls
- `handlers/analytics_handlers.py` - Business intelligence and reporting

**Conversation State Management:**
Uses python-telegram-bot's ConversationHandler for multi-step flows with persistent state storage in `context.user_data`. Priority ordering ensures withdrawal conversations override other flows.

**Design Decision:**
The original monolithic handler (3,594 lines) was decomposed into focused modules to improve maintainability. Each module handles a specific user journey, making the codebase easier to test and modify. The 89% reduction in main handler size significantly improves code readability.

### Business Logic Services

**Account Configuration Service** (`services/account_configuration.py`):
- Automated post-sale account modification using Telethon
- Random name/username generation to anonymize sold accounts
- Profile photo management with local asset storage
- 2FA setup with secure password generation
- Flood-wait error handling for Telegram rate limits

**Session Management** (`services/session_management.py`):
- Telegram session file lifecycle management
- Multi-device detection and forced logout
- 24-hour hold system for conflicting accounts
- Session distribution to buyers with country-based organization

**Proxy Management** (`services/proxy_manager.py`):
- Operation-specific proxy selection (login, OTP retrieval, account creation)
- Proxy health monitoring with success rate tracking
- Automated proxy rotation and refresh scheduling
- Support for multiple proxy providers (Webshare integration)
- Encrypted credential storage using cryptography library

**Design Decision:**
Services use dependency injection patterns where database sessions are passed as parameters rather than created internally. This allows for proper transaction management and testing. The proxy system uses a strategy pattern to select proxies based on operation requirements (e.g., residential proxies for account creation, datacenter proxies for bulk operations).

### Security & Verification

**Multi-Layer Verification:**
1. Visual CAPTCHA generation using PIL (prevents bot access)
2. Channel membership verification via Telegram Bot API
3. Phone number validation and OTP verification through Telethon
4. Activity logging for all critical operations

**Bypass System** (`services/advanced_telegram_bypass.py`):
- Handles Telegram security restrictions for flagged accounts
- Device profile spoofing with rotation
- Retry strategies with exponential backoff
- Flood-wait handling and automatic recovery

**Design Decision:**
The verification system is intentionally multi-layered because Telegram account selling attracts automated abuse. CAPTCHA prevents bot farms, channel verification ensures community engagement, and activity logging provides forensic capabilities for fraud investigation.

### Financial System

**Withdrawal Workflow:**
1. User submits withdrawal request through conversation handler
2. Request posted to Telegram notification channel for leader review
3. Leader approves/rejects via inline keyboard callbacks
4. Balance updated atomically with activity logging
5. Payment confirmation triggers final status update

**Balance Management:**
- Atomic balance updates using SQLAlchemy transactions
- Earnings calculated from completed sales (tracked in AccountSale model)
- Withdrawal history with status tracking (PENDING, APPROVED, COMPLETED, REJECTED)

**Design Decision:**
The two-step approval process (leader review + manual payment confirmation) prevents automated withdrawal fraud. All balance changes are logged in ActivityLog for audit trails. The system uses optimistic locking to prevent race conditions during concurrent withdrawals.

### Internationalization

**Translation Service** (`services/translation_service.py`):
- Support for 8 languages: EN, ES, FR, DE, RU, ZH, HI, AR
- User language preferences stored in database and persisted across sessions
- Message templates in `locales/messages.json`
- Runtime translation for dynamic content

**Design Decision:**
Rather than maintaining separate message files per language, the system uses Google Translate API for dynamic content and JSON templates for static UI elements. This reduces maintenance overhead while providing comprehensive language support.

## External Dependencies

### Third-Party APIs

**Telegram Bot API:**
- Bot interface through python-telegram-bot library
- Webhook support for production deployment (currently using polling)
- Inline keyboard callbacks for user interactions

**Telegram Client API (MTProto):**
- Direct account access via Telethon
- Session file management for sold accounts
- 2FA setup and account configuration

**Proxy Services:**
- Webshare.io integration for residential/datacenter proxies
- Proxy health monitoring and rotation
- Encrypted credential storage

### Infrastructure Services

**Database:**
- PostgreSQL for production (Heroku, Railway, Render)
- SQLite for local development
- Connection pooling via SQLAlchemy QueuePool

**Deployment Platforms:**
- Replit (recommended for ease of use)
- Heroku (with PostgreSQL addon)
- Railway/Render for modern alternatives
- Environment variable configuration for all platforms

**File Storage:**
- Local filesystem for session files and CAPTCHA images
- Session distribution with country-based folder organization
- Temporary file cleanup for CAPTCHA images

### Python Libraries

**Core Dependencies:**
- `python-telegram-bot==20.7` - Bot framework
- `telethon==1.34.0` - Telegram client library
- `sqlalchemy==2.0.23` - Database ORM
- `cryptography==41.0.7` - Password encryption
- `Pillow==10.1.0` - CAPTCHA image generation
- `aiohttp==3.9.1` - Async HTTP client for proxy health checks
- `apscheduler==3.10.4` - Background job scheduling

**Design Decision:**
The dependency list is intentionally minimal to reduce deployment complexity and security surface area. All dependencies are pinned to specific versions to ensure reproducible builds across environments.

### Configuration Management

**Environment Variables:**
- `BOT_TOKEN` - Telegram bot token from @BotFather
- `API_ID` / `API_HASH` - Telegram API credentials from my.telegram.org
- `ADMIN_USER_ID` / `LEADER_CHANNEL_ID` - Administrative access control
- `DATABASE_URL` - PostgreSQL connection (auto-configured on Heroku)
- `SECRET_KEY` - Encryption key for proxy credentials

**Design Decision:**
All sensitive configuration uses environment variables to support cloud deployment and prevent credential leakage in version control. The system automatically detects Heroku's DATABASE_URL format and handles the postgres:// to postgresql:// conversion.