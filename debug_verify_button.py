#!/usr/bin/env python3
"""
Debug script to test the verify membership button functionality
"""
import asyncio
from unittest.mock import MagicMock
from handlers.main_handlers import handle_verify_channels

async def test_verify_button():
    """Test the verify channels handler"""
    print("🧪 Testing verify membership button handler...")
    
    # Create mock update and context
    update = MagicMock()
    context = MagicMock()
    
    # Mock callback query
    update.callback_query.answer = MagicMock()
    update.callback_query.edit_message_text = MagicMock()
    
    # Mock effective user
    update.effective_user.id = 123456
    
    try:
        # Test the handler
        await handle_verify_channels(update, context)
        print("✅ Handler executed successfully")
    except Exception as e:
        print(f"❌ Handler failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_verify_button())