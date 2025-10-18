#!/usr/bin/env python3
"""
CLEAN OTP SYSTEM FIX - Update environment variable names
"""

def fix_env_vars():
    # Read the clean handler
    with open('clean_otp_handler.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix environment variable names
    content = content.replace(
        "os.getenv('TELEGRAM_API_ID', '123456')",
        "os.getenv('API_ID', '21734417')"
    )
    content = content.replace(
        "os.getenv('TELEGRAM_API_HASH', 'abc123')",
        "os.getenv('API_HASH', 'd64eb98d90eb41b8ba3644e3722a3714')"
    )
    
    # Write the corrected version
    with open('clean_otp_handler.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ FIXED: Updated environment variable names for real API credentials!")

if __name__ == "__main__":
    fix_env_vars()