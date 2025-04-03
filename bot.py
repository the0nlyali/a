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
from flask import Flask

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# The Instagram handler will be provided by main.py

def run_bot(instagram_handler=None):
    """Start the bot."""
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN not set in environment variables!")
        return
    
    # If no handler is provided, create a new one
    instagram = instagram_handler if instagram_handler else InstagramHandler()
    logger.info(f"Instagram handler authenticated: {instagram.authenticated}")
    
    try:
        logger.info("Starting Instagram Story Bot...")
        bot = telebot.TeleBot(TELEGRAM_TOKEN)
        
        # Define admin user IDs (these users can manage accounts)
        # You can modify this list to include your own user ID
        admin_ids = [1887983666]  # Replace with actual admin Telegram IDs
        
        # Register account management commands
        if hasattr(instagram, 'account_manager'):
            register_account_commands(bot, instagram.account_manager, admin_ids)
            
        # Register automatic rotation commands
        register_rotation_commands(bot, instagram, admin_ids)
        
        @bot.message_handler(commands=['start'])
        def start_command(message):
            """Send a welcome message when the command /start is issued."""
            bot.reply_to(message, WELCOME_MESSAGE)
        
        @bot.message_handler(commands=['help'])
        def help_command(message):
            """Send a help message when the command /help is issued."""
            bot.reply_to(message, HELP_MESSAGE, parse_mode='Markdown')

        @bot.message_handler(commands=['login'])
        def login_command(message):
            """Process Instagram login credentials."""
            # The message should be in format: /login USERNAME PASSWORD
            parts = message.text.strip().split(maxsplit=2)
            
            # Check if message was sent in private chat or group
            if message.chat.type != 'private':
                bot.reply_to(message, "⚠️ For security reasons, please send login credentials in a private chat with the bot, not in a group!")
                return
                
            # Validate format
            if len(parts) != 3:
                bot.reply_to(message, "❌ Please provide your credentials like this: /login username password")
                return
                
            # Extract username and password
            username = parts[1].strip()
            password = parts[2].strip()
            
            # Set the Telegram bot reference in the Instagram handler
            instagram.set_telegram_bot(bot)
            
            # Save credentials in memory and try to login (including chat_id for notifications)
            instagram.set_credentials(username, password, chat_id=message.chat.id)
            bot.reply_to(message, f"✅ Credentials saved for @{username}. Attempting to log in to Instagram...")
            
            # Start a login thread
            import threading
            
            def login_with_notification():
                success = instagram.try_login()
                if not success:
                    # Notify the user about login failure if not already notified
                    try:
                        bot.send_message(
                            message.chat.id, 
                            "❌ Login attempt failed. Instagram might require verification or the credentials are incorrect. "
                            "Check the Instagram app or email for any security notifications."
                        )
                    except Exception as e:
                        logging.error(f"Error sending login failure notification: {e}")
            
            threading.Thread(target=login_with_notification).start()
            
        @bot.message_handler(commands=['status'])
        def status_command(message):
            """Check authentication status with Instagram."""
            if instagram.authenticated:
                username = instagram.username or "Unknown user"
                bot.reply_to(message, f"✅ You are currently logged in to Instagram as @{username}.")
            else:
                bot.reply_to(message, "❌ You are not logged in to Instagram. Use /login username password to log in.")
            
        @bot.message_handler(commands=['verify'])
        def verify_command(message):
            """Process verification code for Instagram login."""
            # Check if there's a pending verification request
            if not is_verification_pending():
                bot.reply_to(message, "❌ There's no pending verification request. This command is used only when Instagram requires verification.")
                return
                
            # The message should be in format: /verify CODE
            parts = message.text.strip().split()
            if len(parts) != 2:
                bot.reply_to(message, "❌ Please provide the verification code like this: /verify 123456")
                return
                
            # Get the code and save it
            code = parts[1].strip()
            if not code.isdigit() or len(code) != 6:
                bot.reply_to(message, "❌ The verification code should be a 6-digit number")
                return
                
            # Save the code
            save_verification_code(code)
            bot.reply_to(message, "✅ Verification code received. Attempting to log in to Instagram...")
        
        @bot.message_handler(func=lambda message: message.text and message.text.strip().isdigit() and len(message.text.strip()) == 6)
        def handle_verification_code(message):
            """Handle verification code when the user is in verification mode."""
            code = message.text.strip()
            chat_id = str(message.chat.id)
            
            # Check if user is waiting for verification
            if is_user_waiting_for_verification(chat_id):
                try:
                    # Save the verification code
                    save_verification_code(code)
                    
                    # Clear the user's verification state
                    clear_user_verification_state(chat_id)
                    
                    # Notify the user with more details
                    bot.reply_to(
                        message, 
                        "✅ Verification code received! I'm attempting to log in to Instagram now...\n\n"
                        "This may take a few moments. I'll let you know when it's done."
                    )
                    
                    # Log for debugging
                    logging.info(f"Verification code received from user {chat_id}: {code[:2]}****")
                except Exception as e:
                    logging.error(f"Error processing verification code: {e}")
                    bot.reply_to(message, "❌ There was an error processing your verification code. Please try again.")
            else:
                # User sent a 6-digit code but is not in verification mode
                # Check if there is a pending verification at all
                if is_verification_pending():
                    # There is a pending verification, but for another user
                    bot.reply_to(
                        message, 
                        "⚠️ It looks like you're trying to provide a verification code, "
                        "but you're not currently in the verification process. "
                        "Please start with /login first."
                    )
                # Otherwise, just treat as a normal message (pass through to the next handler)
        
        @bot.message_handler(func=lambda message: True)
        def handle_instagram_input(message):
            """Handle the user input - should be an Instagram URL or username or post/reel URL."""
            user_input = message.text
            
            # Send a "processing" message
            processing_message = bot.send_message(message.chat.id, "Processing your request... 🔄")
            
            # Get content from Instagram (stories, posts, or reels)
            success, result_message, media_items = instagram.get_content(user_input)
            
            # Update the processing message with the result
            bot.edit_message_text(
                result_message,
                chat_id=message.chat.id,
                message_id=processing_message.message_id
            )
            
            if not success or not media_items:
                return
            
            # Send media items to the user
            send_media_to_user(bot, message.chat.id, media_items)
            
            # Clean up after sending
            instagram.cleanup_files(media_items)
        
        def send_media_to_user(bot, chat_id, media_items):
            """Send the downloaded Instagram media (stories, posts, reels) to the user"""
            for item in media_items:
                file_path = item['path']
                file_size = Path(file_path).stat().st_size
                
                # Check if file is within Telegram limits
                if file_size > MAX_TELEGRAM_FILE_SIZE:
                    bot.send_message(chat_id, ERROR_MESSAGES["media_too_large"])
                    continue
                
                try:
                    # Send as a photo or video based on type
                    if item['type'] == 'photo':
                        with open(file_path, 'rb') as photo:
                            bot.send_photo(chat_id, photo)
                    else:  # video
                        with open(file_path, 'rb') as video:
                            bot.send_video(chat_id, video)
                            
                    # Small delay to avoid flooding
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error sending media: {e}")
                    bot.send_message(chat_id, "Error sending this content. It might be too large or in an unsupported format.")
        
        # Start the bot
        logger.info("Bot is polling...")
        bot.polling()
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        return

# Flask web server to bind to the required port
app = Flask(__name__)

@app.route('/')
def home():
    return "Instagram Downloader Bot is running!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
