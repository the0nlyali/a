import os
import logging
from flask import Flask, request
from telebot import TeleBot, types
from instagram_handler import InstagramHandler
from account_manager import AccountManager
from verification import VerificationHandler

# Setup
app = Flask(__name__)
bot = TeleBot(os.getenv('TELEGRAM_TOKEN'))

# Initialize services
account_manager = AccountManager()
verification = VerificationHandler()
instagram = InstagramHandler(account_manager, verification)

# Connect components
instagram.set_telegram_bot(bot)
verification.set_telegram_bot(bot)

# Root route
@app.route('/')
def index():
    return "Welcome to the Instagram Downloader Bot!"

# Webhook handler
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == "POST":
        update = types.Update.de_json(request.get_json())
        bot.process_new_updates([update])
    return '', 200

# Command Handlers
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, 
        "📱 *Instagram Downloader Bot*\n\n"
        "1. First /login username password\n"
        "2. Then send @username or story URL\n\n"
        "For 2FA: Just send the 6-digit code when asked",
        parse_mode='Markdown')

@bot.message_handler(commands=['login'])
def login(message):
    try:
        _, username, password = message.text.split(maxsplit=2)
        bot.delete_message(message.chat.id, message.message_id)
        
        # Store credentials
        account_manager.add_account(username, password, message.chat.id)
        
        # Start login process
        instagram.login(username)
        bot.reply_to(message, "🔐 Login process started...")
        
    except ValueError:
        bot.reply_to(message, "❌ Format: /login username password")

# Handle 2FA codes
@bot.message_handler(func=lambda m: verification.is_verification_pending(m.chat.id))
def handle_2fa(message):
    code = message.text.strip()
    if code.isdigit() and len(code) == 6:
        verification.submit_code(message.chat.id, code)
        bot.reply_to(message, "✅ Code received! Completing login...")
    else:
        bot.reply_to(message, "❌ Invalid code. Send 6 digits only")

# Handle Instagram content requests
@bot.message_handler(func=lambda m: True)
def handle_content(message):
    if not message.text:
        return
        
    input_text = message.text.strip()
    bot.send_chat_action(message.chat.id, 'upload_photo')
    
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

if __name__ == '__main__':
    # Set the webhook URL
    webhook_url = "https://a-mc08.onrender.com/webhook"
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
