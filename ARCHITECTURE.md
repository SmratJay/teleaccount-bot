# Telegram Account Bot - Unified Architecture

## Directory Structure
```
teleaccount_bot/
├── database/
│   ├── __init__.py           # DB session management
│   ├── models.py             # All SQLAlchemy models
│   └── operations.py         # Service layer (CRUD operations)
├── handlers/
│   ├── __init__.py           # Unified handler entry point
│   ├── real_handlers.py      # Main user flow (start, selling, verification)
│   ├── main_handlers.py      # User features (balance, withdraw, language, status)
│   ├── admin_handlers.py     # Admin panel features
│   ├── leader_handlers.py    # Leader panel features
│   ├── analytics_handlers.py # Analytics dashboard
│   └── proxy_admin_commands.py # Proxy management commands
├── services/
│   ├── account_configuration.py  # Post-sale account setup
│   ├── account_management.py     # Account freeze/hold management
│   ├── captcha.py                # CAPTCHA generation
│   ├── proxy_manager.py          # Proxy pool management
│   ├── real_telegram.py          # Telethon integration
│   ├── session_management.py     # Telegram session handling
│   └── telegram_logger.py        # Channel logging
├── utils/
│   ├── encryption.py         # Password encryption utilities
│   └── notification_service.py # User notifications
├── webapp/
│   └── server.py             # WebApp server for embedded forms
├── keyboard_layout_fix.py    # Main menu keyboard helper
└── real_main.py              # Bot entry point
```

## Database Models (database/models.py)

### Core Models
- **User**: Bot users with balance, verification status, admin/leader flags
- **TelegramAccount**: Telegram accounts for sale (seller_id, phone, status, freeze info)
- **Withdrawal**: Withdrawal requests (amount, currency, method, address, status)
- **SystemSettings**: Key-value configuration store
- **ProxyPool**: Proxy management with health metrics
- **ActivityLog**: Action logging for security auditing
- **VerificationTask**: CAPTCHA and channel join tasks
- **UserVerification**: User completion tracking for tasks
- **AccountSale**: Sale transaction records with configuration tracking

### Enums
- **AccountStatus**: AVAILABLE, HELD, SOLD, FROZEN, BANNED
- **WithdrawalStatus**: PENDING, APPROVED, COMPLETED, REJECTED
- **UserStatus**: ACTIVE, BANNED, SUSPENDED
- **SaleStatus**: PENDING, IN_PROGRESS, COMPLETED, FAILED

## Handler Architecture

### User Flow (handlers/real_handlers.py)
1. `/start` → CAPTCHA verification
2. Channel verification
3. Main menu with features

### User Features (handlers/main_handlers.py)
- **LFG Button** ✅: Start selling conversation
- **Balance** ✅: Show sold accounts, earnings, balance
- **Withdraw** ✅: TRX, USDT-TRC20/BEP20, Binance Pay
- **Language** ✅: Multi-language support
- **System Capacity** ✅: Global status display
- **Status** ✅: Personal user status
- **Support** ✅: Contact link

### Admin Features (handlers/admin_handlers.py)
- **Mailing Mode** ✅: Broadcast to all users
- **Manual User Edit** ✅: Edit user data/status
- **Account Freeze Management** ✅: Freeze/unfreeze accounts
- **Sale Logs & Approval** ✅: Review account sales
- **Chat History Control** ✅: Toggle chat deletion
- **Session Management** ✅: View holds, release, activity logs
- **IP/Proxy Config** ✅: View/rotate proxies, health dashboard
- **Activity Tracker** ✅: View recent logs and statistics
- **Reports & Logs** ✅: Frozen/spam/OTP reports

### Leader Features (handlers/leader_handlers.py)
- **Withdrawal Management** ✅: Process user withdrawal requests
- **Payment Tracking** ✅: Track leader payment statistics
- **Regional Management** ✅: Manage assigned users

## Services Layer

### Account Configuration (services/account_configuration.py)
**Post-Sale Automation:**
1. Change account name
2. Change username
3. Set new profile photo (random from presets)
4. Setup new 2FA (after user removes existing one)
5. Terminate other sessions

### Account Management (services/account_management.py)
- **Freeze Management**: Freeze accounts with duration and reason
- **24-Hour Hold**: Detect multi-device usage, auto-hold
- **Expiry Checker**: Auto-release expired freezes
- **Activity Tracking**: Log all account actions

### Proxy Management (services/proxy_manager.py)
- **Daily Rotation**: Automatic IP rotation
- **Health Monitoring**: Track response time, success rate, reputation
- **Load Balancing**: Distribute accounts across proxies
- **Provider Support**: Webshare integration, free proxy fallback

### Session Management (services/session_management.py)
- **Auto-Logout**: Terminate all sessions on other devices
- **Multi-Device Detection**: Alert if same number used on 2+ devices
- **24-48 Hour Hold**: Force hold on multi-device accounts

### Telegram Integration (services/real_telegram.py)
- **Telethon Client**: Real Telegram API operations
- **OTP Handling**: Send/receive verification codes
- **Bypass System**: Flagged account handling
- **Channel Logging**: Send reports to dedicated channels

