#!/usr/bin/env python3
"""
Keep Alive Service for Replit Free Tier
This keeps your bot running 24/7 on free Replit by serving a simple web page
"""
from flask import Flask
from threading import Thread
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def home():
    """Health check endpoint"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Telegram Account Bot</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; margin-top: 50px; }
            .status { color: #28a745; font-size: 24px; }
            .info { color: #6c757d; margin-top: 20px; }
        </style>
    </head>
    <body>
        <h1>🤖 Telegram Account Bot</h1>
        <div class="status">✅ Bot is Running!</div>
        <div class="info">
            <p>Your Telegram bot is active and ready to serve users.</p>
            <p>OTP mechanism and withdrawal system are fully operational.</p>
        </div>
    </body>
    </html>
    """

@app.route('/status')
def status():
    """API status endpoint"""
    return {
        "status": "running",
        "bot": "active",
        "features": {
            "otp_mechanism": "operational",
            "withdrawal_system": "operational", 
            "admin_panel": "operational"
        }
    }

@app.route('/health')
def health():
    """Health check for monitoring services"""
    return {"status": "healthy", "timestamp": "2025-10-18"}

def run_flask():
    """Run Flask app in background"""
    try:
        app.run(host='0.0.0.0', port=8080, debug=False)
    except Exception as e:
        logger.error(f"Flask server error: {e}")

def keep_alive():
    """Start the keep-alive server"""
    logger.info("🌐 Starting keep-alive server on port 8080...")
    t = Thread(target=run_flask)
    t.daemon = True  # Dies when main thread dies
    t.start()
    logger.info("✅ Keep-alive server started successfully")

# Usage instructions for UptimeRobot or similar monitoring services:
# 1. Get your Replit URL (e.g., https://telegram-account-bot.yourusername.repl.co)
# 2. Sign up for UptimeRobot (free tier allows 50 monitors)
# 3. Create HTTP(s) monitor pointing to your Replit URL
# 4. Set monitoring interval to 5 minutes
# 5. This will ping your bot every 5 minutes, keeping it alive

if __name__ == "__main__":
    # Test the Flask app independently
    print("🧪 Testing keep-alive server...")
    keep_alive()
    print("✅ Keep-alive server is running!")
    print("Visit http://localhost:8080 to test")
    
    # Keep the main thread alive for testing
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("🛑 Server stopped")