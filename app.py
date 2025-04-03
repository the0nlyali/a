import os
import logging
import threading
from flask import Flask, request
from telebot import TeleBot, types
from instagram_handler import InstagramHandler  # Your existing handler
from account_manager import AccountManager     # Your existing manager

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
bot = TeleBot('7554095948:AAH1fNQXpidwMK3nqkUCND6a3lwNmRDDbik')

# Initialize your services
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

instagram = InstagramHandler()
account_manager = AccountManager(data_dir=DATA_DIR)
instagram.account_manager = account_manager
instagram.set_telegram_bot(bot)  # Connect bot to Instagram handler

# ===== CORE FUNCTIONALITY =====
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "🚀 Send me Instagram @username or story URL to download")

@bot.message_handler(commands=['login'])
def handle_login(message):
    try:
        _, username, password = message.text.split(maxsplit=2)
        bot.delete_message(message.chat.id, message.message_id)
        instagram.set_credentials(username, password, message.chat.id)
        threading.Thread(target=instagram.try_login).start()
        bot.reply_to(message, "🔐 Login attempt started...")
    except ValueError:
        bot.reply_to(message, "❌ Format: /login username password")

@bot.message_handler(func=lambda m: True)
def handle_instagram_links(message):
    if not message.text:
        return
    
    # Show typing action
    bot.send_chat_action(message.chat.id, 'typing')
    
    try:
        # Process download in background
        threading.Thread(
            target=process_download_request,
            args=(message,)
        ).start()
    except Exception as e:
        logger.error(f"Download failed: {e}")
        bot.reply_to(message, "❌ Download failed. Try again later")

def process_download_request(message):
    """Handles the actual download process"""
    try:
        input_text = message.text.strip()
        
        # Get content from Instagram
        success, result, media_items = instagram.get_content(input_text)
        
        if success:
            # Send media if download succeeded
            send_media_to_user(message.chat.id, media_items)
            instagram.cleanup_files(media_items)
        else:
            bot.reply_to(message, result)
            
    except Exception as e:
        logger.error(f"Processing error: {e}")
        bot.reply_to(message, "⚠️ An error occurred. Please try again")

def send_media_to_user(chat_id, media_items):
    """Sends downloaded media to user"""
    for item in media_items:
        try:
            with open(item['path'], 'rb') as media_file:
                if item['type'] == 'photo':
                    bot.send_photo(chat_id, media_file)
                else:
                    bot.send_video(chat_id, media_file)
        except Exception as e:
            logger.error(f"Failed to send media: {e}")

# ===== WEBHOOK SETUP =====
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == "POST":
        json_data = request.get_json()
        update = types.Update.de_json(json_data)
        bot.process_new_updates([update])
    return '', 200

if __name__ == '__main__':
    logger.info("Starting Instagram Downloader Bot...")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
