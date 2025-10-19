"""
Configuration for Advanced Telegram Security Bypass System
Handles flagged accounts and security restrictions
"""

# Bypass Strategy Options
BYPASS_OPTIONS = {
    # Core bypass features
    'enabled': True,
    'auto_retry': True,
    'max_retries': 5,
    'retry_delay': 8,  # seconds between retries
    
    # Device spoofing
    'rotate_devices': True,
    'random_device_on_each_attempt': True,
    
    # Timing and behavior
    'add_realistic_delays': True,
    'min_delay': 1.0,  # seconds
    'max_delay': 3.0,  # seconds
    
    # Advanced features
    'use_browser_masking': True,
    'rotate_user_agents': True,
    'maintain_session_cookies': True,
    
    # Proxy/VPN support (optional)
    'use_proxy': False,
    'proxy_url': None,  # Set to 'socks5://user:pass@host:port' if needed
    
    # 2FA handling
    'support_2fa': True,
    'auto_detect_2fa': True,
    
    # Error handling
    'handle_flood_wait': True,
    'handle_code_expired': True,
    'handle_security_blocks': True,
}

# Device profiles for spoofing
DEVICE_PROFILES = [
    {
        'device_model': 'iPhone 14 Pro',
        'system_version': 'iOS 17.1.1',
        'app_version': '10.2.5',
        'lang_code': 'en',
        'system_lang_code': 'en-US'
    },
    {
        'device_model': 'iPhone 13',
        'system_version': 'iOS 16.6.1',
        'app_version': '10.1.2',
        'lang_code': 'en',
        'system_lang_code': 'en-GB'
    },
    {
        'device_model': 'Samsung Galaxy S23',
        'system_version': 'Android 13',
        'app_version': '10.2.0',
        'lang_code': 'en',
        'system_lang_code': 'en-US'
    },
    {
        'device_model': 'Samsung Galaxy S22',
        'system_version': 'Android 12',
        'app_version': '10.1.1',
        'lang_code': 'en',
        'system_lang_code': 'en-GB'
    },
    {
        'device_model': 'Google Pixel 7',
        'system_version': 'Android 13',
        'app_version': '10.2.3',
        'lang_code': 'en',
        'system_lang_code': 'en-US'
    },
    {
        'device_model': 'OnePlus 11',
        'system_version': 'Android 13',
        'app_version': '10.2.1',
        'lang_code': 'en',
        'system_lang_code': 'en-US'
    },
]

# Browser User-Agents for masking
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]

# Retry strategies for different error types
RETRY_STRATEGIES = {
    'PhoneCodeExpiredError': {
        'max_retries': 3,
        'delay': 5,
        'strategy': 'resend_code'
    },
    'PhoneCodeInvalidError': {
        'max_retries': 2,
        'delay': 3,
        'strategy': 'prompt_user'
    },
    'FloodWaitError': {
        'max_retries': 1,
        'delay': 'wait_time',  # Use the wait time from error
        'strategy': 'wait_and_retry'
    },
    'SecurityBlockError': {
        'max_retries': 5,
        'delay': 10,
        'strategy': 'change_device_and_retry'
    },
    'SessionPasswordNeededError': {
        'max_retries': 1,
        'delay': 0,
        'strategy': 'request_2fa_password'
    },
}

# Timing profiles for human-like behavior
TIMING_PROFILES = {
    'code_reading': (1.0, 2.5),  # Time to read SMS/code
    'typing_per_char': (0.08, 0.18),  # Time per character
    'double_check': (0.5, 1.5),  # Time to verify before submit
    'submission': (0.2, 0.6),  # Time to click submit
}

# Flagged account detection patterns
FLAGGED_INDICATORS = [
    'code was shared',
    'code was previously shared',
    'sign in was not allowed',
    'security check failed',
    'unusual activity detected',
]

# Logging configuration
BYPASS_LOGGING = {
    'log_attempts': True,
    'log_device_changes': True,
    'log_timing': True,
    'log_errors': True,
    'verbose': False,  # Set True for detailed logs
}
