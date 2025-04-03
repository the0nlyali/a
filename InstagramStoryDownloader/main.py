import os
import threading
import time
import requests
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from threading import Thread
from bot import run_bot
from instagram_handler import InstagramHandler

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed from INFO to DEBUG to show more detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create Flask app
app = Flask(__name__)

# Global variables
bot_thread = None
keep_alive_thread = None
instagram_login_thread = None
app_url = os.environ.get("REPL_SLUG", "instagram-downloader-bot") + ".replit.app"
last_ping_time = None
instagram_handler = InstagramHandler()  # Initialize without blocking login


# Flask app is initialized earlier, no need for duplicate initialization
@app.route('/')
def index():
    """Display a simple web interface."""
    global last_ping_time
    
    # Format last ping time if available
    ping_status = "No pings yet"
    if last_ping_time:
        ping_status = f"Last ping: {last_ping_time.strftime('%Y-%m-%d %H:%M:%S')}"
    
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Instagram Downloader Bot</title>
        <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
        <meta http-equiv="refresh" content="300">
    </head>
    <body class="bg-dark" data-bs-theme="dark">
        <div class="container py-5">
            <div class="row justify-content-center">
                <div class="col-md-10">
                    <div class="card border-0 shadow">
                        <div class="card-body p-4">
                            <div class="d-flex align-items-center mb-4">
                                <div class="display-4 me-3">📱</div>
                                <div>
                                    <h1 class="card-title mb-1">Instagram Downloader Bot</h1>
                                    <p class="text-secondary mb-0">Download stories, posts, and reels via Telegram</p>
                                </div>
                            </div>
                            
                            <div class="alert alert-success d-flex align-items-center" role="alert">
                                <div class="me-3 fs-4">✅</div>
                                <div>
                                    <h4 class="alert-heading mb-1">Bot is Online</h4>
                                    <p class="mb-0">{ping_status}</p>
                                </div>
                            </div>
                            
                            <div class="card mb-4 border-0 bg-dark bg-opacity-25">
                                <div class="card-body">
                                    <h4 class="card-title">Features</h4>
                                    <ul class="list-group list-group-flush bg-transparent">
                                        <li class="list-group-item bg-transparent border-secondary">Download Instagram stories from any public profile</li>
                                        <li class="list-group-item bg-transparent border-secondary">Save posts with multiple images and videos</li>
                                        <li class="list-group-item bg-transparent border-secondary">Download reels in high quality</li>
                                        <li class="list-group-item bg-transparent border-secondary">Supports multiple Instagram accounts for rotation</li>
                                        <li class="list-group-item bg-transparent border-secondary">Intelligent rate limiting to avoid Instagram restrictions</li>
                                    </ul>
                                </div>
                            </div>
                            
                            <div class="card mb-4 border-0 bg-dark bg-opacity-25">
                                <div class="card-body">
                                    <h4 class="card-title">How to Use</h4>
                                    <ol class="list-group list-group-flush bg-transparent">
                                        <li class="list-group-item bg-transparent border-secondary">Open Telegram and search for your bot</li>
                                        <li class="list-group-item bg-transparent border-secondary">Start a conversation with <code>/start</code></li>
                                        <li class="list-group-item bg-transparent border-secondary">Send an Instagram username to download stories</li>
                                        <li class="list-group-item bg-transparent border-secondary">Send a post or reel URL to download the content</li>
                                    </ol>
                                </div>
                            </div>
                            
                            <div class="row mb-4">
                                <div class="col-md-6">
                                    <div class="card h-100 border-0 bg-dark bg-opacity-25">
                                        <div class="card-body">
                                            <h4 class="card-title">Basic Commands</h4>
                                            <ul class="list-group list-group-flush bg-transparent">
                                                <li class="list-group-item bg-transparent border-secondary"><code>/start</code> - Start the bot</li>
                                                <li class="list-group-item bg-transparent border-secondary"><code>/help</code> - Show help information</li>
                                                <li class="list-group-item bg-transparent border-secondary"><code>/login username password</code> - Set Instagram credentials</li>
                                                <li class="list-group-item bg-transparent border-secondary"><code>/status</code> - Check if you're logged in</li>
                                                <li class="list-group-item bg-transparent border-secondary"><code>/verify CODE</code> - Enter verification code</li>
                                            </ul>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="card h-100 border-0 bg-dark bg-opacity-25">
                                        <div class="card-body">
                                            <h4 class="card-title">Admin Commands</h4>
                                            <ul class="list-group list-group-flush bg-transparent">
                                                <li class="list-group-item bg-transparent border-secondary"><code>/accounts</code> - List all Instagram accounts</li>
                                                <li class="list-group-item bg-transparent border-secondary"><code>/addaccount username password</code> - Add account</li>
                                                <li class="list-group-item bg-transparent border-secondary"><code>/removeaccount username</code> - Remove account</li>
                                                <li class="list-group-item bg-transparent border-secondary"><code>/rotate</code> - Manual account rotation</li>
                                                <li class="list-group-item bg-transparent border-secondary"><code>/setlimit username limit</code> - Set daily request limit</li>
                                                <li class="list-group-item bg-transparent border-secondary"><code>/setcooldown username hours</code> - Set cooldown period</li>
                                            </ul>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="alert alert-secondary bg-opacity-25">
                                <h5 class="alert-heading">Important Notes</h5>
                                <ul class="mb-0 ps-3">
                                    <li>The bot can only download from public profiles or profiles you have access to</li>
                                    <li>Videos larger than 50MB cannot be sent via Telegram</li>
                                    <li>Instagram may require verification occasionally - check your email</li>
                                    <li>Account rotation system helps avoid Instagram rate limits</li>
                                    <li>Admin commands are only available to specified admin users</li>
                                </ul>
                            </div>
                            
                            <div class="mt-4 text-center">
                                <a href="https://t.me/your_bot_username" class="btn btn-primary btn-lg">
                                    Open Bot on Telegram
                                </a>
                            </div>
                            
                            <div class="mt-4 pt-3 border-top border-secondary">
                                <p class="text-secondary small mb-0 text-center">
                                    This bot is for personal use and educational purposes only. 
                                    Please respect Instagram's terms of service and copyright restrictions.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

