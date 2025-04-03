import os
import logging
from flask import Flask, request
from telebot import TeleBot, types
from instagram_handler import InstagramHandler
from account_manager import AccountManager

# Setup
app = Flask(__name__)
bot = TeleBot(os.getenv('TELEGRAM_TOKEN'))
logger = logging.getLogger(__name__)

# Initialize services
instagram = InstagramHandler()
account_manager = AccountManager()

# Connect components
instagram.account_manager = account_manager
instagram.set_telegram_bot(bot)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to_message(message.chat.id, message.message_id, 
                        "🚀 Send me:\n"
                        "- Instagram @username\n"
                        "- Story URL\n"
                        "- Post URL")

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    try:
        input_text = message.text.strip()
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
            bot.reply_to_message(message.chat.id, message.message_id, response)
    except Exception as e:
        logger.error(f"Error: {e}")
        bot.reply_to_message(message.chat.id, message.message_id, "❌ Download failed")

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == "POST":
        update = types.Update.de_json(request.get_json())
        bot.process_new_updates([update])
    return '', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
