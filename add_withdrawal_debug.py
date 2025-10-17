#!/usr/bin/env python3
"""
Add debug logging to withdrawal handlers to see what's happening
"""

import logging
from datetime import datetime

def add_debug_logging():
    """Add debug logging to track withdrawal handler calls."""
    
    # Read the current handlers
    with open('handlers/main_handlers.py', 'r') as f:
        content = f.read()
    
    # Check if debug logging is already added
    if "DEBUG_WITHDRAWAL" in content:
        print("Debug logging already exists")
        return
    
    # Add debug logging to withdrawal functions
    debug_lines = [
        '    logger.info(f"🔧 DEBUG_WITHDRAWAL - handle_withdraw_trx called by user {user.id}")',
        '    logger.info(f"🔧 DEBUG_WITHDRAWAL - Callback data: {query.data}")',
        '    logger.info(f"🔧 DEBUG_WITHDRAWAL - Context user_data: {context.user_data}")'
    ]
    
    # Find and modify handle_withdraw_trx
    lines = content.split('\n')
    new_lines = []
    
    for i, line in enumerate(lines):
        new_lines.append(line)
        
        # Add debug logging after the function definition
        if 'async def handle_withdraw_trx(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:' in line:
            new_lines.extend([
                '    """Handle TRX withdrawal option."""',
                '    # DEBUG LOGGING',
                '    user = update.effective_user',
                '    logger.info(f"🔧 DEBUG_WITHDRAWAL - handle_withdraw_trx called by user {user.id}")',
                ''
            ])
            # Skip the original docstring
            if i + 1 < len(lines) and '"""' in lines[i + 1]:
                continue
    
    # Write back
    with open('handlers/main_handlers.py', 'w') as f:
        f.write('\n'.join(new_lines))
    
    print("✅ Debug logging added to withdrawal handlers")

if __name__ == "__main__":
    add_debug_logging()