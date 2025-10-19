"""
Quick Setup Script for Telegram Account Selling Bot
Helps you configure environment variables step-by-step
"""
import os
from pathlib import Path


def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")


def print_section(text):
    """Print formatted section"""
    print(f"\n{'─' * 80}")
    print(f"📋 {text}")
    print(f"{'─' * 80}\n")


def check_existing_env():
    """Check if .env file exists and what's configured"""
    env_path = Path(".env")
    
    if not env_path.exists():
        return {}
    
    config = {}
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                if value and value != 'your_token_here' and value != 'your_api_id_here':
                    config[key] = '✅ Configured'
                else:
                    config[key] = '❌ Not set'
    
    return config


def main():
    print_header("🤖 TELEGRAM ACCOUNT SELLING BOT - QUICK SETUP")
    
    print("Welcome! This script will help you configure your bot.\n")
    print("You'll need:")
    print("  1. Telegram Bot Token (from @BotFather)")
    print("  2. Telegram API ID & Hash (from https://my.telegram.org/apps)")
    print("  3. Optional: WebShare.io API Token (from https://proxy.webshare.io/userapi/)\n")
    
    input("Press Enter to continue...")
    
    # Check existing config
    print_section("Checking Existing Configuration")
    
    existing = check_existing_env()
    
    if existing:
        print("Found existing .env file:")
        for key, status in existing.items():
            print(f"  • {key}: {status}")
    else:
        print("No .env file found. Will create new one.")
    
    print("\n")
    
    # Ask what to configure
    print_section("What would you like to configure?")
    
    print("1. ✅ Required: Bot Credentials (BOT_TOKEN, API_ID, API_HASH)")
    print("2. 🌐 Optional: WebShare.io API (Premium proxies)")
    print("3. ⚙️  Optional: Advanced Settings (auto-refresh, strategies)")
    print("4. 📊 View Current Status")
    print("5. ❌ Exit")
    
    choice = input("\nEnter choice (1-5): ").strip()
    
    if choice == '1':
        configure_bot_credentials()
    elif choice == '2':
        configure_webshare()
    elif choice == '3':
        configure_advanced()
    elif choice == '4':
        show_status()
    else:
        print("\n👋 Exiting setup. Run again anytime!")
        return
    
    # Ask if they want to test
    print_section("Ready to Test?")
    print("\nYour configuration is saved!")
    print("\n📋 Next Steps:")
    print("  1. Run integration tests: python tests/test_integration_full.py")
    print("  2. Start the bot: python real_main.py")
    print("  3. Test with: /proxy_stats in Telegram\n")
    
    test = input("Run integration tests now? (y/n): ").strip().lower()
    
    if test == 'y':
        print("\n🧪 Running integration tests...\n")
        os.system("python tests/test_integration_full.py")


