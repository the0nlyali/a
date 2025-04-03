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

# Initialize Flask app and bot
app = Flask(__name__)
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# The Instagram handler will be provided by main.py
instagram = None

# Define admin user IDs (these users can manage accounts)
admin_ids = [1887983666]  # Replace with actual admin Telegram IDs

# ================== ALL YOUR EXISTING HANDLERS (UNCHANGED) ==================
# (I'm keeping all your existing handler functions exactly as they were)
# Only the initialization and startup logic will change for webhook support

@bot.message_handler(commands=['start'])
def start_command(message):
    """Send a welcome message when the command /start is issued."""
    bot.reply_to(message, WELCOME_MESSAGE)

@bot.message_handler(commands=['help'])
def help_command(message):
    """Send a help message when the command /help is issued."""
    bot.reply_to(message, HELP_MESSAGE, parse_mode='Markdown')

# ... [ALL YOUR OTHER HANDLER FUNCTIONS REMAIN EXACTLY THE SAME] ...

def initialize_bot(instagram_handler=None):
    """Initialize the bot with all handlers"""
    global instagram
    
    # If no handler is provided, create a new one
    instagram = instagram_handler if instagram_handler else InstagramHandler()
    logger.info(f"Instagram handler authenticated: {instagram.authenticated}")
    
    # Register account management commands
    if hasattr(instagram, 'account_manager'):
        register_account_commands(bot, instagram.account_manager, admin_ids)
        
    # Register automatic rotation commands
    register_rotation_commands(bot, instagram, admin_ids)

# Flask route to handle webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    return 'Bad request', 400

def run_bot(instagram_handler=None):
    """Start the bot with webhook configuration for Render"""
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN not set in environment variables!")
        return
    
    initialize_bot(instagram_handler)
    
    try:
        logger.info("Starting Instagram Story Bot with webhook...")
        
        # Webhook configuration
        WEBHOOK_URL = "https://a-5jp2.onrender.com"  # REPLACE WITH YOUR RENDER URL
        
        # Remove previous webhook if any
        bot.remove_webhook()
        time.sleep(1)
        
        # Set new webhook
        bot.set_webhook(
            url=WEBHOOK_URL,
            # certificate=open('webhook_cert.pem', 'r')  # Uncomment if using SSL
        )
        
        logger.info(f"Webhook set to: {WEBHOOK_URL}")
        
        # Start Flask server
        port = int(os.environ.get("PORT", 5000))
        app.run(host='0.0.0.0', port=port)
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        return

@app.route('/')
def home():
    return "Instagram Downloader Bot is running!"

if __name__ == "__main__":
    run_bot()
