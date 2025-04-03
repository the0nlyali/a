#!/usr/bin/env python
import os
import logging
import threading
from flask import Flask, request
from telebot import TeleBot, types
from instagram_handler import InstagramHandler
from account_manager import AccountManager

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize Flask and bot
app = Flask(__name__)
bot = TeleBot(os.environ['TELEGRAM_TOKEN'])

# Setup directories
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# Initialize Instagram handler
instagram = InstagramHandler()
account_manager = AccountManager(data_dir=DATA_DIR)
instagram.account_manager = account_manager

# ================== BOT COMMANDS ==================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🚀 Bot is online! Send an Instagram username/URL to download content.")

@bot.message_handler(commands=['login'])
def login(message):
    try:
        _, username, password = message.text.split(maxsplit=2)
        bot.delete_message(message.chat.id, message.message_id)  # Delete credentials
        instagram.set_credentials(username, password, message.chat.id)
        threading.Thread(target=instagram.try_login).start()
        bot.reply_to(message, "🔐 Login attempt started...")
    except ValueError:
        bot.reply_to(message, "❌ Format: /login username password")

# ================== WEBHOOK CONFIG ==================
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == "POST":
        json_data = request.get_data().decode('utf-8')
        update = types.Update.de_json(json_data)
        bot.process_new_updates([update])
        return '', 200
    return 'Bad request', 400

@app.route('/')
def health_check():
    return "✅ Bot is running at a-mc08.onrender.com"

if __name__ == '__main__':
    # Start with production settings
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
