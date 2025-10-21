"""
Test script to verify session data and account manipulation capabilities
"""
import asyncio
import os
from telethon import TelegramClient
from telethon.tl.functions.account import UpdateProfileRequest

# Get API credentials from environment
API_ID = int(os.getenv('API_ID', '0'))
API_HASH = os.getenv('API_HASH', '')

async def test_session_access():
    """Test if we can access the account using the session file"""
    session_file = 'secure_dd89394c.session'
    
    print(f"\n{'='*60}")
    print("TESTING SESSION ACCESS & ACCOUNT MANIPULATION")
    print(f"{'='*60}\n")
    
    if not os.path.exists(session_file):
        print(f"❌ Session file not found: {session_file}")
        return
    
    print(f"✅ Session file found: {session_file} ({os.path.getsize(session_file)} bytes)")
    
    # Create client with the session
    client = TelegramClient(session_file.replace('.session', ''), API_ID, API_HASH)
    
    try:
        await client.connect()
        
        if not await client.is_user_authorized():
            print("❌ Session is not authorized!")
            return
        
        print("✅ Session is authorized!")
        
        # Get current account info
        me = await client.get_me()
        print(f"\n{'='*60}")
        print("CURRENT ACCOUNT DETAILS:")
        print(f"{'='*60}")
        print(f"📱 Phone: {me.phone}")
        print(f"👤 Name: {me.first_name} {me.last_name or ''}")
        print(f"🆔 Username: @{me.username}" if me.username else "🆔 Username: None")
        print(f"🔢 User ID: {me.id}")
        print(f"📝 Bio: {me.about if hasattr(me, 'about') and me.about else 'None'}")
        
        # Test account manipulation - change name temporarily
        print(f"\n{'='*60}")
        print("TESTING ACCOUNT MANIPULATION:")
        print(f"{'='*60}")
        
        original_first_name = me.first_name
        original_last_name = me.last_name or ''
        
        print(f"\n🔄 Attempting to change name to 'Test User'...")
        await client(UpdateProfileRequest(
            first_name="Test",
            last_name="User"
        ))
        
        # Verify change
        me_updated = await client.get_me()
        print(f"✅ Name changed to: {me_updated.first_name} {me_updated.last_name}")
        
        # Revert back to original
        print(f"\n🔄 Reverting to original name...")
        await client(UpdateProfileRequest(
            first_name=original_first_name,
            last_name=original_last_name
        ))
        
        me_reverted = await client.get_me()
        print(f"✅ Name reverted to: {me_reverted.first_name} {me_reverted.last_name or ''}")
        
        print(f"\n{'='*60}")
        print("✅ ACCOUNT MANIPULATION TEST SUCCESSFUL!")
        print("✅ We have full access to manipulate this account!")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(test_session_access())
