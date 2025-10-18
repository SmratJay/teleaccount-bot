#!/usr/bin/env python3
"""
CLEAN OTP SYSTEM IMPLEMENTATION
Replace the messy ultra-aggressive handler with a clean implementation
"""

import re

def clean_otp_implementation():
    # Read the main file
    with open('handlers/real_handlers.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Read the clean implementation
    with open('clean_otp_handler.py', 'r', encoding='utf-8') as f:
        clean_handler = f.read()
    
    # Find the start and end of the messy function
    start_pattern = r'    async def ultra_aggressive_captcha_answer_real\(update, context\):'
    end_pattern = r'    # Add ultra-aggressive message handler for captcha answers \(highest priority\)'
    
    # Replace the messy function with clean implementation
    new_content = re.sub(
        f'({start_pattern}.*?)({end_pattern})',
        f'    {clean_handler.strip()}\n\n    # Add ultra-aggressive message handler for captcha answers (highest priority)',
        content,
        flags=re.DOTALL
    )
    
    # Write back the cleaned file
    with open('handlers/real_handlers.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ CLEANED: Replaced messy OTP code with clean implementation!")

if __name__ == "__main__":
    clean_otp_implementation()