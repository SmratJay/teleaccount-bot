import sqlite3

conn = sqlite3.connect('teleaccount_bot.db')
cursor = conn.cursor()

# Clear encrypted passwords
cursor.execute("UPDATE proxy_pool SET password = NULL")
conn.commit()

print(f"Cleared {cursor.rowcount} passwords")
print("Proxies will use username-only auth or no auth")

conn.close()

# Test ProxyManager now
print("\nTesting ProxyManager...")

from services.proxy_manager import ProxyManager

manager = ProxyManager()
proxy = manager.get_proxy_for_operation('login')

if proxy:
    print("Proxy selected successfully!")
    print(f"   IP: {proxy.addr}")
    print(f"   Port: {proxy.port}")
    print(f"   Username: {proxy.username if proxy.username else 'None'}")
    print(f"   Type: {proxy.proxy_type}")
else:
    print("No proxy selected")
