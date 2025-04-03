import os
import logging
from flask import Flask, request, jsonify
from telebot import TeleBot, types
from instagram_handler import InstagramHandler

# Configure logging
logging.basicConfig(
    format='[%(asctime)s] %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
bot = TeleBot('7554095948:AAH1fNQXpidwMK3nqkUCND6a3lwNmRDDbik')

# Initialize Instagram handler
instagram = InstagramHandler()
instagram.set_telegram_bot(bot)

@app.route('/')
def home():
    return "Instagram Downloader Bot is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == "POST":
        try:
            json_data = request.get_json()
            logger.info(f"Received update: {json_data}")
            
            update = types.Update.de_json(json_data)
            bot.process_new_updates([update])
            return jsonify({"status": "success"}), 200
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return jsonify({"status": "error"}), 500
    return jsonify({"status": "bad request"}), 400

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🚀 Send me Instagram @username or story URL")

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    try:
        input_text = message.text.strip()
        logger.info(f"Processing: {input_text}")
        
        bot.send_chat_action(message.chat.id, 'typing')
        success, response, media = instagram.get_content(input_text)
        
        if success:
            for item in media:
                with open(item['path'], 'rb') as f:
                    if item['type'] == 'photo':
                        bot.send_photo(message.chat.id, f)
                    else:
                        bot.send_video(message.chat.id, f)
            instagram.cleanup_files(media)
        else:
            bot.reply_to(message, response)
    except Exception as e:
        logger.error(f"Handler error: {e}")
        bot.reply_to(message, "❌ Download failed. Try again later")

if __name__ == '__main__':
    # Set webhook automatically on startup
    from threading import Thread
    def set_webhook():
        import time
        time.sleep(5)  # Wait for server to start
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(
            url='https://a-mc08.onrender.com/webhook',
            max_connections=40
        )
        logger.info("Webhook set successfully")
    
    Thread(target=set_webhook).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
