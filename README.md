# Telegram Account Bot

A comprehensive Telegram bot for secure account management with advanced features including automated login, 2FA setup, proxy protection, and withdrawal system.

## 🚀 Features

### 🔐 Security & Account Management
- **Secure Login Flow**: Multi-step verification with captcha protection
- **Unique Proxy Assignment**: Each account gets a dedicated proxy for privacy
- **Automatic 2FA Setup**: Strong password generation and secure storage
- **Session Isolation**: Logout from other devices for exclusive access
- **Duplicate Protection**: 24-hour hold system for conflicting accounts
- **OTP Monitoring**: Real-time detection of external login attempts

### 💰 Financial System
- **Balance Management**: Track earnings and account performance  
- **Multi-Currency Withdrawals**: Support for USDT-BEP20, TRX, and more
- **Admin Control**: Toggle withdrawal systems and manage payouts
- **Secure Processing**: Manual review for all withdrawal requests

### 🛠️ Administration
- **Comprehensive Dashboard**: System statistics and account overview
- **Withdrawal Management**: Approve/reject requests with one click
- **Broadcast System**: Send announcements to all active users
- **Proxy Management**: Control proxy rotation and IP management
- **Activity Logging**: Comprehensive audit trails for all user actions
- **Real-time Monitoring**: Health checks and security alerts
- **System Settings**: Configure currencies and operational parameters

### 🌍 User Experience  
- **Multi-language Support**: English, Spanish, French, German, Russian, Chinese, Hindi, Arabic
- **Language Persistence**: User language preferences saved to database and applied across all menus
- **Intuitive Interface**: Clean inline keyboards and guided flows
- **Responsive Design**: Works seamlessly on mobile and desktop
- **Help System**: Comprehensive documentation and support channels

## 📋 Requirements

### Recent Updates (v2.1.0)
- ✅ **Language Persistence**: User language selections are now saved to database and persist across sessions
- ✅ **Proxy Controls**: Admin panel now includes proxy/IP rotation management controls
- ✅ **Activity Logging**: Comprehensive audit logging for all critical user flows and admin actions
- ✅ **Enhanced Testing**: Added unit tests for core functionality with pytest framework
- ✅ **Code Quality**: Improved error handling and indentation fixes across handlers

### System Requirements
- Python 3.12+
- SQLite (default) or PostgreSQL
- 1GB+ RAM recommended
- Windows/Linux/macOS

### Python Dependencies
All dependencies are listed in `requirements.txt`. Key packages:
```
python-telegram-bot==20.7
telethon==1.33.1
sqlalchemy==2.0.23
python-dotenv==1.0.0
requests==2.31.0
cryptography==41.0.8
aiohttp==3.9.1
pillow==10.1.0
```

### External Services
- Telegram Bot API (get token from @BotFather)
- Telegram API credentials (api_id, api_hash from my.telegram.org)
- Proxy service (optional but recommended for production)
- Database: SQLite (included) or PostgreSQL for production

## 🛠️ Installation & Setup

### 1. Clone Repository
```bash
git clone <repository-url>
cd teleaccount_bot
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Database Setup
The bot uses SQLite by default (no setup required). The database file `teleaccount_bot.db` will be created automatically on first run.

For production PostgreSQL setup:
```bash
# Install PostgreSQL (Ubuntu/Debian)
sudo apt update
sudo apt install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql
CREATE DATABASE teleaccount_bot;
CREATE USER bot_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE teleaccount_bot TO bot_user;
\q

# Update .env with PostgreSQL connection string
DATABASE_URL=postgresql://bot_user:your_secure_password@localhost:5432/teleaccount_bot
```

### 4. Environment Configuration
```bash
# Copy and edit environment file
cp .env.example .env
nano .env
```

**Required Environment Variables:**
```env
# Telegram Bot Configuration
BOT_TOKEN=your_bot_token_here
BOT_USERNAME=your_bot_username

# Telegram API Configuration (for Telethon)  
API_ID=your_api_id
API_HASH=your_api_hash

# Database Configuration (SQLite is default)
# DATABASE_URL=sqlite:///teleaccount_bot.db  # Default
# DATABASE_URL=postgresql://user:pass@localhost:5432/teleaccount_bot  # PostgreSQL

# Admin Configuration
ADMIN_CHAT_ID=your_admin_chat_id
ADMIN_USER_ID=your_admin_user_id

# Channel Configuration (for verification)
CHANNEL_USERNAME=your_channel_username
CHANNEL_ID=your_channel_id

