#!/usr/bin/env python
import os
import logging
import threading
from pathlib import Path
from flask import Flask, request
import telebot
from telebot import types
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
bot = telebot.TeleBot(TELEGRAM_TOKEN)
logger = logging.getLogger(__name__)

# Setup directories
DATA_DIR = Path(__file__).parent / 'data'
DATA_DIR.mkdir(exist_ok=True)

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

# ================== FLASK ROUTES ==================
@app.route('/')
def home():
    return "Instagram Downloader Bot is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        update = types.Update.de_json(request.get_data().decode('utf-8'))
        bot.process_new_updates([update])
        return '', 200
    return 'Bad request', 400

def set_webhook():
    webhook_url = f"https://{os.environ.get('RENDER_APP_NAME')}.onrender.com/webhook"
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    logger.info(f"Webhook set to: {webhook_url}")

if __name__ == '__main__':
    set_webhook()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