@app.route('/ping')
def ping():
    """Endpoint for the keep-alive system to ping"""
    global last_ping_time
    last_ping_time = datetime.now()
    return jsonify({"status": "alive", "time": last_ping_time.isoformat()})

def keep_alive_task():
    """Function to keep the application alive by sending periodic requests to itself"""
    while True:
        try:
            # Self ping to keep the application alive (using port 5000)
            response = requests.get(f"https://{app_url}/ping")
            logging.info(f"Keep-alive ping sent. Response: {response.status_code}")
        except Exception as e:
            logging.error(f"Error sending keep-alive ping: {e}")
        
        # Sleep for 5 minutes before pinging again
        time.sleep(300)  # 5 minutes

def start_bot_thread():
    """Start the bot in a separate thread."""
    global bot_thread, instagram_handler
    if bot_thread is None or not bot_thread.is_alive():
        # Pass the shared Instagram handler to the bot
        bot_thread = threading.Thread(target=lambda: run_bot(instagram_handler))
        bot_thread.daemon = True
        bot_thread.start()

def start_keep_alive_thread():
    """Start the keep-alive mechanism in a separate thread."""
    global keep_alive_thread
    if keep_alive_thread is None or not keep_alive_thread.is_alive():
        keep_alive_thread = threading.Thread(target=keep_alive_task)
        keep_alive_thread.daemon = True
        keep_alive_thread.start()

def start_instagram_login_thread():
    """Start Instagram login in a separate thread to avoid blocking the web app."""
    global instagram_login_thread, instagram_handler
    
    def login_task():
        """Attempt to log in to Instagram in a background thread."""
        time.sleep(10)  # Wait a bit to let other services start
        logging.info("Attempting Instagram login in background thread...")
        success = instagram_handler.try_login()
        if success:
            logging.info("Instagram login successful in background thread")
        else:
            logging.warning("Instagram login failed in background thread, will use public access")
    
    if instagram_login_thread is None or not instagram_login_thread.is_alive():
        instagram_login_thread = threading.Thread(target=login_task)
        instagram_login_thread.daemon = True
        instagram_login_thread.start()

# Only start these when run directly, not when imported by the bot workflow
if __name__ == "__main__":
    # Start the bot thread
    start_bot_thread()
    
    # Start the keep-alive thread
    start_keep_alive_thread()
    
    # Start Instagram login thread
    start_instagram_login_thread()
    
    # Start the Flask app
    app.run(host="0.0.0.0", port=5000, debug=True)
# Ping functionality is now handled by the keep_alive_task function