#!/usr/bin/env python
import os
import logging
import time
from pathlib import Path
import telebot
from telebot import types
from instagram_handler import InstagramHandler
from verification import (save_verification_code, is_verification_pending, 
                         is_user_waiting_for_verification, clear_user_verification_state)
from config import TELEGRAM_TOKEN, WELCOME_MESSAGE, HELP_MESSAGE, ERROR_MESSAGES, MAX_TELEGRAM_FILE_SIZE
from account_manager import AccountManager
from account_commands import register_account_commands
from rotation_commands import register_rotation_commands
from flask import Flask, request

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize Telegram bot
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Initialize Instagram handler
instagram = InstagramHandler()

# Webhook configuration
WEBHOOK_URL = "https://a-5jp2.onrender.com"  # REPLACE WITH YOUR ACTUAL RENDER URL
WEBHOOK_PATH = f"/{TELEGRAM_TOKEN}"

# Register account commands (if needed)
admin_ids = [1887983666]  # Replace with actual admin IDs
register_account_commands(bot, instagram.account_manager, admin_ids)
register_rotation_commands(bot, instagram, admin_ids)

@app.route('/')
def home():
    return "Instagram Bot is running!"

@app.route(WEBHOOK_PATH, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    return 'Invalid content type', 403

# --------------------------
# Telegram Handlers (Keep your existing handlers)
# --------------------------

@bot.message_handler(commands=['start'])
def start_command(message):
    """Send welcome message"""
    bot.reply_to(message, WELCOME_MESSAGE)

@bot.message_handler(commands=['help'])
def help_command(message):
    """Send help message"""
    bot.reply_to(message, HELP_MESSAGE, parse_mode='Markdown')

@bot.message_handler(commands=['login'])
def login_command(message):
    """Process Instagram login credentials"""
    # (Keep your existing login handler logic here)

@bot.message_handler(commands=['status'])
def status_command(message):
    """Check authentication status"""
    # (Keep your existing status handler logic here)

@bot.message_handler(commands=['verify'])
def verify_command(message):
    """Process verification code"""
    # (Keep your existing verification handler logic here)

@bot.message_handler(func=lambda message: message.text and message.text.strip().isdigit() and len(message.text.strip()) == 6)
def handle_verification_code(message):
    """Handle verification code input"""
    # (Keep your existing verification code handler)

@bot.message_handler(func=lambda message: True)
def handle_instagram_input(message):
    """Handle Instagram URLs"""
    # (Keep your existing content handling logic)

def send_media_to_user(bot, chat_id, media_items):
    """Send media files"""
    # (Keep your existing media sending logic)

# --------------------------
# Initialization
# --------------------------

def configure_webhook():
    try:
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(
            url=WEBHOOK_URL + WEBHOOK_PATH,
            # certificate=open('/path/to/cert.pem', 'r')  # Add if using SSL
        )
        logger.info("Webhook configured successfully")
    except Exception as e:
        logger.error(f"Error configuring webhook: {e}")

if __name__ == "__main__":
    # Get port from environment variable (required by Render)
    port = int(os.environ.get("PORT", 5000))
    
    # Configure webhook on startup
    configure_webhook()
    
    # Start Flask server
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        use_reloader=False
    )
