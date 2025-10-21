"""
Simple HTTP Server for Telegram WebApp Forms
Serves the embedded phone and OTP input forms
"""
import http.server
import socketserver
import os
import threading
import logging
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)

class WebAppHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler for WebApp files with CORS support."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.join(os.getcwd(), 'webapp'), **kwargs)
    
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        # Handle preflight requests
        self.send_response(200)
        self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass

class WebAppServer:
    """WebApp server for hosting Telegram forms."""
    
    def __init__(self, port=8080):
        self.port = port
        self.server = None
        self.thread = None
    
    def start(self):
        """Start the WebApp server in background thread."""
        try:
            self.server = socketserver.TCPServer(("", self.port), WebAppHandler)
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            logger.info(f"WebApp server started on http://localhost:{self.port}")
            return True
        except OSError as e:
            if e.errno == 10048:  # Port already in use
                logger.info(f"WebApp server already running on port {self.port}")
                return True
            logger.error(f"Failed to start WebApp server: {e}")
            return False
    
    def stop(self):
        """Stop the WebApp server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            logger.info("WebApp server stopped")
    
    def get_phone_url(self):
        """Get URL for phone input form."""
        return f"http://localhost:{self.port}/phone_input.html"
    
    def get_otp_url(self, phone_number):
        """Get URL for OTP input form with phone number."""
        return f"http://localhost:{self.port}/otp_input.html?phone={phone_number}"

# Global server instance
webapp_server = WebAppServer()

def start_webapp_server():
    """Start the WebApp server."""
    return webapp_server.start()

def get_webapp_urls():
    """Get WebApp URLs for forms."""
    return {
        'phone': webapp_server.get_phone_url(),
        'otp': webapp_server.get_otp_url
    }
