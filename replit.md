# Telegram Account Selling Bot

## Overview

A comprehensive Telegram bot platform designed for selling Telegram accounts. It features advanced security, multi-language support, and automated account configuration. The system manages the entire account lifecycle, from verification and sale to post-sale setup and withdrawal processing, aiming for a robust and automated solution in the Telegram account marketplace.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Core Technology Stack
The bot is built with Python 3.11+ using `asyncio`. It leverages `python-telegram-bot` (v20.7) for the user interface and `Telethon` (v1.34.0) for direct Telegram API interactions. `SQLAlchemy 2.0` serves as the ORM for database management, supporting PostgreSQL and SQLite. The architecture follows a modular handler, service layer, and repository pattern, utilizing `ConversationHandler` for multi-step user flows. This dual-library approach allows for both rich user interaction and programmatic control of Telegram accounts.

### Database Architecture
The database design incorporates `SQLAlchemy 2.0` declarative models and a dedicated service layer for CRUD operations, abstracting direct model access. Key models include `User`, `TelegramAccount`, `Withdrawal`, `ProxyPool`, `AccountSale`, and `ActivityLog`, ensuring comprehensive tracking and auditing.

### Handler System
A modular handler system organizes the bot's functionalities into distinct modules like `verification_flow`, `selling_flow`, `withdrawal_flow`, and `admin_handlers`, significantly improving maintainability and readability by breaking down a formerly monolithic structure.

### Business Logic Services
Core business logic is encapsulated in dedicated services:
- **Account Configuration Service:** Automates post-sale account modifications (name/username generation, profile photos, 2FA setup) using Telethon, including flood-wait handling.
- **Session Management:** Manages Telegram session files, handles multi-device detection, and distributes sessions to buyers.
- **Proxy Management:** Selects operation-specific proxies, monitors their health, and supports rotation with encrypted credentials from providers like Webshare.io.
- **Advanced Telegram Bypass:** Manages Telegram security restrictions, including device profile spoofing and retry strategies.

### Security & Verification
The system employs multi-layered verification including visual CAPTCHAs, Telegram channel membership checks, phone number validation, and OTP verification. All critical operations are logged for security and audit purposes.

### Financial System
Features a robust withdrawal workflow with a two-step approval process involving leader review and manual payment confirmation. Atomic balance updates and comprehensive activity logging ensure financial integrity.

### Internationalization
Supports 8 languages (EN, ES, FR, DE, RU, ZH, HI, AR) with user preferences stored in the database. Dynamic content translation is managed via a translation service.

## External Dependencies

### Third-Party APIs
- **Telegram Bot API:** Used for the primary bot interface and user interactions.
- **Telegram Client API (MTProto):** Accessed via Telethon for direct account manipulation and session management.
- **Webshare.io:** Integrated for providing residential and datacenter proxies.

### Infrastructure Services
- **Database:** PostgreSQL for production environments and SQLite for development.
- **Deployment Platforms:** Designed for deployment on platforms like Replit, Heroku, Railway, and Render, utilizing environment variables for configuration.
- **File Storage:** Local filesystem for session files and CAPTCHA images, with temporary file cleanup.

### Python Libraries
Key libraries include `python-telegram-bot`, `telethon`, `sqlalchemy`, `cryptography` for encryption, `Pillow` for image generation, `aiohttp` for async HTTP requests, and `apscheduler` for background tasks.

### Configuration Management
All sensitive configurations, such as `BOT_TOKEN`, `API_ID`, `API_HASH`, `ADMIN_USER_ID`, `DATABASE_URL`, and `SECRET_KEY`, are managed through environment variables to ensure secure deployment and prevent credential exposure.