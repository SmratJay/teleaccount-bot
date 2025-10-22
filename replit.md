# Telegram Account Selling Bot

## Overview

A comprehensive Telegram bot platform for selling Telegram accounts. It features advanced security, multi-language support, and automated account configuration. The system manages the entire lifecycle from account verification and sale to post-sale configuration and withdrawal processing. The project aims to provide a robust solution for automated Telegram account vending with strong security and user management capabilities.

## Recent Changes (October 22, 2025)

**Reports & Logs Dashboard Polish + Main Menu Optimization (Latest):**
- **Dashboard Cleanup**: Removed Activity Logs and Revenue Report buttons from Reports & Logs panel (now shows User Report, Session Details, Refresh Stats, Back to Admin)
- **User Report Enhancement**: Added "Download UserIDs File" button that generates and sends `userids.txt` with all user IDs who have captured sessions (one ID per line)
- **Session Details Menu**: New menu showing session statistics (total sessions, unique users) with "Download Session Files" button
- **Session File Download**: ConversationHandler allowing admins to download session files by typing username - finds latest session and sends file with metadata
- **Bug Fixes**: Fixed double-answer callback query bug, improved file handling with context managers throughout
- **Main Menu Performance**: Eliminated duplicate database query in `show_real_main_menu()` - reduced from 2 queries to 1 by loading language directly from fetched user object instead of calling `load_user_language()` helper (saves 50-200ms per menu load)

**Previous Main Menu Optimization:**
- Optimized `button_callback()` to fetch user data once and load language from the same object
- Modified `show_real_main_menu()` to accept optional pre-fetched `db_user_cached` parameter
- Updated `start_handler` to pass cached user object when redirecting to main menu
- Language loading now uses direct user object instead of separate DB query
- Main menu redirects are now noticeably faster, especially with network latency