# Proxy Configuration (optional)
PROXY_LIST_URL=your_proxy_list_url
PROXY_USERNAME=your_proxy_username  
PROXY_PASSWORD=your_proxy_password

# Security
ENCRYPTION_KEY=your_32_byte_encryption_key_here

# Webapp (optional)
WEBAPP_URL=https://your-domain.com
PORT=8080
```

### 5. Initialize Database
The database tables will be created automatically on first run. To manually initialize:
```bash
python -c "from database.models import Base; from database import engine; Base.metadata.create_all(engine)"
```

### 6. Set Up Admin User
After first run, add yourself as admin:
```bash
python -c "from database.operations import UserService; from database import SessionLocal; db = SessionLocal(); user = UserService.get_user(db, YOUR_TELEGRAM_USER_ID); user.is_admin = True; db.commit()"
```

### 7. Run the Bot
```bash
python real_main.py
```

For production deployment:
```bash
# Using Heroku
git push heroku main

# Using systemd (Linux)
sudo systemctl start teleaccount-bot
```

### 8. Run Tests (Optional)
```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-mock

# Run all tests
pytest tests/

# Run specific test
pytest tests/test_language_persistence.py -v
```

## 📖 Usage Guide

### For Users

#### Getting Started
1. Start the bot: `/start`
2. Add account: `/lfg` or click "✅ Let's Get Started"
3. Complete captcha verification
4. Enter phone number (international format: +1234567890)
5. Enter verification code from SMS
6. Wait for automatic security setup

#### Managing Accounts
- **Check Balance**: `/balance` - View earnings and withdrawal history
- **View Accounts**: `/accounts` - See all managed accounts and their status  
- **Request Withdrawal**: `/withdraw` - Cash out earnings to crypto wallet
- **Get Help**: `/help` - Access documentation and support

#### Account Status
- **✅ ACTIVE**: Account is working and earning
- **❄️ FROZEN**: Temporary issue, contact support
- **🚫 BANNED**: Account disabled by Telegram
- **⏳ 24_HOUR_HOLD**: Security review in progress

### For Administrators

#### Admin Dashboard
Access: `/admin` (admin privileges required)

**Features:**
- System statistics and overview
- User and account management
- Withdrawal processing
- System configuration
- Broadcast messaging

#### Withdrawal Management
1. Navigate to "💸 Manage Withdrawals"  
2. Review pending requests
3. Click "✅ Approve" or "❌ Reject"
4. Users are automatically notified

#### System Settings
Toggle withdrawal systems:
- USDT-BEP20 withdrawals
- TRX withdrawals
- Additional currencies (configurable)

#### Broadcasting Messages
1. Click "📢 Broadcast Message"
2. Enter message text (supports Markdown)
3. Confirm and send to all users

## 🏗️ Project Structure

```
teleaccount_bot/
├── real_main.py           # Application entry point
├── requirements.txt       # Python dependencies
├── .env.example          # Environment configuration template
├── .gitignore            # Git ignore rules
├── Procfile              # Heroku deployment configuration
├── runtime.txt           # Python runtime version
│
├── database/             # Database layer
│   ├── __init__.py      # Database configuration
│   ├── models.py        # SQLAlchemy models (User, Withdrawal, SystemSettings)
│   ├── operations.py    # Database service layer (UserService, WithdrawalService)
│   └── migrations/      # Database migration scripts
│
├── handlers/             # Bot command handlers
│   ├── __init__.py      # Handler registration
│   ├── real_handlers.py # Main handlers (start, CAPTCHA, verification, LFG flow)
│   ├── main_handlers.py # Withdrawal and transaction handlers
│   ├── admin_handlers.py # Admin dashboard and management
│   ├── leader_handlers.py # Leader system handlers
│   ├── analytics_handlers.py # Analytics dashboard
│   └── proxy_admin_commands.py # Proxy management
│
├── services/             # Core business logic
│   ├── __init__.py
│   ├── proxy_service.py # Proxy assignment and rotation
│   ├── telethon_service.py # Telegram client management
│   ├── notification_service.py # User notifications
│   └── scheduler_service.py # Background tasks
│
├── utils/                # Utility functions
│   ├── __init__.py
│   ├── decorators.py    # Authentication decorators
│   ├── validators.py    # Input validation
│   └── logger.py        # Logging configuration
│
├── locales/              # Internationalization
│   ├── __init__.py      # Locale manager
│   └── *.json           # Translation files (en, es, ru)
│
├── webapp/               # Web interface components
│   └── __init__.py
│
├── assets/               # Static files (captcha images, etc.)
├── temp_captchas/        # Temporary CAPTCHA storage
├── logs/                 # Application logs (auto-created)
├── tests/                # Unit tests and test utilities
└── config/               # Configuration files
```

## 🔧 Configuration

### Database Models

#### Users Table (`database/models.py`)
```python
class User:
    user_id: Integer (Primary Key)
    username: String
    balance: Float
    is_admin: Boolean
    is_leader: Boolean
    is_verified: Boolean
    verification_step: Integer
    language: String
    created_at: DateTime
    updated_at: DateTime
