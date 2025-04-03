#!/usr/bin/env python
import os
import logging
from flask import Flask, request
from telebot import TeleBot, types
from instagram_handler import InstagramHandler
from account_manager import AccountManager
from config import (
    TELEGRAM_TOKEN,
    WELCOME_MESSAGE,
    HELP_MESSAGE,
    ERROR_MESSAGES,
    MAX_TELEGRAM_FILE_SIZE
)

# Initialize Flask and Telegram bot
app = Flask(__name__)
bot = TeleBot(TELEGRAM_TOKEN)
logger = logging.getLogger(__name__)

# Setup directories
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# Initialize Instagram handler
instagram = InstagramHandler()
account_manager = AccountManager(data_dir=DATA_DIR)
instagram.account_manager = account_manager

# ================== TELEGRAM HANDLERS ==================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, WELCOME_MESSAGE)

@bot.message_handler(commands=['help'])
def help(message):
    bot.reply_to(message, HELP_MESSAGE)

@bot.message_handler(commands=['login'])
def login(message):
    try:
        parts = message.text.split()
        if len(parts) == 3:
            _, username, password = parts
            bot.delete_message(message.chat.id, message.message_id)
            instagram.set_credentials(username, password, message.chat.id)
            bot.reply_to(message, "🔐 Attempting login...")
            threading.Thread(target=instagram.try_login).start()
        else:
            bot.reply_to(message, "❌ Format: /login username password")
    except Exception as e:
        logger.error(f"Login error: {e}")
        bot.reply_to(message, "⚠️ Login failed. Try again later.")

# ================== WEBHOOK HANDLER ==================
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_data = request.get_data().decode('utf-8')
        update = types.Update.de_json(json_data)
        bot.process_new_updates([update])
        return '', 200
    return 'Bad request', 400

@app.route('/')
def home():
    return "Instagram Downloader Bot is running!"

if __name__ == '__main__':
    # No automatic webhook setup - you'll set it manually
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