def configure_bot_credentials():
    """Configure basic bot credentials"""
    print_section("Configure Bot Credentials")
    
    print("📝 Let's configure your bot credentials\n")
    
    # Get Bot Token
    print("1️⃣ Telegram Bot Token")
    print("   Get from: @BotFather on Telegram")
    print("   Format: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz\n")
    
    bot_token = input("Enter BOT_TOKEN: ").strip()
    
    # Get API ID
    print("\n2️⃣ Telegram API ID")
    print("   Get from: https://my.telegram.org/apps")
    print("   Format: 12345678\n")
    
    api_id = input("Enter API_ID: ").strip()
    
    # Get API Hash
    print("\n3️⃣ Telegram API Hash")
    print("   Get from: https://my.telegram.org/apps")
    print("   Format: abcdef1234567890abcdef1234567890\n")
    
    api_hash = input("Enter API_HASH: ").strip()
    
    # Validate
    if not bot_token or not api_id or not api_hash:
        print("\n❌ Error: All fields are required!")
        return
    
    # Save to .env
    env_content = f"""# Telegram Bot Configuration
BOT_TOKEN={bot_token}
TELEGRAM_BOT_TOKEN={bot_token}

# Telegram API Credentials
API_ID={api_id}
API_HASH={api_hash}

# Proxy Configuration (500 free proxies already loaded)
PROXY_STRATEGY=weighted
PROXY_MIN_REPUTATION=50

# WebShare.io (Optional - add token below)
WEBSHARE_ENABLED=false
WEBSHARE_API_TOKEN=your_webshare_token_here

# Auto-Refresh (Optional)
PROXY_AUTO_REFRESH=false
PROXY_REFRESH_INTERVAL=86400
FREE_PROXY_SOURCES_ENABLED=true
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("\n✅ Configuration saved to .env!")
    print("\n📊 Status:")
    print(f"  • BOT_TOKEN: ✅ Set ({bot_token[:10]}...)")
    print(f"  • API_ID: ✅ Set ({api_id})")
    print(f"  • API_HASH: ✅ Set ({api_hash[:10]}...)")


def configure_webshare():
    """Configure WebShare.io"""
    print_section("Configure WebShare.io API")
    
    print("🌐 WebShare.io provides premium datacenter proxies")
    print("   • Get API token: https://proxy.webshare.io/userapi/")
    print("   • Free tier: 10 proxies")
    print("   • Paid plans: Up to 1000+ proxies\n")
    
    token = input("Enter WEBSHARE_API_TOKEN (or Enter to skip): ").strip()
    
    if not token:
        print("\n⏭️  Skipped WebShare configuration")
        print("   You can still use 500 free proxies already loaded!")
        return
    
    # Update .env
    env_path = Path(".env")
    if env_path.exists():
        with open(env_path, 'r') as f:
            content = f.read()
        
        content = content.replace('WEBSHARE_ENABLED=false', 'WEBSHARE_ENABLED=true')
        content = content.replace('WEBSHARE_API_TOKEN=your_webshare_token_here', f'WEBSHARE_API_TOKEN={token}')
        
        with open(env_path, 'w') as f:
            f.write(content)
        
        print("\n✅ WebShare.io configured!")
        print("   • Run /fetch_webshare in bot to sync proxies")
    else:
        print("\n❌ Error: .env file not found. Configure bot credentials first!")


def configure_advanced():
    """Configure advanced settings"""
    print_section("Configure Advanced Settings")
    
    print("⚙️  Advanced Configuration Options:\n")
    
    # Auto-refresh
    print("1. Auto-Refresh Scheduler")
    print("   Automatically fetch fresh proxies daily")
    auto_refresh = input("   Enable? (y/n): ").strip().lower()
    
    # Strategy
    print("\n2. Load Balancing Strategy")
    print("   Options: weighted, reputation_based, country_based, round_robin, least_used, random")
    strategy = input("   Strategy (default: weighted): ").strip() or "weighted"
    
    # Min reputation
    print("\n3. Minimum Reputation Score")
    print("   Only use proxies above this score (0-100)")
    min_rep = input("   Min reputation (default: 50): ").strip() or "50"
    
    # Update .env
    env_path = Path(".env")
    if env_path.exists():
        with open(env_path, 'r') as f:
            content = f.read()
        
        if auto_refresh == 'y':
            content = content.replace('PROXY_AUTO_REFRESH=false', 'PROXY_AUTO_REFRESH=true')
        
        content = content.replace('PROXY_STRATEGY=weighted', f'PROXY_STRATEGY={strategy}')
        content = content.replace('PROXY_MIN_REPUTATION=50', f'PROXY_MIN_REPUTATION={min_rep}')
        
        with open(env_path, 'w') as f:
            f.write(content)
        
        print("\n✅ Advanced settings configured!")
    else:
        print("\n❌ Error: .env file not found. Configure bot credentials first!")


def show_status():
    """Show current configuration status"""
    print_section("Current Configuration Status")
    
    existing = check_existing_env()
    
    if not existing:
        print("❌ No configuration found. Please run setup first!\n")
        return
    
    print("📊 Configuration Status:\n")
    
    # Required
    print("✅ Required Settings:")
    for key in ['BOT_TOKEN', 'API_ID', 'API_HASH']:
        status = existing.get(key, '❌ Not set')
        print(f"  • {key}: {status}")
    
    # Optional
    print("\n🌐 Optional Settings:")
    for key in ['WEBSHARE_API_TOKEN', 'WEBSHARE_ENABLED']:
        status = existing.get(key, '❌ Not set')
        print(f"  • {key}: {status}")
    
    # Advanced
    print("\n⚙️  Advanced Settings:")
    for key in ['PROXY_AUTO_REFRESH', 'PROXY_STRATEGY', 'PROXY_MIN_REPUTATION']:
        status = existing.get(key, '❌ Not set')
        print(f"  • {key}: {status}")
    
    print("\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Setup cancelled. Run again anytime!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Please report this issue or configure .env manually")