## Data Flow

### Account Selling Flow
```
User clicks LFG → Enter phone number → OTP sent via Telethon →
User enters OTP → Account verified → AccountConfigurationService runs →
Name/username/photo/2FA changed → Sessions terminated →
Sale logged to database → Channel notification sent
```

### Withdrawal Flow
```
User clicks Withdraw → Select method (TRX/USDT/Binance) →
Enter amount and address → WithdrawalService creates request →
Notification sent to leader channel → Leader processes →
Payment proof uploaded → Status updated to COMPLETED
```

### Freeze/Ban Flow
```
Admin/System detects issue → Account frozen with reason →
Freeze duration set → User notified → Expiry checker runs hourly →
Auto-release when duration expires → User notified
```

## Configuration

### Environment Variables (.env)
```
BOT_TOKEN=              # Telegram bot token
API_ID=                 # Telegram API ID
API_HASH=               # Telegram API hash
DATABASE_URL=           # PostgreSQL/SQLite connection
WEBSHARE_API_KEY=       # Proxy provider key
NOTIFICATION_CHANNEL=   # Channel for logs
WITHDRAWAL_CHANNEL=     # Channel for withdrawal requests
FREEZE_REPORT_CHANNEL=  # Channel for freeze reports
SPAM_REPORT_CHANNEL=    # Channel for spam reports
OTP_REPORT_CHANNEL=     # Channel for OTP logs
```

### System Settings (database)
- `chat_history_deletion_enabled`: Auto-delete chat after sale
- `proxy_rotation_enabled`: Daily IP rotation toggle
- `session_auto_terminate`: Auto-logout other devices
- `freeze_multi_device_enabled`: 24h hold on multi-device detection
- `withdrawal_minimum`: Minimum withdrawal amount
- `default_language`: Default bot language

## Security Features

1. **CAPTCHA Verification**: Image-based human verification
2. **Channel Join Verification**: Require channel membership
3. **Proxy Rotation**: Daily IP changes for account safety
4. **2FA Setup**: Mandatory 2FA on sold accounts
5. **Session Termination**: Auto-logout from other devices
6. **Activity Logging**: All actions tracked for auditing
7. **Freeze System**: Automatic account suspension on issues
8. **Multi-Device Detection**: Alert and hold suspicious activity

## Implemented Features Checklist

### User Panel ✅
- [x] LFG (Sell Button)
- [x] Balance
- [x] Withdraw (TRX, USDT-TRC20, USDT-BEP20, Binance Pay)
- [x] Language Selection
- [x] System Capacity
- [x] Status Check
- [x] Support Contact

### Admin Panel ✅
- [x] Mailing Mode (Broadcast)
- [x] Manual User Edit
- [x] Account Freeze Management
- [x] Sale Logs & Approval
- [x] Chat History Control
- [x] Session Management
- [x] IP/Proxy Configuration
- [x] Activity Tracker
- [x] Reports & Logs

### Leader Panel ✅
- [x] Withdrawal Request Management
- [x] Payment Statistics
- [x] Assigned User Management

### Account Configuration ✅
- [x] Automatic name change
- [x] Automatic username change
- [x] Random profile photo
- [x] 2FA setup
- [x] Session termination

### Session & Security ✅
- [x] Auto-terminate other devices
- [x] Multi-device detection
- [x] 24-48 hour hold system
- [x] Proxy rotation
- [x] Activity logging

### Verification System ✅
- [x] CAPTCHA verification
- [x] Channel join verification
- [x] Task-based verification

## Pending/Future Features

### Not Yet Implemented
- [ ] Separate session file management per country
- [ ] Analytics Dashboard (partially implemented)
- [ ] Settings Overview (currency, limits)
- [ ] Feedback/Issue Reports system
- [ ] Security Control panel (CAPTCHA frequency, 2FA automation)

## Development Guidelines

1. **Model Changes**: Always update both `models.py` and database schema
2. **Handler Registration**: Register in correct order (ConversationHandlers first)
3. **Service Layer**: All business logic in `services/`, not in handlers
4. **Error Handling**: Always use try/except with proper logging
5. **Notifications**: Use `telegram_logger` for channel notifications
6. **Database Sessions**: Always close sessions with `close_db_session()`
7. **Translations**: Use `translation_service` for multi-language support
8. **Testing**: Test all features before deployment

## Deployment

### Local Development
```bash
python real_main.py
```

### Production (Heroku)
```bash
git push heroku main
```

### Database Migration
```bash
python -c "from database import init_db; init_db()"
```

## Troubleshooting

### Common Issues
1. **Import Errors**: Check `database/models.py` for proper model definitions
2. **Unicode Errors**: Ensure all files are UTF-8 encoded
3. **Handler Conflicts**: Check handler registration order in `real_handlers.py`
4. **Database Errors**: Verify model fields match actual database schema
5. **Proxy Issues**: Check `WEBSHARE_API_KEY` and proxy pool health
6. **Session Issues**: Verify Telethon session files exist and are valid

### Debug Mode
Set `DEBUG=True` in `.env` to enable verbose SQL logging.