```

#### Withdrawals Table
```python
class Withdrawal:
    id: Integer (Primary Key)
    user_id: Integer (Foreign Key)
    amount: Float
    currency: String
    withdrawal_address: String
    withdrawal_method: String
    status: String (pending, approved, rejected)
    assigned_leader_id: Integer
    leader_notes: Text
    payment_proof: Text
    created_at: DateTime
    updated_at: DateTime
    processed_at: DateTime
```

#### SystemSettings Table
```python
class SystemSettings:
    key: String (Primary Key)
    value: String
    description: Text
    updated_at: DateTime
```

### Security Features

#### Proxy Management
- Automatic unique proxy assignment
- Failure detection and rotation
- Geographic distribution support
- Connection health monitoring

#### 2FA Protection
- Strong password generation (20+ characters)
- Secure hash storage (SHA-256)
- Automatic setup during account creation
- Database encryption support

#### Session Security
- Exclusive session control
- Other device logout on setup
- Session file protection
- Activity monitoring

#### OTP Detection
- Real-time monitoring for external login attempts
- Automatic admin notifications
- Account security flagging
- Background health checks

## 🚨 Security Considerations

### Data Protection
- All sensitive data is encrypted at rest
- Session files are secured with proper permissions
- Database connections use SSL/TLS
- API keys are environment-based (never hardcoded)

### Access Control
- Admin functions require explicit user ID verification
- User isolation ensures data privacy
- Audit logging for all admin actions
- Rate limiting on sensitive operations

### Operational Security
- Regular security audits recommended
- Monitor logs for suspicious activity
- Keep dependencies updated
- Use strong database credentials

### Compliance
- Respects Telegram Terms of Service
- User data handling follows privacy best practices
- Transparent operation policies
- Support for data deletion requests

## 🐛 Troubleshooting

### Common Issues

#### Database Connection Failed
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Verify connection
psql -h localhost -U bot_user -d teleaccount_bot
```

#### Bot Not Responding
```bash
# Check logs
tail -f logs/bot.log

# Verify token
curl -X GET "https://api.telegram.org/bot<YOUR_TOKEN>/getMe"
```

#### Proxy Issues
- Verify proxy list format and accessibility
- Check proxy credentials
- Monitor proxy failure rates in logs
- Consider using residential proxies

#### Telethon Errors
- Ensure API credentials are correct
- Check session file permissions
- Verify phone number format
- Monitor rate limiting

### Log Analysis
```bash
# Follow logs in real-time
tail -f logs/bot.log

# Search for errors
grep "ERROR" logs/bot.log

# Monitor specific operations
grep "withdrawal\\|lfg\\|login" logs/bot.log
```

## 🔄 Maintenance

### Regular Tasks
- **Database Backups**: Daily automated backups recommended
- **Log Rotation**: Configure logrotate for application logs
- **Dependency Updates**: Monthly security update reviews
- **Performance Monitoring**: Track response times and resource usage

### Monitoring
- Set up alerts for critical errors
- Monitor database performance
- Track user activity patterns
- Watch for security anomalies

### Scaling
- Database connection pooling for high load
- Redis session storage for multi-instance deployment
- Load balancer for webhook endpoints
- Horizontal scaling with message queues

## 📞 Support

### Documentation
- In-bot help system: `/help`
- Admin documentation: `/admin` command guide
- API reference in code comments

### Getting Help
- GitHub Issues: Report bugs and feature requests
- Community Support: Join our Telegram channel
- Professional Support: Contact for enterprise deployments

### Contributing
1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This software is provided for educational and legitimate business purposes only. Users are responsible for compliance with:

- Telegram Terms of Service
- Local and international laws
- Data protection regulations
- Privacy requirements

The developers assume no responsibility for misuse or violations of service terms.

---

**Built with ❤️ for secure Telegram account management**