**Ticket Navigation Stability Fix:**
- Fixed critical bug where ticket navigation jumped to wrong sales when other admins approved/rejected tickets concurrently
- All navigation callbacks now use stable `sale_log.id` instead of ephemeral ticket strings (#0001, #0002)
- Created `navigate_ticket_by_id()` function for ID-based ticket navigation
- Updated all approve/reject handlers to use the new ID-based navigation system
- Ticket numbers (#0001, #0002) are now purely for display; navigation uses database IDs
- Navigation remains stable even under concurrent ticket processing by multiple admins

**CAPTCHA Verification Fix:**
- Fixed issue where previously verified users were forced to re-verify on first `/start` after update
- Added fallback logic: if `captcha_verified_at` is NULL but user has `verification_completed=True`, backfill timestamp and skip verification
- This handles users who verified before the 7-day cache feature was added
- Users now go directly to main menu on first `/start` if they were already verified

**Verification Flow UI Updates:**
- Updated DEFAULT_VERIFICATION_CHANNELS to 2 channels: "MAIN Channel and support" (https://t.me/teleflare_bot_io) and "Backup channel" (no link)
- Changed verification badge from ✅ to 💠 throughout the entire verification flow (CAPTCHA, channel verification, completion messages)
- Improved channel handling: channels without links/usernames are automatically skipped in button display and membership verification
- The Backup channel is listed for users but not enforced, allowing for future configuration

**Deployment Status:**
- Production bot deployed on AWS EC2 with Neon PostgreSQL database
- Replit workflow configured for development/testing only (must stop EC2 instance to use)
- CAPTCHA 7-day cache working correctly with timezone-aware datetime comparison

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Core Technology Stack

**Backend Framework:**
- Python 3.11+ with asyncio
- `python-telegram-bot` (v20.7) for bot interface
- `Telethon` (v1.34.0) for direct Telegram API integration
- `SQLAlchemy 2.0` for ORM (PostgreSQL/SQLite)

**Design Pattern:**
- Modular handler architecture
- Service layer for business logic
- Repository pattern via database operations
- Conversation handler for multi-step user flows

**Architecture Decision Rationale:**
A dual-library approach (`python-telegram-bot` + `Telethon`) is used to combine robust user interaction with direct Telegram account manipulation, enabling both user-facing features and programmatic account control.

### Database Architecture

**ORM Layer:**
- `SQLAlchemy 2.0` declarative models
- Separate service layer for CRUD operations
- Supports PostgreSQL (production) and SQLite (development)

**Key Models:**
- `User`: Bot users, balance, verification, privileges
- `TelegramAccount`: Accounts for sale, status, proxy
- `Withdrawal`: Financial requests, approval workflow
- `ProxyPool`: Proxy management, health metrics
- `AccountSale`: Transaction records
- `ActivityLog`: Audit trail

**Design Decision:**
A service layer abstracts database operations, preventing direct model access from handlers, enhancing modularity, and facilitating comprehensive activity logging.

### Handler System

**Modular Architecture:**
The bot uses a unified modular handler system to prevent code duplication and ensure single responsibility. Key modules include:
- `verification_flow.py` (CAPTCHA, channel verification)
- `selling_flow.py` (account selling)
- `withdrawal_flow.py` (withdrawal requests)
- `admin_handlers.py` (administrative functions)
- `analytics_handlers.py` (reporting)

**Conversation State Management:**
Utilizes `python-telegram-bot`'s `ConversationHandler` for multi-step flows with persistent state storage, prioritizing critical conversations like withdrawals.

**Design Decision:**
Decomposition of a monolithic handler into focused modules significantly improves maintainability, testability, and readability.

### Business Logic Services

**Account Configuration Service:**
- Automated post-sale account modification using Telethon (name/username, profile photo, 2FA setup).
- Handles Telegram rate limits and flood-wait errors.

**Session Management:**
- Telegram session file lifecycle management.
- Multi-device detection, forced logout, and 24-hour hold system.
- Country-based session distribution.

**Proxy Management:**
- Operation-specific proxy selection and health monitoring.
- Automated proxy rotation and refresh.
- Supports multiple providers (e.g., Webshare.io) and encrypts credentials.

**Security & Verification:**
- **Multi-Layer Verification:** Visual CAPTCHA, channel membership, phone number validation, OTP verification, and activity logging.
- **Bypass System:** Handles Telegram security restrictions, device profile spoofing, and retry strategies.

**Financial System:**
- **Withdrawal Workflow:** User request, leader approval via notification channel, atomic balance updates, activity logging, and payment confirmation.
- **Balance Management:** Atomic balance updates via SQLAlchemy transactions, earnings from completed sales, and withdrawal history tracking.

**Internationalization:**
- **Translation Service:** Supports 8 languages (EN, ES, FR, DE, RU, ZH, HI, AR) with user preferences stored in the database.
- Uses `locales/messages.json` for templates and runtime translation for dynamic content.

## External Dependencies

### Third-Party APIs

**Telegram Bot API:**
- Bot interface through `python-telegram-bot` library.
- Webhook support for production deployment.

**Telegram Client API (MTProto):**
- Direct account access via `Telethon` for session management and account configuration.

**Proxy Services:**
- Webshare.io integration for residential/datacenter proxies.

### Infrastructure Services

**Database:**
- PostgreSQL for production.
- SQLite for local development.

**Deployment Platforms:**
- Replit, Heroku, Railway/Render, AWS EC2.

**File Storage:**
- Local filesystem for session files and CAPTCHA images.

### Python Libraries

**Core Dependencies:**
- `python-telegram-bot==20.7`
- `telethon==1.34.0`
- `sqlalchemy==2.0.23`
- `cryptography==41.0.7`
- `Pillow==10.1.0`
- `aiohttp==3.9.1`
- `apscheduler==3.10.4`

### Configuration Management

**Environment Variables:**
- `BOT_TOKEN`, `API_ID`, `API_HASH`, `ADMIN_USER_ID`, `LEADER_CHANNEL_ID`, `DATABASE_URL`, `SECRET_KEY`.